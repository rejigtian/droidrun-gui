"""ToolsAgent — XML tool-calling agent for device interaction.

Replaces CodeActAgent's Python code generation + exec() with a structured
XML tool-calling protocol. The LLM emits <function_calls> blocks, the agent
parses them, executes the tools, and feeds <function_results> back.

Uses the same event system and workflow structure as CodeActAgent for
compatibility with DroidAgent's execute_task() method.
"""

import asyncio
import inspect
import logging
from typing import TYPE_CHECKING, Optional, Type

from llama_index.core.llms.llm import LLM
from llama_index.core.workflow import Context, StartEvent, StopEvent, Workflow, step
from opentelemetry import trace
from pydantic import BaseModel

from droidrun.agent.codeact.events import (
    FastAgentEndEvent,
    FastAgentInputEvent,
    FastAgentOutputEvent,
    FastAgentResponseEvent,
    FastAgentToolCallEvent,
)
from droidrun.agent.codeact.xml_parser import (
    ToolCall,
    ToolResult,
    build_param_types,
    build_tool_definitions_xml,
    format_tool_results,
    parse_tool_calls,
)
from droidrun.agent.common.constants import LLM_HISTORY_LIMIT
from droidrun.agent.common.events import RecordUIStateEvent, ScreenshotEvent
from droidrun.agent.usage import get_usage_from_response
from droidrun.agent.utils.chat_utils import limit_history, to_chat_messages
from droidrun.agent.utils.inference import acall_with_retries
from droidrun.agent.utils.prompt_resolver import PromptResolver
from droidrun.agent.utils.signatures import ATOMIC_ACTION_SIGNATURES
from droidrun.agent.utils.tracing_setup import record_langfuse_screenshot
from droidrun.config_manager.config_manager import AgentConfig, TracingConfig
from droidrun.config_manager.prompt_loader import PromptLoader
from droidrun.tools import Tools

if TYPE_CHECKING:
    from droidrun.agent.droid import DroidAgentState

logger = logging.getLogger("droidrun")


class FastAgent(Workflow):
    """Agent that uses XML tool-calling instead of code generation.

    Uses ReAct cycle: Thought -> Tool Call -> Observation -> repeat until complete().
    Messages stored as list[dict], converted to ChatMessage only for LLM calls.
    """

    def __init__(
        self,
        llm: LLM,
        agent_config: AgentConfig,
        tools_instance: Tools,
        custom_tools: dict = None,
        atomic_tools: dict = None,
        debug: bool = False,
        shared_state: Optional["DroidAgentState"] = None,
        output_model: Type[BaseModel] | None = None,
        prompt_resolver: Optional[PromptResolver] = None,
        tracing_config: TracingConfig | None = None,
        *args,
        **kwargs,
    ):
        assert llm, "llm must be provided."
        super().__init__(*args, **kwargs)

        self.llm = llm
        self.agent_config = agent_config
        self.config = agent_config.fast_agent
        self.max_steps = agent_config.max_steps
        self.vision = agent_config.fast_agent.vision
        self.debug = debug
        self.tools = tools_instance
        self.shared_state = shared_state
        self.output_model = output_model
        self.prompt_resolver = prompt_resolver or PromptResolver()
        self.tracing_config = tracing_config

        self.system_prompt: dict | None = None
        self.tool_call_counter = 0
        self.remembered_info: list[str] | None = None

        # Build tool list from atomic + custom tools
        if atomic_tools is None:
            atomic_tools = ATOMIC_ACTION_SIGNATURES

        self._atomic_tools = atomic_tools
        self._custom_tools = custom_tools or {}
        merged_signatures = {**atomic_tools, **(custom_tools or {})}

        # Build callable tool functions with tools/shared_state bound
        self.tool_list = {}
        for action_name, signature in merged_signatures.items():
            func = signature["function"]
            if inspect.iscoroutinefunction(func):

                async def async_wrapper(
                    *a, f=func, ti=tools_instance, ss=shared_state, **kw
                ):
                    return await f(*a, tools=ti, shared_state=ss, **kw)

                self.tool_list[action_name] = async_wrapper
            else:

                def sync_wrapper(
                    *a, f=func, ti=tools_instance, ss=shared_state, **kw
                ):
                    return f(*a, tools=ti, shared_state=ss, **kw)

                self.tool_list[action_name] = sync_wrapper

        self.tool_list["remember"] = tools_instance.remember
        self.tool_list["complete"] = tools_instance.complete

        # Build tool descriptions for system prompt
        self.tool_descriptions = build_tool_definitions_xml(
            atomic_tools, custom_tools
        )

        # Build param type map for XML coercion
        self.param_types = build_param_types(merged_signatures)

        self._available_secrets = []
        self._output_schema = None
        if self.output_model is not None:
            self._output_schema = self.output_model.model_json_schema()

        logger.debug("FastAgent initialized.")

    async def _build_system_prompt(self) -> dict:
        """Build system prompt message."""
        template_context = {
            "tool_descriptions": self.tool_descriptions,
            "available_secrets": self._available_secrets,
            "available_tools": set(self.tool_list.keys()),
            "variables": (
                self.shared_state.custom_variables if self.shared_state else {}
            ),
            "output_schema": self._output_schema,
        }

        custom_system_prompt = self.prompt_resolver.get_prompt("fast_agent_system")
        if custom_system_prompt:
            system_text = PromptLoader.render_template(
                custom_system_prompt,
                template_context,
            )
        else:
            system_text = await PromptLoader.load_prompt(
                self.agent_config.get_fast_agent_system_prompt_path(),
                template_context,
            )
        return {"role": "system", "content": [{"text": system_text}]}

    async def _build_user_prompt(self, goal: str) -> dict:
        """Build initial user prompt message."""
        custom_user_prompt = self.prompt_resolver.get_prompt("fast_agent_user")
        if custom_user_prompt:
            user_text = PromptLoader.render_template(
                custom_user_prompt,
                {
                    "goal": goal,
                    "variables": (
                        self.shared_state.custom_variables
                        if self.shared_state
                        else {}
                    ),
                },
            )
        else:
            user_text = await PromptLoader.load_prompt(
                self.agent_config.get_fast_agent_user_prompt_path(),
                {
                    "goal": goal,
                    "variables": (
                        self.shared_state.custom_variables
                        if self.shared_state
                        else {}
                    ),
                },
            )
        return {"role": "user", "content": [{"text": user_text}]}

    @step
    async def prepare_chat(self, ctx: Context, ev: StartEvent) -> FastAgentInputEvent:
        """Initialize message history with goal."""
        self.tools._set_context(ctx)
        logger.debug("Preparing chat for task execution...")

        # Get available secrets
        if hasattr(self.tools, "credential_manager") and self.tools.credential_manager:
            self._available_secrets = await self.tools.credential_manager.get_keys()

        # Build system prompt (lazy load)
        if self.system_prompt is None:
            self.system_prompt = await self._build_system_prompt()

        # Get goal and build user message
        user_input = ev.get("input", default=None)
        assert user_input, "User input cannot be empty."

        user_message = await self._build_user_prompt(user_input)
        self.shared_state.message_history.clear()
        self.shared_state.message_history.append(user_message)

        # Store remembered info if provided
        remembered_info = ev.get("remembered_info", default=None)
        if remembered_info:
            self.remembered_info = remembered_info
            memory_text = "\n### Remembered Information:\n"
            for idx, item in enumerate(remembered_info, 1):
                memory_text += f"{idx}. {item}\n"
            self.shared_state.message_history[0]["content"].append(
                {"text": memory_text}
            )

        return FastAgentInputEvent()

    @step
    async def handle_llm_input(
        self, ctx: Context, ev: FastAgentInputEvent
    ) -> FastAgentResponseEvent | FastAgentEndEvent:
        """Get device state, call LLM, return response."""
        ctx.write_event_to_stream(ev)

        # Check then bump step counter
        if self.shared_state.step_number >= self.max_steps:
            event = FastAgentEndEvent(
                success=False,
                reason=f"Reached max step count of {self.max_steps} steps",
                tool_call_count=self.tool_call_counter,
            )
            ctx.write_event_to_stream(event)
            return event

        self.shared_state.step_number += 1
        logger.info(f"🔄 Step {self.shared_state.step_number}/{self.max_steps}")

        # Capture screenshot if needed
        screenshot = None
        if self.vision or (
            hasattr(self.tools, "save_trajectories")
            and self.tools.save_trajectories != "none"
        ):
            try:
                result = await self.tools.take_screenshot()
                if isinstance(result, tuple):
                    success, screenshot = result
                    if not success:
                        logger.warning("Screenshot capture failed")
                        screenshot = None
                else:
                    screenshot = result

                if screenshot:
                    ctx.write_event_to_stream(ScreenshotEvent(screenshot=screenshot))
                    parent_span = trace.get_current_span()
                    record_langfuse_screenshot(
                        screenshot,
                        parent_span=parent_span,
                        screenshots_enabled=bool(
                            self.tracing_config
                            and self.tracing_config.langfuse_screenshots
                        ),
                        vision_enabled=self.vision,
                    )
                    await ctx.store.set("screenshot", screenshot)
                    logger.debug("📸 Screenshot captured for FastAgent")
            except Exception as e:
                logger.warning(f"Failed to capture screenshot: {e}")

        # Get device state
        try:
            formatted_text, focused_text, a11y_tree, phone_state = (
                await self.tools.get_state()
            )

            # Update shared state
            self.shared_state.formatted_device_state = formatted_text
            self.shared_state.focused_text = focused_text
            self.shared_state.a11y_tree = a11y_tree
            self.shared_state.phone_state = phone_state

            # Extract and store package/app name
            self.shared_state.update_current_app(
                package_name=phone_state.get("packageName", "Unknown"),
                activity_name=phone_state.get("currentApp", "Unknown"),
            )

            # Stream formatted state for trajectory
            ctx.write_event_to_stream(RecordUIStateEvent(ui_state=a11y_tree))

            # Add device state to last user message
            self.shared_state.message_history[-1]["content"].append(
                {"text": f"\n{formatted_text}\n"}
            )

        except Exception as e:
            logger.warning(
                f"⚠️ Error retrieving state from the connected device: {e}"
            )
            if self.debug:
                logger.error("State retrieval error details:", exc_info=True)

        # Add screenshot to message if vision enabled
        if self.vision and screenshot:
            self.shared_state.message_history[-1]["content"].append(
                {"image": screenshot}
            )

        # Limit history and prepare for LLM
        limited_history = limit_history(
            self.shared_state.message_history,
            LLM_HISTORY_LIMIT * 2,
            preserve_first=True,
        )

        # Build final messages: system + history
        messages_to_send = [self.system_prompt] + limited_history
        chat_messages = to_chat_messages(messages_to_send)

        # Call LLM
        logger.info("FastAgent response:", extra={"color": "yellow"})
        response = await acall_with_retries(
            self.llm, chat_messages, stream=self.agent_config.streaming
        )

        if response is None:
            return FastAgentEndEvent(
                success=False,
                reason="LLM response is None. This is a critical error.",
                tool_call_count=self.tool_call_counter,
            )

        # Extract usage
        usage = None
        try:
            usage = get_usage_from_response(self.llm.class_name(), response)
        except Exception as e:
            logger.warning(f"Could not get usage: {e}")

        # Store assistant response
        response_text = response.message.content
        self.shared_state.message_history.append(
            {"role": "assistant", "content": [{"text": response_text}]}
        )

        # Parse tool calls from response
        thought, tool_calls = parse_tool_calls(response_text, self.param_types)

        # Extract just the <function_calls> blocks for the event
        tool_calls_xml = None
        if tool_calls:
            from droidrun.agent.codeact.xml_parser import OPEN_TAG, CLOSE_TAG

            blocks = []
            for part in response_text.split(OPEN_TAG)[1:]:
                close_idx = part.find(CLOSE_TAG)
                if close_idx != -1:
                    blocks.append(OPEN_TAG + part[: close_idx + len(CLOSE_TAG)])
            tool_calls_xml = "\n".join(blocks) if blocks else None

        # Store tool calls in context for execute step (avoid re-parsing)
        if tool_calls:
            await ctx.store.set("pending_tool_calls", tool_calls)

        # Update unified state
        self.shared_state.last_thought = thought

        event = FastAgentResponseEvent(
            thought=thought,
            code=tool_calls_xml,
            usage=usage,
        )
        ctx.write_event_to_stream(event)
        return event

    @step
    async def handle_llm_output(
        self, ctx: Context, ev: FastAgentResponseEvent
    ) -> FastAgentToolCallEvent | FastAgentInputEvent:
        """Route to execution or request tool call if missing."""
        has_tool_calls = ev.code is not None

        if not ev.thought:
            logger.warning("LLM provided tool calls without reasoning.")
            no_thoughts_text = (
                "Your previous response called tools without explaining your reasoning first. "
                "Remember to always describe your thought process and plan *before* calling tools.\n\n"
                "The tool calls you made will be executed below.\n\n"
                "Now, describe the next step you will take to address the original goal."
            )
            self.shared_state.message_history.append(
                {"role": "user", "content": [{"text": no_thoughts_text}]}
            )
        else:
            logger.debug(f"Reasoning: {ev.thought}")

        if has_tool_calls:
            event = FastAgentToolCallEvent(tool_calls_repr=ev.code)
            ctx.write_event_to_stream(event)
            return event
        else:
            # No tool calls — ask for them
            no_tools_text = (
                "No tool calls were provided. If you want to mark the task as complete "
                "(whether it failed or succeeded), use the `complete` tool:\n\n"
                "<function_calls>\n"
                '<invoke name="complete">\n'
                '<parameter name="success">true</parameter>\n'
                '<parameter name="message">Explanation here</parameter>\n'
                "</invoke>\n"
                "</function_calls>"
            )
            self.shared_state.message_history.append(
                {"role": "user", "content": [{"text": no_tools_text}]}
            )
            return FastAgentInputEvent()

    @step
    async def execute_code(
        self, ctx: Context, ev: FastAgentToolCallEvent
    ) -> FastAgentOutputEvent | FastAgentEndEvent:
        """Execute parsed tool calls and return results."""
        tool_calls = await ctx.store.get("pending_tool_calls", [])

        if not tool_calls:
            event = FastAgentOutputEvent(output="No tool calls to execute.")
            ctx.write_event_to_stream(event)
            return event

        results: list[ToolResult] = []

        for call in tool_calls:
            logger.debug(f"Executing: {call.name}({call.parameters})")
            self.tool_call_counter += 1

            result = await self._execute_tool_call(call)
            results.append(result)

            # Check if complete() was called successfully
            if self.tools.finished:
                logger.debug("✅ Task marked as complete via complete() tool")

                success = (
                    self.tools.success if self.tools.success is not None else False
                )
                reason = (
                    self.tools.reason
                    if self.tools.reason
                    else "Task completed without reason"
                )
                self.tools.finished = False

                event = FastAgentEndEvent(
                    success=success,
                    reason=reason,
                    tool_call_count=self.tool_call_counter,
                )
                ctx.write_event_to_stream(event)
                return event

        # Format results
        results_xml = format_tool_results(results)
        logger.info("💡 Tool results:", extra={"color": "dim"})
        logger.info(f"{results_xml}")
        await asyncio.sleep(self.agent_config.after_sleep_action)

        # Update remembered info
        self.remembered_info = self.tools.memory

        event = FastAgentOutputEvent(output=results_xml)
        ctx.write_event_to_stream(event)
        return event

    async def _execute_tool_call(self, call: ToolCall) -> ToolResult:
        """Execute a single tool call and return the result."""
        tool_func = self.tool_list.get(call.name)

        if tool_func is None:
            return ToolResult(
                name=call.name,
                output=f"Unknown tool: {call.name}. Available tools: {list(self.tool_list.keys())}",
                is_error=True,
            )

        params = call.parameters
        # Remap 'message' -> 'reason' for complete() (LLM sees "message", function expects "reason")
        if call.name == "complete" and "message" in params:
            params = {**params, "reason": params.pop("message")}

        try:
            if inspect.iscoroutinefunction(tool_func):
                result = await tool_func(**params)
            else:
                result = tool_func(**params)

            output = str(result) if result is not None else "Tool executed successfully."
            return ToolResult(name=call.name, output=output)

        except TypeError as e:
            return ToolResult(
                name=call.name,
                output=f"Invalid arguments: {e}",
                is_error=True,
            )
        except Exception as e:
            logger.error(f"💥 Tool {call.name} failed: {e}")
            if self.debug:
                logger.error("Exception details:", exc_info=True)
            return ToolResult(
                name=call.name,
                output=f"Error: {type(e).__name__}: {e}",
                is_error=True,
            )

    @step
    async def handle_execution_result(
        self, ctx: Context, ev: FastAgentOutputEvent
    ) -> FastAgentInputEvent:
        """Add execution result to history and loop back."""
        output = ev.output or "Tool executed, but produced no output."

        # Add results as user message
        self.shared_state.message_history.append(
            {"role": "user", "content": [{"text": output}]}
        )

        return FastAgentInputEvent()

    @step
    async def finalize(self, ev: FastAgentEndEvent, ctx: Context) -> StopEvent:
        self.tools.finished = False
        ctx.write_event_to_stream(ev)

        return StopEvent(
            result={
                "success": ev.success,
                "reason": ev.reason,
                "tool_call_count": ev.tool_call_count,
            }
        )
