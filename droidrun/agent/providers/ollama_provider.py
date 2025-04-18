"""
Ollama provider implementation.
"""

import asyncio
import logging
from typing import Optional

from openai import OpenAI
from ..llm_provider import LLMProvider

# Set up logger
logger = logging.getLogger("droidrun")

class OllamaProvider(LLMProvider):
    """Ollama provider implementation."""
    
    def _initialize_client(self) -> None:
        """Initialize the Ollama client."""
        # Set default model if not specified
        if not self.model_name:
            self.model_name = "llama3.1:8b"
        
        # Set up base URL
        if self.base_url is None:
            self.base_url = "http://localhost:11434/v1"
        if not self.base_url.startswith('http://'):
            self.base_url = "http://" + self.base_url
        if not self.base_url.endswith('/v1'):
            self.base_url += "/v1"
        
        # Initialize client with Ollama configuration
        self.client = OpenAI(
            api_key="ollama",  # Ollama doesn't need an API key
            base_url=self.base_url
        )
        logger.info(f"Initialized Ollama client with model {self.model_name} at {self.base_url}")
    
    async def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        screenshot_data: Optional[bytes] = None
    ) -> str:
        """Generate a response using Ollama."""
        try:
            messages = [
                {"role": "system", "content": system_prompt},
            ]

            # Add screenshot if provided
            if screenshot_data:
                logger.warning("Ollama does not support image inputs. Ignoring screenshot data.")

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
            
            # Update token usage statistics if available
            # Note: Ollama might not provide token usage info in the same way
            if hasattr(response, 'usage'):
                usage = response.usage
                self.update_token_usage(
                    getattr(usage, 'prompt_tokens', 0),
                    getattr(usage, 'completion_tokens', 0)
                )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error calling Ollama API: {e}")
            raise 