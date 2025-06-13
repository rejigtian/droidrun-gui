"""
DroidAgent - A wrapper class that coordinates the planning and execution of tasks
to achieve a user's goal on an Android device.
"""

import logging
from typing import List

from llama_index.core.llms.llm import LLM
from llama_index.core.workflow import step, StartEvent, StopEvent, Workflow, Context
from droidrun.agent.droid.events import *
from droidrun.agent.codeact import CodeActAgent
from droidrun.agent.codeact.events import EpisodicMemoryEvent
from droidrun.agent.planner import PlannerAgent
from droidrun.agent.context.task_manager import TaskManager
from droidrun.agent.utils.trajectory import Trajectory
from droidrun.tools import load_tools
from droidrun.agent.common.events import ScreenshotEvent
from droidrun.agent.common.default import MockWorkflow
from droidrun.agent.context import ContextInjectionManager
from droidrun.agent.context.agent_persona import AgentPersona
from droidrun.agent.context.personas import DEFAULT
from droidrun.agent.oneflows.reflector import Reflector


logger = logging.getLogger("droidrun")

class DroidAgent(Workflow):
    """
A wrapper class that coordinates between PlannerAgent (creates plans) and 
    CodeActAgent (executes tasks) to achieve a user's goal.
    """
    
    def __init__(
        self, 
        goal: str,
        llm: LLM,
        personas: List[AgentPersona] = [DEFAULT],
        max_steps: int = 15,
        timeout: int = 1000,
        max_retries: int = 3,
        reasoning: bool = True,
        enable_tracing: bool = False,
        debug: bool = False,
        device_serial: str = None,
        save_trajectories: bool = False,
        *args,
        **kwargs
    ):
        """
        Initialize the DroidAgent wrapper.
        
        Args:
            goal: The user's goal or command to execute
            llm: The language model to use for both agents
            max_steps: Maximum number of steps for both agents
            timeout: Timeout for agent execution in seconds
            max_retries: Maximum number of retries for failed tasks
            reasoning: Whether to use the PlannerAgent for complex reasoning (True) 
                      or send tasks directly to CodeActAgent (False)
            enable_tracing: Whether to enable Arize Phoenix tracing
            debug: Whether to enable verbose debug logging
            device_serial: Target Android device serial number
            **kwargs: Additional keyword arguments to pass to the agents
        """
        super().__init__(timeout=timeout ,*args,**kwargs)
        # Setup global tracing first if enabled
        if enable_tracing:
            try:
                from llama_index.core import set_global_handler
                set_global_handler("arize_phoenix")
                logger.info("🔍 Arize Phoenix tracing enabled globally")
            except ImportError:
                logger.warning("⚠️ Arize Phoenix package not found, tracing disabled")
                enable_tracing = False

        if debug:
            logger.setLevel(logging.DEBUG)
        
        self.goal = goal
        self.llm = llm
        self.max_steps = max_steps
        self.max_codeact_steps = max_steps
        self.timeout = timeout
        self.max_retries = max_retries
        self.reasoning = reasoning
        self.debug = debug
        self.device_serial = device_serial

        self.event_counter = 0
        self.save_trajectories = save_trajectories
        
        self.trajectory = Trajectory()
        self.task_manager = TaskManager()
        self.task_iter = None
        self.cim = ContextInjectionManager(personas=personas)
        self.current_episodic_memory = None

        logger.info("🤖 Initializing DroidAgent...")
        
        tool_list, tools_instance = load_tools(serial=device_serial)
        self.tool_list = tool_list
        self.tools_instance = tools_instance


        if self.reasoning:
            logger.info("📝 Initializing Planner Agent...")
            self.planner_agent = PlannerAgent(
                goal=goal,
                llm=llm,
                personas=personas,
                task_manager=self.task_manager,
                tools_instance=tools_instance,
                timeout=timeout,
                debug=debug
            )
            self.add_workflows(planner_agent=self.planner_agent)
            self.max_codeact_steps = 5

            self.reflector = Reflector(llm=llm)
            
        else:
            logger.debug("🚫 Planning disabled - will execute tasks directly with CodeActAgent")
            self.planner_agent = None
        
        logger.info("✅ DroidAgent initialized successfully.")
    
    @step
    async def execute_task(
        self,
        ctx: Context,
        ev: CodeActExecuteEvent
        ) -> CodeActResultEvent:
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
                max_steps=self.max_codeact_steps,
                all_tools_list=self.tool_list,
                tools_instance=self.tools_instance,
                debug=self.debug,
                timeout=self.timeout,
            )

            handler = codeact_agent.run(
                input=task.description,
                remembered_info=self.tools_instance.memory,
                reflection=reflection
            )
            
            async for nested_ev in handler.stream_events():
                self.handle_stream_event(nested_ev, ctx)

            result = await handler

            
            if "success" in result and result["success"]:
                return CodeActResultEvent(success=True, reason=result["reason"], task=task, steps=result["codeact_steps"])
            else:
                return CodeActResultEvent(success=False, reason=result["reason"], task=task, steps=result["codeact_steps"])
                
        except Exception as e:
            logger.error(f"Error during task execution: {e}")
            if self.debug:
                import traceback
                logger.error(traceback.format_exc())
            return CodeActResultEvent(success=False, reason=f"Error: {str(e)}", task=task, steps=result["codeact_steps"])
    
    @step
    async def handle_codeact_execute(self, ctx: Context, ev: CodeActResultEvent) -> FinalizeEvent | ReflectionEvent:
        try:
            task = ev.task
            if not self.reasoning:
                return FinalizeEvent(success=ev.success, reason=ev.reason, task=[task], steps=ev.steps)
            
            return ReflectionEvent(task=task)

        except Exception as e:
            logger.error(f"❌ Error during DroidAgent execution: {e}")
            if self.debug:
                import traceback
                logger.error(traceback.format_exc())
            return FinalizeEvent(success=False, reason=str(e), task=self.task_manager.get_task_history(), steps=self.step_counter)
        

    @step
    async def reflect(
        self,
        ctx: Context,
        ev: ReflectionEvent
        ) -> ReasoningLogicEvent | CodeActExecuteEvent:


        task = ev.task
        if ev.task.agent_type == "AppStarterExpert":
            self.task_manager.complete_task(task)
            return ReasoningLogicEvent()
        
        reflection = await self.reflector.reflect_on_episodic_memory(episodic_memory=self.current_episodic_memory, goal=task.description)

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
        planner_agent: Workflow = MockWorkflow()
        ) -> FinalizeEvent | CodeActExecuteEvent:
        try:
            if self.step_counter >= self.max_steps:
                return FinalizeEvent(success=False, reason=f"Reached maximum number of steps ({self.max_steps})", task=self.task_manager.get_task_history(), steps=self.step_counter)
            self.step_counter += 1

            if ev.reflection:
                handler = planner_agent.run(remembered_info=self.tools_instance.memory, reflection=ev.reflection)
            else:
                if self.task_iter:
                    try:
                        task = next(self.task_iter)
                        return CodeActExecuteEvent(task=task, reflection=None)
                    except StopIteration as e:
                        logger.info("Planning next steps...")

                logger.debug(f"Planning step {self.step_counter}/{self.max_steps}")

                handler = planner_agent.run(remembered_info=self.tools_instance.memory, reflection=None)

            async for nested_ev in handler.stream_events():
                self.handle_stream_event(nested_ev, ctx)

            result = await handler

            self.tasks = self.task_manager.get_all_tasks()
            self.task_iter = iter(self.tasks)

            if self.task_manager.goal_completed:
                logger.info(f"✅ Goal completed: {self.task_manager.message}")
                return FinalizeEvent(success=True, reason=self.task_manager.message, task=self.task_manager.get_task_history(), steps=self.step_counter)
            if not self.tasks:
                logger.warning("No tasks generated by planner")
                return FinalizeEvent(success=False, reason="Planner did not generate any tasks", task=self.task_manager.get_task_history(), steps=self.step_counter)
            
            return CodeActExecuteEvent(task=next(self.task_iter), reflection=None)
        
        except Exception as e:
            logger.error(f"❌ Error during DroidAgent execution: {e}")
            if self.debug:
                import traceback
                logger.error(traceback.format_exc())
            return FinalizeEvent(success=False, reason=str(e), task=self.task_manager.get_task_history(), steps=self.step_counter)
    

    @step
    async def start_handler(self, ctx: Context, ev: StartEvent) -> CodeActExecuteEvent | ReasoningLogicEvent:
        """
        Main execution loop that coordinates between planning and execution.
        
        Returns:
            Dict containing the execution result
        """
        logger.info(f"🚀 Running DroidAgent to achieve goal: {self.goal}")
        
        self.step_counter = 0
        self.retry_counter = 0
    
        if not self.reasoning:
            logger.info(f"🔄 Direct execution mode - executing goal: {self.goal}")
            task = Task(
                description=self.goal,
                status=self.task_manager.STATUS_PENDING,
                agent_type="Default"
            )
            
            return CodeActExecuteEvent(task=task, reflection=None)
        
        return ReasoningLogicEvent()
                
        
    @step
    async def finalize(self, ctx: Context, ev: FinalizeEvent) -> StopEvent:
        ctx.write_event_to_stream(ev)

        result = {
            "success": ev.success,
            "reason": ev.reason,
            "steps": ev.steps,
        }

        if self.trajectory:
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

            else:
                self.trajectory.events.append(ev)



