"""API key lookup and persistence helpers."""

from __future__ import annotations

from dataclasses import dataclass
import os

from dotenv import dotenv_values, set_key, unset_key
from droidrun.config_manager.credential_paths import API_KEY_ENV_FILE

ENV_FILE = API_KEY_ENV_FILE

API_KEY_ENV_VARS = {
    "google": "GOOGLE_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "zai": "ZAI_API_KEY",
    "minimax": "MINIMAX_API_KEY",
}


@dataclass(frozen=True)
class ApiKeySources:
    """API key values from the shell and the saved env file."""

    shell: str = ""
    saved: str = ""


def load_env_key_sources() -> dict[str, ApiKeySources]:
    """Load API keys from shell env vars and the shared env file.

    The returned mapping keeps the two sources separate so callers can decide
    whether to prefer the live shell environment or the persisted file.
    """
    file_values = dotenv_values(ENV_FILE) if ENV_FILE.exists() else {}
    result: dict[str, ApiKeySources] = {}

    for slot, env_var in API_KEY_ENV_VARS.items():
        result[slot] = ApiKeySources(
            shell=os.environ.get(env_var, "") or "",
            saved=(file_values.get(env_var, "") or ""),
        )

    return result


def load_env_keys() -> dict[str, str]:
    """Load API keys. The credentials env file takes precedence over shell env vars.

    Returns:
        Dict mapping slot name (e.g. "google") to key value.
    """
    result: dict[str, str] = {}
    for slot, sources in load_env_key_sources().items():
        result[slot] = sources.saved or sources.shell
    return result


def resolve_env_key(slot: str, source: str = "auto") -> str:
    """Resolve an API key for a provider slot from a specific source.

    Args:
        slot: Provider slot name, e.g. "openai" or "anthropic".
        source: "auto" (shell first, then saved file), "env" (shell only), or
            "file" (saved env file only).
    """
    sources = load_env_key_sources().get(slot, ApiKeySources())
    if source == "env":
        return sources.shell
    if source == "file":
        return sources.saved
    return sources.shell or sources.saved


def save_env_keys(keys: dict[str, str]) -> None:
    """Persist API keys to the shared credentials env file and set them as env vars.

    Args:
        keys: Dict mapping slot name (e.g. "google") to key value.
    """
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not ENV_FILE.exists():
        ENV_FILE.touch()
    for slot, val in keys.items():
        env_var = API_KEY_ENV_VARS.get(slot)
        if not env_var:
            continue
        if val:
            set_key(str(ENV_FILE), env_var, val)
            os.environ[env_var] = val
        else:
            success, _ = unset_key(str(ENV_FILE), env_var, quote_mode="never")
            if success is None:
                pass
            os.environ.pop(env_var, None)
