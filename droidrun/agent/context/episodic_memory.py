from dataclasses import dataclass, field
from typing import List, Optional

from droidrun.agent.context.agent_persona import AgentPersona


@dataclass
class EpisodicMemoryStep:
    chat_history: str
    response: str
    timestamp: float
    screenshot: Optional[bytes]

@dataclass
class EpisodicMemory:
    persona: AgentPersona
    steps: List[EpisodicMemoryStep] = field(default_factory=list)
