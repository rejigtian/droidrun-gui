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

from llama_index.core.llms import TextBlock, ImageBlock, ChatMessage
from llama_index.core.workflow import Workflow, step, Context, StartEvent, StopEvent
from llama_index.core.llms.llm import LLM

from droidrun.agent.executor.prompts import build_executor_system_prompt, parse_executor_response
from droidrun.agent.executor.events import (
    ExecutorActionEvent,
    ExecutorResultEvent
)
from droidrun.agent.utils.tools import (
    click, long_press, type, system_button, swipe, open_app
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

        logger.info("✅ ExecutorAgent initialized successfully.")


    @step
    async def think(
        self,
        ctx: Context["DroidAgentState"],
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

        state = await ctx.store.get_state()


        app_card = ""  # TODO: Implement app card retrieval

        system_prompt = build_executor_system_prompt(
            state=state,
            subgoal=subgoal,
            app_card=app_card
        )

        
        blocks = [TextBlock(text=system_prompt)]
        if self.vision:
            screenshot = state.screenshot
            assert screenshot is not None, "Screenshot is required for vision but got None"
            blocks.append(ImageBlock(image=screenshot))
        messages = [ChatMessage(role="system", blocks=blocks)]

        try:
            response = await self.llm.achat(messages=messages)
            response_text = str(response)
        except Exception as e:
            logger.error(f"❌ LLM call failed: {e}")
            return ExecutorActionEvent(
                action_json=json.dumps({"action": "invalid"}),
                thought=f"LLM call failed: {str(e)}",
                description="Failed to get action from LLM"
            )

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
        ctx: Context["DroidAgentState"],
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
            action_type = action_dict.get("action", "unknown")
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

    @step
    async def finalize(
        self,
        ctx: Context["DroidAgentState"],
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
