from __future__ import annotations

from types import SimpleNamespace

import pytest

from droidrun.agent.utils import llm_picker
from droidrun.cli import configure_wizard


class _FakeLLM(llm_picker.LLM):
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    @property
    def metadata(self):  # pragma: no cover - unused in these tests
        return None

    def chat(self, messages, **kwargs):  # pragma: no cover - unused in these tests
        raise NotImplementedError

    def complete(self, prompt, formatted=False, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def stream_chat(self, messages, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def stream_complete(self, prompt, **kwargs):  # pragma: no cover
        raise NotImplementedError


def test_load_llm_uses_explicit_provider_map(monkeypatch) -> None:
    imported: list[str] = []

    def fake_import(module_path: str):
        imported.append(module_path)
        return SimpleNamespace(OpenAI=_FakeLLM)

    monkeypatch.setattr(llm_picker.importlib, "import_module", fake_import)

    llm = llm_picker.load_llm("OpenAI", model="gpt-5.4", temperature=0.2)

    assert imported == ["llama_index.llms.openai"]
    assert isinstance(llm, _FakeLLM)
    assert llm.kwargs["model"] == "gpt-5.4"


def test_load_llm_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="Unsupported provider"):
        llm_picker.load_llm("MadeUpProvider", model="anything")


def test_load_llm_passes_custom_model_through_openai_like(monkeypatch) -> None:
    def fake_import(module_path: str):
        assert module_path == "llama_index.llms.openai_like"
        return SimpleNamespace(OpenAILike=_FakeLLM)

    monkeypatch.setattr(llm_picker.importlib, "import_module", fake_import)

    llm = llm_picker.load_llm(
        "OpenAILike",
        model="custom/private-model",
        base_url="https://example.test/v1",
    )

    assert isinstance(llm, _FakeLLM)
    assert llm.kwargs["model"] == "custom/private-model"
    assert llm.kwargs["api_base"] == "https://example.test/v1"
    assert llm.kwargs["is_chat_model"] is True


def test_prompt_model_choice_allows_custom_model_for_known_catalog(monkeypatch) -> None:
    monkeypatch.setattr(configure_wizard, "_select_with_back", lambda *args, **kwargs: "enter_model")
    monkeypatch.setattr(
        configure_wizard,
        "text_prompt",
        lambda *args, **kwargs: "custom-model-id",
    )

    selected = configure_wizard._prompt_model_choice(
        ["gpt-5.4", "gpt-5.4-mini"],
        default_model="gpt-5.4",
    )

    assert selected == "custom-model-id"


def test_prompt_model_choice_returns_catalog_selection(monkeypatch) -> None:
    monkeypatch.setattr(configure_wizard, "_select_with_back", lambda *args, **kwargs: "gpt-5.4-mini")

    selected = configure_wizard._prompt_model_choice(
        ["gpt-5.4", "gpt-5.4-mini"],
        default_model="gpt-5.4",
    )

    assert selected == "gpt-5.4-mini"
