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
from llama_index.core.workflow import Context, StartEvent, StopEvent, Workflow, step
from llama_index.core.workflow.handler import WorkflowHandler
from workflows.events import Event

from droidrun.config_manager.config_manager import (
    DroidRunConfig,
    AgentConfig,
    DeviceConfig,
    ToolsConfig,
    LoggingConfig,
    TracingConfig,
    TelemetryConfig,
)

from droidrun.agent.codeact import CodeActAgent
from droidrun.agent.codeact.events import EpisodicMemoryEvent
from droidrun.agent.common.events import MacroEvent, RecordUIStateEvent, ScreenshotEvent
from droidrun.agent.context.task_manager import Task, TaskManager
from droidrun.agent.droid.events import (
    CodeActExecuteEvent,
    CodeActResultEvent,
    DroidAgentState,
    ExecutorInputEvent,
    ExecutorResultEvent,
    FinalizeEvent,
    ManagerInputEvent,
    ManagerPlanEvent,
)
from droidrun.agent.executor import ExecutorAgent
from droidrun.agent.manager import ManagerAgent
from droidrun.agent.utils.tools import ATOMIC_ACTION_SIGNATURES
from droidrun.agent.utils.trajectory import Trajectory
from droidrun.telemetry import (
    DroidAgentFinalizeEvent,
    DroidAgentInitEvent,
    capture,
    flush,
)
from droidrun.telemetry.phoenix import arize_phoenix_callback_handler
from droidrun.tools import Tools

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
        llms: dict[str, LLM] | LLM,
        tools: Tools,
        config: DroidRunConfig | None = None,
        agent_config: AgentConfig | None = None,
        device_config: DeviceConfig | None = None,
        tools_config: ToolsConfig | None = None,
        logging_config: LoggingConfig | None = None,
        tracing_config: TracingConfig | None = None,
        telemetry_config: TelemetryConfig | None = None,
        excluded_tools: List[str] = None,
        custom_tools: dict = None,
        timeout: int = 1000,
        *args,
        **kwargs,
    ):
        """
        Initialize the DroidAgent wrapper.

        Args:
            goal: User's goal or command
            llms: Dict of agent-specific LLMs or single LLM for all
            tools: Tools instance (AdbTools or IOSTools)
            config: Full config override (optional)
            agent_config: Agent config override (optional)
            device_config: Device config override (optional)
            tools_config: Tools config override (optional)
            logging_config: Logging config override (optional)
            tracing_config: Tracing config override (optional)
            telemetry_config: Telemetry config override (optional)
            excluded_tools: Tools to exclude
            custom_tools: Custom tool definitions
            timeout: Workflow timeout in seconds
        """
        from droidrun.config_manager import config as global_config

        self.user_id = kwargs.pop("user_id", None)

        base_config = config if config is not None else global_config

        self.config = DroidRunConfig(
            agent=agent_config or base_config.agent,
            device=device_config or base_config.device,
            tools=tools_config or base_config.tools,
            logging=logging_config or base_config.logging,
            tracing=tracing_config or base_config.tracing,
            telemetry=telemetry_config or base_config.telemetry,
            llm_profiles=base_config.llm_profiles,
        )

        super().__init__(timeout=timeout, *args, **kwargs)  # noqa: B026

        self._configure_default_logging(debug=self.config.logging.debug)

        if self.config.tracing.enabled:
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

        self.goal = goal
        self.timeout = timeout
        self.custom_tools = custom_tools or {}

        if isinstance(llms, dict):
            self.manager_llm = llms.get('manager')
            self.executor_llm = llms.get('executor')
            self.codeact_llm = llms.get('codeact')
            self.text_manipulator_llm = llms.get('text_manipulator')
            self.app_opener_llm = llms.get('app_opener')

            if self.config.agent.reasoning and (not self.manager_llm or not self.executor_llm):
                raise ValueError("When reasoning=True, 'manager' and 'executor' LLMs must be provided in llms dict")
            if not self.codeact_llm:
                raise ValueError("'codeact' LLM must be provided in llms dict")

            logger.info("📚 Using agent-specific LLMs from dictionary")
        else:
            logger.info("📚 Using single LLM for all agents")
            self.manager_llm = llms
            self.executor_llm = llms
            self.codeact_llm = llms
            self.text_manipulator_llm = llms
            self.app_opener_llm = llms


        self.event_counter = 0
        self.trajectory = Trajectory(goal=goal)
        self.task_manager = TaskManager()
        self.task_iter = None
        self.current_episodic_memory = None

        logger.info("🤖 Initializing DroidAgent...")
        logger.info(f"💾 Trajectory saving: {self.config.logging.save_trajectory}")

        self.tools_instance = tools
        self.tools_instance.save_trajectories = self.config.logging.save_trajectory

        self.shared_state = DroidAgentState(
            instruction=goal,
            err_to_manager_thresh=2
        )

        if self.config.agent.reasoning:
            logger.info("📝 Initializing Manager and Executor Agents...")
            self.manager_agent = ManagerAgent(
                llm=self.manager_llm,
                tools_instance=tools,
                shared_state=self.shared_state,
                config=self.config.agent.manager,
                custom_tools=self.custom_tools,
                timeout=timeout,
            )
            self.executor_agent = ExecutorAgent(
                llm=self.executor_llm,
                tools_instance=tools,
                shared_state=self.shared_state,
                config=self.config.agent.executor,
                custom_tools=self.custom_tools,
                timeout=timeout,
            )
            self.planner_agent = None
        else:
            logger.debug("🚫 Reasoning disabled - executing directly with CodeActAgent")
            self.manager_agent = None
            self.executor_agent = None
            self.planner_agent = None

        atomic_tools = list(ATOMIC_ACTION_SIGNATURES.keys())

        capture(
            DroidAgentInitEvent(
                goal=goal,
                llms={"manager": self.manager_llm.class_name(), "executor": self.executor_llm.class_name(), "codeact": self.codeact_llm.class_name(), "text_manipulator": self.text_manipulator_llm.class_name(), "app_opener": self.app_opener_llm.class_name()},
                tools=",".join(atomic_tools + ["remember", "complete"]),
                max_steps=self.config.agent.max_steps,
                timeout=timeout,
                vision={
                    "manager": self.config.agent.manager.vision,
                    "executor": self.config.agent.executor.vision,
                    "codeact": self.config.agent.codeact.vision
                },
                reasoning=self.config.agent.reasoning,
                enable_tracing=self.config.tracing.enabled,
                debug=self.config.logging.debug,
                save_trajectories=self.config.logging.save_trajectory,
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

        logger.info(f"🔧 Executing task: {task.description}")

        try:
            max_codeact_steps = 5 if self.config.agent.reasoning else self.config.agent.max_steps
            codeact_agent = CodeActAgent(
                llm=self.codeact_llm,
                config=self.config.agent.codeact,
                tools_instance=self.tools_instance,
                custom_tools=self.custom_tools,
                debug=self.config.logging.debug,
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
            if self.config.logging.debug:
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
            if self.config.logging.debug:
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
        self, ctx: Context, ev: StartEvent
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

        if not self.config.agent.reasoning:
            logger.info(f"🔄 Direct execution mode - executing goal: {self.goal}")
            task = Task(
                description=self.goal,
                status=self.task_manager.STATUS_PENDING,
                agent_type="Default",
            )
            return CodeActExecuteEvent(task=task)

        logger.info("🧠 Reasoning mode - initializing Manager/Executor workflow")
        return ManagerInputEvent()

    # ========================================================================
    # Manager/Executor Workflow Steps
    # ========================================================================

    @step
    async def run_manager(
        self,
        ctx: Context,
        ev: ManagerInputEvent
    ) -> ManagerPlanEvent | FinalizeEvent:
        """
        Run Manager planning phase.

        Pre-flight checks for termination before running manager.
        The Manager analyzes current state and creates a plan with subgoals.
        """
        if self.step_counter >= self.config.agent.max_steps:
            logger.warning(f"⚠️ Reached maximum steps ({self.config.agent.max_steps})")
            return self._create_finalize_event(
                success=False,
                reason=f"Reached maximum steps ({self.config.agent.max_steps})",
                output=f"Reached maximum steps ({self.config.agent.max_steps})"
            )

        logger.info(f"📋 Running Manager for planning... (step {self.step_counter}/{self.config.agent.max_steps})")

        # Run Manager workflow
        handler = self.manager_agent.run()

        # Stream nested events
        async for nested_ev in handler.stream_events():
            self.handle_stream_event(nested_ev, ctx)

        result = await handler

        # Manager already updated shared_state, just return event with results
        return ManagerPlanEvent(
            plan=result["plan"],
            current_subgoal=result["current_subgoal"],
            thought=result["thought"],
            manager_answer=result.get("manager_answer", "")
        )

    @step
    async def handle_manager_plan(
        self,
        ctx: Context,
        ev: ManagerPlanEvent
    ) -> ExecutorInputEvent | FinalizeEvent:
        """
        Process Manager output and decide next step.

        Checks if task is complete or if Executor should take action.
        """
        # Check for answer-type termination
        if ev.manager_answer.strip():
            logger.info(f"💬 Manager provided answer: {ev.manager_answer}")
            self.shared_state.progress_status = f"Answer: {ev.manager_answer}"

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
        ctx: Context,
        ev: ExecutorInputEvent
    ) -> ExecutorResultEvent:
        """
        Run Executor action phase.

        The Executor selects and executes a specific action for the current subgoal.
        """
        logger.info("⚡ Running Executor for action...")

        # Run Executor workflow (Executor will update shared_state directly)
        handler = self.executor_agent.run(subgoal=ev.current_subgoal)

        # Stream nested events
        async for nested_ev in handler.stream_events():
            self.handle_stream_event(nested_ev, ctx)

        result = await handler

        # Update coordination state after execution
        self.shared_state.action_history.append(result["action"])
        self.shared_state.summary_history.append(result["summary"])
        self.shared_state.action_outcomes.append(result["outcome"])
        self.shared_state.error_descriptions.append(result["error"])
        self.shared_state.last_action = result["action"]
        self.shared_state.last_summary = result["summary"]
        self.shared_state.last_action_thought = result.get("thought", "")
        self.shared_state.action_pool.append(result["action_json"])

        return ExecutorResultEvent(
            action=result["action"],
            outcome=result["outcome"],
            error=result["error"],
            summary=result["summary"]
        )

    @step
    async def handle_executor_result(
        self,
        ctx: Context,
        ev: ExecutorResultEvent
    ) -> ManagerInputEvent:
        """
        Process Executor result and continue.

        Checks for error escalation and loops back to Manager.
        Note: Max steps check is now done in run_manager pre-flight.
        """
        # Check error escalation
        err_thresh = self.shared_state.err_to_manager_thresh

        if len(self.shared_state.action_outcomes) >= err_thresh:
            latest = self.shared_state.action_outcomes[-err_thresh:]
            error_count = sum(1 for o in latest if not o)
            if error_count == err_thresh:
                logger.warning(f"⚠️ Error escalation: {err_thresh} consecutive errors")
                self.shared_state.error_flag_plan = True

        self.step_counter += 1
        logger.info(f"🔄 Step {self.step_counter}/{self.config.agent.max_steps} complete, looping to Manager")

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
            "reason": ev.reason,
            "output": ev.output,
            "steps": ev.steps,
        }

        if self.trajectory and self.config.logging.save_trajectory != "none":
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
