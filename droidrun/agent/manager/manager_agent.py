"""
ManagerAgent - Planning and reasoning workflow.

This agent is responsible for:
- Analyzing the current state
- Creating plans and subgoals
- Tracking progress
- Deciding when tasks are complete
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List

from llama_index.core.llms.llm import LLM
from llama_index.core.workflow import Context, StartEvent, StopEvent, Workflow, step

from droidrun.agent.manager.events import ManagerPlanEvent, ManagerThinkingEvent
from droidrun.agent.manager.prompts import build_manager_system_prompt, parse_manager_response
from droidrun.agent.utils import convert_messages_to_chatmessages
from droidrun.agent.utils.chat_utils import remove_empty_messages
from droidrun.agent.utils.device_state_formatter import get_device_state_exact_format
from droidrun.agent.utils.inference import acall_with_retries
from droidrun.agent.utils.tools import build_custom_tool_descriptions

if TYPE_CHECKING:
    from droidrun.agent.droid.events import DroidAgentState
    from droidrun.tools import Tools

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
        tools_instance: "Tools",
        shared_state: "DroidAgentState",
        custom_tools: dict = None,
        debug: bool = False,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.llm = llm
        self.vision = vision
        self.personas = personas
        self.tools_instance = tools_instance
        self.shared_state = shared_state
        self.custom_tools = custom_tools or {}
        self.debug = debug

        logger.info("✅ ManagerAgent initialized successfully.")

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _build_system_prompt(
        self,
        has_text_to_modify: bool
    ) -> str:
        """
        Build system prompt with all context.

        Args:
            has_text_to_modify: Whether text manipulation mode is enabled

        Returns:
            Complete system prompt
        """

        # Get error history if error_flag_plan is set
        error_history = []
        if self.shared_state.error_flag_plan:
            k = self.shared_state.err_to_manager_thresh
            error_history = [
                {
                    "action": act,
                    "summary": summ,
                    "error": err_des
                }
                for act, summ, err_des in zip(
                    self.shared_state.action_history[-k:],
                    self.shared_state.summary_history[-k:],
                    self.shared_state.error_descriptions[-k:], strict=True
                )
            ]

        # Build custom tools descriptions
        custom_tools_descriptions = build_custom_tool_descriptions(self.custom_tools)

        return build_manager_system_prompt(
            instruction=self.shared_state.instruction,
            has_text_to_modify=has_text_to_modify,
            app_card="",  # TODO: implement app card retrieval system
            device_date=self.tools_instance.get_date(),
            important_notes="",  # TODO: expose important_notes in DroidAgentState if needed
            error_flag=self.shared_state.error_flag_plan,
            error_history=error_history,
            custom_tools_descriptions=custom_tools_descriptions
        )

    def _build_messages_with_context(
        self,
        system_prompt: str,
        screenshot: str = None
    ) -> list[dict]:
        """
        Build messages from history and inject current context.

        Args:
            system_prompt: System prompt to use
            screenshot: Path to current screenshot (if vision enabled)

        Returns:
            List of message dicts ready for conversion
        """
        import copy

        # Start with system message
        messages = [
            {"role": "system", "content": [{"text": system_prompt}]}
        ]

        # Add accumulated message history (deep copy to avoid mutation)
        messages.extend(copy.deepcopy(self.shared_state.message_history))

        # ====================================================================
        # Inject memory, device state, screenshot to LAST user message
        # ====================================================================
        # Find last user message index
        user_indices = [i for i, msg in enumerate(messages) if msg['role'] == 'user']

        if user_indices:
            last_user_idx = user_indices[-1]

            # Add memory to last user message
            current_memory = (self.shared_state.memory or "").strip()
            if current_memory:
                if messages[last_user_idx]['content'] and 'text' in messages[last_user_idx]['content'][0]:
                    messages[last_user_idx]['content'][0]['text'] += f"\n<memory>\n{current_memory}\n</memory>\n"
                else:
                    messages[last_user_idx]['content'].insert(0, {"text": f"<memory>\n{current_memory}\n</memory>\n"})

            # Add device state to last user message
            current_a11y = (self.shared_state.ui_elements_list_after or self.shared_state.device_state_text or "").strip()
            if current_a11y:
                if messages[last_user_idx]['content'] and 'text' in messages[last_user_idx]['content'][0]:
                    messages[last_user_idx]['content'][0]['text'] += f"\n<device_state>\n{current_a11y}\n</device_state>\n"
                else:
                    messages[last_user_idx]['content'].insert(0, {"text": f"<device_state>\n{current_a11y}\n</device_state>\n"})

            # Add screenshot to last user message
            if screenshot and self.vision:
                messages[last_user_idx]['content'].append({"image": screenshot})

            # Add previous device state to SECOND-TO-LAST user message (if exists)
            if len(user_indices) >= 2:
                second_last_user_idx = user_indices[-2]
                prev_a11y = (self.shared_state.ui_elements_list_before or "").strip()

                if prev_a11y:
                    if messages[second_last_user_idx]['content'] and 'text' in messages[second_last_user_idx]['content'][0]:
                        messages[second_last_user_idx]['content'][0]['text'] += f"\n<device_state>\n{prev_a11y}\n</device_state>\n"
                    else:
                        messages[second_last_user_idx]['content'].insert(0, {"text": f"<device_state>\n{prev_a11y}\n</device_state>\n"})
        messages = remove_empty_messages(messages)
        return messages

    async def _validate_and_retry_llm_call(
        self,
        ctx: Context,
        initial_messages: list[dict],
        initial_response: str
    ) -> str:
        """
        Validate LLM response and retry if needed.

        Args:
            ctx: Workflow context
            initial_messages: Messages sent to LLM
            initial_response: Initial LLM response

        Returns:
            Final validated response (may be same as initial or from retry)
        """

        output_planning = initial_response
        parsed = parse_manager_response(output_planning)

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            # Validation rules
            error_message = None

            if parsed["answer"] and not parsed["plan"]:
                # Valid: answer without plan (task complete)
                break
            elif parsed["plan"] and parsed["answer"]:
                error_message = "You cannot use both request_accomplished tag while the plan is not finished. If you want to use request_accomplished tag, please make sure the plan is finished.\nRetry again."
            elif not parsed["plan"]:
                error_message = "You must provide a plan to complete the task. Please provide a plan with the correct format."
            else:
                # Valid: plan without answer
                break

            if error_message:
                retry_count += 1
                logger.warning(f"Manager response invalid (retry {retry_count}/{max_retries}): {error_message}")

                # Retry with error message
                retry_messages = initial_messages + [
                    {"role": "assistant", "content": [{"text": output_planning}]},
                    {"role": "user", "content": [{"text": error_message}]}
                ]

                chat_messages = convert_messages_to_chatmessages(retry_messages)

                try:
                    response = await acall_with_retries(self.llm, chat_messages)
                    output_planning = response.message.content
                    parsed = parse_manager_response(output_planning)
                except Exception as e:
                    logger.error(f"LLM retry failed: {e}")
                    break  # Give up retrying

        return output_planning

    # ========================================================================
    # Workflow Steps
    # ========================================================================

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
        2. Detects text manipulation mode
        3. Builds message history entry with last action
        4. Stores context for think() step
        """
        logger.info("💬 Preparing manager input...")

        # ====================================================================
        # Step 1: Get device state (UI elements accessibility tree)
        # ====================================================================
        device_state_text, focused_text = get_device_state_exact_format(self.tools_instance.get_state())

        # ====================================================================
        # Step 2: Capture screenshot if vision enabled
        # ====================================================================
        screenshot = None
        if self.vision:
            try:
                result = self.tools_instance.take_screenshot()
                if isinstance(result, tuple):
                    success, screenshot = result
                    if not success:
                        screenshot = None
                else:
                    screenshot = result
                logger.debug("📸 Screenshot captured for Manager")
            except Exception as e:
                logger.warning(f"Failed to capture screenshot: {e}")
                screenshot = None

        # ====================================================================
        # Step 3: Detect text manipulation mode
        # ====================================================================
        focused_text = focused_text or ""
        focused_text_clean = focused_text.replace("'", "").strip()

        # Check if focused text differs from last typed text
        # last_typed_text = ""
        # if self.shared_state.action_history:
        #     recent_actions = self.shared_state.action_history[-1:] if len(self.shared_state.action_history) >= 1 else []
        #     for action in reversed(recent_actions):
        #         if isinstance(action, dict) and action.get('action') == 'type':
        #             last_typed_text = action.get('text', '')
        #             break

        has_text_to_modify = (focused_text_clean != "")

        # ====================================================================
        # Step 4: Update state with device info
        # ====================================================================
        self.shared_state.device_state_text = device_state_text
        self.shared_state.focused_text = focused_text
        # Shift UI elements: before ← after, after ← current
        self.shared_state.ui_elements_list_before = self.shared_state.ui_elements_list_after
        self.shared_state.ui_elements_list_after = device_state_text

        # ====================================================================
        # Step 5: Build user message entry
        # ====================================================================
        parts = []

        # Add context from last action
        if self.shared_state.finish_thought:
            parts.append(f"<thought>\n{self.shared_state.finish_thought}\n</thought>\n")

        if self.shared_state.last_action:
            import json
            action_str = json.dumps(self.shared_state.last_action)
            parts.append(f"<last_action>\n{action_str}\n</last_action>\n")

        if self.shared_state.last_summary:
            parts.append(f"<last_action_description>\n{self.shared_state.last_summary}\n</last_action_description>\n")

        
        self.shared_state.message_history.append({
            "role": "user",
            "content": [{"text": "".join(parts)}]
        })

        # Store has_text_to_modify and screenshot for next step
        self.shared_state.has_text_to_modify = has_text_to_modify
        self.shared_state.screenshot = screenshot

        logger.debug(f"  - Device state prepared (text_modify={has_text_to_modify}, screenshot={screenshot is not None})")
        return ManagerThinkingEvent()

    @step
    async def think(
        self,
        ctx: Context,
        ev: ManagerThinkingEvent
    ) -> ManagerPlanEvent:
        """
        Manager reasons and creates plan.

        This step:
        1. Builds system prompt with all context
        2. Builds messages from history with injected context
        3. Calls LLM
        4. Validates and retries if needed
        5. Parses response
        6. Updates state (memory, message history)
        """
        logger.info("🧠 Manager thinking about the plan...")

        has_text_to_modify = self.shared_state.has_text_to_modify
        screenshot = self.shared_state.screenshot

        # ====================================================================
        # Step 1: Build system prompt
        # ====================================================================
        system_prompt = self._build_system_prompt(has_text_to_modify)

        # ====================================================================
        # Step 2: Build messages with context
        # ====================================================================
        messages = self._build_messages_with_context(
            system_prompt=system_prompt,
            screenshot=screenshot
        )

        # ====================================================================
        # Step 3: Convert messages and call LLM
        # ====================================================================
        chat_messages = convert_messages_to_chatmessages(messages)

        try:
            response = await acall_with_retries(self.llm, chat_messages)
            output_planning = response.message.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise RuntimeError(f"Error calling LLM in manager: {e}") from e

        # ====================================================================
        # Step 4: Validate and retry if needed
        # ====================================================================
        output_planning = await self._validate_and_retry_llm_call(
            ctx=ctx,
            initial_messages=messages,
            initial_response=output_planning
        )

        # ====================================================================
        # Step 5: Parse response
        # ====================================================================
        parsed = parse_manager_response(output_planning)

        # ====================================================================
        # Step 6: Update state
        # ====================================================================
        memory_update = parsed.get("memory", "").strip()

        # Update memory (append, not replace)
        if memory_update:
            if self.shared_state.memory:
                self.shared_state.memory += "\n" + memory_update
            else:
                self.shared_state.memory = memory_update

        # Append assistant response to message history
        self.shared_state.message_history.append({
            "role": "assistant",
            "content": [{"text": output_planning}]
        })

        # Update planning fields
        self.shared_state.plan = parsed["plan"]
        self.shared_state.current_subgoal = parsed["current_subgoal"]
        self.shared_state.completed_plan = parsed.get("completed_subgoal", "No completed subgoal.")
        self.shared_state.finish_thought = parsed["thought"]
        self.shared_state.manager_answer = parsed["answer"]

        logger.info(f"📝 Plan: {parsed['plan'][:100]}...")
        logger.debug(f"  - Current subgoal: {parsed['current_subgoal']}")
        logger.debug(f"  - Manager answer: {parsed['answer'][:50] if parsed['answer'] else 'None'}")

        return ManagerPlanEvent(
            plan=parsed["plan"],
            current_subgoal=parsed["current_subgoal"],
            completed_plan=parsed.get("completed_subgoal", "No completed subgoal."),
            thought=parsed["thought"],
            manager_answer=parsed["answer"],
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
