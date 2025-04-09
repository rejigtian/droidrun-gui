"""
LLM Reasoning - Provides reasoning capabilities for the ReAct agent.

This module handles the integration with LLM providers to generate reasoning steps.
"""

import asyncio
import json
import os
import re
import logging
from typing import Any, Dict, List, Optional

# Import OpenAI for LLM integration
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Import Anthropic for Claude integration
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

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
        max_tokens: int = 2000
    ):
        """Initialize the LLM reasoner.
        
        Args:
            llm_provider: LLM provider ('openai', 'anthropic', or 'gemini'). 
                         If model_name starts with 'gemini-', provider will be set to 'gemini' automatically.
            model_name: Model name to use
            api_key: API key for the LLM provider
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
        """
        # Auto-detect Gemini models
        if model_name and model_name.startswith("gemini-"):
            llm_provider = "gemini"
            
        self.llm_provider = llm_provider.lower()
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Token usage tracking
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0
        self.api_calls = 0
        
        # Set up model and client based on provider
        if self.llm_provider == "gemini":
            if not OPENAI_AVAILABLE:
                raise ImportError("OpenAI package not installed. Install with 'pip install openai'")
            
            # Set default model if not specified
            self.model_name = model_name or "gemini-2.0-flash"
            
            # Get API key from env var if not provided
            self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
            if not self.api_key:
                raise ValueError("Gemini API key not provided and not found in environment (GEMINI_API_KEY)")
            
            print("APIKEY: ", self.api_key)
            # Initialize client with Gemini configuration
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
            logger.info(f"Initialized Gemini client with model {self.model_name}")
            
        elif self.llm_provider == "openai":
            if not OPENAI_AVAILABLE:
                raise ImportError("OpenAI package not installed. Install with 'pip install openai'")
            
            # Set default model if not specified
            self.model_name = model_name or "gpt-4o-mini"
            
            # Get API key from env var if not provided
            self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OpenAI API key not provided and not found in environment")
            
            # Initialize client
            self.client = OpenAI(api_key=self.api_key)
            
        elif self.llm_provider == "anthropic":
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("Anthropic package not installed. Install with 'pip install anthropic'")
            
            # Set default model if not specified
            self.model_name = model_name or "claude-3-opus-20240229"
            
            # Get API key from env var if not provided
            self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
            if not self.api_key:
                raise ValueError("Anthropic API key not provided and not found in environment")
            
            # Initialize client
            self.client = anthropic.Anthropic(api_key=self.api_key)
            
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")
    
    def get_token_usage_stats(self) -> Dict[str, int]:
        """Get current token usage statistics.
        
        Returns:
            Dictionary with token usage statistics
        """
        return {
            "prompt_tokens": self.total_prompt_tokens,
            "completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
            "api_calls": self.api_calls
        }
    
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
            # Call the LLM based on provider
            if self.llm_provider in ["openai", "gemini"]:  # Handle both OpenAI and Gemini with OpenAI client
                response = await self._call_openai(system_prompt, user_prompt, screenshot_data)
            elif self.llm_provider == "anthropic":
                response = await self._call_anthropic(system_prompt, user_prompt, screenshot_data)
            else:
                raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")
            
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

        1. Analyze the current screen state from the UI state by taking a screenshot
        2. Think step-by-step to plan your actions
        3. Choose the most appropriate tool for each step
        4. Return your response in JSON format with the following fields:
        - thought: Your detailed reasoning about the current state and what to do next
        - action: The name of the tool to execute
        - parameters: A dictionary of parameters to pass to the tool

        You have two very important tools for your observations.
        1. You can take a screenshot to get a better understanding of the current screen including all texts and images on the screen. Use this to to analyze the current ui context.
        2. If you want to take action, after you analyzed the context, you can get all the clickable elements for your next interactive step. Only use this tool if you know about your current ui context.

        """
                
        # Tool documentation with exact parameter names
        tool_docs = {
            "tap": "tap(index: int) - Tap on the element with the given index on the device",
            
            "swipe": "swipe(start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 300) - Swipe from (start_x,start_y) to (end_x,end_y) over duration_ms milliseconds",
            
            "input_text": "input_text(text: str) - Input text on the device - this works only if an input is focused. Always make sure that an edit field was tapped before inserting text",
            
            "press_key": "press_key(keycode: int) - Press a key on the device using keycode",
            
            "start_app": "start_app(package: str, activity: str = '') - Start an app using its package name (e.g., 'com.android.settings')",

            "take_screenshot": "take_screenshot() - Take a screenshot of the device",
            
            "list_packages": "list_packages(include_system_apps: bool = False) - List installed packages on the device, returns detailed package information",
            
            "get_clickables": "get_clickables() - Get only the clickable UI elements from the device screen. Returns a dictionary containing interactive elements with their properties",
            
            "complete": "complete(result: str) - IMPORTANT: This tool should ONLY be called after you have ACTUALLY completed all necessary actions for the goal. It does not perform any actions itself - it only signals that you have already achieved the goal through other actions. ALWAYS MAKE SURE YOU REACHED YOUR GOAL BY TAKING A SCREENSHOT BEFORE CALLIN COMPLETE. Include a summary of what was accomplished as the result parameter.",
        }
        
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
    
    async def _call_openai(self, system_prompt: str, user_prompt: str, screenshot_data: Optional[bytes] = None) -> str:
        """Call OpenAI or Gemini API to generate a response.
        
        Args:
            system_prompt: System prompt string
            user_prompt: User prompt string
            screenshot_data: Optional bytes containing the latest screenshot
        
        Returns:
            Generated response string
        """
        try:
            messages = [
                {"role": "system", "content": system_prompt},
            ]

            # If we have a screenshot, add it as a message with the image
            if screenshot_data:
                import base64
                base64_image = base64.b64encode(screenshot_data).decode('utf-8')
                
                # Different image format for Gemini vs OpenAI
                if self.llm_provider != "gemini":
                    image_content = {
                        "type": "image",
                        "image_url": {
                            "data": base64_image,
                            "format": "jpeg"
                        }
                    }
                else:
                    image_content = {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Here's the current screenshot of the device. Please analyze it to help with the next action."
                        },
                        image_content
                    ]
                })

            # Add the main user prompt
            messages.append({"role": "user", "content": user_prompt})

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"}
            )
            
            # Extract token usage statistics
            usage = response.usage
            prompt_tokens = usage.prompt_tokens
            completion_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens
            
            # Update token usage counters
            self.total_prompt_tokens += prompt_tokens
            self.total_completion_tokens += completion_tokens
            self.total_tokens += total_tokens
            self.api_calls += 1
            
            # Print token usage information
            logger.info("===== Token Usage Statistics =====")
            logger.info(f"API Call #{self.api_calls}")
            logger.info(f"This call: {prompt_tokens} prompt + {completion_tokens} completion = {total_tokens} tokens")
            logger.info(f"Cumulative: {self.total_prompt_tokens} prompt + {self.total_completion_tokens} completion = {self.total_tokens} tokens")
            logger.info("=================================")
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error calling {'Gemini' if self.llm_provider == 'gemini' else 'OpenAI'} API: {e}")
            raise
    
    async def _call_anthropic(self, system_prompt: str, user_prompt: str, screenshot_data: Optional[bytes] = None) -> str:
        """Call Anthropic API to generate a response.
        
        Args:
            system_prompt: System prompt string
            user_prompt: User prompt string
            screenshot_data: Optional bytes containing the latest screenshot
        
        Returns:
            Generated response string
        """
        try:
            messages = []

            # If we have a screenshot, add it as a message with the image
            if screenshot_data:
                import base64
                # Convert the image bytes to base64
                base64_image = base64.b64encode(screenshot_data).decode('utf-8')
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": base64_image
                            }
                        },
                        {
                            "type": "text",
                            "text": "Here's the current screenshot of the device. Please analyze it to help with the next action."
                        }
                    ]
                })

            # Add the main user prompt
            messages.append({"role": "user", "content": user_prompt})

            response = await asyncio.to_thread(
                self.client.messages.create,
                model=self.model_name,
                system=system_prompt,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Error calling Anthropic API: {e}")
            raise
    
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