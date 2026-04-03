from __future__ import annotations

from droidrun.config_manager import env_keys
from droidrun.config_manager.config_manager import LLMProfile


def test_load_env_key_sources_keeps_shell_and_saved_separate(
    monkeypatch, tmp_path
) -> None:
    env_file = tmp_path / "api_keys.env"
    env_file.write_text(
        "OPENAI_API_KEY=file-openai\nANTHROPIC_API_KEY=file-anthropic\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(env_keys, "ENV_FILE", env_file)
    monkeypatch.setenv("OPENAI_API_KEY", "shell-openai")

    sources = env_keys.load_env_key_sources()

    assert sources["openai"].shell == "shell-openai"
    assert sources["openai"].saved == "file-openai"
    assert env_keys.load_env_keys()["openai"] == "file-openai"


def test_llm_profile_api_key_source_precedence(monkeypatch, tmp_path) -> None:
    env_file = tmp_path / "api_keys.env"
    env_file.write_text(
        "OPENAI_API_KEY=file-openai\nZAI_API_KEY=file-zai\n", encoding="utf-8"
    )

    monkeypatch.setattr(env_keys, "ENV_FILE", env_file)
    monkeypatch.setenv("OPENAI_API_KEY", "shell-openai")
    monkeypatch.setenv("ZAI_API_KEY", "shell-zai")

    explicit = LLMProfile(
        provider="OpenAI",
        kwargs={"api_key": "explicit-openai"},
    )
    assert explicit.to_load_llm_kwargs()["api_key"] == "explicit-openai"

    env_profile = LLMProfile(provider="OpenAI", api_key_source="env")
    assert env_profile.to_load_llm_kwargs()["api_key"] == "shell-openai"

    file_profile = LLMProfile(provider="OpenAI", api_key_source="file")
    assert file_profile.to_load_llm_kwargs()["api_key"] == "file-openai"

    auto_profile = LLMProfile(provider="OpenAI", api_key_source="auto")
    assert auto_profile.to_load_llm_kwargs()["api_key"] == "shell-openai"

    zai_profile = LLMProfile(
        provider="OpenAILike",
        provider_family="zai",
        api_key_source="env",
    )
    assert zai_profile.to_load_llm_kwargs()["api_key"] == "shell-zai"
