from dataclasses import dataclass
from typing import Optional

@dataclass
class Reflection:
    """Represents the result of a reflection analysis on episodic memory."""
    goal_achieved: bool
    summary: str
    advice: Optional[str] = None
    raw_response: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Reflection':
        """Create a Reflection from a dictionary (e.g., parsed JSON)."""
        return cls(
            goal_achieved=data.get('goal_achieved', False),
            summary=data.get('summary', ''),
            advice=data.get('advice'),
            raw_response=data.get('raw_response')
        )