"""
DroidAgent - A wrapper class that coordinates the planning and execution of tasks
to achieve a user's goal on an Android device.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Tuple

from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.llms.llm import LLM
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.workflow import step, StartEvent, StopEvent, Workflow, Context
from droidrun.agent.droid.events import *
from droidrun.agent.codeact import CodeActAgent
from droidrun.agent.planner import PlannerAgent
from droidrun.agent.utils.executer import SimpleCodeExecutor
from droidrun.agent.utils.task_manager import TaskManager
from droidrun.tools import load_tools

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
        max_steps: int = 15,
        timeout: int = 1000,
        max_retries: int = 3,
        reasoning: bool = True,
        enable_tracing: bool = False,
        debug: bool = False,
        device_serial: str = None,
        *args,
        **kwargs
    ):
        """
        Initialize the DroidAgent wrapper.
        
        Args:
            goal: The user's goal or command to execute
            llm: The language model to use for both agents
            tools_instance: An instance of the Tools class
            tool_list: Dictionary of available tools
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
        super().__init__(timeout=timeout, *args, **kwargs)
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
        self.max_steps = max_steps
        self.timeout = timeout
        self.max_retries = max_retries
        self.task_manager = TaskManager()
        self.reasoning = reasoning
        self.debug = debug
        self.device_serial = device_serial
        
        # Store trajectory steps and callback
        self.trajectory_steps = []
        self.trajectory_callback = self._handle_trajectory_step
        
        logger.info("🤖 Initializing DroidAgent wrapper...")

        tool_list, tools_instance = load_tools(serial=device_serial)
        
        self.tools_instance = tools_instance
        self.tool_list = tool_list
        
        # Ensure remember tool is in the tool_list if available
        if hasattr(tools_instance, 'remember') and 'remember' not in tool_list:
            logger.debug("📝 Adding 'remember' tool to the available tools")
            tool_list['remember'] = tools_instance.remember
        
        # Create code executor
        logger.debug("🔧 Initializing Code Executor...")
        loop = asyncio.get_event_loop()
        self.executor = SimpleCodeExecutor(
            loop=loop,
            locals={},
            tools=tool_list,
            globals={"__builtins__": __builtins__}
        )
        
        # Create memory buffer for the planning agent if reasoning is enabled
        if self.reasoning:
            self.planning_memory = ChatMemoryBuffer.from_defaults(llm=llm)
        
        # Create CodeActAgent
        logger.info("🧠 Initializing CodeAct Agent...")
        self.codeact_agent = CodeActAgent(
            llm=llm,
            code_execute_fn=self.executor.execute,
            available_tools=tool_list.values(),
            tools=tools_instance,
            max_steps=999999, 
            debug=debug,
            timeout=timeout,
            trajectory_callback=self.trajectory_callback
        )
        if self.reasoning:

            planning_tools = {
                "set_tasks": self.task_manager.set_tasks,
                "add_task": self.task_manager.add_task,
                "get_all_tasks": self.task_manager.get_all_tasks,
                "clear_tasks": self.task_manager.clear_tasks,
                "complete_goal": self.task_manager.complete_goal
            }
            planning_executor = SimpleCodeExecutor(
                loop=asyncio.get_event_loop(),
                globals={},
                locals={},
                tools=planning_tools
            )
        
            logger.info("📝 Initializing Planner Agent...")
            self.planner_agent = PlannerAgent(
                goal=goal,
                llm=llm,
                agent=self.codeact_agent, 
                executer=planning_executor,
                tools_instance=tools_instance,
                timeout=timeout,
                max_retries=max_retries,
                debug=debug,
                trajectory_callback=self.trajectory_callback
            )
            
            # Give task manager to the planner
            self.planner_agent.task_manager = self.task_manager
        else:
            logger.debug("🚫 Planning disabled - will execute tasks directly with CodeActAgent")
            self.planner_agent = None
        
        logger.info("✅ DroidAgent initialized successfully.")
    
    async def _handle_trajectory_step(self, step):
        """
        Callback to handle trajectory steps from both agents.
        This adds the step to our trajectory_steps list and yields it if needed.
        
        Args:
            step: A trajectory step dictionary with metadata
        """
        # Add metadata about current time
        step["timestamp"] = time.time()
        
        # Add to trajectory
        self.trajectory_steps.append(step)
        
        # Log for debugging if needed
        logger.debug(f"📝 Trajectory step: {step['type']} (step {step['step']})")
            
    def get_trajectory(self):
        """
        Get the current trajectory.
        
        Returns:
            List of trajectory steps
        """
        return self.trajectory_steps.copy()
    
    @step
    async def _execute_task_with_codeact(self, ev: CodeActExecuteEvent, ctx: Context) -> CodeActResultEvent:
        """
        Execute a single task using the CodeActAgent.
        
        Args:
            task: Task dictionary with description and status
            
        Returns:
            Tuple of (success, reason)
        """
        task = await ctx.get("task")
        task_description = task["description"]
        logger.info(f"🔧 Executing task: {task_description}")
        
        # Update task status
        task["status"] = self.task_manager.STATUS_ATTEMPTING
        
        # Run the CodeActAgent
        try:
            # Reset the tools finished flag before execution
            self.tools_instance.finished = False
            self.tools_instance.success = None
            self.tools_instance.reason = None
            
            # Execute the CodeActAgent with the task description as input
            # Pass input as a keyword argument, not as a dictionary
            result = await self.codeact_agent.run(input=task_description)
            
            # Check if the tools instance was marked as finished by the 'complete' function
            if self.tools_instance.finished:
                if self.tools_instance.success:
                    task["status"] = self.task_manager.STATUS_COMPLETED
                    logger.debug(f"Task completed successfully: {self.tools_instance.reason}")
                    return CodeActResultEvent(success=True, reason=self.tools_instance.reason or "Task completed successfully", task=task)
                else:
                    task["status"] = self.task_manager.STATUS_FAILED
                    task["failure_reason"] = self.tools_instance.reason or "Task failed without specific reason"
                    logger.warning(f"Task failed: {task['failure_reason']}")
                    return CodeActResultEvent(success=False, reason=self.tools_instance.reason or "Task failed without specific reason", task=task)
            
            # If tools instance wasn't marked as finished, check the result directly
            if result and isinstance(result, dict) and "success" in result and result["success"]:
                task["status"] = self.task_manager.STATUS_COMPLETED
                logger.debug(f"Task completed with result: {result}")
                return CodeActResultEvent(success=True, reason=result.get("reason", "Task completed successfully"), task=task)
            else:
                failure_reason = result.get("reason", "Unknown failure") if isinstance(result, dict) else "Task execution failed"
                task["status"] = self.task_manager.STATUS_FAILED
                task["failure_reason"] = failure_reason
                logger.warning(f"Task failed: {failure_reason}")
                return CodeActResultEvent(success=False, reason=failure_reason, task=task)
                
        except Exception as e:
            logger.error(f"Error during task execution: {e}")
            if self.debug:
                import traceback
                logger.error(traceback.format_exc())
            task["status"] = self.task_manager.STATUS_FAILED
            task["failure_reason"] = f"Error: {str(e)}"
            return CodeActResultEvent(success=False, reason=f"Error: {str(e)}", task=task)
    
    @step
    async def handle_codeact_execute(self, ev: CodeActResultEvent, ctx: Context) -> FinalizeEvent | ReasoningLogicEvent:
        try:
            task = await ctx.get("task")
            if not self.reasoning:
                return FinalizeEvent(success=ev.success, reason=ev.reason, task=[task], steps=1)
            task_idx = self.tasks.index(task)
            result_info = {
                "execution_details": ev.reason,
                "step_executed": self.step_counter,
                "codeact_steps": self.codeact_agent.steps_counter
            }
            if ev.success:
                self.task_manager.update_status(
                    task_idx, 
                    self.task_manager.STATUS_COMPLETED, 
                    result_info
                )
                logger.info(f"✅ Task completed: {task['description']}")
            
            if not ev.success:
                # Store detailed failure information if not already set
                if "failure_reason" not in task:
                    self.task_manager.update_status(
                        task_idx,
                        self.task_manager.STATUS_FAILED,
                        {"failure_reason": ev.reason, **result_info}
                    )
                    # Handle retries
                    if self.retry_counter < self.max_retries:
                        self.retry_counter += 1
                        logger.info(f"Retrying... ({self.retry_counter}/{self.max_retries})")
                    else:
                        logger.error(f"Max retries exceeded for task")
                        final_message = f"Failed after {self.max_retries} retries. Reason: {ev.reason}"
                        return FinalizeEvent(success=False, reason=final_message, task=self.task_manager.get_task_history(), steps=self.step_counter)
            return ReasoningLogicEvent()
        except Exception as e:
            logger.error(f"❌ Error during DroidAgent execution: {e}")
            if self.debug:
                import traceback
                logger.error(traceback.format_exc())
            return FinalizeEvent(success=False, reason=str(e), task=self.task_manager.get_task_history(), steps=self.step_counter)
    @step
    async def finalize(self, ev: FinalizeEvent) -> StopEvent:
        return StopEvent(result= {
            "success": ev.success,
            "reason": ev.reason,
            "steps": ev.steps,
            "task_history": ev.task,
            "trajectory": self.trajectory_steps
        })
    
    @step
    async def handle_reasoning_logic(self, ev: ReasoningLogicEvent, ctx: Context) -> FinalizeEvent | TaskRunnerEvent:
        try:
            if self.step_counter >= self.max_steps:
                return FinalizeEvent(success=False, reason=f"Reached maximum number of steps ({self.max_steps})", task=self.task_manager.get_task_history(), steps=self.step_counter)
            self.step_counter += 1
            logger.debug(f"Planning step {self.step_counter}/{self.max_steps}")

            await self.planner_agent.run()
            self.tasks = self.task_manager.get_all_tasks()
            logger.debug(f'Tasks: {self.tasks}')
            self.task_iter = iter(self.tasks)

            if self.task_manager.task_completed:
                logger.info(f"✅ Goal completed: {self.task_manager.message}")
                return FinalizeEvent(success=True, reason=self.task_manager.message, task=self.task_manager.get_task_history(), steps=self.step_counter)
            if not self.tasks:
                logger.warning("No tasks generated by planner")
                return FinalizeEvent(success=False, reason="Planner did not generate any tasks", task=self.task_manager.get_task_history(), steps=self.step_counter)
            
            return TaskRunnerEvent()
        except Exception as e:
            logger.error(f"❌ Error during DroidAgent execution: {e}")
            if self.debug:
                import traceback
                logger.error(traceback.format_exc())
            return FinalizeEvent(success=False, reason=str(e), task=self.task_manager.get_task_history(), steps=self.step_counter)
    
    @step
    async def handle_task_loop(self, ev: TaskRunnerEvent, ctx: Context) -> CodeActExecuteEvent | ReasoningLogicEvent | FinalizeEvent:
        try:
            while True:
                task = next(self.task_iter, None)
                if task is None:
                    return ReasoningLogicEvent()
                if task["status"] == self.task_manager.STATUS_PENDING:
                    self.codeact_agent.steps_counter = 0
                    await ctx.set("task", task)
                    return CodeActExecuteEvent()
        except Exception as e:
            logger.error(f"❌ Error during DroidAgent execution: {e}")
            if self.debug:
                import traceback
                logger.error(traceback.format_exc())
            return FinalizeEvent(success=False, reason=str(e), task=self.task_manager.get_task_history(), steps=self.step_counter)
    @step
    async def start_handler(self, ev: StartEvent, ctx: Context) -> CodeActExecuteEvent | ReasoningLogicEvent | FinalizeEvent:
        """
        Main execution loop that coordinates between planning and execution.
        Yields trajectory steps during execution.
        
        Returns:
            Dict containing the execution result and complete trajectory
        """
        logger.info(f"🚀 Running DroidAgent to achieve goal: {self.goal}")
        
        self.step_counter = 0
        self.retry_counter = 0
        
        # Clear trajectory from any previous runs
        self.trajectory_steps = []
        
        try:
            # If reasoning is disabled, directly execute the goal as a single task in CodeActAgent
            if not self.reasoning:
                logger.info(f"🔄 Direct execution mode - executing goal: {self.goal}")
                # Create a simple task for the goal
                task = {
                    "description": self.goal,
                    "status": self.task_manager.STATUS_PENDING
                }
                
                # Execute the task directly with CodeActAgent
                await ctx.set("task", task)
                return CodeActExecuteEvent()
            
            # Standard reasoning mode with planning
            return ReasoningLogicEvent()
                
        except Exception as e:
            logger.error(f"❌ Error during DroidAgent execution: {e}")
            if self.debug:
                import traceback
                logger.error(traceback.format_exc())
            return FinalizeEvent(success=False, reason=str(e), task=self.task_manager.get_task_history(), steps=self.step_counter)