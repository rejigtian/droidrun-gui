"""
Memory store module for storing agent memories independently.
"""

from typing import List, Dict, Any
from collections import deque
import time

# Global memory store (using deque for efficient fixed-size operations)
_memories = deque(maxlen=5)  # Only keep the last 5 memories

def add_memory(memory: str) -> None:
    """Add a memory to the global memory store.
    Only the last 5 memories are retained.
    
    Args:
        memory: The memory to add
    """
    global _memories
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    _memories.append({
        "content": memory,
        "timestamp": timestamp
    })
    
def get_memories() -> List[Dict[str, str]]:
    """Get all memories from the global memory store.
    
    Returns:
        List of memories with timestamps
    """
    global _memories
    return list(_memories)

def get_formatted_memories() -> str:
    """Get formatted memories as a string.
    
    Returns:
        Formatted string with memories
    """
    memories = get_memories()
    if not memories:
        return "No memories stored yet."
    
    formatted = "🧠 AGENT MEMORY\n"
    for i, memory in enumerate(memories, 1):
        timestamp = memory['timestamp']
        content = memory['content']
        formatted += f"│ {i}. [{timestamp}] {content}\n"
    return formatted

def clear_memories() -> None:
    """Clear all memories from the global memory store."""
    global _memories
    _memories.clear() 