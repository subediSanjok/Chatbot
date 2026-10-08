from __future__ import annotations

import json
import asyncio
import base64
import importlib
from typing import AsyncIterator

try:
    nodriver = importlib.import_module("zendriver")
    cdp = getattr(nodriver, "cdp", None)
    has_nodriver = True
except (ImportError, Exception):
    try:
        nodriver = importlib.import_module("nodriver")
        cdp = getattr(nodriver, "cdp", None)
        has_nodriver = True
    except (ImportError, Exception):
        nodriver = None
        cdp = None
        has_nodriver = False

from .base_provider import AsyncAuthedProvider, ProviderModelMixin
from ..typing import AsyncResult, Messages, MediaListType
from ..errors import MissingAuthError
from ..providers.response import (
    JsonConversation,
    BaseConversation,
    AuthResult,
    ImageResponse,
    FinishReason,
    SuggestedFollowups,
    TitleGeneration,
    SourceLink,
    ImagePreview,
    Reasoning,
    Sources,
)
from ..requests import get_nodriver_session
from ..image import is_accepted_format
from .helper import get_last_user_message
from .. import debug


class Conversation(JsonConversation):
    conversation_id: str

    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id


def extract_bucket_items(messages: Messages) -> list[dict]:
    """Extract bucket items from messages content."""
    bucket_items = []
    for message in messages:
        if isinstance(message, dict) and isinstance(message.get("content"), list):
            for content_item in message["content"]:
                if isinstance(content_item, dict) and "bucket_id" in content_item and "name" not in content_item:
                    bucket_items.append(content_item)
        if message.get("role") == "assistant":
            bucket_items = []
    return bucket_items


class CopilotSession(AsyncAuthedProvider, ProviderModelMixin):
    parent = "Copilot"
    label = "Microsoft Copilot (Session)"
    url = "https://copilot.microsoft.com"
    
    working = has_nodriver
    use_nodriver = has_nodriver
    active_by_default = True
    use_stream_timeout = False
    
    default_model = "Copilot"
    models = [default_model, "Think Deeper", "Smart (GPT-5)", "Study"]
    model_aliases = {
        "o1": "Think Deeper",
        "gpt-4": default_model,
        "gpt-4o": default_model,
        "gpt-5": "GPT-5",
        "study": "Study",
    }
    lock = asyncio.Lock()

    @classmethod
    async def on_auth_async(cls, *_args, **_kwargs) -> AsyncIterator:
        yield AuthResult()

    @classmethod
    async def create_authed(
        cls,
        _model: str,
        messages: Messages,
        _auth_result: AuthResult,
        proxy: str = None,
        timeout: int = 30,
        prompt: str = None,
        _media: MediaListType = None,
        conversation: BaseConversation = None,
        **_kwargs
    ) -> AsyncResult:
        async with get_nodriver_session(proxy=proxy) as session:
            if prompt is None:
                prompt = get_last_user_message(messages, False)
            if conversation is not None:
                conversation_id = conversation.conversation_id
                url = f"{cls.url}/chats/{conversation_id}"
            else:
                url = cls.url
            page = await session.get(url)
            await page.send(cdp.network.enable())
            queue = asyncio.Queue()

            def handle_ws_message(event):
                if hasattr(event, "response") and event.response.payload_data:
                    queue.put_nowait((event.request_id, event.response.payload_data))

            page.add_handler(
                cdp.network.WebSocketFrameReceived,
                handle_ws_message
            )
            textarea = await page.select("textarea")
            if textarea is not None:
                await textarea.send_keys(prompt)
                await asyncio.sleep(1)
                try:
                    button = await page.select("[data-testid=\"submit-button\"]")
                except TimeoutError:
                    button = None
                if button:
                    await button.click()
                    try:
                        turnstile = await page.select('#cf-turnstile')
                    except TimeoutError:
                        turnstile = None
                    if turnstile:
                        debug.log("Found Element: 'cf-turnstile'")
                        await asyncio.sleep(3)
                        await click_trunstile(page)

        done = False
        msg = None
        image_prompt: str = None
        last_msg = None
        sources = {}
        while not done:
            try:
                _, msg_txt = await asyncio.wait_for(queue.get(), 1 if done else timeout)
                msg = json.loads(msg_txt)
            except Exception:
                break
            last_msg = msg
            if msg.get("event") == "startMessage":
                yield Conversation(msg.get("conversationId"))
            elif msg.get("event") == "appendText":
                yield msg.get("text")
            elif msg.get("event") == "generatingImage":
                image_prompt = msg.get("prompt")
            elif msg.get("event") == "imageGenerated":
                yield ImageResponse(msg.get("url"), image_prompt, {"preview": msg.get("thumbnailUrl")})
            elif msg.get("event") == "done":
                yield FinishReason("stop")
                done = True
            elif msg.get("event") == "suggestedFollowups":
                yield SuggestedFollowups(msg.get("suggestions"))
                break
            elif msg.get("event") == "replaceText":
                yield msg.get("text")
            elif msg.get("event") == "titleUpdate":
                yield TitleGeneration(msg.get("title"))
            elif msg.get("event") == "citation":
                sources[msg.get("url")] = msg
                yield SourceLink(list(sources.keys()).index(msg.get("url")), msg.get("url"))
            elif msg.get("event") == "partialImageGenerated":
                mime_type = is_accepted_format(base64.b64decode(msg.get("content")[:12]))
                yield ImagePreview(f"data:{mime_type};base64,{msg.get('content')}", image_prompt)
            elif msg.get("event") == "chainOfThought":
                yield Reasoning(msg.get("text"))
            elif msg.get("event") == "error":
                raise RuntimeError(f"Error: {msg}")
            elif msg.get("event") not in ["received", "startMessage", "partCompleted", "connected"]:
                debug.log(f"Copilot Message: {msg_txt[:100]}...")
        if not done:
            raise MissingAuthError(f"Invalid response: {last_msg}")
        if sources:
            yield Sources(sources.values())


if has_nodriver:
    async def click_trunstile(page: nodriver.Tab, element='document.getElementById("cf-turnstile")'):
        for _ in range(3):
            size = None
            for idx in range(15):
                size = await page.js_dumps(f'{element}?.getBoundingClientRect()||{{}}')
                debug.log(f"Found size: {size.get('x'), size.get('y')}")
                if "x" not in size:
                    break
                await page.flash_point(size.get("x") + idx * 3, size.get("y") + idx * 3)
                await page.mouse_click(size.get("x") + idx * 3, size.get("y") + idx * 3)
                await asyncio.sleep(2)
            if "x" not in size:
                break
        debug.log("Finished clicking trunstile.")