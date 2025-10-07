"""
ManagerAgent - Planning and reasoning workflow.

This agent is responsible for:
- Analyzing the current state
- Creating plans and subgoals
- Tracking progress
- Deciding when tasks are complete
"""

import logging
from typing import List, TYPE_CHECKING

from llama_index.core.workflow import Workflow, step, Context, StartEvent, StopEvent
from llama_index.core.llms.llm import LLM
from llama_index.core.base.llms.types import ChatMessage

from droidrun.agent.manager.events import ManagerThinkingEvent, ManagerPlanEvent
from droidrun.agent.manager.prompts import (
    DEFAULT_MANAGER_SYSTEM_PROMPT,
    DEFAULT_MANAGER_USER_PROMPT,
)

if TYPE_CHECKING:
    from droidrun.agent.droid.events import DroidAgentState

logger = logging.getLogger("droidrun")


class ManagerAgent(Workflow):
    """
    Planning and reasoning agent that decides what to do next.

    The Manager:
    1. Analyzes current device state and action history
    2. Creates plans with specific subgoals
    3. Tracks progress and completed steps
    4. Decides when tasks are complete or need to provide answers
    """

    def __init__(
        self,
        llm: LLM,
        vision: bool,
        personas: List,
        tools_instance,
        debug: bool = False,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.llm = llm
        self.vision = vision
        self.personas = personas
        self.tools_instance = tools_instance
        self.debug = debug

        self.system_prompt = DEFAULT_MANAGER_SYSTEM_PROMPT
        logger.info("✅ ManagerAgent initialized successfully.")

    @step
    async def prepare_input(
        self,
        ctx: Context,
        ev: StartEvent
    ) -> ManagerThinkingEvent:
        """
        Gather context and prepare manager prompt.

        This step:
        1. Gets current device state (UI elements, screenshot)
        2. Builds message history entry with last action
        3. Prepares all context for the manager to reason about
        """
        logger.info("💬 Preparing manager input...")

        # Read current state
        state = await ctx.store.get_state()

        # TODO: Get device state (android-world specific)
        # from android_world.standalone_device_state import get_device_state_exact_format
        # device_state_text, focused_text = get_device_state_exact_format()

        # For now, use placeholder
        device_state_text = "TODO: Implement device state gathering"
        focused_text = ""

        # Update state with device info
        async with ctx.store.edit_state() as state:
            state.device_state_text = device_state_text
            state.focused_text = focused_text
            # Shift UI elements for before/after tracking
            state.ui_elements_list_before = state.ui_elements_list_after
            state.ui_elements_list_after = device_state_text

        # Build message history entry
        parts = []

        # Add last action context if available
        if state.finish_thought:
            parts.append(f"<thought>\n{state.finish_thought}\n</thought>\n")

        if state.last_action:
            import json
            action_str = json.dumps(state.last_action)
            parts.append(f"<last_action>\n{action_str}\n</last_action>\n")

        if state.last_summary:
            parts.append(f"<last_action_description>\n{state.last_summary}\n</last_action_description>\n")

        # Append to message history
        if parts:
            async with ctx.store.edit_state() as state:
                state.message_history.append({
                    "role": "user",
                    "content": [{"text": "".join(parts)}]
                })

        logger.debug(f"  - Device state prepared")
        return ManagerThinkingEvent()

    @step
    async def think(
        self,
        ctx: Context,
        ev: ManagerThinkingEvent
    ) -> ManagerPlanEvent:
        """
        Manager thinks and creates plan.

        This step:
        1. Calls LLM with manager prompt and context
        2. Parses the response for plan, subgoals, thoughts
        3. Updates memory if provided by manager
        4. Returns structured plan event
        """
        logger.info("🧠 Manager thinking about the plan...")

        state = await ctx.store.get_state()

        # TODO: Build full manager prompt with all context
        # - instruction
        # - device state
        # - action history
        # - memory
        # - error flags
        # Reference: mobile_agent_v3.py Manager.get_messages()

        # TODO: Call LLM
        # system_message = ChatMessage(role="system", content=self.system_prompt)
        # messages = [system_message] + build_messages_from_history(state)
        # response = await self.llm.achat(messages=messages)

        # TODO: Parse response
        # Reference: mobile_agent_v3.py Manager.parse_response()
        # Should extract:
        # - thought: <thought>...</thought>
        # - plan: <plan>...</plan>
        # - current_subgoal: <current_subgoal>...</current_subgoal>
        # - completed_plan: <completed_plan>...</completed_plan>
        # - memory: <memory>...</memory> (optional)
        # - answer: <answer>...</answer> (optional)

        # Placeholder for now
        logger.warning("⚠️ Using placeholder manager response - TODO: implement LLM call")
        plan = "TODO: implement manager LLM call and parsing"
        current_subgoal = "TODO: next subgoal"
        completed_plan = state.completed_plan  # Keep existing
        thought = "Manager reasoning not yet implemented"
        manager_answer = ""
        memory_update = ""

        # Update memory if provided
        if memory_update:
            async with ctx.store.edit_state() as state:
                if state.memory:
                    state.memory += "\n" + memory_update
                else:
                    state.memory = memory_update

        # Append assistant response to message history
        async with ctx.store.edit_state() as state:
            state.message_history.append({
                "role": "assistant",
                "content": [{"text": f"<thought>{thought}</thought>\n<plan>{plan}</plan>"}]
            })

        logger.info(f"📝 Plan: {plan}")
        logger.debug(f"  - Current subgoal: {current_subgoal}")

        return ManagerPlanEvent(
            plan=plan,
            current_subgoal=current_subgoal,
            completed_plan=completed_plan,
            thought=thought,
            manager_answer=manager_answer,
            memory_update=memory_update
        )

    @step
    async def finalize(
        self,
        ctx: Context,
        ev: ManagerPlanEvent
    ) -> StopEvent:
        """Return manager results to parent workflow."""
        logger.debug("✅ Manager planning complete")

        return StopEvent(result={
            "plan": ev.plan,
            "current_subgoal": ev.current_subgoal,
            "completed_plan": ev.completed_plan,
            "thought": ev.thought,
            "manager_answer": ev.manager_answer,
            "memory_update": ev.memory_update
        })
