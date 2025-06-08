from dataclasses import dataclass, field
from droidrun.agent.context.agent_persona import AgentPersona
from typing import List

@dataclass
class EpisodicMemoryStep:
    chat_history: str
    response: str
    timestamp: float

@dataclass 
class EpisodicMemory:
    persona: AgentPersona
    steps: List[EpisodicMemoryStep] = field(default_factory=list)