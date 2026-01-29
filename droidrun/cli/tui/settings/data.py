"""Settings data model for the TUI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from droidrun.config_manager.config_manager import DroidrunConfig

from droidrun.config_manager.env_keys import load_env_keys, save_env_keys

PROVIDERS = [
    "GoogleGenAI",
    "OpenAI",
    "Anthropic",
    "Ollama",
    "OpenAILike",
]

AGENT_ROLES = ["manager", "executor", "codeact", "scripter"]


@dataclass
class LLMSettings:
    """Per-agent LLM override. Empty strings mean 'use default'."""

    provider: str = ""
    model: str = ""
    temperature: float | None = None


@dataclass
class SettingsData:
    """All TUI settings in one object."""

    # Default LLM
    default_provider: str = "GoogleGenAI"
    default_model: str = "gemini-2.5-flash"
    default_temperature: float = 0.2

    # Per-agent overrides
    agent_llms: dict[str, LLMSettings] = field(default_factory=lambda: {
        role: LLMSettings() for role in AGENT_ROLES
    })

    # API keys
    api_keys: dict[str, str] = field(default_factory=lambda: {
        "google": "",
        "gemini": "",
        "openai": "",
        "anthropic": "",
    })

    # Base URL for OpenAILike / Ollama
    base_url: str = ""

    # Agent
    manager_vision: bool = True
    executor_vision: bool = False
    codeact_vision: bool = False
    max_steps: int = 15

    # Advanced
    use_tcp: bool = False
    prompt_directory: str = ""
    save_trajectory: bool = False
    tracing_enabled: bool = False
    tracing_provider: str = "phoenix"

    @classmethod
    def from_config(cls, config: DroidrunConfig) -> SettingsData:
        """Build settings from a loaded DroidrunConfig."""
        # Read default from the first available profile or fall back
        profiles = config.llm_profiles or {}
        default_profile = profiles.get("codeact") or profiles.get("manager")

        default_provider = default_profile.provider if default_profile else "GoogleGenAI"
        default_model = default_profile.model if default_profile else "gemini-2.5-flash"
        default_temp = default_profile.temperature if default_profile else 0.2

        # Per-agent overrides
        agent_llms: dict[str, LLMSettings] = {}
        for role in AGENT_ROLES:
            profile = profiles.get(role)
            if profile and (profile.provider != default_provider or profile.model != default_model):
                agent_llms[role] = LLMSettings(
                    provider=profile.provider,
                    model=profile.model,
                    temperature=profile.temperature if profile.temperature != default_temp else None,
                )
            else:
                agent_llms[role] = LLMSettings()

        api_keys = load_env_keys()

        # Read base_url from default profile
        base_url = ""
        if default_profile:
            base_url = default_profile.base_url or default_profile.api_base or ""

        return cls(
            default_provider=default_provider,
            default_model=default_model,
            default_temperature=default_temp,
            agent_llms=agent_llms,
            api_keys=api_keys,
            base_url=base_url,
            manager_vision=config.agent.manager.vision,
            executor_vision=config.agent.executor.vision,
            codeact_vision=config.agent.codeact.vision,
            max_steps=config.agent.max_steps,
            use_tcp=config.device.use_tcp,
            prompt_directory="",
            save_trajectory=config.logging.save_trajectory != "none",
            tracing_enabled=config.tracing.enabled,
            tracing_provider=config.tracing.provider,
        )

    def save_keys(self) -> None:
        """Persist API keys to ~/.config/droidrun/.env and set as env vars."""
        save_env_keys(self.api_keys)

    def apply_to_config(self, config: DroidrunConfig) -> None:
        """Apply all TUI settings onto a DroidrunConfig, in place.

        After this, DroidAgent can be created with just `config=config`
        and it will load LLMs from profiles via load_agent_llms → load_llm.
        """
        from droidrun.config_manager.config_manager import LLMProfile

        # LLM profiles — update every profile in the config
        all_roles = list(config.llm_profiles.keys())
        for role in all_roles:
            provider = self._resolve_provider(role)
            model = self._resolve_model(role)
            temp = self._resolve_temperature(role)

            profile = config.llm_profiles[role]
            profile.provider = provider
            profile.model = model
            profile.temperature = temp

            if self.base_url:
                profile.base_url = self.base_url

        # Agent
        config.agent.max_steps = self.max_steps
        config.agent.manager.vision = self.manager_vision
        config.agent.executor.vision = self.executor_vision
        config.agent.codeact.vision = self.codeact_vision

        # Device
        config.device.use_tcp = self.use_tcp

        # Logging
        config.logging.save_trajectory = "action" if self.save_trajectory else "none"

        # Tracing
        config.tracing.enabled = self.tracing_enabled
        config.tracing.provider = self.tracing_provider

    def _resolve_provider(self, role: str) -> str:
        override = self.agent_llms.get(role)
        if override and override.provider:
            return override.provider
        return self.default_provider

    def _resolve_model(self, role: str) -> str:
        override = self.agent_llms.get(role)
        if override and override.model:
            return override.model
        return self.default_model

    def _resolve_temperature(self, role: str) -> float:
        override = self.agent_llms.get(role)
        if override and override.temperature is not None:
            return override.temperature
        return self.default_temperature
