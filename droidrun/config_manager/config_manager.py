from __future__ import annotations

import os
import threading
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional

import yaml

from droidrun.config_manager.path_resolver import PathResolver
from droidrun.config_manager.safe_execution import SafeExecutionConfig


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
    system_prompt: str = "system.jinja2"
    user_prompt: str = "user.jinja2"
    safe_execution: bool = False


@dataclass
class ManagerConfig:
    """Manager agent configuration."""

    vision: bool = False
    system_prompt: str = "system.jinja2"


@dataclass
class ExecutorConfig:
    """Executor agent configuration."""

    vision: bool = False
    system_prompt: str = "system.jinja2"


@dataclass
class ScripterConfig:
    """Scripter agent configuration."""

    enabled: bool = True
    max_steps: int = 10
    execution_timeout: float = 30.0
    system_prompt_path: str = "system.jinja2"
    safe_execution: bool = False


@dataclass
class AppCardConfig:
    """App card configuration."""

    enabled: bool = True
    mode: str = "local"  # local | server | composite
    app_cards_dir: str = "config/app_cards"
    server_url: Optional[str] = None
    server_timeout: float = 2.0
    server_max_retries: int = 2


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
    scripter: ScripterConfig = field(default_factory=ScripterConfig)
    app_cards: AppCardConfig = field(default_factory=AppCardConfig)

    def get_codeact_system_prompt_path(self) -> str:
        """Get resolved absolute path to CodeAct system prompt."""
        path = f"{self.prompts_dir}/codeact/{self.codeact.system_prompt}"
        return str(PathResolver.resolve(path, must_exist=True))

    def get_codeact_user_prompt_path(self) -> str:
        """Get resolved absolute path to CodeAct user prompt."""
        path = f"{self.prompts_dir}/codeact/{self.codeact.user_prompt}"
        return str(PathResolver.resolve(path, must_exist=True))

    def get_manager_system_prompt_path(self) -> str:
        """Get resolved absolute path to Manager system prompt."""
        path = f"{self.prompts_dir}/manager/{self.manager.system_prompt}"
        return str(PathResolver.resolve(path, must_exist=True))

    def get_executor_system_prompt_path(self) -> str:
        """Get resolved absolute path to Executor system prompt."""
        path = f"{self.prompts_dir}/executor/{self.executor.system_prompt}"
        return str(PathResolver.resolve(path, must_exist=True))

    def get_scripter_system_prompt_path(self) -> str:
        """Get resolved absolute path to Scripter system prompt."""
        path = f"{self.prompts_dir}/scripter/{self.scripter.system_prompt_path}"
        return str(PathResolver.resolve(path, must_exist=True))


@dataclass
class DeviceConfig:
    """Device-related configuration."""

    serial: Optional[str] = None
    use_tcp: bool = False
    platform: str = "android"  # "android" or "ios"


@dataclass
class TelemetryConfig:
    """Telemetry configuration."""

    enabled: bool = True


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
class CredentialsConfig:
    """Credentials configuration."""

    enabled: bool = False
    file_path: str = "credentials.yaml"


@dataclass
class DroidrunConfig:
    """Complete DroidRun configuration schema."""

    agent: AgentConfig = field(default_factory=AgentConfig)
    llm_profiles: Dict[str, LLMProfile] = field(default_factory=dict)
    device: DeviceConfig = field(default_factory=DeviceConfig)
    telemetry: TelemetryConfig = field(default_factory=TelemetryConfig)
    tracing: TracingConfig = field(default_factory=TracingConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    tools: ToolsConfig = field(default_factory=ToolsConfig)
    credentials: CredentialsConfig = field(default_factory=CredentialsConfig)
    safe_execution: SafeExecutionConfig = field(default_factory=SafeExecutionConfig)

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
                kwargs={},
            ),
            "executor": LLMProfile(
                provider="GoogleGenAI",
                model="models/gemini-2.5-pro",
                temperature=0.1,
                kwargs={},
            ),
            "codeact": LLMProfile(
                provider="GoogleGenAI",
                model="models/gemini-2.5-pro",
                temperature=0.2,
                kwargs={},
            ),
            "text_manipulator": LLMProfile(
                provider="GoogleGenAI",
                model="models/gemini-2.5-pro",
                temperature=0.3,
                kwargs={},
            ),
            "app_opener": LLMProfile(
                provider="GoogleGenAI",
                model="models/gemini-2.5-pro",
                temperature=0.0,
                kwargs={},
            ),
            "scripter": LLMProfile(
                provider="GoogleGenAI",
                model="models/gemini-2.5-flash",
                temperature=0.1,
                kwargs={},
            ),
            "structured_output": LLMProfile(
                provider="GoogleGenAI",
                model="models/gemini-2.5-flash",
                temperature=0.0,
                kwargs={},
            ),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        result = asdict(self)
        # Convert LLMProfile objects to dicts
        result["llm_profiles"] = {
            name: asdict(profile) for name, profile in self.llm_profiles.items()
        }
        # safe_execution is already converted by asdict
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DroidrunConfig":
        """Create config from dictionary."""
        # Parse LLM profiles
        llm_profiles = {}
        for name, profile_data in data.get("llm_profiles", {}).items():
            llm_profiles[name] = LLMProfile(**profile_data)

        # Parse agent config with sub-configs
        agent_data = data.get("agent", {})

        codeact_data = agent_data.get("codeact", {})
        codeact_config = (
            CodeActConfig(**codeact_data) if codeact_data else CodeActConfig()
        )

        manager_data = agent_data.get("manager", {})
        manager_config = (
            ManagerConfig(**manager_data) if manager_data else ManagerConfig()
        )

        executor_data = agent_data.get("executor", {})
        executor_config = (
            ExecutorConfig(**executor_data) if executor_data else ExecutorConfig()
        )

        script_data = agent_data.get("scripter", {})
        scripter_config = (
            ScripterConfig(**script_data) if script_data else ScripterConfig()
        )

        app_cards_data = agent_data.get("app_cards", {})
        app_cards_config = (
            AppCardConfig(**app_cards_data) if app_cards_data else AppCardConfig()
        )

        agent_config = AgentConfig(
            max_steps=agent_data.get("max_steps", 15),
            reasoning=agent_data.get("reasoning", False),
            after_sleep_action=agent_data.get("after_sleep_action", 1.0),
            wait_for_stable_ui=agent_data.get("wait_for_stable_ui", 0.3),
            prompts_dir=agent_data.get("prompts_dir", "config/prompts"),
            codeact=codeact_config,
            manager=manager_config,
            executor=executor_config,
            scripter=scripter_config,
            app_cards=app_cards_config,
        )

        # Parse safe_execution config
        safe_exec_data = data.get("safe_execution", {})
        safe_execution_config = (
            SafeExecutionConfig(**safe_exec_data)
            if safe_exec_data
            else SafeExecutionConfig()
        )

        return cls(
            agent=agent_config,
            llm_profiles=llm_profiles,
            device=DeviceConfig(**data.get("device", {})),
            telemetry=TelemetryConfig(**data.get("telemetry", {})),
            tracing=TracingConfig(**data.get("tracing", {})),
            logging=LoggingConfig(**data.get("logging", {})),
            tools=ToolsConfig(**data.get("tools", {})),
            credentials=CredentialsConfig(**data.get("credentials", {})),
            safe_execution=safe_execution_config,
        )

    @classmethod
    def from_yaml(cls, path: str) -> "DroidrunConfig":
        """
        Create config from YAML file.

        Args:
            path: Path to YAML config file (can be relative or absolute)

        Returns:
            DroidrunConfig instance

        Raises:
            FileNotFoundError: If the YAML file doesn't exist
            yaml.YAMLError: If the YAML is malformed

        Example:
            >>> config = DroidrunConfig.from_yaml("config.yaml")
            >>> config = DroidrunConfig.from_yaml("/absolute/path/config.yaml")
        """
        import logging

        logger = logging.getLogger("droidrun")

        if not os.path.exists(path):
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if data:
                try:
                    return cls.from_dict(data)
                except Exception as e:
                    logger.warning(
                        f"Failed to parse config from {path}, using defaults: {e}"
                    )
                    return cls()
            else:
                logger.warning(f"Empty config file at {path}, using defaults")
                return cls()


# ---------- ConfigManager ----------
class ConfigManager:
    """
    Thread-safe singleton ConfigManager with typed configuration schema.

    Usage:
        from droidrun.config_manager.config_manager import ConfigManager
        from droidrun.agent.utils.llm_picker import load_llms_from_profiles

        # Create config instance (singleton pattern)
        config = ConfigManager()

        # Access typed config objects
        print(config.agent.max_steps)

        # Load all LLMs from profiles
        llms = load_llms_from_profiles(config.llm_profiles)
        manager_llm = llms['manager']
        executor_llm = llms['executor']
        codeact_llm = llms['codeact']

        # Load specific profiles with overrides
        llms = load_llms_from_profiles(
            config.llm_profiles,
            profile_names=['manager', 'executor'],
            manager={'temperature': 0.1}
        )

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
        # 3) Default "config.yaml" (checks working dir, then package dir)
        if path:
            self.path = PathResolver.resolve(path)
        else:
            env = os.environ.get("DROIDRUN_CONFIG")
            if env:
                self.path = PathResolver.resolve(env)
            else:
                # Default: checks CWD first, then package dir
                self.path = PathResolver.resolve("config.yaml")

        # Initialize with default config
        self._config = DroidrunConfig()
        self.validate_fn: Optional[Callable[[DroidrunConfig], None]] = None

        self._ensure_file_exists()
        self.load_config()

        self._initialized = True

    # ---------------- Typed property access ----------------
    @property
    def config(self) -> DroidrunConfig:
        """
        Access the internal DroidrunConfig object.

        WARNING: Returns a mutable object. Direct modifications bypass thread safety.
        For thread-safe access, use specific property accessors (agent, device, etc.)
        or use as_dict() to get an immutable copy.
        """
        with self._lock:
            return self._config

    @property
    def agent(self) -> AgentConfig:
        """
        Access agent configuration.

        WARNING: Returns a mutable object. Modifications should be followed by save()
        to persist changes. Thread safety is not guaranteed after the lock is released.
        """
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
    def credentials(self) -> CredentialsConfig:
        """Access credentials configuration."""
        with self._lock:
            return self._config.credentials

    @property
    def llm_profiles(self) -> Dict[str, LLMProfile]:
        """
        Access LLM profiles.

        WARNING: Returns a mutable dictionary. Modifications affect the live config.
        Use get_llm_profile() for read-only access or as_dict() for immutable copy.
        """
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

    # ---------------- I/O ----------------
    def _ensure_file_exists(self) -> None:
        """Create default config file if it doesn't exist."""
        parent = self.path.parent
        parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            # Generate config programmatically from DroidrunConfig defaults
            default_config = DroidrunConfig()
            with open(self.path, "w", encoding="utf-8") as f:
                yaml.dump(
                    default_config.to_dict(),
                    f,
                    sort_keys=False,
                    default_flow_style=False,
                )

    def load_config(self) -> None:
        """
        Load YAML from file into memory. Runs validator if registered.

        On parse failure, falls back to default config with a warning.
        This may mask configuration errors - check logs for warnings.
        """
        with self._lock:
            if not self.path.exists():
                # create starter file and set default config
                self._ensure_file_exists()
                self._config = DroidrunConfig()
                return

            self._config = DroidrunConfig.from_yaml(str(self.path))
            self._run_validation()

    def save(self) -> None:
        """Persist current in-memory config to YAML file."""
        with self._lock:
            with open(self.path, "w", encoding="utf-8") as f:
                yaml.dump(
                    self._config.to_dict(), f, sort_keys=False, default_flow_style=False
                )

    def reload(self) -> None:
        """Reload config from disk (useful when edited externally or via UI)."""
        self.load_config()

    # ---------------- Validation ----------------
    def register_validator(self, fn: Callable[[DroidrunConfig], None]) -> None:
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
            ['system.jinja2', 'experimental.jinja2', 'minimal.jinja2']
        """
        agent_type = agent_type.lower()
        if agent_type not in ["codeact", "manager", "executor", "scripter"]:
            raise ValueError(
                f"Invalid agent_type: {agent_type}. Must be one of: codeact, manager, executor, scripter"
            )

        # Resolve prompts directory
        prompts_path = f"{self.agent.prompts_dir}/{agent_type}"
        prompts_dir = PathResolver.resolve(prompts_path)

        if not prompts_dir.exists():
            return []

        # List all .md files in the directory
        return sorted([f.name for f in prompts_dir.glob("*.jinja2")])

    # useful for tests to reset singleton state
    @classmethod
    def _reset_instance_for_testing(cls) -> None:
        with cls._instance_lock:
            cls._instance = None

    def __repr__(self) -> str:
        return f"<ConfigManager path={self.path!s}>"
