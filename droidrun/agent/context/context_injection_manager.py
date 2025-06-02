"""
Context Injection Manager - Manages specialized agent personas with dynamic tool and context injection.

This module provides the ContextInjectionManager class that manages different agent personas,
each with specific system prompts, contexts, and tool subsets tailored for specialized tasks.
"""

import logging
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass
from droidrun.agent.context.agent_persona import AgentPersona
from droidrun.agent.context.personas import UI_EXPERT, APP_STARTER_EXPERT

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
        self.personas = {
            UI_EXPERT.name: UI_EXPERT,
            APP_STARTER_EXPERT.name: APP_STARTER_EXPERT
        }
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
    
    def get_available_personas(self) -> List[str]:
        """
        Get list of available agent persona names.
        
        Returns:
            List of available persona names
        """
        return list(self.personas.keys())
    
    def inject_context(self, agent_type: str, full_tool_list: Dict[str, Callable], tools_instance: Any) -> Dict[str, Any]:
        """
        Inject specialized context and tools for a specific agent type.
        
        Args:
            agent_type: The type of specialized agent
            full_tool_list: Complete dictionary of available tools
            tools_instance: The tools instance for accessing device methods
            
        Returns:
            Dictionary containing:
            - 'system_prompt': Specialized system prompt
            - 'tool_list': Filtered tool list for this agent
            - 'persona': The AgentPersona instance
            - 'context_info': Additional context information
            
        Raises:
            ValueError: If agent_type is not recognized
        """
        persona = self.get_persona(agent_type)
        if not persona:
            available = ", ".join(self.get_available_personas())
            raise ValueError(f"Unknown agent type '{agent_type}'. Available types: {available}")
        
        # Filter tools based on persona's allowed tools
        filtered_tools = {}
        for tool_name in persona.allowed_tools:
            if tool_name in full_tool_list:
                filtered_tools[tool_name] = full_tool_list[tool_name]
            else:
                logger.warning(f"⚠️ Tool '{tool_name}' not found in full tool list for {agent_type}")
        
        # Add tools instance methods that are always needed
        essential_methods = ["take_screenshot", "get_clickables", "get_phone_state"]
        for method_name in essential_methods:
            if hasattr(tools_instance, method_name):
                # These are not included in filtered_tools as they're accessed via tools_instance
                pass
        
        context_info = {
            "agent_type": agent_type,
            "expertise_areas": persona.expertise_areas,
            "total_tools": len(filtered_tools),
            "allowed_tools": persona.allowed_tools,
            "description": persona.description
        }
        
        logger.info(f"🎭 Injected context for {agent_type}: {len(filtered_tools)} tools available")
        logger.debug(f"   Tools: {list(filtered_tools.keys())}")
        
        return {
            "system_prompt": persona.system_prompt,
            "tool_list": filtered_tools,
            "persona": persona,
            "context_info": context_info
        }
    
    def get_system_prompt_with_tools(self, agent_type: str, tool_descriptions: str) -> str:
        """
        Get the complete system prompt with tool descriptions for a specific agent.
        
        Args:
            agent_type: The type of specialized agent
            tool_descriptions: Formatted descriptions of available tools
            
        Returns:
            Complete system prompt with integrated tool descriptions
        """
        persona = self.get_persona(agent_type)
        if not persona:
            raise ValueError(f"Unknown agent type '{agent_type}'")
        
        # Create the complete system prompt with tool integration
        complete_prompt = f"""{persona.system_prompt}

        **Available Tools for {agent_type}:**
        The following tools are available for you to use in your specialized role:

        {tool_descriptions}

        **Tool Usage Guidelines:**
        - Use tools that align with your specialization
        - Always call `complete(success: bool, reason: str)` when your task is finished
        - Provide clear, descriptive reasoning for your actions

        **Important Notes:**
        - You are part of a multi-agent system working on a larger goal
        - Focus on your specialized area of expertise
        - Coordinate with other agents through the task completion system
        - Always provide detailed feedback about your actions and their outcomes"""

        return complete_prompt
    