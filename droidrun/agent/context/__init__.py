"""
Agent Context Module - Provides specialized agent personas and context injection management.

This module contains:
- AgentPersona: Dataclass for defining specialized agent configurations
- ContextInjectionManager: Manager for handling different agent personas and their contexts
"""

from .agent_persona import AgentPersona
from .context_injection_manager import ContextInjectionManager
from .episodic_memory import EpisodicMemory, EpisodicMemoryStep
from .task_manager import Task, TaskManager

__all__ = [
    "AgentPersona",
    "ContextInjectionManager",
    "EpisodicMemory",
    "EpisodicMemoryStep",
    "TaskManager",
    "Task"
]
