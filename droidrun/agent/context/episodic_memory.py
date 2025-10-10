from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class EpisodicMemoryStep:
    chat_history: str
    response: str
    timestamp: float
    screenshot: Optional[bytes]


@dataclass
class EpisodicMemory:
    steps: List[EpisodicMemoryStep] = field(default_factory=list)
