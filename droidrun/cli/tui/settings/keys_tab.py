"""Keys tab — API key inputs per provider and base URL."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import HorizontalGroup, VerticalGroup
from textual.widgets import Input, Label

from droidrun.config_manager.env_keys import API_KEY_ENV_VARS
from droidrun.cli.tui.settings.data import SettingsData
from droidrun.cli.tui.settings.section import Section

_KEY_LABELS = {
    "google": "Google",
    "gemini": "Gemini",
    "openai": "OpenAI",
    "anthropic": "Anthropic",
}


class KeysTab(VerticalGroup):
    """Content for the Keys tab pane."""

    def __init__(self, settings: SettingsData) -> None:
        super().__init__()
        self.settings = settings

    def compose(self) -> ComposeResult:
        with Section("API Keys", hint="saved to ~/.config/droidrun/.env"):
            for key_name in API_KEY_ENV_VARS:
                label = _KEY_LABELS.get(key_name, key_name.title())
                with HorizontalGroup(classes="field-row"):
                    yield Label(label, classes="field-label")
                    yield Input(
                        value=self.settings.api_keys.get(key_name, ""),
                        placeholder=API_KEY_ENV_VARS[key_name],
                        password=True,
                        id=f"key-{key_name}",
                        classes="field-input",
                    )

        with Section("Base URL", hint="for OpenAILike / Ollama"):
            with HorizontalGroup(classes="field-row"):
                yield Label("URL", classes="field-label")
                yield Input(
                    value=self.settings.base_url,
                    placeholder="https://api.example.com/v1",
                    id="base-url",
                    classes="field-input",
                )

    def collect(self) -> dict:
        """Collect current API key values and base URL."""
        keys = {
            key_name: self.query_one(f"#key-{key_name}", Input).value.strip()
            for key_name in API_KEY_ENV_VARS
        }
        return {
            "api_keys": keys,
            "base_url": self.query_one("#base-url", Input).value.strip(),
        }
