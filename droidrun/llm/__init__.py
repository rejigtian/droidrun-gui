"""
DroidRun LLM Module.

This module provides LLM providers for the Agent to use for reasoning.
"""

from droidrun.agent.llm_reasoning import LLMReasoner as BaseLLM

# Alias OpenAILLM and AnthropicLLM for backward compatibility
class OpenAILLM(BaseLLM):
    """
    OpenAI-based LLM provider.
    """
    def __init__(self, model="gpt-4o", **kwargs):
        super().__init__(provider="openai", model=model, **kwargs)

class AnthropicLLM(BaseLLM):
    """
    Anthropic-based LLM provider.
    """
    def __init__(self, model="claude-3-opus-20240229", **kwargs):
        super().__init__(provider="anthropic", model=model, **kwargs)

__all__ = ["BaseLLM", "OpenAILLM", "AnthropicLLM"] 