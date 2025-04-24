"""
OpenAI provider implementation.
"""

import os
import asyncio
import base64
import logging
from typing import Optional

from openai import OpenAI
from ..llm_provider import LLMProvider

# Set up logger
logger = logging.getLogger("droidrun")

class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation."""
    
    def _initialize_client(self) -> None:
        """Initialize the OpenAI client."""
        # Get API key from env var if not provided
        self.api_key = self.api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided and not found in environment")
        
        # Set default model if not specified
        if not self.model_name:
            self.model_name = "gpt-4o-mini"
            if self.vision:
                self.model_name = "gpt-4o"  # Default vision model
        
        # Verify vision model compatibility
        if self.vision and not (self.model_name.startswith("gpt-4-vision") or 
                               self.model_name.startswith("gpt-4o") or 
                               self.model_name.endswith("-vision")):
            raise ValueError(f"The selected model '{self.model_name}' does not support vision. "
                           "Please manually specify a vision-capable model like gpt-4o or gpt-4-vision.")
        
        # Initialize client
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        logger.info(f"Initialized OpenAI client with model {self.model_name}, base_url={self.base_url}")
    
    async def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        screenshot_data: Optional[bytes] = None
    ) -> str:
        """Generate a response using OpenAI."""
        try:
            messages = [
                {"role": "system", "content": system_prompt},
            ]

            # Add screenshot if provided
            if screenshot_data:
                base64_image = base64.b64encode(screenshot_data).decode('utf-8')
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Here's the current screenshot of the device. Please analyze it to help with the next action."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
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
            
            # Update token usage statistics
            usage = response.usage
            self.update_token_usage(usage.prompt_tokens, usage.completion_tokens)
            
            # Log token usage
            logger.info("===== Token Usage Statistics =====")
            logger.info(f"API Call #{self.api_calls}")
            logger.info(f"This call: {usage.prompt_tokens} prompt + {usage.completion_tokens} completion = {usage.total_tokens} tokens")
            logger.info(f"Cumulative: {self.get_token_usage_stats()}")
            logger.info("=================================")
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            raise 
