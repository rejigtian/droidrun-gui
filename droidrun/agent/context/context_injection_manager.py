"""
Context Injection Manager - Manages specialized agent personas with dynamic tool and context injection.

This module provides the ContextInjectionManager class that manages different agent personas,
each with specific system prompts, contexts, and tool subsets tailored for specialized tasks.
"""

import logging
from typing import Optional, List
from droidrun.agent.context.agent_persona import AgentPersona
import chromadb
import json

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

    def __init__(self):
        """Initialize the Context Injection Manager with predefined personas."""
        self.client = chromadb.PersistentClient(path="/Users/timo/.droidrun/registry")
        self.collection = self.client.get_collection("personas")

        logger.info(f"🎭 ContextInjectionManager initialized with {0} personas")

    def _load_persona(self, data: str) -> AgentPersona:
        persona = json.loads(data)
        logger.info(f"🎭 Loaded persona: {persona['name']}")
        return AgentPersona(
            name=persona['name'],
            system_prompt=persona['system_prompt'],
            allowed_tools=persona['allowed_tools'],
            description=persona['description'],
            expertise_areas=persona['expertise_areas'],
            user_prompt=persona['user_prompt'],
            required_context=persona['required_context'],
        )

    def get_persona(self, agent_name: str) -> Optional[AgentPersona]:
        """
        Get a specific agent persona by type.

        Args:
            agent_type: The type of agent ("UIExpert" or "AppStarterExpert")

        Returns:
            AgentPersona instance or None if not found
        """
        print(f"🎭 Getting persona: {agent_name}")
        result = self.collection.get(ids=[agent_name])
        return self._load_persona(result.get("documents")[0])

    def list_personas(self, task: str) -> List[AgentPersona]:
        logger.info(f"🎭 Listing personas for task: {task}")
        result = self.collection.query(query_texts=[task], n_results=10)
        logger.info(
            f"🎭 Found {len(result.get('documents'))} personas for task: {task}"
        )
        return [self._load_persona(data) for data in result.get("documents")[0]]
