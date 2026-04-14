"""
Persistent settings storage (JSON file).
Mirrors the desktop app's ConfigManager approach.
"""

import json
import os
from pathlib import Path
from typing import Any

SETTINGS_PATH = Path(__file__).parent.parent / "data" / "settings.json"

_DEFAULTS = {
    "default_provider": "GoogleGenAI",
    "gemini_model": "gemini-2.0-flash",
    "openai_model": "gpt-4o",
    "anthropic_model": "claude-sonnet-4-6",
    "deepseek_model": "deepseek-chat",
    "zhipu_model": "glm-4-plus",
    "ollama_model": "llama3.2",
    "max_steps": 15,
    "google_api_key": "",
    "openai_api_key": "",
    "anthropic_api_key": "",
    "deepseek_api_key": "",
    "zhipu_api_key": "",
    "ollama_base_url": "http://localhost:11434",
}


def _load() -> dict:
    SETTINGS_PATH.parent.mkdir(exist_ok=True)
    if SETTINGS_PATH.exists():
        try:
            with open(SETTINGS_PATH) as f:
                data = json.load(f)
            return {**_DEFAULTS, **data}
        except Exception:
            pass
    return dict(_DEFAULTS)


def _save(data: dict):
    SETTINGS_PATH.parent.mkdir(exist_ok=True)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(data, f, indent=2)


def get_all() -> dict:
    return _load()


def get(key: str, default: Any = None) -> Any:
    return _load().get(key, default)


def update(updates: dict):
    data = _load()
    data.update(updates)
    _save(data)
    # Also propagate API keys to environment variables
    _propagate_env(data)


def _propagate_env(data: dict):
    key_map = {
        "google_api_key": "GOOGLE_API_KEY",
        "openai_api_key": "OPENAI_API_KEY",
        "anthropic_api_key": "ANTHROPIC_API_KEY",
        "deepseek_api_key": "DEEPSEEK_API_KEY",
        "zhipu_api_key": "ZHIPUAI_API_KEY",
    }
    for setting_key, env_key in key_map.items():
        val = data.get(setting_key, "")
        if val:
            os.environ[env_key] = val
