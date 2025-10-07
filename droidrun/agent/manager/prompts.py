"""
Prompts for the ManagerAgent.
"""

# TODO: Port and adapt prompts from mobile_agent_v3.py Manager class
# Reference: android_world/agents/mobile_agent_v3_agent.py Manager.get_prompt()

DEFAULT_MANAGER_SYSTEM_PROMPT = """
TODO: Implement Manager system prompt

The Manager is responsible for:
- Planning and reasoning about the task
- Breaking down complex tasks into subgoals
- Tracking progress and completed steps
- Deciding when the task is complete
- Providing answers for answer-type tasks

Output format should include:
- <thought>: reasoning about current state and next steps
- <plan>: list of remaining subgoals
- <current_subgoal>: the immediate next action to take
- <completed_plan>: what has been accomplished so far
- <memory>: (optional) important information to remember
- <answer>: (optional) final answer if task requires it
"""


DEFAULT_MANAGER_USER_PROMPT = """
TODO: Implement Manager user prompt template

Should include:
- Current instruction/goal: {instruction}
- Device state information
- Action history and outcomes
- Current UI elements
- Memory/context from previous steps
"""


def build_manager_prompt(
    instruction: str,
    device_state: str,
    action_history: list,
    memory: str = "",
    error_flag: bool = False,
) -> str:
    """
    Build the manager prompt with current context.

    TODO: Implement prompt building logic from mobile_agent_v3.py
    """
    return DEFAULT_MANAGER_USER_PROMPT.format(
        instruction=instruction,
        # Add more context as needed
    )
