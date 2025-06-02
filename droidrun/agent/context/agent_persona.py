from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass

@dataclass
class AgentPersona:
    """Represents a specialized agent persona with its configuration."""
    name: str
    system_prompt: str
    user_prompt: str
    description: str
    allowed_tools: List[str]
    required_context: List[str]
    expertise_areas: List[str]

AppAgent = AgentPersona
