"""
DroidAgent - A wrapper class that coordinates the planning and execution of tasks
to achieve a user's goal on an Android device.

Architecture:
- When reasoning=False: Uses CodeActAgent directly
- When reasoning=True: Uses Manager (planning) + Executor (action) workflows
"""

import logging
from typing import List
import llama_index.core
from llama_index.core.llms.llm import LLM
from llama_index.core.workflow import step, StartEvent, StopEvent, Workflow, Context
from llama_index.core.workflow.handler import WorkflowHandler
from droidrun.agent.droid.events import *
from droidrun.agent.codeact import CodeActAgent
from droidrun.agent.codeact.events import EpisodicMemoryEvent
from droidrun.agent.manager import ManagerAgent
from droidrun.agent.executor import ExecutorAgent
from droidrun.agent.context.task_manager import TaskManager
from droidrun.agent.utils.trajectory import Trajectory
from droidrun.tools import Tools
from droidrun.agent.common.events import ScreenshotEvent, MacroEvent, RecordUIStateEvent
from droidrun.agent.context import ContextInjectionManager
from droidrun.agent.context.agent_persona import AgentPersona
from droidrun.agent.context.personas import DEFAULT
from droidrun.agent.utils.tools import ATOMIC_ACTION_SIGNATURES
from droidrun.telemetry.phoenix import arize_phoenix_callback_handler
from droidrun.telemetry import (
    capture,
    flush,
    DroidAgentInitEvent,
    DroidAgentFinalizeEvent,
)

logger = logging.getLogger("droidrun")


class DroidAgent(Workflow):
    """
    A wrapper class that coordinates between agents to achieve a user's goal.

    Reasoning modes:
    - reasoning=False: Uses CodeActAgent directly for immediate execution
    - reasoning=True: Uses ManagerAgent (planning) + ExecutorAgent (actions)
    """

    @staticmethod
    def _configure_default_logging(debug: bool = False):
        """
        Configure default logging for DroidAgent if no handlers are present.
        This ensures logs are visible when using DroidAgent directly.
        """
        # Only configure if no handlers exist (avoid duplicate configuration)
        if not logger.handlers:
            # Create a console handler
            handler = logging.StreamHandler()

            # Set format
            if debug:
                formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s", "%H:%M:%S")
            else:
                formatter = logging.Formatter("%(message)s")

            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG if debug else logging.INFO)
            logger.propagate = False

    def __init__(
        self,
        goal: str,
        llm: LLM,
        tools: Tools,
        personas: List[AgentPersona] = [DEFAULT],
        max_steps: int = 15,
        timeout: int = 1000,
        vision: bool = False,
        reasoning: bool = False,
        enable_tracing: bool = False,
        debug: bool = False,
        save_trajectories: str = "none",
        excluded_tools: List[str] = None,
        *args,
        **kwargs,
    ):
        """
        Initialize the DroidAgent wrapper.

        Args:
            goal: The user's goal or command to execute
            llm: The language model to use for both agents
            max_steps: Maximum number of steps for both agents
            timeout: Timeout for agent execution in seconds
            reasoning: Whether to use Manager+Executor for complex reasoning (True)
                      or send tasks directly to CodeActAgent (False)
            enable_tracing: Whether to enable Arize Phoenix tracing
            debug: Whether to enable verbose debug logging
            save_trajectories: Trajectory saving level. Can be:
                - "none" (no saving)
                - "step" (save per step)
                - "action" (save per action)
            **kwargs: Additional keyword arguments to pass to the agents
        """
        self.user_id = kwargs.pop("user_id", None)
        super().__init__(timeout=timeout, *args, **kwargs)
        # Configure default logging if not already configured
        self._configure_default_logging(debug=debug)

        # Setup global tracing first if enabled
        if enable_tracing:
            try:
                handler = arize_phoenix_callback_handler()
                llama_index.core.global_handler = handler
                logger.info("🔍 Arize Phoenix tracing enabled globally")
            except ImportError:
                logger.warning(
                    "⚠️  Arize Phoenix is not installed.\n"
                    "    To enable Phoenix integration, install with:\n"
                    "    • If installed via tool: `uv tool install droidrun[phoenix]`"
                    "    • If installed via pip: `uv pip install droidrun[phoenix]`\n"
                )
                enable_tracing = False

        self.goal = goal
        self.llm = llm
        self.vision = vision
        self.max_steps = max_steps
        self.max_codeact_steps = max_steps
        self.timeout = timeout
        self.reasoning = reasoning
        self.debug = debug

        self.event_counter = 0
        # Handle backward compatibility: bool -> str mapping
        if isinstance(save_trajectories, bool):
            self.save_trajectories = "step" if save_trajectories else "none"
        else:
            # Validate string values
            valid_values = ["none", "step", "action"]
            if save_trajectories not in valid_values:
                logger.warning(
                    f"Invalid save_trajectories value: {save_trajectories}. Using 'none' instead."
                )
                self.save_trajectories = "none"
            else:
                self.save_trajectories = save_trajectories

        self.trajectory = Trajectory(goal=goal)
        self.task_manager = TaskManager()
        self.task_iter = None

        self.cim = ContextInjectionManager(personas=personas)
        self.current_episodic_memory = None

        logger.info("🤖 Initializing DroidAgent...")
        logger.info(f"💾 Trajectory saving level: {self.save_trajectories}")

        self.tools_instance = tools

        self.tools_instance.save_trajectories = self.save_trajectories

        if self.reasoning:
            logger.info("📝 Initializing Manager and Executor Agents...")
            self.manager_agent = ManagerAgent(
                llm=llm,
                vision=vision,
                personas=personas,
                tools_instance=tools,
                timeout=timeout,
                debug=debug,
            )
            self.executor_agent = ExecutorAgent(
                llm=llm,
                vision=vision,
                tools_instance=tools,
                persona=None,  # Need to figure this out
                timeout=timeout,
                debug=debug,
            )
            self.max_codeact_steps = 5


            # Keep planner_agent for backward compatibility (can be removed later)
            self.planner_agent = None

        else:
            logger.debug("🚫 Reasoning disabled - will execute tasks directly with CodeActAgent")
            self.manager_agent = None
            self.executor_agent = None
            self.planner_agent = None

        # Get tool names from ATOMIC_ACTION_SIGNATURES for telemetry
        atomic_tools = list(ATOMIC_ACTION_SIGNATURES.keys())
        
        capture(
            # TODO: do proper telemetry instead of this ductaped crap
            DroidAgentInitEvent(
                goal=goal,
                llm=llm.class_name(),
                tools=",".join(atomic_tools + ["remember", "complete"]),
                personas=",".join([p.name for p in personas]),
                max_steps=max_steps,
                timeout=timeout,
                vision=vision,
                reasoning=reasoning,
                enable_tracing=enable_tracing,
                debug=debug,
                save_trajectories=save_trajectories,
            ),
            self.user_id,
        )

        logger.info("✅ DroidAgent initialized successfully.")

    def run(self, *args, **kwargs) -> WorkflowHandler:
        """
        Run the DroidAgent workflow.
        """
        return super().run(*args, **kwargs)

    def _create_finalize_event(
        self,
        success: bool,
        reason: str,
        output: str
    ) -> FinalizeEvent:
        """
        Single source of truth for creating FinalizeEvent.

        This helper ensures all FinalizeEvent creation is consistent
        across the workflow.

        Args:
            success: Whether the task succeeded
            reason: Reason for completion (deprecated, use output)
            output: Output message

        Returns:
            FinalizeEvent ready to be returned
        """
        return FinalizeEvent(
            success=success,
            reason=reason,
            output=output,
            task=[], # TODO: use the final plan as the tasks and the goal as task
            tasks=[],
            steps=self.step_counter
        )

    @step
    async def execute_task(self, ctx: Context, ev: CodeActExecuteEvent) -> CodeActResultEvent:
        """
        Execute a single task using the CodeActAgent.

        Args:
            task: Task dictionary with description and status

        Returns:
            Tuple of (success, reason)
        """
        task: Task = ev.task
        persona = self.cim.get_persona(task.agent_type)

        logger.info(f"🔧 Executing task: {task.description}")

        try:
            codeact_agent = CodeActAgent(
                llm=self.llm,
                persona=persona,
                vision=self.vision,
                max_steps=self.max_codeact_steps,
                tools_instance=self.tools_instance,
                debug=self.debug,
                timeout=self.timeout,
            )

            handler = codeact_agent.run(
                input=task.description,
                remembered_info=self.tools_instance.memory,
            )

            async for nested_ev in handler.stream_events():
                self.handle_stream_event(nested_ev, ctx)

            result = await handler

            if "success" in result and result["success"]:
                return CodeActResultEvent(
                    success=True,
                    reason=result["reason"],
                    task=task,
                    steps=result["codeact_steps"],
                )
            else:
                return CodeActResultEvent(
                    success=False,
                    reason=result["reason"],
                    task=task,
                    steps=result["codeact_steps"],
                )

        except Exception as e:
            logger.error(f"Error during task execution: {e}")
            if self.debug:
                import traceback

                logger.error(traceback.format_exc())
            return CodeActResultEvent(success=False, reason=f"Error: {str(e)}", task=task, steps=[])

    @step
    async def handle_codeact_execute(
        self, ctx: Context, ev: CodeActResultEvent
    ) -> FinalizeEvent:
        try:
            task = ev.task
            return FinalizeEvent(
                success=ev.success,
                reason=ev.reason,
                output=ev.reason,
                task=[task],
                tasks=[task],
                steps=ev.steps,
            )
        except Exception as e:
            logger.error(f"❌ Error during DroidAgent execution: {e}")
            if self.debug:
                import traceback

                logger.error(traceback.format_exc())
            tasks = self.task_manager.get_task_history()
            return FinalizeEvent(
                success=False,
                reason=str(e),
                output=str(e),
                task=tasks,
                tasks=tasks,
                steps=self.step_counter,
            )

    @step
    async def start_handler(
        self, ctx: Context[DroidAgentState], ev: StartEvent
    ) -> CodeActExecuteEvent | ManagerInputEvent:
        """
        Main execution loop that coordinates between planning and execution.

        Returns:
            Event to trigger next step based on reasoning mode
        """
        logger.info(f"🚀 Running DroidAgent to achieve goal: {self.goal}")
        ctx.write_event_to_stream(ev)

        self.step_counter = 0
        self.retry_counter = 0

        if not self.reasoning:
            logger.info(f"🔄 Direct execution mode - executing goal: {self.goal}")
            task = Task(
                description=self.goal,
                status=self.task_manager.STATUS_PENDING,
                agent_type="Default",
            )

            return CodeActExecuteEvent(task=task)

        # Reasoning mode - initialize state and start with Manager
        logger.info("🧠 Reasoning mode - initializing Manager/Executor workflow")

        # Initialize DroidAgentState in context
        async with ctx.store.edit_state() as state:
            state.instruction = self.goal
            state.err_to_manager_thresh = 2
        return ManagerInputEvent()

    # ========================================================================
    # Manager/Executor Workflow Steps
    # ========================================================================

    @step
    async def run_manager(
        self,
        ctx: Context[DroidAgentState],
        ev: ManagerInputEvent
    ) -> ManagerPlanEvent | FinalizeEvent:
        """
        Run Manager planning phase.

        Pre-flight checks for termination before running manager.
        The Manager analyzes current state and creates a plan with subgoals.
        """
        # ====================================================================
        # PRE-FLIGHT: Check if we should terminate before running manager
        # ====================================================================

        # Check 1: Max steps reached
        if self.step_counter >= self.max_steps:
            logger.warning(f"⚠️ Reached maximum steps ({self.max_steps})")
            return self._create_finalize_event(
                success=False,
                reason=f"Reached maximum steps ({self.max_steps})",
                output=f"Reached maximum steps ({self.max_steps})"
            )

        # ====================================================================
        # All checks passed - run Manager
        # ====================================================================
        logger.info(f"📋 Running Manager for planning... (step {self.step_counter}/{self.max_steps})")

        # Run Manager workflow (shares same context)
        handler = self.manager_agent.run(ctx=ctx)

        # Stream nested events
        async for nested_ev in handler.stream_events():
            self.handle_stream_event(nested_ev, ctx)

        result = await handler

        # Update state with planning results
        async with ctx.store.edit_state() as state:
            state.plan = result["plan"]
            state.current_subgoal = result["current_subgoal"]
            state.completed_plan = result["completed_plan"]
            state.finish_thought = result["thought"]
            state.manager_answer = result.get("manager_answer", "")

        return ManagerPlanEvent(
            plan=result["plan"],
            current_subgoal=result["current_subgoal"],
            completed_plan=result["completed_plan"],
            thought=result["thought"],
            manager_answer=result.get("manager_answer", "")
        )

    @step
    async def handle_manager_plan(
        self,
        ctx: Context[DroidAgentState],
        ev: ManagerPlanEvent
    ) -> ExecutorInputEvent | FinalizeEvent:
        """
        Process Manager output and decide next step.

        Checks if task is complete or if Executor should take action.
        """
        # Check for answer-type termination
        if ev.manager_answer.strip():
            logger.info(f"💬 Manager provided answer: {ev.manager_answer}")
            async with ctx.store.edit_state() as state:
                state.progress_status = f"Answer: {ev.manager_answer}"

            return self._create_finalize_event(
                success=True,
                reason=ev.manager_answer,
                output=ev.manager_answer
            )

        # Continue to Executor with current subgoal
        logger.info(f"▶️  Proceeding to Executor with subgoal: {ev.current_subgoal}")
        return ExecutorInputEvent(current_subgoal=ev.current_subgoal)

    @step
    async def run_executor(
        self,
        ctx: Context[DroidAgentState],
        ev: ExecutorInputEvent
    ) -> ExecutorResultEvent:
        """
        Run Executor action phase.

        The Executor selects and executes a specific action for the current subgoal.
        """
        logger.info("⚡ Running Executor for action...")

        # Run Executor workflow (shares same context)
        handler = self.executor_agent.run(
            ctx=ctx,
            subgoal=ev.current_subgoal
        )

        # Stream nested events
        async for nested_ev in handler.stream_events():
            self.handle_stream_event(nested_ev, ctx)

        result = await handler

        # Update state with execution results
        async with ctx.store.edit_state() as state:
            state.action_history.append(result["action"])
            state.summary_history.append(result["summary"])
            state.action_outcomes.append(result["outcome"])
            state.error_descriptions.append(result["error"])
            state.last_action = result["action"]
            state.last_summary = result["summary"]
            state.last_action_thought = result.get("thought", "")
            state.action_pool.append(result["action_json"])
            state.progress_status = state.completed_plan

        return ExecutorResultEvent(
            action=result["action"],
            outcome=result["outcome"],
            error=result["error"],
            summary=result["summary"]
        )

    @step
    async def handle_executor_result(
        self,
        ctx: Context[DroidAgentState],
        ev: ExecutorResultEvent
    ) -> ManagerInputEvent:
        """
        Process Executor result and continue.

        Checks for error escalation and loops back to Manager.
        Note: Max steps check is now done in run_manager pre-flight.
        """
        # Check error escalation
        state = await ctx.store.get_state()
        err_thresh = state.err_to_manager_thresh

        if len(state.action_outcomes) >= err_thresh:
            latest = state.action_outcomes[-err_thresh:]
            error_count = sum(1 for o in latest if o == False)
            if error_count == err_thresh:
                logger.warning(f"⚠️ Error escalation: {err_thresh} consecutive errors")
                async with ctx.store.edit_state() as state:
                    state.error_flag_plan = True

        self.step_counter += 1
        logger.info(f"🔄 Step {self.step_counter}/{self.max_steps} complete, looping to Manager")

        # Always loop back to Manager (it will check max steps in pre-flight)
        return ManagerInputEvent()

    # ========================================================================
    # End Manager/Executor Workflow Steps
    # ========================================================================

    @step
    async def finalize(self, ctx: Context, ev: FinalizeEvent) -> StopEvent:
        ctx.write_event_to_stream(ev)
        capture(
            DroidAgentFinalizeEvent(
                tasks=",".join([f"{t.agent_type}:{t.description}" for t in ev.task]),
                success=ev.success,
                output=ev.output,
                steps=ev.steps,
            ),
            self.user_id,
        )
        flush()

        result = {
            "success": ev.success,
            # deprecated. use output instead.
            "reason": ev.reason,
            "output": ev.output,
            "steps": ev.steps,
        }

        if self.trajectory and self.save_trajectories != "none":
            self.trajectory.save_trajectory()

        return StopEvent(result)

    def handle_stream_event(self, ev: Event, ctx: Context):
        if isinstance(ev, EpisodicMemoryEvent):
            self.current_episodic_memory = ev.episodic_memory
            return

        if not isinstance(ev, StopEvent):
            ctx.write_event_to_stream(ev)

            if isinstance(ev, ScreenshotEvent):
                self.trajectory.screenshots.append(ev.screenshot)
            elif isinstance(ev, MacroEvent):
                self.trajectory.macro.append(ev)
            elif isinstance(ev, RecordUIStateEvent):
                self.trajectory.ui_states.append(ev.ui_state)
            else:
                self.trajectory.events.append(ev)
