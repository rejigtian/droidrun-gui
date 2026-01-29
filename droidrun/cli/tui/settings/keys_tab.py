"""Keys tab — API key inputs per provider and base URL."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Input, Label, Static

from droidrun.config_manager.env_keys import API_KEY_ENV_VARS
from droidrun.cli.tui.settings.data import SettingsData

# Display names for each key slot
_KEY_LABELS = {
    "google": "Google",
    "gemini": "Gemini",
    "openai": "OpenAI",
    "anthropic": "Anthropic",
}


class KeysTab(Vertical):
    """Content for the Keys tab pane."""

    DEFAULT_CSS = """
    KeysTab {
        padding: 1 2;
    }
    KeysTab .section-title {
        color: #CAD3F6;
        text-style: bold;
        margin-bottom: 1;
    }
    KeysTab .section-hint {
        color: #47475e;
        margin-bottom: 1;
    }
    KeysTab .key-row {
        height: auto;
        margin-bottom: 1;
    }
    KeysTab .key-label {
        width: 14;
        padding-top: 1;
        color: #838BBC;
    }
    KeysTab .key-input {
        width: 1fr;
    }
    KeysTab .separator {
        color: #2e2e4a;
        margin: 1 0;
    }
    KeysTab .field-row {
        height: auto;
        margin-bottom: 1;
    }
    KeysTab .field-label {
        width: 14;
        padding-top: 1;
        color: #838BBC;
    }
    KeysTab .field-input {
        width: 1fr;
    }
    """

    def __init__(self, settings: SettingsData) -> None:
        super().__init__()
        self.settings = settings

    def compose(self) -> ComposeResult:
        yield Static("API Keys", classes="section-title")
        yield Static("saved to ~/.config/droidrun/.env", classes="section-hint")

        for key_name in API_KEY_ENV_VARS:
            label = _KEY_LABELS.get(key_name, key_name.title())
            with Horizontal(classes="key-row"):
                yield Label(label, classes="key-label")
                yield Input(
                    value=self.settings.api_keys.get(key_name, ""),
                    placeholder=API_KEY_ENV_VARS[key_name],
                    password=True,
                    id=f"key-{key_name}",
                    classes="key-input",
                )

        yield Static("─" * 50, classes="separator")
        yield Static("Base URL", classes="section-title")
        yield Static("for OpenAILike / Ollama (e.g. http://localhost:11434)", classes="section-hint")

        with Horizontal(classes="field-row"):
            yield Label("Base URL", classes="field-label")
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
