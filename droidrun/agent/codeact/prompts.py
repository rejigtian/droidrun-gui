"""
Prompt templates for the CodeActAgent.

This module contains all the prompts used by the CodeActAgent,
separated from the workflow logic for better maintainability.
"""


# User prompt template that presents the current request and prompts for reasoning
DEFAULT_CODE_ACT_USER_PROMPT = """**Current Request:**
{goal}

**Is the precondition met? What is your reasoning and the next step to address this request?** Explain your thought process then provide code in ```python ... ``` tags if needed."""""

# Prompt to remind the agent to provide thoughts before code
DEFAULT_NO_THOUGHTS_PROMPT = """Your previous response provided code without explaining your reasoning first. Remember to always describe your thought process and plan *before* providing the code block.

The code you provided will be executed below.

Now, describe the next step you will take to address the original goal: {goal}"""

# Export all prompts
__all__ = [
    "DEFAULT_CODE_ACT_USER_PROMPT", 
    "DEFAULT_NO_THOUGHTS_PROMPT"
] 