"""
Context Injection Manager - Manages specialized agent personas with dynamic tool and context injection.

This module provides the ContextInjectionManager class that manages different agent personas,
each with specific system prompts, contexts, and tool subsets tailored for specialized tasks.
"""

import logging
from typing import Optional, List
from droidrun.agent.context.agent_persona import AgentPersona

logger = logging.getLogger("droidrun")


class ContextInjectionManager:
    """
    Manages different agent personas with specialized contexts and tool subsets.
    
    This class is responsible for:
    - Defining agent personas with specific capabilities
    - Injecting appropriate system prompts based on agent type
    - Filtering tool lists to match agent specialization
    - Providing context-aware configurations for CodeActAgent instances
    """
    
    def __init__(
            self,
            personas: List[AgentPersona]
        ):
        """Initialize the Context Injection Manager with predefined personas."""

        self.personas = {}

        for persona in personas:
            self.personas[persona.name] = persona

        logger.info(f"🎭 ContextInjectionManager initialized with {len(self.personas)} personas")
    
    def get_persona(self, agent_type: str) -> Optional[AgentPersona]:
        """
        Get a specific agent persona by type.
        
        Args:
            agent_type: The type of agent ("UIExpert" or "AppStarterExpert")
            
        Returns:
            AgentPersona instance or None if not found
        """
        return self.personas.get(agent_type)
    
    def get_all_personas(self) -> List[str]:
        """
        Get list of available agent persona names.
        
        Returns:
            List of available persona names
        """
        return self.personas
    