"""
Shared event handler for CLI, TUI and SDK.

Translates workflow events into ``logging`` calls with ``extra`` params
(color, step_increment, etc.).  The actual rendering is handled by
whichever ``logging.Handler`` is attached (CLILogHandler, TUILogHandler, …).
"""

import logging

from droidrun.agent.codeact.events import (
    CodeActCodeEvent,
    CodeActEndEvent,
    CodeActInputEvent,
    CodeActOutputEvent,
    CodeActResponseEvent,
    FastAgentEndEvent,
    FastAgentInputEvent,
    FastAgentOutputEvent,
    FastAgentResponseEvent,
    FastAgentToolCallEvent,
)
from droidrun.agent.common.events import (
    InputTextActionEvent,
    RecordUIStateEvent,
    ScreenshotEvent,
    SwipeActionEvent,
    TapActionEvent,
)
from droidrun.agent.droid.events import (
    ExecutorResultEvent,
    FastAgentExecuteEvent,
    FastAgentResultEvent,
    FinalizeEvent,
)
from droidrun.agent.executor.events import (
    ExecutorActionEvent,
    ExecutorActionResultEvent,
)
from droidrun.agent.manager.events import (
    ManagerContextEvent,
    ManagerPlanDetailsEvent,
    ManagerResponseEvent,
)
from droidrun.agent.scripter.events import ScripterThinkingEvent

logger = logging.getLogger("droidrun")


class EventHandler:
    """Translates workflow events into logger calls.

    No UI state tracking — purely converts events into log records with
    ``extra`` params so that any attached handler can render them.
    """

    def handle(self, event) -> None:  # noqa: C901
        # ── Screenshots / UI state ──────────────────────────────────
        if isinstance(event, ScreenshotEvent):
            logger.debug("📸 Taking screenshot...")

        elif isinstance(event, RecordUIStateEvent):
            logger.debug("✏️ Recording UI state")

        # ── Manager events (reasoning mode) ─────────────────────────
        elif isinstance(event, ManagerContextEvent):
            logger.debug("🧠 Manager preparing context...")

        elif isinstance(event, ManagerResponseEvent):
            logger.debug("📥 Manager received LLM response")

        elif isinstance(event, ManagerPlanDetailsEvent):
            if event.thought:
                preview = (
                    event.thought[:120] + "..."
                    if len(event.thought) > 120
                    else event.thought
                )
                logger.debug(f"💭 Thought: {preview}", extra={"color": "cyan"})
            if event.subgoal:
                preview = (
                    event.subgoal[:150] + "..."
                    if len(event.subgoal) > 150
                    else event.subgoal
                )
                logger.debug(f"📋 Next step: {preview}", extra={"color": "yellow"})
            if event.answer:
                preview = (
                    event.answer[:200] + "..."
                    if len(event.answer) > 200
                    else event.answer
                )
                logger.debug(f"💬 Answer: {preview}", extra={"color": "green"})
            if event.plan:
                logger.debug(f"▸ {event.plan}", extra={"color": "yellow"})
            if event.memory_update:
                logger.debug(
                    f"🧠 Memory: {event.memory_update[:100]}...",
                    extra={"color": "cyan"},
                )

        # ── Executor events (reasoning mode) ────────────────────────
        elif isinstance(event, ExecutorActionEvent):
            if event.description:
                logger.debug(
                    f"🎯 Action: {event.description}", extra={"color": "yellow"}
                )
            if event.thought:
                preview = (
                    event.thought[:120] + "..."
                    if len(event.thought) > 120
                    else event.thought
                )
                logger.debug(f"💭 Reasoning: {preview}", extra={"color": "cyan"})

        elif isinstance(event, ExecutorActionResultEvent):
            if event.success:
                logger.debug(f"✅ {event.summary}", extra={"color": "green"})
            else:
                error_msg = event.error or "Unknown error"
                logger.debug(
                    f"❌ {event.summary} ({error_msg})", extra={"color": "red"}
                )

        elif isinstance(event, ExecutorResultEvent):
            logger.debug("Step complete", extra={"color": "magenta"})

        # ── CodeAct events (direct mode) ────────────────────────────
        elif isinstance(event, CodeActInputEvent):
            logger.debug("💬 Task input received...")

        elif isinstance(event, CodeActResponseEvent):
            logger.debug("CodeAct response", extra={"color": "magenta"})
            if event.thought:
                preview = (
                    event.thought[:150] + "..."
                    if len(event.thought) > 150
                    else event.thought
                )
                logger.debug(f"🧠 Thinking: {preview}", extra={"color": "cyan"})
            if event.code:
                logger.debug("💻 Executing action code", extra={"color": "yellow"})
                logger.debug(f"{event.code}", extra={"color": "blue"})

        elif isinstance(event, CodeActCodeEvent):
            logger.debug("⚡ Executing action...", extra={"color": "yellow"})

        elif isinstance(event, CodeActOutputEvent):
            if event.output:
                output = str(event.output)
                preview = output[:100] + "..." if len(output) > 100 else output
                if "Error" in output or "Exception" in output:
                    logger.debug(f"❌ Action error: {preview}", extra={"color": "red"})
                else:
                    logger.debug(
                        f"⚡ Action result: {preview}", extra={"color": "green"}
                    )

        elif isinstance(event, CodeActEndEvent):
            status = "done" if event.success else "failed"
            color = "green" if event.success else "red"
            logger.debug(
                f"■ {status}: {event.reason} ({event.code_executions} runs)",
                extra={"color": color},
            )

        # ── FastAgent events (direct mode, XML tool-calling) ────────
        elif isinstance(event, FastAgentInputEvent):
            logger.debug("💬 Task input received...")

        elif isinstance(event, FastAgentResponseEvent):
            logger.debug("FastAgent response", extra={"color": "magenta"})
            if event.thought:
                preview = (
                    event.thought[:150] + "..."
                    if len(event.thought) > 150
                    else event.thought
                )
                logger.debug(f"🧠 Thinking: {preview}", extra={"color": "cyan"})
            if event.code:
                logger.debug("💻 Executing action code", extra={"color": "yellow"})
                logger.debug(f"{event.code}", extra={"color": "blue"})

        elif isinstance(event, FastAgentToolCallEvent):
            logger.debug("⚡ Executing tool calls...", extra={"color": "yellow"})

        elif isinstance(event, FastAgentOutputEvent):
            if event.output:
                output = str(event.output)
                preview = output[:100] + "..." if len(output) > 100 else output
                if "Error" in output or "Exception" in output:
                    logger.debug(f"❌ Action error: {preview}", extra={"color": "red"})
                else:
                    logger.debug(
                        f"⚡ Action result: {preview}", extra={"color": "green"}
                    )

        elif isinstance(event, FastAgentEndEvent):
            status = "done" if event.success else "failed"
            color = "green" if event.success else "red"
            logger.debug(
                f"■ {status}: {event.reason} ({event.tool_call_count} runs)",
                extra={"color": color},
            )

        # ── FastAgent coordination events ────────────────────────────
        elif isinstance(event, FastAgentExecuteEvent):
            logger.debug("🔧 Starting task execution...", extra={"color": "magenta"})

        elif isinstance(event, FastAgentResultEvent):
            if event.success:
                logger.debug(f"Task result: {event.reason}", extra={"color": "green"})
            else:
                logger.debug(f"Task failed: {event.reason}", extra={"color": "red"})

        # ── Scripter events ─────────────────────────────────────────
        elif isinstance(event, ScripterThinkingEvent):
            if event.thought:
                logger.debug(f"    {event.thought}", extra={"color": "cyan"})
            if event.code:
                logger.debug("  $ script", extra={"color": "blue"})
                for line in event.code.split("\n")[:5]:
                    if line.strip():
                        logger.debug(f"    {line}", extra={"color": "blue"})

        # ── Macro / action events ───────────────────────────────────
        elif isinstance(event, TapActionEvent):
            logger.debug(f"› tap  {event.description}", extra={"color": "white"})

        elif isinstance(event, SwipeActionEvent):
            logger.debug(f"› swipe  {event.description}", extra={"color": "white"})

        elif isinstance(event, InputTextActionEvent):
            logger.debug(f"› input  {event.text}", extra={"color": "white"})

        # ── Droid coordination events ───────────────────────────────
        elif isinstance(event, FinalizeEvent):
            if event.success:
                logger.info(
                    f"🎉 Goal achieved: {event.reason}", extra={"color": "green"}
                )
            else:
                logger.info(f"❌ Goal failed: {event.reason}", extra={"color": "red"})

        # ── Fallback ────────────────────────────────────────────────
        else:
            logger.debug(f"🔄 {event.__class__.__name__}")
