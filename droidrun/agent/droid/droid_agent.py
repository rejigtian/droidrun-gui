"""
DroidAgent - A wrapper class that coordinates the planning and execution of tasks
to achieve a user's goal on an Android device.

Architecture:
- When reasoning=False: Uses CodeActAgent directly
- When reasoning=True: Uses Manager (planning) + Executor (action) workflows
"""

import logging
import copy
from typing import List

from llama_index.core.llms.llm import LLM
from llama_index.core.workflow import step, StartEvent, StopEvent, Workflow, Context
from llama_index.core.workflow.handler import WorkflowHandler
from droidrun.agent.droid.events import *
from droidrun.agent.codeact import CodeActAgent
from droidrun.agent.codeact.events import EpisodicMemoryEvent
from droidrun.agent.manager import ManagerAgent
from droidrun.agent.executor import ExecutorAgent
from droidrun.agent.planner import PlannerAgent  # Keep for backward compatibility
from droidrun.agent.context.task_manager import TaskManager
from droidrun.agent.utils.trajectory import Trajectory
from droidrun.tools import Tools, describe_tools
from droidrun.agent.common.events import ScreenshotEvent, MacroEvent, RecordUIStateEvent
from droidrun.agent.common.default import MockWorkflow
from droidrun.agent.context import ContextInjectionManager
from droidrun.agent.context.agent_persona import AgentPersona
from droidrun.agent.context.personas import DEFAULT
from droidrun.agent.oneflows.reflector import Reflector
from droidrun.agent.executor.prompts import DETAILED_TIPS
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
        reflection: bool = False,
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
            reflection: Whether to reflect on steps the CodeActAgent did to give the PlannerAgent advice
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
                from llama_index.core import set_global_handler

                set_global_handler("arize_phoenix")
                logger.info("🔍 Arize Phoenix tracing enabled globally")
            except ImportError:
                logger.warning("⚠️ Arize Phoenix package not found, tracing disabled")
                enable_tracing = False

        self.goal = goal
        self.llm = llm
        self.vision = vision
        self.max_steps = max_steps
        self.max_codeact_steps = max_steps
        self.timeout = timeout
        self.reasoning = reasoning
        self.reflection = reflection
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

        self.tool_list = describe_tools(tools, excluded_tools)
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

            if self.reflection:
                self.reflector = Reflector(llm=llm, debug=debug)

            # Keep planner_agent for backward compatibility (can be removed later)
            self.planner_agent = None

        else:
            logger.debug("🚫 Reasoning disabled - will execute tasks directly with CodeActAgent")
            self.manager_agent = None
            self.executor_agent = None
            self.planner_agent = None

        capture(
            DroidAgentInitEvent(
                goal=goal,
                llm=llm.class_name(),
                tools=",".join(self.tool_list),
                personas=",".join([p.name for p in personas]),
                max_steps=max_steps,
                timeout=timeout,
                vision=vision,
                reasoning=reasoning,
                reflection=reflection,
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
        reflection = ev.reflection if ev.reflection is not None else None
        persona = self.cim.get_persona(task.agent_type)

        logger.info(f"🔧 Executing task: {task.description}")

        try:
            codeact_agent = CodeActAgent(
                llm=self.llm,
                persona=persona,
                vision=self.vision,
                max_steps=self.max_codeact_steps,
                all_tools_list=self.tool_list,
                tools_instance=self.tools_instance,
                debug=self.debug,
                timeout=self.timeout,
            )

            handler = codeact_agent.run(
                input=task.description,
                remembered_info=self.tools_instance.memory,
                reflection=reflection,
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
    ) -> FinalizeEvent | ReflectionEvent | ReasoningLogicEvent:
        try:
            task = ev.task
            if not self.reasoning:
                return FinalizeEvent(
                    success=ev.success,
                    reason=ev.reason,
                    output=ev.reason,
                    task=[task],
                    tasks=[task],
                    steps=ev.steps,
                )

            if self.reflection and ev.success:
                return ReflectionEvent(task=task)

            # Reasoning is enabled but reflection is disabled.
            # Success: mark complete and proceed to next step in reasoning loop.
            # Failure: mark failed and trigger planner immediately without advancing to the next queued task.
            if ev.success:
                self.task_manager.complete_task(task, message=ev.reason)
                return ReasoningLogicEvent()
            else:
                self.task_manager.fail_task(task, failure_reason=ev.reason)
                return ReasoningLogicEvent(force_planning=True)

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
    async def reflect(
        self, ctx: Context, ev: ReflectionEvent
    ) -> ReasoningLogicEvent:
        task = ev.task
        if ev.task.agent_type == "AppStarterExpert":
            self.task_manager.complete_task(task)
            return ReasoningLogicEvent()

        reflection = await self.reflector.reflect_on_episodic_memory(
            episodic_memory=self.current_episodic_memory, goal=task.description
        )

        if reflection.goal_achieved:
            self.task_manager.complete_task(task)
            return ReasoningLogicEvent()

        else:
            self.task_manager.fail_task(task)
            return ReasoningLogicEvent(reflection=reflection)

    @step
    async def handle_reasoning_logic(
        self,
        ctx: Context,
        ev: ReasoningLogicEvent,
    ) -> FinalizeEvent | CodeActExecuteEvent:
        try:
            if self.step_counter >= self.max_steps:
                output = f"Reached maximum number of steps ({self.max_steps})"
                tasks = self.task_manager.get_task_history()
                return FinalizeEvent(
                    success=False,
                    reason=output,
                    output=output,
                    task=tasks,
                    tasks=tasks,
                    steps=self.step_counter,
                )
            self.step_counter += 1

            if ev.reflection:
                handler = self.planner_agent.run(
                    remembered_info=self.tools_instance.memory, reflection=ev.reflection
                )
            else:
                if not ev.force_planning and self.task_iter:
                    try:
                        task = next(self.task_iter)
                        return CodeActExecuteEvent(task=task, reflection=None)
                    except StopIteration as e:
                        logger.info("Planning next steps...")

                logger.debug(f"Planning step {self.step_counter}/{self.max_steps}")

                handler = self.planner_agent.run(
                    remembered_info=self.tools_instance.memory, reflection=None
                )

            async for nested_ev in handler.stream_events():
                self.handle_stream_event(nested_ev, ctx)

            result = await handler

            self.tasks = self.task_manager.get_all_tasks()
            self.task_iter = iter(self.tasks)

            if self.task_manager.goal_completed:
                logger.info(f"✅ Goal completed: {self.task_manager.message}")
                tasks = self.task_manager.get_task_history()
                return FinalizeEvent(
                    success=True,
                    reason=self.task_manager.message,
                    output=self.task_manager.message,
                    task=tasks,
                    tasks=tasks,
                    steps=self.step_counter,
                )
            if not self.tasks:
                logger.warning("No tasks generated by planner")
                output = "Planner did not generate any tasks"
                tasks = self.task_manager.get_task_history()
                return FinalizeEvent(
                    success=False,
                    reason=output,
                    output=output,
                    task=tasks,
                    tasks=tasks,
                    steps=self.step_counter,
                )

            return CodeActExecuteEvent(task=next(self.task_iter), reflection=None)

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

            return CodeActExecuteEvent(task=task, reflection=None)

        # Reasoning mode - initialize state and start with Manager
        logger.info("🧠 Reasoning mode - initializing Manager/Executor workflow")

        # Initialize DroidAgentState in context
        async with ctx.store.edit_state() as state:
            state.instruction = self.goal
            state.err_to_manager_thresh = 2
            state.additional_knowledge_manager = "" # not used yet but nice to keep for custom knowledge or tools
            state.additional_knowledge_executor = copy.deepcopy(DETAILED_TIPS) # will prolly remove this later and make a proper single system prompt

        return ManagerInputEvent()

    # ========================================================================
    # Manager/Executor Workflow Steps
    # ========================================================================

    @step
    async def run_manager(
        self,
        ctx: Context[DroidAgentState],
        ev: ManagerInputEvent
    ) -> ManagerPlanEvent:
        """
        Run Manager planning phase.

        The Manager analyzes current state and creates a plan with subgoals.
        """
        logger.info("📋 Running Manager for planning...")

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
        state = await ctx.store.get_state()

        # Check for answer-type termination
        if ev.manager_answer.strip():
            logger.info(f"💬 Manager provided answer: {ev.manager_answer}")
            async with ctx.store.edit_state() as state:
                state.progress_status = f"Answer: {ev.manager_answer}"

            return FinalizeEvent(
                success=True,
                reason=ev.manager_answer,
                output=ev.manager_answer,
                task=[],
                tasks=[],
                steps=self.step_counter
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
    ) -> ManagerInputEvent | FinalizeEvent:
        """
        Process Executor result and continue or finalize.

        Checks for max steps, error escalation, and loops back to Manager.
        """
        # Check max steps
        if self.step_counter >= self.max_steps:
            logger.warning(f"⚠️ Reached maximum steps ({self.max_steps})")
            state = await ctx.store.get_state()
            return FinalizeEvent(
                success=False,
                reason=f"Reached maximum steps ({self.max_steps})",
                output=f"Reached maximum steps ({self.max_steps})",
                task=[],
                tasks=[],
                steps=self.step_counter
            )

        # Check error escalation
        state = await ctx.store.get_state()
        err_thresh = state.err_to_manager_thresh

        if len(state.action_outcomes) >= err_thresh:
            latest = state.action_outcomes[-err_thresh:]
            error_count = sum(1 for o in latest if o in ["B", "C"])
            if error_count == err_thresh:
                logger.warning(f"⚠️ Error escalation: {err_thresh} consecutive errors")
                async with ctx.store.edit_state() as state:
                    state.error_flag_plan = True

        self.step_counter += 1
        logger.info(f"🔄 Step {self.step_counter}/{self.max_steps} complete, looping to Manager")

        # Loop back to Manager for next planning iteration
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
