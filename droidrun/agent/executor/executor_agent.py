"""
ExecutorAgent - Action execution workflow.

This agent is responsible for:
- Taking a specific subgoal from the Manager
- Analyzing the current UI state
- Selecting and executing appropriate actions
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from llama_index.core.llms import ChatMessage, ImageBlock, TextBlock
from llama_index.core.llms.llm import LLM
from llama_index.core.workflow import Context, StartEvent, StopEvent, Workflow, step

from droidrun.agent.executor.events import ExecutorActionEvent, ExecutorResultEvent
from droidrun.agent.executor.prompts import build_executor_system_prompt, parse_executor_response
from droidrun.agent.utils.tools import click, long_press, open_app, swipe, system_button, type
from droidrun.agent.utils.inference import acall_with_retries
from droidrun.config_manager import config
import asyncio

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
        shared_state: "DroidAgentState",
        persona=None,
        custom_tools: dict = None,
        debug: bool = False,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.llm = llm
        self.vision = vision
        self.tools_instance = tools_instance
        self.shared_state = shared_state
        self.persona = persona
        self.custom_tools = custom_tools or {}
        self.debug = debug

        logger.info("✅ ExecutorAgent initialized successfully.")


    @step
    async def think(
        self,
        ctx: Context,
        ev: StartEvent
    ) -> ExecutorActionEvent:
        """
        Executor decides which action to take.

        This step:
        1. Calls LLM with executor prompt and context
        2. Parses the response for action, thought, description
        3. Validates action format (blocks answer actions!)
        4. Returns action event
        """
        subgoal = ev.get("subgoal", "")
        logger.info(f"🧠 Executor thinking about action for: {subgoal}")

        app_card = ""  # TODO: Implement app card retrieval

        system_prompt = build_executor_system_prompt(
            state=self.shared_state,
            subgoal=subgoal,
            app_card=app_card
        )

        blocks = [TextBlock(text=system_prompt)]
        if self.vision:
            screenshot = self.shared_state.screenshot
            if screenshot is not None:
                blocks.append(ImageBlock(image=screenshot))
                logger.debug("📸 Using screenshot for Executor")
            else:
                logger.warning("⚠️ Vision enabled but no screenshot available")
        messages = [ChatMessage(role="user", blocks=blocks)]

        try:
            response = await acall_with_retries(self.llm, messages)
            response_text = str(response)
        except Exception as e:
            raise RuntimeError(f"Error calling LLM in executor: {e}") from e

        # Parse response
        try:
            parsed = parse_executor_response(response_text)
        except Exception as e:
            logger.error(f"❌ Failed to parse executor response: {e}")
            return ExecutorActionEvent(
                action_json=json.dumps({"action": "invalid"}),
                thought=f"Failed to parse response: {str(e)}",
                description="Invalid response format from LLM"
            )

        logger.info(f"💡 Thought: {parsed['thought']}")
        logger.info(f"🎯 Action: {parsed['action']}")
        logger.debug(f"  - Description: {parsed['description']}")

        return ExecutorActionEvent(
            action_json=parsed["action"],
            thought=parsed["thought"],
            description=parsed["description"]
        )

    @step
    async def execute(
        self,
        ctx: Context,
        ev: ExecutorActionEvent
    ) -> ExecutorResultEvent:
        """
        Execute the selected action using the tools instance.

        Maps action JSON to appropriate tool calls and handles execution.
        """
        logger.info(f"⚡ Executing action: {ev.description}")

        # Parse action JSON
        try:
            action_dict = json.loads(ev.action_json)
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse action JSON: {e}")
            return ExecutorResultEvent(
                action={"action": "invalid"},
                outcome=False,
                error=f"Invalid action JSON: {str(e)}",
                summary="Failed to parse action",
                thought=ev.thought,
                action_json=ev.action_json
            )

        # Execute the action
        outcome, error, summary = await self._execute_action(action_dict, ev.description)

        if outcome:
            await asyncio.sleep(config.agent.after_sleep_action)

        logger.info(f"{'✅' if outcome else '❌'} Execution complete: {summary}")

        return ExecutorResultEvent(
            action=action_dict,
            outcome=outcome,
            error=error,
            summary=summary,
            thought=ev.thought,
            action_json=ev.action_json
        )

    async def _execute_action(self, action_dict: dict, description: str) -> tuple[bool, str, str]:
        """
        Execute a single action based on the action dictionary.

        Args:
            action_dict: Dictionary containing action type and parameters
            description: Human-readable description of the action

        Returns:
            Tuple of (outcome: bool, error: str, summary: str)
        """

        action_type = action_dict.get("action", "unknown")

        # Check custom_tools first (before atomic actions)
        if action_type in self.custom_tools:
            return await self._execute_custom_tool(action_type, action_dict)

        try:
            if action_type == "click":
                index = action_dict.get("index")
                if index is None:
                    return False, "Missing 'index' parameter", "Failed: click requires index"

                result = click(self.tools_instance, index)
                return True, "None", f"Clicked element at index {index}"

            elif action_type == "long_press":
                index = action_dict.get("index")
                if index is None:
                    return False, "Missing 'index' parameter", "Failed: long_press requires index"

                success = long_press(self.tools_instance, index)
                if success:
                    return True, "None", f"Long pressed element at index {index}"
                else:
                    return False, "Long press failed", f"Failed to long press at index {index}"

            elif action_type == "type":
                text = action_dict.get("text")
                index = action_dict.get("index", -1)

                if text is None:
                    return False, "Missing 'text' parameter", "Failed: type requires text"

                result = type(self.tools_instance, text, index)
                return True, "None", f"Typed '{text}' into element at index {index}"

            elif action_type == "system_button":
                button = action_dict.get("button")
                if button is None:
                    return False, "Missing 'button' parameter", "Failed: system_button requires button"

                result = system_button(self.tools_instance, button)
                if "Error" in result:
                    return False, result, f"Failed to press {button} button"
                return True, "None", f"Pressed {button} button"

            elif action_type == "swipe":
                coordinate = action_dict.get("coordinate")
                coordinate2 = action_dict.get("coordinate2")

                if coordinate is None or coordinate2 is None:
                    return False, "Missing coordinate parameters", "Failed: swipe requires coordinate and coordinate2"

                # Validate coordinate format before calling swipe
                if not isinstance(coordinate, list) or len(coordinate) != 2:
                    return False, f"Invalid coordinate format: {coordinate}", "Failed: coordinate must be [x, y]"
                if not isinstance(coordinate2, list) or len(coordinate2) != 2:
                    return False, f"Invalid coordinate2 format: {coordinate2}", "Failed: coordinate2 must be [x, y]"

                success = swipe(self.tools_instance, coordinate, coordinate2)
                if success:
                    return True, "None", f"Swiped from {coordinate} to {coordinate2}"
                else:
                    return False, "Swipe failed", f"Failed to swipe from {coordinate} to {coordinate2}"

            elif action_type == "open_app":
                text = action_dict.get("text")
                if text is None:
                    return False, "Missing 'text' parameter", "Failed: open_app requires text"

                result = open_app(self.tools_instance, text)
                return True, "None", f"Opened app: {text}"

            else:
                return False, f"Unknown action type: {action_type}", f"Failed: unknown action '{action_type}'"

        except Exception as e:
            logger.error(f"❌ Exception during action execution: {e}", exc_info=True)
            return False, f"Exception: {str(e)}", f"Failed to execute {action_type}: {str(e)}"

    async def _execute_custom_tool(self, action_type: str, action_dict: dict) -> tuple[bool, str, str]:
        """
        Execute a custom tool based on the action dictionary.

        Args:
            action_type: The custom tool name
            action_dict: Dictionary containing action parameters

        Returns:
            Tuple of (outcome: bool, error: str, summary: str)
        """
        try:
            tool_spec = self.custom_tools[action_type]
            tool_func = tool_spec["function"]

            # Extract arguments (exclude 'action' key)
            tool_args = {k: v for k, v in action_dict.items() if k != "action"}

            # Execute the custom tool function
            # First argument is always tools_instance (bound in same pattern as atomic actions)
            if asyncio.iscoroutinefunction(tool_func):
                result = await tool_func(self.tools_instance, **tool_args)
            else:
                result = tool_func(self.tools_instance, **tool_args)

            # Success case
            summary = f"Executed custom tool '{action_type}'"
            if result is not None:
                summary += f": {str(result)}"

            return True, "None", summary

        except TypeError as e:
            # Likely missing or wrong arguments
            error_msg = f"Invalid arguments for custom tool '{action_type}': {str(e)}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg, f"Failed: {action_type}"

        except Exception as e:
            # General execution error
            error_msg = f"Error executing custom tool '{action_type}': {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return False, error_msg, f"Failed: {action_type}"

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
