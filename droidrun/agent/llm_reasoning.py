"""
LLM Reasoning - Provides reasoning capabilities for the ReAct agent.

This module handles the integration with LLM providers to generate reasoning steps.
"""

import json
import re
import textwrap
import logging
from typing import Any, Dict, List, Optional

from .providers import (
    OpenAIProvider,
    AnthropicProvider,
    GeminiProvider,
    OllamaProvider
)

# Set up logger
logger = logging.getLogger("droidrun")

# Simple token estimator (very rough approximation)
def estimate_tokens(text: str) -> int:
    """Estimate number of tokens in a string.
    
    This is a very rough approximation based on the rule of thumb that
    1 token is approximately 4 characters for English text.
    
    Args:
        text: Input text
    
    Returns:
        Estimated token count
    """
    if not text:
        return 0
    return len(text) // 4 + 1  # Add 1 to be safe

class LLMReasoner:
    """LLM-based reasoner for ReAct agent."""
    
    def __init__(
        self,
        llm_provider: str = "openai",
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2000,
        vision: bool = False,
        base_url: Optional[str] = None
    ):
        """Initialize the LLM reasoner.
        
        Args:
            llm_provider: LLM provider ('openai', 'anthropic', 'gemini', or 'ollama'). 
            If model_name starts with 'gemini-', provider will be set to 'gemini' automatically.
            model_name: Model name to use
            api_key: API key for the LLM provider
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            vision: Whether vision capabilities (screenshot) are enabled
            base_url: Optional base URL for the API (mainly used for Ollama)
        """
        # Auto-detect Gemini models
        if model_name and model_name.startswith("gemini-"):
            llm_provider = "gemini"
            
        self.llm_provider = llm_provider.lower()
        
        # Initialize the appropriate provider
        provider_class = {
            "openai": OpenAIProvider,
            "anthropic": AnthropicProvider,
            "gemini": GeminiProvider,
            "ollama": OllamaProvider
        }.get(self.llm_provider)
        
        if not provider_class:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")
        
        self.provider = provider_class(
            model_name=model_name,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            vision=vision,
            base_url=base_url
        )
    
    def get_token_usage_stats(self) -> Dict[str, int]:
        """Get current token usage statistics.
        
        Returns:
            Dictionary with token usage statistics
        """
        return self.provider.get_token_usage_stats()
    
    async def reason(
        self,
        goal: str,
        history: List[Dict[str, Any]],
        available_tools: Optional[List[str]] = None,
        current_ui_state: Optional[str] = None,
        current_phone_state: Optional[str] = None,
        screenshot_data: Optional[bytes] = None,
        memories: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Generate a reasoning step using the LLM.
        
        Args:
            goal: The automation goal
            history: List of previous steps as dictionaries
            available_tools: Optional list of available tool names
            screenshot_data: Optional bytes containing the latest screenshot
            memories: Optional list of memories from the memory store
        
        Returns:
            Dictionary with next reasoning step, including thought,
            action, and any parameters
        """
        # Print current token usage stats before making the call
        logger.info(f"Token usage before API call: {self.get_token_usage_stats()}")
        
        # Construct the prompt
        system_prompt = self._create_system_prompt(
            goal,
            available_tools,
            history,
            memories,
            current_ui_state,
            current_phone_state
        )
        user_prompt = self._create_user_prompt(goal)
        
        try:
            # Call the provider
            response = await self.provider.generate_response(
                textwrap.dedent(system_prompt),
                textwrap.dedent(user_prompt),
                screenshot_data
            )

            logger.info(f"Prompts:\nSystem: {system_prompt}\nUser: {user_prompt}")
            # Parse the response
            result = self._parse_response(response)
            
            # Print updated token usage stats after the call
            logger.info(f"Token usage after API call: {self.get_token_usage_stats()}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in LLM reasoning: {e}")
            # Return a fallback response
            return {
                "thought": f"LLM reasoning error: {e}",
                "action": "error",
                "parameters": {}
            }
    
    def _create_system_prompt(self,
        goal: str,
        available_tools: Optional[List[str]] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        memories: Optional[List[Dict[str, str]]] = None,
        current_ui_state: Optional[str] = None,
        current_phone_state: Optional[str] = None,
        ) -> str:
        """Create the system prompt for the LLM.
        
        Args:
            available_tools: Optional list of available tool names   
            history: List of previous steps
            memories: Optional list of memories from the memory store
        
        Returns:
            System prompt string
        """
        # Base system prompt
        prompt =f"""
        You are Droidrun - the best assistant for an Android phone there is.
        Your task is to control an Android device to achieve a specified goal that is given to you.
        You always do your very best and do everything in your power to achieve the goal you are given.
        You are completely on your own. But you like to be alone.
        Droidrun is always alone and achieves his goal with the most efficency.
        Just recently you crushed a benchmark for Android Phones by achieving a remarkable 98-Percent success rate.
        However that is not enough as the following goal will give you the 100-Percent success rate and will mark you as the best Agent in the world of all time.

        Your goal is the following:
        {goal}
        
        You always follow these guidelines:

        1. Analyze the current screen state from the UI state getting all UI elements
        2. Think step-by-step to plan your actions
        3. Choose the most appropriate tool for each step
        4. Return your response in JSON format with the following fields:
        - thought: Your detailed reasoning about the current state and what to do next
        - action: The name of the tool to execute (use EXACT tool name without any parentheses)
        - parameters: A dictionary of parameters to pass to the tool

        IMPORTANT: The following sections are for your understanding.
        tools - Describe what tools you can call to take action
        memories - Describe what important things you have remembered from previous steps 
        history - Describe what actions and observations you have already made
        phone_state - Describe what state the phone is currently in
        ui_structure - Describe the current UI structure of the current Android screen
        \
        """

        prompt += "<tools>\n"
        prompt += self._add_tools_to_prompt(available_tools)
        prompt += "</tools>\n\n"

        prompt += "<memories>\n"
        prompt += self._add_memories_to_prompt(memories)
        prompt += "</memories>\n\n"

        prompt += "<history>\n"
        prompt += self._add_history_to_prompt(history)
        prompt += "</history>\n\n"

        prompt += "<phone_state>\n"
        prompt += f"{current_phone_state}"
        prompt += "</phone_state>\n\n"

        prompt += "<ui_structure>\n"
        prompt += f"{current_ui_state}"
        prompt += "</ui_structure>"

        return prompt

        
    
    def _create_user_prompt(
        self,
        goal: str
    ) -> str:
        """Create the user prompt for the LLM.
        
        Args:
            goal: The automation goal
        
        Returns:
            User prompt string
        """
        prompt = f"Goal: {goal}\n\n"
        prompt += "Based on the current state, what's your next action? Return your response in JSON format."
        
        return prompt


    def _add_tools_to_prompt(self, available_tools: Optional[List[str]]) -> str:
            """Add available tools information to the prompt.
            
            Args:
                available_tools: Optional list of available tool names
                
            Returns:
                String containing tools documentation
            """
            from .tool_docs import tool_docs
            if not available_tools:
                return ""
                
            # Add take_screenshot tool only if vision is enabled
            if self.provider.vision:
                available_tools.append("take_screenshot")
                
            tools_prompt = ""
            
            # Only include docs for available tools
            for tool in available_tools:
                if tool in tool_docs:
                    tools_prompt += f"- {tool_docs[tool]}\n"
                else:
                    tools_prompt += f"- {tool} (parameters unknown)\n"
                    
            return tools_prompt
    
    def _add_memories_to_prompt(self, memories: Optional[List[Dict[str, str]]]) -> str:
        """Add memories information to the prompt.
        
        Args:
            memories: Optional list of memories from the memory store
            
        Returns:
            String containing formatted memories
        """
        if not memories or len(memories) == 0:
            return ""
            
        memories_prompt = ""
        for i, memory in enumerate(memories, 1):
            memories_prompt += f"{i}. {memory['content']}\n"
        
        return memories_prompt
    

    def _add_history_to_prompt(self, history: Optional[List[Dict[str, Any]]]) -> str:
        """Add recent history information to the prompt.
        
        Args:
            history: Optional list of previous steps
            
        Returns:
            String containing formatted history
        """
        if not history:
            return ""
            
        # Filter out GOAL type steps
        filtered_history = [step for step in history if step.get("type", "").upper() != "GOAL"]
            
        # Get only the last 5 steps (if available)
        recent_history = filtered_history[-10:] if len(filtered_history) >= 10 else filtered_history
        
        history_prompt = ""
        # Add the recent history steps
        for step in recent_history:
            step_type = step.get("type", "").upper()
            content = step.get("content", "")
            step_number = step.get("step_number", 0)
            history_prompt += f"Step {step_number} - {step_type}: {content}\n"
        
        history_prompt += "\n"
        return history_prompt
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse the LLM response into a structured format.
        
        Args:
            response: LLM response string
        
        Returns:
            Dictionary with parsed response
        """
        try:
            # Try to parse as JSON
            data = json.loads(response)
            
            # Ensure required fields are present
            if "thought" not in data:
                data["thought"] = "No thought provided"
            if "action" not in data:
                data["action"] = "no_action"
            if "parameters" not in data:
                data["parameters"] = {}
                
            return data
        except json.JSONDecodeError:
            # If not valid JSON, try to extract fields using regex
            thought_match = re.search(r'thought["\s:]+([^"]+)', response)
            action_match = re.search(r'action["\s:]+([^",\n]+)', response)
            params_match = re.search(r'parameters["\s:]+({.+})', response, re.DOTALL)
            
            thought = thought_match.group(1) if thought_match else "Failed to parse thought"
            action = action_match.group(1) if action_match else "no_action"
            
            # Try to parse parameters
            params = {}
            if params_match:
                try:
                    params_str = params_match.group(1)
                    # Replace single quotes with double quotes for valid JSON
                    params_str = params_str.replace("'", "\"")
                    params = json.loads(params_str)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse parameters JSON")
            
            return {
                "thought": thought,
                "action": action,
                "parameters": params
            } 
    
