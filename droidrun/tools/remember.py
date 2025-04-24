"""
Remember tool - Allows the agent to remember important information.
"""

import logging

# Import the memory store
from .memory_store import add_memory, get_formatted_memories

# Set up logger
logger = logging.getLogger("droidrun")

async def remember(memory: str) -> str:
    """Store an important piece of information for later reference.
    This tool allows the agent to maintain a short-term memory of important facts or insights.
    Only the 5 most recent memories are retained.

    :param memory: Important information to remember.
    :return: Formatted string with all current memories.
    """
    try:
        logger.info(f"Remembering: {memory}")

        # Add the memory to the global memory store
        add_memory(memory)

        # Return the formatted memories
        return get_formatted_memories()
    except Exception as e:
        logger.error(f"Error storing memory: {e}")
        return f"Error storing memory: {e}" 