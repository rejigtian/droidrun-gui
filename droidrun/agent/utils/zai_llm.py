"""ZAI (GLM) LLM wrapper.

Mirrors OpenClaw's ZAI provider handling:
- Injects ``tool_stream: true`` via ``extra_body``
- Sets ``supportsDeveloperRole: false``, ``supportsUsageInStreaming: false``,
  ``supportsStrictMode: false`` by stripping unsupported OpenAI params
- Flattens multipart content arrays to plain strings
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

from llama_index.core.base.llms.types import (
    ChatMessage,
    ChatResponse,
    ChatResponseAsyncGen,
    ChatResponseGen,
)
from llama_index.core.bridge.pydantic import Field
from llama_index.llms.openai_like import OpenAILike

# Params that ZAI does not support (OpenClaw compat flags)
_ZAI_UNSUPPORTED_PARAMS = {
    "stream_options",
    "parallel_tool_calls",
    "response_format",
    "strict",
    "service_tier",
    "store",
    "reasoning_effort",
    "modalities",
    "audio",
}


# ZAI models with vision support (v = vision variant)
_ZAI_VISION_MODELS = {"glm-5v-turbo", "glm-4.6v", "glm-4.5v"}


def _flatten_content(message_dicts: list, *, strip_images: bool = False) -> list:
    """Flatten multipart content arrays for ZAI compatibility.

    When strip_images is True (text-only models), removes image parts
    and flattens to plain strings. When False (vision models), keeps
    image parts but still flattens text-only messages.
    """
    out = []
    for msg in message_dicts:
        content = msg.get("content")
        if isinstance(content, list):
            if strip_images:
                # Text-only model: drop all non-text parts
                text_parts = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                    elif isinstance(part, str):
                        text_parts.append(part)
                msg = {**msg, "content": "\n".join(text_parts)}
            else:
                # Vision model: flatten only if all parts are text
                has_non_text = any(
                    isinstance(part, dict) and part.get("type") != "text"
                    for part in content
                )
                if not has_non_text:
                    text_parts = []
                    for part in content:
                        if isinstance(part, dict):
                            text_parts.append(part.get("text", ""))
                        elif isinstance(part, str):
                            text_parts.append(part)
                    msg = {**msg, "content": "\n".join(text_parts)}
        out.append(msg)
    return out


def _strip_unsupported(kwargs: dict) -> dict:
    """Remove params ZAI doesn't accept."""
    return {k: v for k, v in kwargs.items() if k not in _ZAI_UNSUPPORTED_PARAMS}


class ZaiLLM(OpenAILike):
    """ZAI-compatible LLM that handles GLM API quirks."""

    context_window: int = Field(default=204800)
    is_chat_model: bool = Field(default=True)

    def __init__(self, **kwargs: Any) -> None:
        additional = kwargs.get("additional_kwargs", {})
        extra_body = additional.get("extra_body", {})
        extra_body.setdefault("tool_stream", True)
        additional["extra_body"] = extra_body
        kwargs["additional_kwargs"] = additional
        super().__init__(**kwargs)

    @classmethod
    def class_name(cls) -> str:
        return "ZaiLLM"

    def _get_model_kwargs(self, **kwargs: Any) -> Dict[str, Any]:
        result = super()._get_model_kwargs(**kwargs)
        return _strip_unsupported(result)

    def _prepare_messages(self, messages: Sequence[ChatMessage]) -> list:
        from llama_index.llms.openai.utils import to_openai_message_dicts

        message_dicts = to_openai_message_dicts(messages, model=self.model)
        strip_images = self.model.lower() not in _ZAI_VISION_MODELS
        return _flatten_content(message_dicts, strip_images=strip_images)

    def _chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponse:
        from llama_index.llms.openai.utils import from_openai_message, from_openai_token_logprobs

        client = self._get_client()
        message_dicts = self._prepare_messages(messages)

        response = client.chat.completions.create(
            messages=message_dicts,
            stream=False,
            **self._get_model_kwargs(**kwargs),
        )

        openai_message = response.choices[0].message
        message = from_openai_message(openai_message, modalities=self.modalities or ["text"])
        logprobs = None
        if response.choices[0].logprobs and response.choices[0].logprobs.content:
            logprobs = from_openai_token_logprobs(response.choices[0].logprobs.content)

        return ChatResponse(
            message=message,
            raw=response,
            logprobs=logprobs,
            additional_kwargs=self._get_response_token_counts(response),
        )

    async def _achat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponse:
        from llama_index.llms.openai.utils import from_openai_message, from_openai_token_logprobs

        aclient = self._get_aclient()
        message_dicts = self._prepare_messages(messages)

        response = await aclient.chat.completions.create(
            messages=message_dicts,
            stream=False,
            **self._get_model_kwargs(**kwargs),
        )

        openai_message = response.choices[0].message
        message = from_openai_message(openai_message, modalities=self.modalities or ["text"])
        logprobs = None
        if response.choices[0].logprobs and response.choices[0].logprobs.content:
            logprobs = from_openai_token_logprobs(response.choices[0].logprobs.content)

        return ChatResponse(
            message=message,
            raw=response,
            logprobs=logprobs,
            additional_kwargs=self._get_response_token_counts(response),
        )

    def _stream_chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponseGen:
        from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCall

        client = self._get_client()
        message_dicts = self._prepare_messages(messages)

        def gen() -> ChatResponseGen:
            content = ""
            tool_calls: List[ChoiceDeltaToolCall] = []
            is_function = False

            for response in client.chat.completions.create(
                messages=message_dicts,
                **self._get_model_kwargs(stream=True, **kwargs),
            ):
                if len(response.choices) > 0:
                    delta = response.choices[0].delta
                else:
                    delta = None

                if delta and delta.tool_calls:
                    is_function = True
                    for tc in delta.tool_calls:
                        idx = tc.index
                        while len(tool_calls) <= idx:
                            tool_calls.append(
                                ChoiceDeltaToolCall(
                                    index=len(tool_calls),
                                    function={"name": "", "arguments": ""},
                                )
                            )
                        if tc.function and tc.function.name:
                            tool_calls[idx].function.name += tc.function.name
                        if tc.function and tc.function.arguments:
                            tool_calls[idx].function.arguments += tc.function.arguments
                        if tc.id:
                            tool_calls[idx].id = tc.id

                role = delta.role if delta else None
                token = delta.content if delta else ""
                content += token or ""

                additional_kwargs: Dict[str, Any] = {}
                if is_function:
                    additional_kwargs["tool_calls"] = tool_calls

                yield ChatResponse(
                    message=ChatMessage(
                        role=role or "assistant",
                        content=content,
                        additional_kwargs=additional_kwargs,
                    ),
                    delta=token or "",
                    raw=response,
                    additional_kwargs=self._get_response_token_counts(response),
                )

        return gen()

    async def _astream_chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponseAsyncGen:
        from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCall

        aclient = self._get_aclient()
        message_dicts = self._prepare_messages(messages)

        async def gen() -> ChatResponseAsyncGen:
            content = ""
            tool_calls: List[ChoiceDeltaToolCall] = []
            is_function = False

            async for response in await aclient.chat.completions.create(
                messages=message_dicts,
                **self._get_model_kwargs(stream=True, **kwargs),
            ):
                if len(response.choices) > 0:
                    delta = response.choices[0].delta
                else:
                    delta = None

                if delta and delta.tool_calls:
                    is_function = True
                    for tc in delta.tool_calls:
                        idx = tc.index
                        while len(tool_calls) <= idx:
                            tool_calls.append(
                                ChoiceDeltaToolCall(
                                    index=len(tool_calls),
                                    function={"name": "", "arguments": ""},
                                )
                            )
                        if tc.function and tc.function.name:
                            tool_calls[idx].function.name += tc.function.name
                        if tc.function and tc.function.arguments:
                            tool_calls[idx].function.arguments += tc.function.arguments
                        if tc.id:
                            tool_calls[idx].id = tc.id

                role = delta.role if delta else None
                token = delta.content if delta else ""
                content += token or ""

                additional_kwargs: Dict[str, Any] = {}
                if is_function:
                    additional_kwargs["tool_calls"] = tool_calls

                yield ChatResponse(
                    message=ChatMessage(
                        role=role or "assistant",
                        content=content,
                        additional_kwargs=additional_kwargs,
                    ),
                    delta=token or "",
                    raw=response,
                    additional_kwargs=self._get_response_token_counts(response),
                )

        return gen()
