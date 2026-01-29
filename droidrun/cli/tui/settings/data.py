"""Settings data model for the TUI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

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

# Maps provider name to the env key slot used by save_env_keys/load_env_keys.
# Providers not listed here store their api_key in kwargs instead.
PROVIDER_ENV_KEY_SLOT: dict[str, str] = {
    "GoogleGenAI": "google",
    "OpenAI": "openai",
    "Anthropic": "anthropic",
}

# Which fields are relevant per provider.
PROVIDER_FIELDS: dict[str, dict[str, Any]] = {
    "GoogleGenAI": {"api_key": True, "base_url": False},
    "OpenAI":      {"api_key": True, "base_url": False},
    "Anthropic":   {"api_key": True, "base_url": False},
    "Ollama":      {"api_key": False, "base_url": True},
    "OpenAILike":  {"api_key": True, "base_url": True},
}


@dataclass
class ProfileSettings:
    """Full LLM profile for one agent role."""

    provider: str = "GoogleGenAI"
    model: str = "models/gemini-2.5-pro"
    temperature: float = 0.2
    api_key: str = ""
    base_url: str = ""
    kwargs: dict[str, str] = field(default_factory=dict)


@dataclass
class SettingsData:
    """All TUI settings in one object."""

    # Per-agent LLM profiles (the real config, no fake global)
    profiles: dict[str, ProfileSettings] = field(default_factory=lambda: {
        role: ProfileSettings() for role in AGENT_ROLES
    })

    # Per-agent custom prompt paths
    agent_prompts: dict[str, str] = field(default_factory=lambda: {
        role: "" for role in AGENT_ROLES
    })

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
        llm_profiles = config.llm_profiles or {}
        env_keys = load_env_keys()

        profiles: dict[str, ProfileSettings] = {}
        for role in AGENT_ROLES:
            lp = llm_profiles.get(role)
            if lp:
                # Determine API key source
                provider = lp.provider
                env_slot = PROVIDER_ENV_KEY_SLOT.get(provider)
                if env_slot:
                    api_key = env_keys.get(env_slot, "")
                elif provider == "OpenAILike":
                    api_key = lp.kwargs.get("api_key", "stub")
                else:
                    api_key = lp.kwargs.get("api_key", "")

                # Build kwargs without api_key (shown separately)
                kwargs = {k: str(v) for k, v in lp.kwargs.items() if k != "api_key"}

                profiles[role] = ProfileSettings(
                    provider=provider,
                    model=lp.model,
                    temperature=lp.temperature,
                    api_key=api_key,
                    base_url=lp.base_url or lp.api_base or "",
                    kwargs=kwargs,
                )
            else:
                profiles[role] = ProfileSettings()

        agent_prompts = {
            "manager": config.agent.manager.system_prompt,
            "executor": config.agent.executor.system_prompt,
            "codeact": config.agent.codeact.system_prompt,
            "scripter": config.agent.scripter.system_prompt,
        }

        return cls(
            profiles=profiles,
            agent_prompts=agent_prompts,
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

        # Save env-based API keys for all cloud providers that have a key set
        env_keys: dict[str, str] = {}
        for role, profile in self.profiles.items():
            env_slot = PROVIDER_ENV_KEY_SLOT.get(profile.provider)
            if env_slot and profile.api_key:
                env_keys[env_slot] = profile.api_key
        if env_keys:
            save_env_keys(env_keys)

        try:
            config = ConfigLoader.load()
        except Exception:
            from droidrun.config_manager.config_manager import DroidrunConfig
            config = DroidrunConfig()

        self.apply_to_config(config)
        ConfigLoader.save(config)

    @staticmethod
    def _build_kwargs(ps: ProfileSettings) -> dict[str, Any]:
        """Parse kwargs string values to typed values and inject api_key for OpenAILike."""
        parsed: dict[str, Any] = {}
        for k, v in ps.kwargs.items():
            if not k:
                continue
            try:
                parsed[k] = int(v)
            except ValueError:
                try:
                    parsed[k] = float(v)
                except ValueError:
                    parsed[k] = v
        if ps.provider == "OpenAILike":
            parsed["api_key"] = ps.api_key or "stub"
        return parsed

    @staticmethod
    def _apply_profile_to_llm(ps: ProfileSettings, cp: Any, update_model: bool = True) -> None:
        """Write a ProfileSettings onto an LLMProfile config object."""
        cp.provider = ps.provider
        if update_model:
            cp.model = ps.model
        cp.temperature = ps.temperature
        if ps.base_url:
            cp.base_url = ps.base_url
            if ps.provider == "OpenAILike":
                cp.api_base = ps.base_url
        else:
            cp.base_url = None
            cp.api_base = None
        cp.kwargs = SettingsData._build_kwargs(ps)

    def apply_to_config(self, config: DroidrunConfig) -> None:
        """Apply all TUI settings onto a DroidrunConfig, in place."""
        for role, ps in self.profiles.items():
            if role not in config.llm_profiles:
                continue
            self._apply_profile_to_llm(ps, config.llm_profiles[role])

        # Propagate codeact settings to hidden roles (text_manipulator, app_opener, structured_output)
        # keeping their existing model (these are usually lighter models)
        codeact_ps = self.profiles.get("codeact")
        if codeact_ps:
            for hidden_role in ("text_manipulator", "app_opener", "structured_output"):
                if hidden_role in config.llm_profiles:
                    self._apply_profile_to_llm(
                        codeact_ps, config.llm_profiles[hidden_role], update_model=False
                    )

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
