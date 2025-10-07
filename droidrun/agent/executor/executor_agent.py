"""
ExecutorAgent - Action execution workflow.

This agent is responsible for:
- Taking a specific subgoal from the Manager
- Analyzing the current UI state
- Selecting and executing appropriate actions
"""

import logging
import json
from typing import TYPE_CHECKING

from llama_index.core.workflow import Workflow, step, Context, StartEvent, StopEvent
from llama_index.core.llms.llm import LLM
from llama_index.core.base.llms.types import ChatMessage

from droidrun.agent.executor.events import (
    ExecutorThinkingEvent,
    ExecutorActionEvent,
    ExecutorResultEvent
)
from droidrun.agent.executor.prompts import (
    DEFAULT_EXECUTOR_SYSTEM_PROMPT,
    DEFAULT_EXECUTOR_USER_PROMPT,
    DETAILED_TIPS
)

if TYPE_CHECKING:
    from droidrun.agent.droid.events import DroidAgentState

logger = logging.getLogger("droidrun")


class ExecutorAgent(Workflow):
    """
    Action execution agent that performs specific actions.

    The Executor:
    1. Receives a subgoal from the Manager
    2. Analyzes current UI state and context
    3. Selects an appropriate action to take
    4. Executes the action on the device
    5. Reports the outcome
    """

    def __init__(
        self,
        llm: LLM,
        vision: bool,
        tools_instance,
        persona=None,
        debug: bool = False,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.llm = llm
        self.vision = vision
        self.tools_instance = tools_instance
        self.persona = persona
        self.debug = debug

        self.system_prompt = DEFAULT_EXECUTOR_SYSTEM_PROMPT
        logger.info("✅ ExecutorAgent initialized successfully.")

    @step
    async def prepare_input(
        self,
        ctx: Context,
        ev: StartEvent
    ) -> ExecutorThinkingEvent:
        """
        Gather context for action selection.

        This step:
        1. Gets current subgoal from StartEvent
        2. Gets current screenshot (if vision enabled)
        3. Gets current UI state
        4. Prepares all context for the executor
        """
        logger.info("💬 Preparing executor input...")

        state = await ctx.store.get_state()
        subgoal = ev.get("subgoal", "")

        # TODO: Get current screenshot
        # if self.vision:
        #     screenshot = self.tools_instance.take_screenshot()[1]
        #     await ctx.store.set("screenshot", screenshot)

        # TODO: Get current UI state if not already fresh
        # from android_world.standalone_device_state import get_device_state_exact_format
        # device_state_text, focused_text = get_device_state_exact_format()
        # async with ctx.store.edit_state() as state:
        #     state.device_state_text = device_state_text
        #     state.focused_text = focused_text

        logger.debug(f"  - Subgoal: {subgoal}")
        return ExecutorThinkingEvent(subgoal=subgoal)

    @step
    async def think(
        self,
        ctx: Context,
        ev: ExecutorThinkingEvent
    ) -> ExecutorActionEvent:
        """
        Executor decides which action to take.

        This step:
        1. Calls LLM with executor prompt and context
        2. Parses the response for action, thought, description
        3. Validates action format
        4. Returns action event
        """
        logger.info(f"🧠 Executor thinking about action for: {ev.subgoal}")

        state = await ctx.store.get_state()

        # TODO: Build full executor prompt with all context
        # - subgoal
        # - device state / UI elements
        # - action history
        # - additional knowledge (DETAILED_TIPS)
        # Reference: mobile_agent_v3.py Executor.get_prompt()

        # TODO: Call LLM
        # system_message = ChatMessage(role="system", content=self.system_prompt)
        # user_message = build_executor_message(ev.subgoal, state)
        # if self.vision:
        #     screenshot = await ctx.store.get("screenshot")
        #     # Add image to message
        # response = await self.llm.achat(messages=[system_message, user_message])

        # TODO: Parse response
        # Reference: mobile_agent_v3.py Executor.parse_response()
        # Should extract:
        # - thought: <thought>...</thought>
        # - action: JSON action object
        # - description: <description>...</description>

        # Placeholder for now
        logger.warning("⚠️ Using placeholder executor response - TODO: implement LLM call")
        action_json = json.dumps({"action": "TODO"})
        thought = "Executor reasoning not yet implemented"
        description = "TODO: implement executor action selection"

        logger.info(f"💡 Thought: {thought}")
        logger.debug(f"  - Action: {action_json}")

        return ExecutorActionEvent(
            action_json=action_json,
            thought=thought,
            description=description
        )

    @step
    async def execute(
        self,
        ctx: Context,
        ev: ExecutorActionEvent
    ) -> ExecutorResultEvent:
        """
        Execute the selected action.

        This step:
        1. Converts action JSON to appropriate format
        2. Executes action on device/environment
        3. Determines outcome (success/partial/failure)
        4. Returns result with outcome and any errors
        """
        logger.info(f"⚡ Executing action: {ev.description}")

        # TODO: Convert action JSON to environment-specific format
        # Reference: mobile_agent_v3.py convert_fc_action_to_json_action()
        # action_dict = json.loads(ev.action_json)
        # converted_action = convert_to_json_action(action_dict)

        # TODO: Execute on environment
        # try:
        #     self.tools_instance.execute_action(converted_action)
        #     outcome = "A"  # Success
        #     error = "None"
        # except Exception as e:
        #     logger.error(f"Action execution failed: {e}")
        #     outcome = "C"  # Failure
        #     error = str(e)

        # Placeholder for now
        logger.warning("⚠️ Action execution not implemented - TODO: implement action execution")
        action = json.loads(ev.action_json)
        outcome = "A"  # Assume success for now
        error = "None"
        summary = ev.description

        logger.info(f"✅ Action executed with outcome: {outcome}")

        return ExecutorResultEvent(
            action=action,
            outcome=outcome,
            error=error,
            summary=summary,
            thought=ev.thought,
            action_json=ev.action_json
        )

    @step
    async def finalize(
        self,
        ctx: Context,
        ev: ExecutorResultEvent
    ) -> StopEvent:
        """Return executor results to parent workflow."""
        logger.debug("✅ Executor execution complete")

        return StopEvent(result={
            "action": ev.action,
            "outcome": ev.outcome,
            "error": ev.error,
            "summary": ev.summary,
            "thought": ev.thought,
            "action_json": ev.action_json
        })
