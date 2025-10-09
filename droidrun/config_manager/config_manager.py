from __future__ import annotations

import os
import threading
import yaml
from pathlib import Path
from typing import Any, Callable, Optional, Dict
from dataclasses import dataclass, field, asdict

# ---------- Helpers / defaults ----------
def _default_config_text() -> str:
    """Generate default config.yaml content with all settings."""
    return """# DroidRun Configuration File
# This file is auto-generated. Edit values as needed.

# === Agent Settings ===
agent:
  # Maximum number of steps per task
  max_steps: 15
  # Enable vision capabilities per agent (screenshots)
  vision:
    manager: false
    executor: false
    codeact: false
  # Enable planning with reasoning mode
  reasoning: false

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
  # Sleep duration after each action (seconds)
  after_sleep_action: 1.0

# === Telemetry Settings ===
telemetry:
  # Enable anonymous telemetry
  enabled: true

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

# === Tool Settings ===
tools:
  # Enable drag tool
  allow_drag: false
"""

def _default_project_config_path() -> Path:
    """
    Use module-relative resolution: two parents above this file -> project root.
    """
    return Path(__file__).resolve().parents[2] / "config.yaml"


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
class VisionConfig:
    """Per-agent vision settings."""
    manager: bool = False
    executor: bool = False
    codeact: bool = False
    
    def to_dict(self) -> Dict[str, bool]:
        return {"manager": self.manager, "executor": self.executor, "codeact": self.codeact}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VisionConfig":
        """Create VisionConfig from dictionary or bool."""
        if isinstance(data, bool):
            # Support single bool → apply to all agents
            return cls(manager=data, executor=data, codeact=data)
        return cls(
            manager=data.get("manager", False),
            executor=data.get("executor", False),
            codeact=data.get("codeact", False),
        )


@dataclass
class AgentConfig:
    """Agent-related configuration."""
    max_steps: int = 15
    vision: VisionConfig = field(default_factory=VisionConfig)
    reasoning: bool = False
    after_sleep_action: float = 1.0
    wait_for_stable_ui: float = 0.3


@dataclass
class DeviceConfig:
    """Device-related configuration."""
    serial: Optional[str] = None
    use_tcp: bool = False


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
                provider="OpenAI",
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
        # Convert VisionConfig to dict
        if isinstance(result["agent"]["vision"], dict):
            pass  # Already a dict from asdict
        else:
            result["agent"]["vision"] = self.agent.vision.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DroidRunConfig":
        """Create config from dictionary."""
        # Parse LLM profiles
        llm_profiles = {}
        for name, profile_data in data.get("llm_profiles", {}).items():
            llm_profiles[name] = LLMProfile(**profile_data)
        
        # Parse agent config with vision
        agent_data = data.get("agent", {})
        vision_data = agent_data.get("vision", {})
        vision_config = VisionConfig.from_dict(vision_data)
        
        agent_config = AgentConfig(
            max_steps=agent_data.get("max_steps", 15),
            vision=vision_config,
            reasoning=agent_data.get("reasoning", False),
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
        from droidrun.config_manager import config
        
        # Access typed config objects
        print(config.agent.max_steps)
        
        # Load all 3 LLMs
        llms = config.load_all_llms()
        fast_llm = llms['fast']
        mid_llm = llms['mid']
        smart_llm = llms['smart']
        
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

        # resolution order:
        # 1) explicit path arg
        # 2) DROIDRUN_CONFIG env var
        # 3) module-relative project_root/config.yaml (two parents up)
        if path:
            self.path = Path(path).expanduser().resolve()
        else:
            env = os.environ.get("DROIDRUN_CONFIG")
            if env:
                self.path = Path(env).expanduser().resolve()
            else:
                self.path = _default_project_config_path().resolve()

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

    # useful for tests to reset singleton state
    @classmethod
    def _reset_instance_for_testing(cls) -> None:
        with cls._instance_lock:
            cls._instance = None

    def __repr__(self) -> str:
        return f"<ConfigManager path={self.path!s}>"


# ---------- global singleton ----------
config = ConfigManager()