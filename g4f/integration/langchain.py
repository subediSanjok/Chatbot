from __future__ import annotations

import importlib
from typing import Any, Dict
from pydantic import Field
from g4f.client import AsyncClient, Client
from g4f.client.stubs import ChatCompletionMessage
from g4f.errors import MissingRequirementsError

try:
    _openai_module = importlib.import_module("langchain_community.chat_models.openai")
    ChatOpenAI = getattr(_openai_module, "ChatOpenAI")
    BaseMessage = getattr(_openai_module, "BaseMessage")
    convert_message_to_dict = getattr(_openai_module, "convert_message_to_dict")
    has_langchain = True
except (ImportError, Exception):
    has_langchain = False
    _openai_module = None
    ChatOpenAI = object
    BaseMessage = object

    def convert_message_to_dict(message: Any) -> dict:
        return {}


def new_convert_message_to_dict(message: BaseMessage) -> dict:
    message_dict: Dict[str, Any]
    if isinstance(message, ChatCompletionMessage):
        message_dict = {"role": message.role, "content": message.content}
        if message.tool_calls is not None:
            message_dict["tool_calls"] = [{
                "id": tool_call.id,
                "type": tool_call.type,
                "function": tool_call.function
            } for tool_call in message.tool_calls]
            if message_dict["content"] == "":
                message_dict["content"] = None
    else:
        message_dict = convert_message_to_dict(message)
    return message_dict


if has_langchain and _openai_module is not None:
    setattr(_openai_module, "convert_message_to_dict", new_convert_message_to_dict)


class ChatAI(ChatOpenAI):
    model_name: str = Field(default="gpt-4o", alias="model")

    def __init__(self, *args, **kwargs):
        if not has_langchain:
            raise MissingRequirementsError('Install "langchain-community" to use ChatAI')
        super().__init__(*args, **kwargs)

    @classmethod
    def validate_environment(cls, values: dict) -> dict:
        if not has_langchain:
            raise MissingRequirementsError('Install "langchain-community" to use ChatAI')
        client_params = {
            "api_key": values["api_key"] if "api_key" in values else None,
            "provider": values["model_kwargs"]["provider"] if "provider" in values["model_kwargs"] else None,
        }
        values["client"] = Client(**client_params).chat.completions
        values["async_client"] = AsyncClient(
            **client_params
        ).chat.completions
        return values