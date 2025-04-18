"""
Anthropic provider implementation.
"""

import os
import asyncio
import base64
import logging
from typing import Optional

import anthropic
from ..llm_provider import LLMProvider

# Set up logger
logger = logging.getLogger("droidrun")

class AnthropicProvider(LLMProvider):
    """Anthropic provider implementation."""
    
    def _initialize_client(self) -> None:
        """Initialize the Anthropic client."""
        # Get API key from env var if not provided
        self.api_key = self.api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key not provided and not found in environment")
        
        # Set default model if not specified
        if not self.model_name:
            self.model_name = "claude-3-opus-20240229"
        
        # Verify vision model compatibility
        if self.vision and not "claude-3" in self.model_name:
            raise ValueError(f"The selected model '{self.model_name}' does not support vision. "
                           "Please manually specify a Claude 3 model which supports vision capabilities.")
        
        # Initialize client
        self.client = anthropic.Anthropic(api_key=self.api_key)
        logger.info(f"Initialized Anthropic client with model {self.model_name}")
    
    async def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        screenshot_data: Optional[bytes] = None
    ) -> str:
        """Generate a response using Anthropic."""
        try:
            messages = []

            # Add screenshot if provided
            if screenshot_data:
                base64_image = base64.b64encode(screenshot_data).decode('utf-8')
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
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
            
            # Update token usage statistics if available
            # Note: Anthropic might not provide token usage info in the same way
            # This is a placeholder for when/if they add this feature
            if hasattr(response, 'usage'):
                usage = response.usage
                self.update_token_usage(
                    getattr(usage, 'prompt_tokens', 0),
                    getattr(usage, 'completion_tokens', 0)
                )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Error calling Anthropic API: {e}")
            raise 