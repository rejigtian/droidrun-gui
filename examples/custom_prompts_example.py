"""
Example: Using Custom Prompts with DroidAgent

This example demonstrates how to override default prompts at runtime by passing
a dict of custom Jinja2 template strings to DroidAgent.

Valid prompt keys:
- "codeact_system": CodeActAgent system prompt
- "codeact_user": CodeActAgent user prompt
- "manager_system": ManagerAgent system prompt
- "executor_system": ExecutorAgent system prompt
- "scripter_system": ScripterAgent system prompt
"""

import asyncio

from droidrun.agent.droid import DroidAgent
from droidrun.config_manager import ConfigManager

# Initialize config
config_manager = ConfigManager()
config = config_manager.config


async def main():
    # ============================================================================
    # Example 1: Override CodeAct system prompt (non-reasoning mode)
    # ============================================================================

    custom_codeact_system = """You are a helpful assistant that controls Android devices.

Available tools:
{{ tool_descriptions }}

{% if available_secrets %}
Available credentials (use get_<SECRET_ID>() to access):
{% for secret in available_secrets %}
- {{ secret }}
{% endfor %}
{% endif %}

Your task is to execute actions using Python code blocks.
Always explain your reasoning before providing code.
"""

    custom_prompts = {
        "codeact_system": custom_codeact_system,
    }

    agent = DroidAgent(
        goal="Open Chrome and go to google.com",
        config=config,
        prompts=custom_prompts,  # Pass custom prompts here
    )

    result = await agent.run()
    print(f"Success: {result.success}")
    print(f"Reason: {result.reason}")

    # ============================================================================
    # Example 2: Override Manager system prompt (reasoning mode)
    # ============================================================================

    custom_manager_system = """You are a strategic planner for Android device automation.

Current Instruction: {{ instruction }}

{% if app_card %}
App Information:
{{ app_card }}
{% endif %}

Your job is to:
1. Analyze the current device state
2. Create a step-by-step plan
3. Identify the current subgoal

Output your response with these tags:
<plan>Your multi-step plan here</plan>
<current_subgoal>The next immediate action to take</current_subgoal>
<thought>Your reasoning</thought>
"""

    custom_executor_system = """You are an action executor for Android devices.

Current subgoal: {{ subgoal }}

Available actions:
{% for action_name, action_spec in atomic_actions.items() %}
- {{ action_name }}: {{ action_spec.description }}
{% endfor %}

Output your response with these tags:
<thought>Your reasoning</thought>
<action>{"action": "action_name", ...params...}</action>
<description>What this action will do</description>
"""

    reasoning_prompts = {
        "manager_system": custom_manager_system,
        "executor_system": custom_executor_system,
    }

    # Enable reasoning mode in config
    config.agent.reasoning = True

    agent = DroidAgent(
        goal="Send a message 'Hello' to John on WhatsApp",
        config=config,
        prompts=reasoning_prompts,
    )

    result = await agent.run()
    print(f"Success: {result.success}")
    print(f"Reason: {result.reason}")

    # ============================================================================
    # Example 3: Custom user prompt for CodeAct
    # ============================================================================

    custom_user_prompt = """Task: {{ goal }}

{% if variables %}
Available variables:
{% for key, value in variables.items() %}
- {{ key }}: {{ value }}
{% endfor %}
{% endif %}

Complete this task using the available tools.
"""

    user_prompt_override = {
        "codeact_user": custom_user_prompt,
    }

    agent = DroidAgent(
        goal="Take a screenshot",
        config=config,
        prompts=user_prompt_override,
        variables={"max_retries": 3, "timeout": 30},
    )

    result = await agent.run()
    print(f"Success: {result.success}")


if __name__ == "__main__":
    asyncio.run(main())
