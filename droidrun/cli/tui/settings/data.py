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
    """Per-agent LLM settings. Always populated with resolved values."""

    provider: str = ""
    model: str = ""
    temperature: float = 0.2


@dataclass
class SettingsData:
    """All TUI settings in one object."""

    # Default LLM
    default_provider: str = "GoogleGenAI"
    default_model: str = "gemini-2.5-flash"
    default_temperature: float = 0.2

    # Per-agent LLM (always filled with resolved values)
    agent_llms: dict[str, LLMSettings] = field(default_factory=lambda: {
        role: LLMSettings() for role in AGENT_ROLES
    })

    # Per-agent custom prompt paths
    agent_prompts: dict[str, str] = field(default_factory=lambda: {
        role: "" for role in AGENT_ROLES
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
    save_trajectory: bool = False
    tracing_enabled: bool = False
    tracing_provider: str = "phoenix"

    @classmethod
    def from_config(cls, config: DroidrunConfig) -> SettingsData:
        """Build settings from a loaded DroidrunConfig."""
        profiles = config.llm_profiles or {}
        default_profile = profiles.get("codeact") or profiles.get("manager")

        default_provider = default_profile.provider if default_profile else "GoogleGenAI"
        default_model = default_profile.model if default_profile else "gemini-2.5-flash"
        default_temp = default_profile.temperature if default_profile else 0.2

        # Per-agent LLMs — always show the resolved value
        agent_llms: dict[str, LLMSettings] = {}
        for role in AGENT_ROLES:
            profile = profiles.get(role)
            agent_llms[role] = LLMSettings(
                provider=profile.provider if profile else default_provider,
                model=profile.model if profile else default_model,
                temperature=profile.temperature if profile else default_temp,
            )

        # Per-agent custom prompt paths
        agent_prompts = {
            "manager": config.agent.manager.system_prompt,
            "executor": config.agent.executor.system_prompt,
            "codeact": config.agent.codeact.system_prompt,
            "scripter": config.agent.scripter.system_prompt,
        }

        api_keys = load_env_keys()

        base_url = ""
        if default_profile:
            base_url = default_profile.base_url or default_profile.api_base or ""

        return cls(
            default_provider=default_provider,
            default_model=default_model,
            default_temperature=default_temp,
            agent_llms=agent_llms,
            agent_prompts=agent_prompts,
            api_keys=api_keys,
            base_url=base_url,
            manager_vision=config.agent.manager.vision,
            executor_vision=config.agent.executor.vision,
            codeact_vision=config.agent.codeact.vision,
            max_steps=config.agent.max_steps,
            use_tcp=config.device.use_tcp,
            save_trajectory=config.logging.save_trajectory != "none",
            tracing_enabled=config.tracing.enabled,
            tracing_provider=config.tracing.provider,
        )

    def save(self) -> None:
        """Persist all settings: API keys to .env and config to config.yaml."""
        from droidrun.config_manager.loader import ConfigLoader

        save_env_keys(self.api_keys)

        try:
            config = ConfigLoader.load()
        except Exception:
            from droidrun.config_manager.config_manager import DroidrunConfig
            config = DroidrunConfig()

        self.apply_to_config(config)
        ConfigLoader.save(config)

    def save_keys(self) -> None:
        """Persist API keys to ~/.config/droidrun/.env and set as env vars."""
        save_env_keys(self.api_keys)

    def apply_to_config(self, config: DroidrunConfig) -> None:
        """Apply all TUI settings onto a DroidrunConfig, in place."""
        from droidrun.config_manager.config_manager import LLMProfile

        # LLM profiles
        for role in list(config.llm_profiles.keys()):
            llm = self.agent_llms.get(role)
            profile = config.llm_profiles[role]
            profile.provider = llm.provider if llm else self.default_provider
            profile.model = llm.model if llm else self.default_model
            profile.temperature = llm.temperature if llm else self.default_temperature
            if self.base_url:
                profile.base_url = self.base_url

        # Per-agent prompt paths
        prompt = self.agent_prompts.get("manager", "")
        if prompt:
            config.agent.manager.system_prompt = prompt
        prompt = self.agent_prompts.get("executor", "")
        if prompt:
            config.agent.executor.system_prompt = prompt
        prompt = self.agent_prompts.get("codeact", "")
        if prompt:
            config.agent.codeact.system_prompt = prompt
        prompt = self.agent_prompts.get("scripter", "")
        if prompt:
            config.agent.scripter.system_prompt = prompt

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
