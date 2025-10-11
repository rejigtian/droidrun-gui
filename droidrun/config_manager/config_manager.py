from __future__ import annotations

import os
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml

from droidrun.config_manager.path_resolver import PathResolver


# ---------- Helpers / defaults ----------
def _default_config_text() -> str:
    """Generate default config.yaml content with all settings."""
    return """# DroidRun Configuration File
# This file is auto-generated. Edit values as needed.

# === Agent Settings ===
agent:
  # Maximum number of steps per task
  max_steps: 15
  # Enable planning with reasoning mode
  reasoning: false
  # Sleep duration after each action, waits for ui state to be updated (seconds)
  after_sleep_action: 1.0
  # Wait duration for UI to stabilize (seconds)
  wait_for_stable_ui: 0.3
  # Base directory for prompt templates
  prompts_dir: config/prompts

  # CodeAct Agent Configuration
  codeact:
    # Enable vision capabilities (screenshots)
    vision: false
    # System prompt filename (located in prompts_dir/codeact/)
    system_prompt: system.md
    # User prompt filename (located in prompts_dir/codeact/)
    user_prompt: user.md

  # Manager Agent Configuration
  manager:
    # Enable vision capabilities (screenshots)
    vision: false
    # System prompt filename (located in prompts_dir/manager/)
    system_prompt: system.md

  # Executor Agent Configuration
  executor:
    # Enable vision capabilities (screenshots)
    vision: false
    # System prompt filename (located in prompts_dir/executor/)
    system_prompt: system.md

  # App Cards Configuration
  app_cards:
    # Enable app-specific instruction cards
    enabled: true
    # Directory containing app card files
    app_cards_dir: config/app_cards

# === LLM Profiles ===
# Define LLM configurations for each agent type
llm_profiles:
  # Manager: Plans and reasons about task progress
  manager:
    provider: GoogleGenAI
    model: models/gemini-2.5-pro
    temperature: 0.2
    kwargs:
      max_tokens: 8192

  # Executor: Selects and executes atomic actions
  executor:
    provider: GoogleGenAI
    model: models/gemini-2.5-pro
    temperature: 0.1
    kwargs:
      max_tokens: 4096

  # CodeAct: Generates and executes code actions
  codeact:
    provider: GoogleGenAI
    model: models/gemini-2.5-pro
    temperature: 0.2
    kwargs:
      max_tokens: 8192

  # Text Manipulator: Edits text in input fields
  text_manipulator:
    provider: GoogleGenAI
    model: models/gemini-2.5-pro
    temperature: 0.3
    kwargs:
      max_tokens: 4096

  # App Opener: Opens apps by name/description
  app_opener:
    provider: OpenAI
    model: gpt-4o-mini
    temperature: 0.0
    base_url: null
    api_base: null
    kwargs:
      max_tokens: 512
      api_key: YOUR_API_KEY

# === Device Settings ===
device:
  # Default device serial (null = auto-detect)
  serial: null
  # Use TCP communication instead of content provider
  use_tcp: false

# === Telemetry Settings ===
telemetry:
  # Enable anonymous telemetry
  enabled: false

# === Tracing Settings ===
tracing:
  # Enable Arize Phoenix tracing
  enabled: false

# === Logging Settings ===
logging:
  # Enable debug logging
  debug: false
  # Trajectory saving level (none, step, action)
  save_trajectory: none
  rich_text: false
# === Tool Settings ===
tools:
  # Enable drag tool
  allow_drag: false
"""

# Removed: _default_project_config_path() - now using PathResolver


# ---------- Config Schema ----------
@dataclass
class LLMProfile:
    """LLM profile configuration."""
    provider: str = "GoogleGenAI"
    model: str = "models/gemini-2.0-flash-exp"
    temperature: float = 0.2
    base_url: Optional[str] = None
    api_base: Optional[str] = None
    kwargs: Dict[str, Any] = field(default_factory=dict)

    def to_load_llm_kwargs(self) -> Dict[str, Any]:
        """Convert profile to kwargs for load_llm function."""
        result = {
            "model": self.model,
            "temperature": self.temperature,
        }
        # Add optional URL parameters
        if self.base_url:
            result["base_url"] = self.base_url
        if self.api_base:
            result["api_base"] = self.api_base
        # Merge additional kwargs
        result.update(self.kwargs)
        return result


@dataclass
class CodeActConfig:
    """CodeAct agent configuration."""
    vision: bool = False
    system_prompt: str = "system.md"
    user_prompt: str = "user.md"


@dataclass
class ManagerConfig:
    """Manager agent configuration."""
    vision: bool = False
    system_prompt: str = "system.md"


@dataclass
class ExecutorConfig:
    """Executor agent configuration."""
    vision: bool = False
    system_prompt: str = "system.md"


@dataclass
class AppCardConfig:
    """App card configuration."""
    enabled: bool = True
    app_cards_dir: str = "config/app_cards"


@dataclass
class AgentConfig:
    """Agent-related configuration."""
    max_steps: int = 15
    reasoning: bool = False
    after_sleep_action: float = 1.0
    wait_for_stable_ui: float = 0.3
    prompts_dir: str = "config/prompts"

    codeact: CodeActConfig = field(default_factory=CodeActConfig)
    manager: ManagerConfig = field(default_factory=ManagerConfig)
    executor: ExecutorConfig = field(default_factory=ExecutorConfig)
    app_cards: AppCardConfig = field(default_factory=AppCardConfig)

    def get_codeact_system_prompt_path(self) -> str:
        """Get full path to CodeAct system prompt."""
        return f"{self.prompts_dir}/codeact/{self.codeact.system_prompt}"

    def get_codeact_user_prompt_path(self) -> str:
        """Get full path to CodeAct user prompt."""
        return f"{self.prompts_dir}/codeact/{self.codeact.user_prompt}"

    def get_manager_system_prompt_path(self) -> str:
        """Get full path to Manager system prompt."""
        return f"{self.prompts_dir}/manager/{self.manager.system_prompt}"

    def get_executor_system_prompt_path(self) -> str:
        """Get full path to Executor system prompt."""
        return f"{self.prompts_dir}/executor/{self.executor.system_prompt}"


@dataclass
class DeviceConfig:
    """Device-related configuration."""
    serial: Optional[str] = None
    use_tcp: bool = False


@dataclass
class TelemetryConfig:
    """Telemetry configuration."""
    enabled: bool = False


@dataclass
class TracingConfig:
    """Tracing configuration."""
    enabled: bool = False


@dataclass
class LoggingConfig:
    """Logging configuration."""
    debug: bool = False
    save_trajectory: str = "none"
    rich_text: bool = False

@dataclass
class ToolsConfig:
    """Tools configuration."""
    allow_drag: bool = False


@dataclass
class DroidRunConfig:
    """Complete DroidRun configuration schema."""
    agent: AgentConfig = field(default_factory=AgentConfig)
    llm_profiles: Dict[str, LLMProfile] = field(default_factory=dict)
    device: DeviceConfig = field(default_factory=DeviceConfig)
    telemetry: TelemetryConfig = field(default_factory=TelemetryConfig)
    tracing: TracingConfig = field(default_factory=TracingConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    tools: ToolsConfig = field(default_factory=ToolsConfig)

    def __post_init__(self):
        """Ensure default profiles exist."""
        if not self.llm_profiles:
            self.llm_profiles = self._default_profiles()

    @staticmethod
    def _default_profiles() -> Dict[str, LLMProfile]:
        """Get default agent specific LLM profiles."""
        return {
            "manager": LLMProfile(
                provider="GoogleGenAI",
                model="models/gemini-2.5-pro",
                temperature=0.2,
                kwargs={}
            ),
            "executor": LLMProfile(
                provider="GoogleGenAI",
                model="models/gemini-2.5-pro",
                temperature=0.1,
                kwargs={}
            ),
            "codeact": LLMProfile(
                provider="GoogleGenAI",
                model="models/gemini-2.5-pro",
                temperature=0.2,
                kwargs={"max_tokens": 8192 }
            ),
            "text_manipulator": LLMProfile(
                provider="GoogleGenAI",
                model="models/gemini-2.5-pro",
                temperature=0.3,
                kwargs={}
            ),
            "app_opener": LLMProfile(
                provider="GoogleGenAI",
                model="models/gemini-2.5-pro",
                temperature=0.0,
                kwargs={}
            ),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        result = asdict(self)
        # Convert LLMProfile objects to dicts
        result["llm_profiles"] = {
            name: asdict(profile) for name, profile in self.llm_profiles.items()
        }
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DroidRunConfig":
        """Create config from dictionary."""
        # Parse LLM profiles
        llm_profiles = {}
        for name, profile_data in data.get("llm_profiles", {}).items():
            llm_profiles[name] = LLMProfile(**profile_data)

        # Parse agent config with sub-configs
        agent_data = data.get("agent", {})

        codeact_data = agent_data.get("codeact", {})
        codeact_config = CodeActConfig(**codeact_data) if codeact_data else CodeActConfig()

        manager_data = agent_data.get("manager", {})
        manager_config = ManagerConfig(**manager_data) if manager_data else ManagerConfig()

        executor_data = agent_data.get("executor", {})
        executor_config = ExecutorConfig(**executor_data) if executor_data else ExecutorConfig()

        app_cards_data = agent_data.get("app_cards", {})
        app_cards_config = AppCardConfig(**app_cards_data) if app_cards_data else AppCardConfig()

        agent_config = AgentConfig(
            max_steps=agent_data.get("max_steps", 15),
            reasoning=agent_data.get("reasoning", False),
            after_sleep_action=agent_data.get("after_sleep_action", 1.0),
            wait_for_stable_ui=agent_data.get("wait_for_stable_ui", 0.3),
            prompts_dir=agent_data.get("prompts_dir", "config/prompts"),
            codeact=codeact_config,
            manager=manager_config,
            executor=executor_config,
            app_cards=app_cards_config,
        )

        return cls(
            agent=agent_config,
            llm_profiles=llm_profiles,
            device=DeviceConfig(**data.get("device", {})),
            telemetry=TelemetryConfig(**data.get("telemetry", {})),
            tracing=TracingConfig(**data.get("tracing", {})),
            logging=LoggingConfig(**data.get("logging", {})),
            tools=ToolsConfig(**data.get("tools", {})),
        )


# ---------- ConfigManager ----------
class ConfigManager:
    """
    Thread-safe singleton ConfigManager with typed configuration schema.

    Usage:
        from droidrun.config_manager.config_manager import ConfigManager

        # Create config instance (singleton pattern)
        config = ConfigManager()

        # Access typed config objects
        print(config.agent.max_steps)

        # Load all LLMs
        llms = config.load_all_llms()
        manager_llm = llms['manager']
        executor_llm = llms['executor']
        codeact_llm = llms['codeact']

        # Modify and save
        config.save()
    """
    _instance: Optional["ConfigManager"] = None
    _instance_lock = threading.Lock()

    def __new__(cls, path: Optional[str] = None):
        # ensure singleton
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self, path: Optional[str] = None):
        if getattr(self, "_initialized", False):
            return

        self._lock = threading.RLock()

        # Resolution order:
        # 1) Explicit path arg
        # 2) DROIDRUN_CONFIG env var
        # 3) Default "config.yaml" (checks working dir, then project dir)
        if path:
            self.path = PathResolver.resolve(path)
        else:
            env = os.environ.get("DROIDRUN_CONFIG")
            if env:
                self.path = PathResolver.resolve(env)
            else:
                # Default: checks CWD first, then project dir
                self.path = PathResolver.resolve("config.yaml")

        # Initialize with default config
        self._config = DroidRunConfig()
        self.validate_fn: Optional[Callable[[DroidRunConfig], None]] = None

        self._ensure_file_exists()
        self.load_config()

        self._initialized = True

    # ---------------- Typed property access ----------------
    @property
    def agent(self) -> AgentConfig:
        """Access agent configuration."""
        with self._lock:
            return self._config.agent

    @property
    def device(self) -> DeviceConfig:
        """Access device configuration."""
        with self._lock:
            return self._config.device

    @property
    def telemetry(self) -> TelemetryConfig:
        """Access telemetry configuration."""
        with self._lock:
            return self._config.telemetry

    @property
    def tracing(self) -> TracingConfig:
        """Access tracing configuration."""
        with self._lock:
            return self._config.tracing

    @property
    def logging(self) -> LoggingConfig:
        """Access logging configuration."""
        with self._lock:
            return self._config.logging

    @property
    def tools(self) -> ToolsConfig:
        """Access tools configuration."""
        with self._lock:
            return self._config.tools

    @property
    def llm_profiles(self) -> Dict[str, LLMProfile]:
        """Access LLM profiles."""
        with self._lock:
            return self._config.llm_profiles

    # ---------------- LLM Profile Helpers ----------------
    def get_llm_profile(self, profile_name: str) -> LLMProfile:
        """
        Get an LLM profile by name.

        Args:
            profile_name: Name of the profile (fast, mid, smart, custom, etc.)

        Returns:
            LLMProfile object

        Raises:
            KeyError: If profile_name doesn't exist
        """
        with self._lock:
            if profile_name not in self._config.llm_profiles:
                raise KeyError(
                    f"LLM profile '{profile_name}' not found. "
                    f"Available profiles: {list(self._config.llm_profiles.keys())}"
                )

            return self._config.llm_profiles[profile_name]

    def load_llm_from_profile(self, profile_name: str, **override_kwargs):
        """
        Load an LLM using a profile configuration.

        Args:
            profile_name: Name of the profile to use (fast, mid, smart, custom)
            **override_kwargs: Additional kwargs to override profile settings

        Returns:
            Initialized LLM instance

        Example:
            # Use specific profile
            llm = config.load_llm_from_profile("smart")

            # Override specific settings
            llm = config.load_llm_from_profile("fast", temperature=0.5)
        """
        from droidrun.agent.utils.llm_picker import load_llm

        profile = self.get_llm_profile(profile_name)

        # Get kwargs from profile
        kwargs = profile.to_load_llm_kwargs()

        # Override with any provided kwargs
        kwargs.update(override_kwargs)

        # Load the LLM
        return load_llm(provider_name=profile.provider, **kwargs)

    def load_all_llms(self, profile_names: Optional[list[str]] = None, **override_kwargs_per_profile):
        """
        Load multiple LLMs from profiles for different use cases.

        Args:
            profile_names: List of profile names to load. If None, loads agent-specific profiles
            **override_kwargs_per_profile: Dict of profile-specific overrides
                Example: manager={'temperature': 0.1}, executor={'max_tokens': 8000}

        Returns:
            Dict mapping profile names to initialized LLM instances

        Example:
            # Load all agent-specific profiles
            llms = config.load_all_llms()
            manager_llm = llms['manager']
            executor_llm = llms['executor']
            codeact_llm = llms['codeact']

            # Load specific profiles
            llms = config.load_all_llms(['manager', 'executor'])

            # Load with overrides
            llms = config.load_all_llms(
                manager={'temperature': 0.1},
                executor={'max_tokens': 8000}
            )
        """
        from droidrun.agent.utils.llm_picker import load_llm

        if profile_names is None:
            profile_names = ["manager", "executor", "codeact", "text_manipulator", "app_opener"]

        llms = {}
        for profile_name in profile_names:
            profile = self.get_llm_profile(profile_name)

            # Get kwargs from profile
            kwargs = profile.to_load_llm_kwargs()

            # Apply profile-specific overrides if provided
            if profile_name in override_kwargs_per_profile:
                kwargs.update(override_kwargs_per_profile[profile_name])

            # Load the LLM
            llms[profile_name] = load_llm(provider_name=profile.provider, **kwargs)

        return llms

    # ---------------- I/O ----------------
    def _ensure_file_exists(self) -> None:
        parent = self.path.parent
        parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            with open(self.path, "w", encoding="utf-8") as f:
                f.write(_default_config_text())

    def load_config(self) -> None:
        """Load YAML from file into memory. Runs validator if registered."""
        with self._lock:
            if not self.path.exists():
                # create starter file and set default config
                self._ensure_file_exists()
                self._config = DroidRunConfig()
                return

            with open(self.path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data:
                    try:
                        self._config = DroidRunConfig.from_dict(data)
                    except Exception as e:
                        # If parsing fails, use defaults and log warning
                        import logging
                        logger = logging.getLogger("droidrun")
                        logger.warning(f"Failed to parse config, using defaults: {e}")
                        self._config = DroidRunConfig()
                else:
                    self._config = DroidRunConfig()
            self._run_validation()

    def save(self) -> None:
        """Persist current in-memory config to YAML file."""
        with self._lock:
            with open(self.path, "w", encoding="utf-8") as f:
                yaml.dump(self._config.to_dict(), f, sort_keys=False, default_flow_style=False)

    def reload(self) -> None:
        """Reload config from disk (useful when edited externally or via UI)."""
        self.load_config()

    # ---------------- Validation ----------------
    def register_validator(self, fn: Callable[[DroidRunConfig], None]) -> None:
        """
        Register a validation function that takes the config object and raises
        an exception if invalid. The validator is run immediately on registration.
        """
        with self._lock:
            self.validate_fn = fn
            self._run_validation()

    def _run_validation(self) -> None:
        if self.validate_fn is None:
            return
        try:
            self.validate_fn(self._config)
        except Exception as exc:
            raise Exception(f"Validation failed: {exc}") from exc

    def as_dict(self) -> Dict[str, Any]:
        """Return a deep copy of the config dict to avoid accidental mutation."""
        with self._lock:
            import copy
            return copy.deepcopy(self._config.to_dict())

    # Implemented for for config webiu so we can have dropdown prompt selection. but canceled webui plan.
    def list_available_prompts(self, agent_type: str) -> List[str]:
        """
        List all available prompt files for a given agent type.

        Args:
            agent_type: One of "codeact", "manager", "executor"

        Returns:
            List of prompt filenames available in the agent's prompts directory

        Example:
            >>> config.list_available_prompts("manager")
            ['system.md', 'experimental.md', 'minimal.md']
        """
        agent_type = agent_type.lower()
        if agent_type not in ["codeact", "manager", "executor"]:
            raise ValueError(f"Invalid agent_type: {agent_type}. Must be one of: codeact, manager, executor")

        # Resolve prompts directory
        prompts_path = f"{self.agent.prompts_dir}/{agent_type}"
        prompts_dir = PathResolver.resolve(prompts_path)

        if not prompts_dir.exists():
            return []

        # List all .md files in the directory
        return sorted([f.name for f in prompts_dir.glob("*.md")])

    # useful for tests to reset singleton state
    @classmethod
    def _reset_instance_for_testing(cls) -> None:
        with cls._instance_lock:
            cls._instance = None

    def __repr__(self) -> str:
        return f"<ConfigManager path={self.path!s}>"


