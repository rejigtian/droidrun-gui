"""
LLM Reasoning - Provides reasoning capabilities for the ReAct agent.

This module handles the integration with LLM providers to generate reasoning steps.
"""

import json
import re
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
        screenshot_data: Optional[bytes] = None
    ) -> Dict[str, Any]:
        """Generate a reasoning step using the LLM.
        
        Args:
            goal: The automation goal
            history: List of previous steps as dictionaries
            available_tools: Optional list of available tool names
            screenshot_data: Optional bytes containing the latest screenshot
        
        Returns:
            Dictionary with next reasoning step, including thought,
            action, and any parameters
        """
        # Print current token usage stats before making the call
        logger.info(f"Token usage before API call: {self.get_token_usage_stats()}")
        
        # Construct the prompt
        system_prompt = self._create_system_prompt(available_tools)
        user_prompt = self._create_user_prompt(goal, history)
        
        try:
            # Call the provider
            response = await self.provider.generate_response(
                system_prompt,
                user_prompt,
                screenshot_data
            )
            
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
    
    def _create_system_prompt(self, available_tools: Optional[List[str]] = None) -> str:
        """Create the system prompt for the LLM.
        
        Args:
            available_tools: Optional list of available tool names
        
        Returns:
            System prompt string
        """
        # Base system prompt
        prompt = """
        You are an user assitant for an Android phone. Your task is to control an Android device to achieve a specified goal the user is asking for.
        Follow these guidelines:

        1. Analyze the current screen state from the UI state getting all UI elements
        2. Think step-by-step to plan your actions
        3. Choose the most appropriate tool for each step
        4. Return your response in JSON format with the following fields:
        - thought: Your detailed reasoning about the current state and what to do next
        - action: The name of the tool to execute (use EXACT tool name without any parentheses)
        - parameters: A dictionary of parameters to pass to the tool

        IMPORTANT: When specifying the action field:
        - Never add parentheses to the tool name
        - Common mistakes to avoid:
          ❌ "get_clickables()"
          ✅ "get_clickables"

        You have two very important tools for your observations.
        1. You can get all UI elements to get a better understanding of the current screen including all texts container on the screen. Use this to to analyze the current ui context.
        2. If you want to take action, after you analyzed the context, you can get all the clickable elements for your next interactive step. Only use this tool if you know about your current ui context.

        """
        
        # Add vision-specific instructions if vision is enabled
        if self.provider.vision:
            prompt += """
            You have access to screenshots through the take_screenshot tool. Use it when visual context is needed.
            """
        else:
            prompt += """
            Vision is disabled. Rely solely on text-based UI element data from get_clickables.
            """
                
        # Tool documentation with exact parameter names
        tool_docs = {
            "tap": "tap(index: int) - Tap on the element with the given index on the device",
            
            "swipe": "swipe(start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 300) - Swipe from (start_x,start_y) to (end_x,end_y) over duration_ms milliseconds",
            
            "input_text": "input_text(text: str) - Input text on the device - this works only if an input is focused. Always make sure that an edit field was tapped before inserting text",
            
            "press_key": "press_key(keycode: int) - Press a key on the device using keycode",
            
            "start_app": "start_app(package: str, activity: str = '') - Start an app using its package name (e.g., 'com.android.settings')",
            
            "list_packages": "list_packages(include_system_apps: bool = False) - List installed packages on the device, returns detailed package information",
            
            "get_clickables": "get_clickables() - Get only the clickable UI elements from the device screen. Returns a dictionary containing interactive elements with their properties",

            "complete": "complete(result: str) - IMPORTANT: This tool should ONLY be called after you have ACTUALLY completed all necessary actions for the goal. It does not perform any actions itself - it only signals that you have already achieved the goal through other actions. Include a summary of what was accomplished as the result parameter.",
        }
        
        # Add take_screenshot tool only if vision is enabled
        if self.provider.vision:
            tool_docs["take_screenshot"] = "take_screenshot() - Take a screenshot to better understand the current UI. Use when you need visual context."
        
        # Add available tools information if provided
        if available_tools:
            prompt += "\n\nAvailable tools and their parameters:\n"
            
            # Only include docs for available tools
            for tool in available_tools:
                if tool in tool_docs:
                    prompt += f"- {tool_docs[tool]}\n"
                else:
                    prompt += f"- {tool} (parameters unknown)\n"
        
        return prompt
    
    def _create_user_prompt(
        self,
        goal: str,
        history: List[Dict[str, Any]],
    ) -> str:
        """Create the user prompt for the LLM.
        
        Args:
            goal: The automation goal
            history: List of previous steps
        
        Returns:
            User prompt string
        """
        prompt = f"Goal: {goal}\n\n"
        
        # Add truncated history if available
        if history:
            # Start with a budget for tokens (very rough approximation)
            total_budget = 100000  # Conservative limit to leave room for response
            
            # Estimate tokens for the goal and other parts
            goal_tokens = estimate_tokens(goal) * 2  # Account for repetition
            
            # Calculate remaining budget for history
            history_budget = total_budget - goal_tokens
            
            # Start with most recent history and work backwards
            truncated_history = []
            current_size = 0
            
            # Copy and reverse history to process most recent first
            reversed_history = list(reversed(history))
            
            for step in reversed_history:
                step_type = step.get("type", "").upper()
                content = step.get("content", "")
                step_text = f"{step_type}: {content}\n"
                step_tokens = estimate_tokens(step_text)
                
                # If this step would exceed our budget, stop adding
                if current_size + step_tokens > history_budget:
                    # Add a note about truncation
                    truncated_history.insert(0, "... (earlier history truncated)")
                    break
                
                # Otherwise, add this step and update our current size
                truncated_history.insert(0, step_text)
                current_size += step_tokens
            
            # Add the truncated history to the prompt
            prompt += "History:\n"
            for step_text in truncated_history:
                prompt += step_text
            prompt += "\n"
        
        prompt += "Based on the current state, what's your next action? Return your response in JSON format."
        
        # Final sanity check - if prompt is still too large, truncate aggressively
        if estimate_tokens(prompt) > 100000:
            logger.warning("Prompt still too large after normal truncation. Applying emergency truncation.")
            # Keep the beginning (goal) and end (instructions) but truncate the middle
            beginning = prompt[:2000]  # Keep goal
            end = prompt[-1000:]       # Keep final instructions
            prompt = beginning + "\n... (content truncated to fit token limits) ...\n" + end
        
        return prompt
    
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