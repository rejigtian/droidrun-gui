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
)
from droidrun.agent.common.events import (
    InputTextActionEvent,
    RecordUIStateEvent,
    ScreenshotEvent,
    SwipeActionEvent,
    TapActionEvent,
)
from droidrun.agent.droid.events import (
    CodeActExecuteEvent,
    CodeActResultEvent,
    ExecutorResultEvent,
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
                preview = event.thought[:120] + "..." if len(event.thought) > 120 else event.thought
                logger.debug(f"💭 Thought: {preview}")
            if event.subgoal:
                preview = event.subgoal[:150] + "..." if len(event.subgoal) > 150 else event.subgoal
                logger.debug(f"📋 Next step: {preview}")
            if event.answer:
                preview = event.answer[:200] + "..." if len(event.answer) > 200 else event.answer
                logger.debug(f"💬 Answer: {preview}")
            if event.plan:
                logger.debug(f"▸ {event.plan}")
            if event.memory_update:
                logger.debug(f"🧠 Memory: {event.memory_update[:100]}...")

        # ── Executor events (reasoning mode) ────────────────────────
        elif isinstance(event, ExecutorActionEvent):
            if event.description:
                logger.debug(f"🎯 Action: {event.description}")
            if event.thought:
                preview = event.thought[:120] + "..." if len(event.thought) > 120 else event.thought
                logger.debug(f"💭 Reasoning: {preview}")

        elif isinstance(event, ExecutorActionResultEvent):
            if event.success:
                logger.debug(f"✅ {event.summary}")
            else:
                error_msg = event.error or "Unknown error"
                logger.debug(f"❌ {event.summary} ({error_msg})")

        elif isinstance(event, ExecutorResultEvent):
            logger.debug(
                "Step complete",
                extra={"step_increment": True},
            )

        # ── CodeAct events (direct mode) ────────────────────────────
        elif isinstance(event, CodeActInputEvent):
            logger.debug("💬 Task input received...")

        elif isinstance(event, CodeActResponseEvent):
            logger.debug(
                "CodeAct response",
                extra={"step_increment": True},
            )
            if event.thought:
                preview = event.thought[:150] + "..." if len(event.thought) > 150 else event.thought
                logger.debug(f"🧠 Thinking: {preview}")
            if event.code:
                logger.debug("💻 Executing action code")
                logger.debug(f"{event.code}")

        elif isinstance(event, CodeActCodeEvent):
            logger.debug("⚡ Executing action...")

        elif isinstance(event, CodeActOutputEvent):
            if event.output:
                output = str(event.output)
                preview = output[:100] + "..." if len(output) > 100 else output
                if "Error" in output or "Exception" in output:
                    logger.debug(f"❌ Action error: {preview}")
                else:
                    logger.debug(f"⚡ Action result: {preview}")

        elif isinstance(event, CodeActEndEvent):
            status = "done" if event.success else "failed"
            logger.debug(f"■ {status}: {event.reason} ({event.code_executions} runs)")

        # ── Scripter events ─────────────────────────────────────────
        elif isinstance(event, ScripterThinkingEvent):
            if event.thought:
                logger.debug(f"    {event.thought}")
            if event.code:
                logger.debug("  $ script")
                for line in event.code.split("\n")[:5]:
                    if line.strip():
                        logger.debug(f"    {line}")

        # ── Macro / action events ───────────────────────────────────
        elif isinstance(event, TapActionEvent):
            logger.debug(f"› tap  {event.description}")

        elif isinstance(event, SwipeActionEvent):
            logger.debug(f"› swipe  {event.description}")

        elif isinstance(event, InputTextActionEvent):
            logger.debug(f"› input  {event.text}")

        # ── Droid coordination events ───────────────────────────────
        elif isinstance(event, CodeActExecuteEvent):
            logger.debug("🔧 Starting task execution...")

        elif isinstance(event, CodeActResultEvent):
            if hasattr(event, "success") and hasattr(event, "reason"):
                if event.success:
                    logger.debug(f"Task result: {event.reason}")
                else:
                    logger.debug(f"Task failed: {event.reason}")

        elif isinstance(event, FinalizeEvent):
            if hasattr(event, "success") and hasattr(event, "reason"):
                if event.success:
                    logger.info(f"🎉 Goal achieved: {event.reason}")
                else:
                    logger.info(f"❌ Goal failed: {event.reason}")

        # ── Fallback ────────────────────────────────────────────────
        else:
            logger.debug(f"🔄 {event.__class__.__name__}")
