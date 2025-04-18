"""
Base interface for LLM providers.

This module defines the abstract base class that all LLM providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2000,
        vision: bool = False,
        base_url: Optional[str] = None
    ):
        """Initialize the LLM provider.
        
        Args:
            model_name: Model name to use
            api_key: API key for the LLM provider
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            vision: Whether vision capabilities are enabled
            base_url: Optional base URL for the API
        """
        self.model_name = model_name
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.vision = vision
        self.base_url = base_url
        
        # Token usage tracking
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0
        self.api_calls = 0
        
        # Initialize the client
        self._initialize_client()
    
    @abstractmethod
    def _initialize_client(self) -> None:
        """Initialize the API client for this provider."""
        pass
    
    @abstractmethod
    async def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        screenshot_data: Optional[bytes] = None
    ) -> str:
        """Generate a response using the LLM.
        
        Args:
            system_prompt: System prompt string
            user_prompt: User prompt string
            screenshot_data: Optional bytes containing the latest screenshot
        
        Returns:
            Generated response string
        """
        pass
    
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
    
    def update_token_usage(self, prompt_tokens: int, completion_tokens: int) -> None:
        """Update token usage statistics.
        
        Args:
            prompt_tokens: Number of prompt tokens used
            completion_tokens: Number of completion tokens used
        """
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_tokens += prompt_tokens + completion_tokens
        self.api_calls += 1 