from __future__ import annotations

import importlib
from typing import Optional, Any
from functools import partial
from dataclasses import dataclass, field
from g4f.errors import MissingRequirementsError
from ..client import AsyncClient, ChatCompletion

try:
    _pydantic_ai = importlib.import_module("pydantic_ai")
    ModelResponsePart = getattr(_pydantic_ai, "ModelResponsePart")
    ThinkingPart = getattr(_pydantic_ai, "ThinkingPart")
    ToolCallPart = getattr(_pydantic_ai, "ToolCallPart")

    _pydantic_ai_models = importlib.import_module("pydantic_ai.models")
    Model = getattr(_pydantic_ai_models, "Model")
    ModelResponse = getattr(_pydantic_ai_models, "ModelResponse")
    KnownModelName = getattr(_pydantic_ai_models, "KnownModelName")
    infer_model = getattr(_pydantic_ai_models, "infer_model")

    _pydantic_ai_usage = importlib.import_module("pydantic_ai.usage")
    RequestUsage = getattr(_pydantic_ai_usage, "RequestUsage")

    _pydantic_ai_openai = importlib.import_module("pydantic_ai.models.openai")
    OpenAIChatModel = getattr(_pydantic_ai_openai, "OpenAIChatModel")
    OpenAISystemPromptRole = getattr(_pydantic_ai_openai, "OpenAISystemPromptRole")
    _now_utc = getattr(_pydantic_ai_openai, "_now_utc")
    split_content_into_text_and_thinking = getattr(_pydantic_ai_openai, "split_content_into_text_and_thinking")
    replace = getattr(_pydantic_ai_openai, "replace")
    _pydantic_ai_openai.NOT_GIVEN = None
    has_pydantic_ai = True
except (ImportError, Exception):
    has_pydantic_ai = False

    class ModelResponsePart:
        pass

    class ThinkingPart:
        def __init__(self, *args, **kwargs):
            pass

    class ToolCallPart:
        def __init__(self, *args, **kwargs):
            pass

    class Model:
        pass

    class ModelResponse:
        def __init__(self, *args, **kwargs):
            pass

    KnownModelName = str
    infer_model = None

    class RequestUsage:
        def __init__(self, *args, **kwargs):
            pass

    OpenAIChatModel = object
    OpenAISystemPromptRole = object

    def _now_utc():
        return None

    def split_content_into_text_and_thinking(*args, **kwargs):
        return []

    def replace(*args, **kwargs):
        return None

    _pydantic_ai_models = None


@dataclass(init=False)
class AIModel(OpenAIChatModel):
    """A model that uses the G4F API."""

    client: AsyncClient = field(repr=False)
    system_prompt_role: Any = field(default=None)

    _model_name: str = field(repr=False)
    _provider: str = field(repr=False)
    _system: Optional[str] = field(repr=False)

    def __init__(
        self,
        model_name: str,
        provider: str | None = None,
        *,
        system_prompt_role: Any = None,
        system: str | None = 'g4f',
        **kwargs
    ):
        """Initialize an AI model.

        Args:
            model_name: The name of the AI model to use.
            system_prompt_role: The role to use for the system prompt message.
            system: The model provider used, defaults to 'g4f'.
        """
        if not has_pydantic_ai:
            raise MissingRequirementsError('Install "pydantic_ai" to use AIModel')
        self._model_name = model_name
        self._provider = getattr(provider, '__name__', provider)
        self.client = AsyncClient(provider=provider, **kwargs)
        self.system_prompt_role = system_prompt_role
        self._system = system

    def name(self) -> str:
        if self._provider:
            return f'g4f:{self._provider}:{self._model_name}'
        return f'g4f:{self._model_name}'

    def _process_response(self, response: ChatCompletion | str) -> Any:
        """Process a non-streamed response, and prepare a message to return."""
        if not has_pydantic_ai:
            raise MissingRequirementsError('Install "pydantic_ai" to use AIModel')
        choice = response.choices[0]
        items: list[Any] = []

        if reasoning := getattr(choice.message, 'reasoning', None):
            items.append(ThinkingPart(id='reasoning', content=reasoning, provider_name=self._system))

        if choice.message.content:
            items.extend(
                (replace(part, id='content', provider_name=self._system) if isinstance(part, ThinkingPart) else part)
                for part in split_content_into_text_and_thinking(choice.message.content, self.profile.thinking_tags)
            )
        if choice.message.tool_calls is not None:
            for c in choice.message.tool_calls:
                items.append(ToolCallPart(c.function.name, c.function.arguments, tool_call_id=c.id))
        usage = RequestUsage(
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
        )

        return ModelResponse(
            parts=items,
            usage=usage,
            model_name=response.model,
            timestamp=_now_utc(),
            provider_details=None,
            provider_response_id=response.id,
            provider_name=self._provider,
            finish_reason=choice.finish_reason,
        )


def new_infer_model(model: Any, api_key: str = None) -> Any:
    if not has_pydantic_ai:
        raise MissingRequirementsError('Install "pydantic_ai" to use infer_model')
    if isinstance(model, Model):
        return model
    if isinstance(model, str) and model.startswith("g4f:"):
        model_str = model[4:]
        if ":" in model_str:
            provider, model_str = model_str.split(":", 1)
            return AIModel(model_str, provider=provider, api_key=api_key)
        return AIModel(model_str)
    return infer_model(model)


def patch_infer_model(api_key: str | None = None):
    if has_pydantic_ai and _pydantic_ai_models is not None:
        _pydantic_ai_models.infer_model = partial(new_infer_model, api_key=api_key)