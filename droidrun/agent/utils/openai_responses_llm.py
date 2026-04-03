"""OpenAI Responses API LLM for gpt-5.x models with API key auth.

Uses ``client.responses.create()`` instead of ``client.chat.completions.create()``.
Responses API logic extracted from ``OpenAIOAuth`` to support plain API key auth.
"""

from __future__ import annotations

from typing import Any, Sequence

from llama_index.core.base.llms.types import (
    ChatMessage,
    ChatResponse,
    ChatResponseAsyncGen,
    ChatResponseGen,
    LLMMetadata,
    MessageRole,
)
from llama_index.core.bridge.pydantic import Field
from llama_index.llms.openai import OpenAI
from llama_index.llms.openai.utils import to_openai_message_dicts

DEFAULT_API_BASE = "https://api.openai.com/v1"


class OpenAIResponsesLLM(OpenAI):
    """OpenAI LLM that uses the Responses API for gpt-5.x models."""

    api_base: str = Field(default=DEFAULT_API_BASE)

    @classmethod
    def class_name(cls) -> str:
        return "OpenAIResponsesLLM"

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(
            context_window=272000,
            num_output=self.max_tokens or 128000,
            is_chat_model=True,
            is_function_calling_model=False,
            model_name=self.model,
        )

    def _resolve_instructions(self, messages: Sequence[ChatMessage]) -> str:
        """Extract system prompt from messages as instructions."""
        parts: list[str] = []
        for msg in messages:
            if msg.role != MessageRole.SYSTEM:
                continue
            content = msg.content
            if isinstance(content, str) and content.strip():
                parts.append(content.strip())
        return "\n\n".join(parts) if parts else "You are a helpful assistant."

    def _build_responses_payload(
        self, messages: Sequence[ChatMessage],
    ) -> list[dict[str, Any]]:
        """Convert ChatMessages to Responses API input format."""
        non_system = [m for m in messages if m.role != MessageRole.SYSTEM]
        try:
            payload_raw = to_openai_message_dicts(
                non_system,
                model=self.model,
                is_responses_api=True,
                store=False,
            )
        except TypeError:
            payload_raw = to_openai_message_dicts(
                non_system,
                model=self.model,
                is_responses_api=True,
            )

        if isinstance(payload_raw, str):
            payload: list[dict[str, Any]] = [
                {"role": "user", "content": payload_raw}
            ]
        else:
            payload = payload_raw

        normalized: list[dict[str, Any]] = []
        for item in payload:
            role = str(item.get("role", "user"))
            content = item.get("content")

            if isinstance(content, str):
                text_type = "input_text" if role == "user" else "output_text"
                normalized.append(
                    {**item, "content": [{"type": text_type, "text": content}]}
                )
                continue

            if isinstance(content, list):
                fixed: list[Any] = []
                for entry in content:
                    if (
                        isinstance(entry, dict)
                        and entry.get("type") == "text"
                        and isinstance(entry.get("text"), str)
                    ):
                        text_type = (
                            "input_text" if role == "user" else "output_text"
                        )
                        fixed.append({**entry, "type": text_type})
                    else:
                        fixed.append(entry)
                normalized.append({**item, "content": fixed})
                continue

            normalized.append(item)

        return normalized

    def _collect_stream_text_sync(self, events: Any) -> tuple[str, Any]:
        """Collect streamed response text synchronously."""
        text_parts: list[str] = []
        final_response: Any = None
        try:
            for event in events:
                event_type = getattr(event, "type", "")
                if event_type == "response.output_text.delta":
                    delta = getattr(event, "delta", None)
                    if isinstance(delta, str) and delta:
                        text_parts.append(delta)
                elif event_type == "response.completed":
                    final_response = getattr(event, "response", None)
        finally:
            close = getattr(events, "close", None)
            if callable(close):
                close()

        if final_response is not None:
            final_text = getattr(final_response, "output_text", None)
            if isinstance(final_text, str):
                return final_text, final_response

        return "".join(text_parts), final_response

    async def _collect_stream_text_async(self, events: Any) -> tuple[str, Any]:
        """Collect streamed response text asynchronously."""
        text_parts: list[str] = []
        final_response: Any = None
        try:
            async for event in events:
                event_type = getattr(event, "type", "")
                if event_type == "response.output_text.delta":
                    delta = getattr(event, "delta", None)
                    if isinstance(delta, str) and delta:
                        text_parts.append(delta)
                elif event_type == "response.completed":
                    final_response = getattr(event, "response", None)
        finally:
            aclose = getattr(events, "aclose", None)
            if callable(aclose):
                await aclose()

        if final_response is not None:
            final_text = getattr(final_response, "output_text", None)
            if isinstance(final_text, str):
                return final_text, final_response

        return "".join(text_parts), final_response

    def _build_request_kwargs(self, messages: Sequence[ChatMessage]) -> dict[str, Any]:
        """Build the kwargs for responses.create()."""
        return {
            "model": self.model,
            "instructions": self._resolve_instructions(messages),
            "store": False,
            "stream": True,
        }

    def _chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponse:
        client = self._get_client()
        payload = self._build_responses_payload(messages)
        request_kwargs = self._build_request_kwargs(messages)

        events = client.responses.create(input=payload, **request_kwargs)
        text, response = self._collect_stream_text_sync(events)

        return ChatResponse(
            message=ChatMessage(role=MessageRole.ASSISTANT, content=text),
            raw=response,
            additional_kwargs={},
        )

    async def _achat(
        self, messages: Sequence[ChatMessage], **kwargs: Any
    ) -> ChatResponse:
        aclient = self._get_aclient()
        payload = self._build_responses_payload(messages)
        request_kwargs = self._build_request_kwargs(messages)

        events = await aclient.responses.create(input=payload, **request_kwargs)
        text, response = await self._collect_stream_text_async(events)

        return ChatResponse(
            message=ChatMessage(role=MessageRole.ASSISTANT, content=text),
            raw=response,
            additional_kwargs={},
        )

    def _stream_chat(
        self, messages: Sequence[ChatMessage], **kwargs: Any
    ) -> ChatResponseGen:
        client = self._get_client()
        payload = self._build_responses_payload(messages)
        request_kwargs = self._build_request_kwargs(messages)

        def gen() -> ChatResponseGen:
            content = ""
            events = client.responses.create(input=payload, **request_kwargs)
            try:
                for event in events:
                    event_type = getattr(event, "type", "")
                    if event_type == "response.output_text.delta":
                        delta = getattr(event, "delta", "")
                        if delta:
                            content += delta
                            yield ChatResponse(
                                message=ChatMessage(
                                    role=MessageRole.ASSISTANT, content=content
                                ),
                                delta=delta,
                                raw=event,
                            )
                    elif event_type == "response.completed":
                        final = getattr(event, "response", None)
                        final_text = (
                            getattr(final, "output_text", None)
                            if final
                            else None
                        )
                        if isinstance(final_text, str):
                            content = final_text
                        yield ChatResponse(
                            message=ChatMessage(
                                role=MessageRole.ASSISTANT, content=content
                            ),
                            delta="",
                            raw=final,
                        )
            finally:
                close = getattr(events, "close", None)
                if callable(close):
                    close()

        return gen()

    async def _astream_chat(
        self, messages: Sequence[ChatMessage], **kwargs: Any
    ) -> ChatResponseAsyncGen:
        aclient = self._get_aclient()
        payload = self._build_responses_payload(messages)
        request_kwargs = self._build_request_kwargs(messages)

        async def gen() -> ChatResponseAsyncGen:
            content = ""
            events = await aclient.responses.create(
                input=payload, **request_kwargs
            )
            try:
                async for event in events:
                    event_type = getattr(event, "type", "")
                    if event_type == "response.output_text.delta":
                        delta = getattr(event, "delta", "")
                        if delta:
                            content += delta
                            yield ChatResponse(
                                message=ChatMessage(
                                    role=MessageRole.ASSISTANT, content=content
                                ),
                                delta=delta,
                                raw=event,
                            )
                    elif event_type == "response.completed":
                        final = getattr(event, "response", None)
                        final_text = (
                            getattr(final, "output_text", None)
                            if final
                            else None
                        )
                        if isinstance(final_text, str):
                            content = final_text
                        yield ChatResponse(
                            message=ChatMessage(
                                role=MessageRole.ASSISTANT, content=content
                            ),
                            delta="",
                            raw=final,
                        )
            finally:
                aclose = getattr(events, "aclose", None)
                if callable(aclose):
                    await aclose()

        return gen()
