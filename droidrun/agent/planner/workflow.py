from llama_index.core.workflow import (
    StartEvent,
    StopEvent,
    Workflow,
    step,
)
from droidrun.agent.planner.events import *
from droidrun.agent.planner.prompts import (
    DEFAULT_PLANNER_SYSTEM_PROMPT,
    DEFAULT_PLANNER_USER_PROMPT,
)
import logging
import re
import os
from typing import List, Optional, Tuple, TYPE_CHECKING, Union
import inspect
# LlamaIndex imports for LLM interaction and types
from llama_index.core.base.llms.types import ChatMessage, ChatResponse
from llama_index.core.llms.llm import LLM
from llama_index.core.workflow import Workflow, StartEvent, StopEvent, Context, step
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.llms.llm import LLM
from droidrun.agent.utils.executer import SimpleCodeExecutor
from droidrun.agent.utils.chat_utils import add_ui_text_block, add_screenshot_image_block, add_phone_state_block, message_copy
from droidrun.agent.planner.task_manager import TaskManager

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Setup logger
logger = logging.getLogger("droidrun")

if TYPE_CHECKING:
    from droidrun.tools import Tools

class PlannerAgent(Workflow):
    def __init__(self, goal: str, llm: LLM, agent: Optional[Workflow], tools_instance: 'Tools', 
                 executer = None, system_prompt = None, user_prompt = None, max_retries = 1, 
                 enable_tracing = False, debug = False, trajectory_callback = None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        
        # Setup tracing if enabled
        if enable_tracing:
            try:
                from llama_index.core import set_global_handler
                set_global_handler("arize_phoenix")
                logger.info("Arize Phoenix tracing enabled")
            except ImportError:
                logger.warning("Arize Phoenix package not found, tracing disabled")
        else:
            if debug:
                logger.debug("Arize Phoenix tracing disabled")
            
        self.llm = llm
        self.goal = goal
        self.task_manager = TaskManager()
        self.tools = [self.task_manager.set_tasks, self.task_manager.add_task, self.task_manager.get_all_tasks, self.task_manager.clear_tasks, self.task_manager.complete_goal, self.task_manager.start_agent]
        self.debug = debug  # Set debug attribute before using it in other methods
        self.tools_description = self.parse_tool_descriptions()
        if not executer:
            self.executer = SimpleCodeExecutor(loop=None, globals={}, locals={}, tools=self.tools, use_same_scope=True)
        else:
            self.executer = executer
        self.system_prompt = system_prompt or DEFAULT_PLANNER_SYSTEM_PROMPT.format(tools_description=self.tools_description)
        self.user_prompt = user_prompt or DEFAULT_PLANNER_USER_PROMPT.format(goal=goal)
        self.system_message = ChatMessage(role="system", content=self.system_prompt)
        self.user_message = ChatMessage(role="user", content=self.user_prompt)
        self.memory = None
        self.agent = agent  # This can now be None when used just for planning
        self.tools_instance = tools_instance

        self.max_retries = max_retries # Number of retries for a failed task

        self.current_retry = 0 # Current retry count

        self.steps_counter = 0 # Steps counter
        
        # Callback function for yielding trajectory steps
        self.trajectory_callback = trajectory_callback

    def _extract_code_and_thought(self, response_text: str) -> Tuple[Optional[str], str]:
        """
        Extracts code from Markdown blocks (```python ... ```) and the surrounding text (thought),
        handling indented code blocks.

        Returns:
            Tuple[Optional[code_string], thought_string]
        """
        if self.debug:
            logger.debug("✂️ Extracting code and thought from response...")
        code_pattern = r"^\s*```python\s*\n(.*?)\n^\s*```\s*?$" # Added ^\s*, re.MULTILINE, and made closing fence match more robust
        # Use re.DOTALL to make '.' match newlines and re.MULTILINE to make '^' match start of lines
        code_matches = list(re.finditer(code_pattern, response_text, re.DOTALL | re.MULTILINE))

        if not code_matches:
            # No code found, the entire response is thought
            if self.debug:
                logger.debug("  - No code block found. Entire response is thought.")
            return None, response_text.strip()

        extracted_code_parts = []
        for match in code_matches:
             # group(1) is the (.*?) part - the actual code content
             code_content = match.group(1)
             extracted_code_parts.append(code_content) # Keep original indentation for now

        extracted_code = "\n\n".join(extracted_code_parts)
        if self.debug:
            logger.debug(f"  - Combined extracted code:\n```python\n{extracted_code}\n```")


        # Extract thought text (text before the first code block, between blocks, and after the last)
        thought_parts = []
        last_end = 0
        for match in code_matches:
            # Use span(0) to get the start/end of the *entire* match (including fences and indentation)
            start, end = match.span(0)
            thought_parts.append(response_text[last_end:start])
            last_end = end
        thought_parts.append(response_text[last_end:]) # Text after the last block

        thought_text = "".join(thought_parts).strip()
        # Avoid overly long debug messages for thought
        if self.debug:
            thought_preview = (thought_text[:100] + '...') if len(thought_text) > 100 else thought_text
            logger.debug(f"  - Extracted thought: {thought_preview}")

        return extracted_code, thought_text
    
    def parse_tool_descriptions(self) -> str:
        """Parses the available tools and their descriptions for the system prompt."""
        if self.debug:
            logger.debug("🛠️ Parsing tool descriptions for Planner Agent...")
        # self.available_tools is a list of functions, we need to get their docstrings, names, and signatures and display them as `def name(args) -> return_type:\n"""docstring"""    ...\n`
        tool_descriptions = []
        for tool in self.tools:
            assert callable(tool), f"Tool {tool} is not callable."
            tool_name = tool.__name__
            tool_signature = inspect.signature(tool)
            tool_docstring = tool.__doc__ or "No description available."
            # Format the function signature and docstring
            formatted_signature = f"def {tool_name}{tool_signature}:\n    \"\"\"{tool_docstring}\"\"\"\n..."
            tool_descriptions.append(formatted_signature)
            if self.debug:
                logger.debug(f"  - Parsed tool: {tool_name}")
        # Join all tool descriptions into a single string
        descriptions = "\n".join(tool_descriptions)
        if self.debug:
            logger.debug(f"🔩 Found {len(tool_descriptions)} tools.")
        return descriptions
    
    @step
    async def prepare_chat(self, ev: StartEvent, ctx: Context) -> InputEvent:
        logger.info("💬 Preparing planning session...")
        await ctx.set("step", "generate_plan")
        
        # Check if we already have a memory buffer, otherwise create one
        if not self.memory:
            if self.debug:
                logger.debug("  - Creating new memory buffer.")
            self.memory = ChatMemoryBuffer.from_defaults(llm=self.llm)
            # Add system message to memory
            await self.memory.aput(self.system_message)
        else:
            if self.debug:
                logger.debug("  - Using existing memory buffer with chat history.")
        
        # Check for user input
        user_input = ev.get("input", default=None)
        
        # Validate we have either memory, input, or a user prompt
        assert len(self.memory.get_all()) > 0 or user_input or self.user_prompt, "Memory input, user prompt or user input cannot be empty."
        
        # Add user input to memory if provided or use the user prompt if this is a new conversation
        if user_input:
            if self.debug:
                logger.debug("  - Adding user input to memory.")
            await self.memory.aput(ChatMessage(role="user", content=user_input))
        elif self.user_prompt and len(self.memory.get_all()) <= 1:  # Only add user prompt if memory only has system message
            if self.debug:
                logger.debug("  - Adding goal to memory.")
            await self.memory.aput(ChatMessage(role="user", content=self.user_prompt))
        
        # Update context
        await ctx.set("memory", self.memory)
        input_messages = self.memory.get_all()
        if self.debug:
            logger.debug(f"  - Memory contains {len(input_messages)} messages")
        return InputEvent(input=input_messages)
    
    @step
    async def handle_llm_input(self, ev: InputEvent, ctx: Context) -> Union[StopEvent, ModelResponseEvent]:
        """Handle LLM input."""
        # Get chat history from event
        chat_history = ev.input
        assert len(chat_history) > 0, "Chat history cannot be empty."

        self.steps_counter += 1
        logger.info(f"🧠 Thinking about how to plan the goal...")
        # Get LLM response
        response = await self._get_llm_response(chat_history)
        # Add response to memory
        await self.memory.aput(response.message)
        
        # Yield planner trajectory step if callback is provided
        if self.trajectory_callback:
            trajectory_step = {
                "type": "planner_thought",
                "step": self.steps_counter,
                "content": response.message.content
            }
            await self.trajectory_callback(trajectory_step)
            
        return ModelResponseEvent(response=response.message.content)
    
    @step
    async def handle_llm_output(self, ev: ModelResponseEvent, ctx: Context) -> Union[StopEvent, ExecutePlan]:
        """Handle LLM output."""
        response = ev.response
        if response:
            if self.debug:
                logger.debug("🤖 LLM response received.")
        if self.debug:
            logger.debug("🤖 Processing planning output...")
        planner_step = await ctx.get("step", default=None)
        code, thoughts = self._extract_code_and_thought(response)
        if self.debug:
            logger.debug(f"  - Thoughts: {'Yes' if thoughts else 'No'}, Code: {'Yes' if code else 'No'}")   
        if code:
            # Execute code if present
            if self.debug:
                logger.debug(f"Response: {response}")
            result = await self.executer.execute(code)
            logger.info(f"📝 Planning complete")
            if self.debug:
                logger.debug(f"  - Planning code executed. Result: {result}")
            # Add result to memory
            await self.memory.aput(ChatMessage(role="user", content=f"Execution Result:\n```\n{result}\n```"))
            
            # Yield planner code execution trajectory step if callback is provided
            if self.trajectory_callback:
                trajectory_step = {
                    "type": "planner_code_execution",
                    "step": self.steps_counter,
                    "code": code,
                    "result": result
                }
                await self.trajectory_callback(trajectory_step)
                    
        # Check if there are any pending tasks
        pending_tasks = self.task_manager.get_pending_tasks()
        
        if self.task_manager.task_completed:
            logger.info("✅ Goal marked as complete by planner.")
            return StopEvent(result={'finished': True, 'message': "Task execution completed.", 'steps': self.steps_counter})
        elif pending_tasks:
            # If there are pending tasks, automatically start execution
            logger.info("🚀 Starting task execution...")
            
            # Yield plan trajectory step if callback is provided
            if self.trajectory_callback and pending_tasks:
                trajectory_step = {
                    "type": "planner_generated_plan",
                    "step": self.steps_counter,
                    "tasks": [task.copy() for task in pending_tasks]
                }
                await self.trajectory_callback(trajectory_step)
                
            return ExecutePlan()
        else:
            # If no tasks were set, prompt the planner to set tasks or complete the goal
            await self.memory.aput(ChatMessage(role="user", content=f"Please either set new tasks using set_tasks() or mark the goal as complete using complete_goal() if done."))
            if self.debug:
                logger.debug("🔄 Waiting for next plan or completion.")
            return InputEvent(input=self.memory.get_all())
    @step
    async def execute_plan(self, ev: ExecutePlan, ctx: Context) -> Union[ExecutePlan, TaskFailedEvent]:
        """Execute the plan by running tasks through the agent."""
        if self.debug:
            logger.debug("🔄 Executing plan...")
        
        # Get all tasks
        tasks = self.task_manager.get_all_tasks()
        
        # Yield plan execution trajectory step if callback is provided
        if self.trajectory_callback:
            trajectory_step = {
                "type": "planner_execute_plan",
                "step": self.steps_counter,
                "tasks": [task["description"] for task in tasks],
                "status": "started"
            }
            await self.trajectory_callback(trajectory_step)
        
        # Execute each task in sequence
        for task in tasks:
            if task["status"] == self.task_manager.STATUS_PENDING:
                logger.info(f"🎯 Executing task: {task['description']}")
                
                # Yield task start trajectory step if callback is provided
                if self.trajectory_callback:
                    trajectory_step = {
                        "type": "planner_task",
                        "step": self.steps_counter,
                        "task": task["description"],
                        "status": "started"
                    }
                    await self.trajectory_callback(trajectory_step)
                
                # Execute the task using the agent
                result = await self.execute_agent(ExecutePlan(task=task), ctx)
                
                # Check if task failed
                if isinstance(result, TaskFailedEvent):
                    # Yield task failure trajectory step if callback is provided
                    if self.trajectory_callback:
                        trajectory_step = {
                            "type": "planner_task",
                            "step": self.steps_counter,
                            "task": task["description"],
                            "status": "failed",
                            "reason": result.reason
                        }
                        await self.trajectory_callback(trajectory_step)
                    return result
                
                # Yield task completion trajectory step if callback is provided
                if self.trajectory_callback:
                    trajectory_step = {
                        "type": "planner_task",
                        "step": self.steps_counter,
                        "task": task["description"],
                        "status": "completed"
                    }
                    await self.trajectory_callback(trajectory_step)
        
        # Yield plan completion trajectory step if callback is provided
        if self.trajectory_callback:
            trajectory_step = {
                "type": "planner_execute_plan",
                "step": self.steps_counter,
                "tasks": [task["description"] for task in tasks],
                "status": "completed"
            }
            await self.trajectory_callback(trajectory_step)
        
        return StopEvent(result={"success": True, "message": "All tasks completed successfully"})

    async def execute_agent(self, ev: ExecutePlan, ctx: Context) -> Union[ExecutePlan, TaskFailedEvent]:
        """Execute a single task using the agent."""
        task = ev.task
        if not self.agent:
            logger.warning("No agent provided for task execution")
            return TaskFailedEvent(reason="No agent provided for task execution")
        
        try:
            # Execute the task using the agent
            result = await self.agent.run(input=task["description"])
            
            # Yield agent execution trajectory step if callback is provided
            if self.trajectory_callback:
                trajectory_step = {
                    "type": "planner_agent_execution",
                    "step": self.steps_counter,
                    "task": task["description"],
                    "result": result
                }
                await self.trajectory_callback(trajectory_step)
            
            if result and isinstance(result, dict):
                if result.get("success", False):
                    task["status"] = self.task_manager.STATUS_COMPLETED
                    task["result"] = result
                    return ExecutePlan(task=task)
                else:
                    task["status"] = self.task_manager.STATUS_FAILED
                    task["failure_reason"] = result.get("reason", "Unknown failure")
                    return TaskFailedEvent(reason=task["failure_reason"])
            else:
                task["status"] = self.task_manager.STATUS_FAILED
                task["failure_reason"] = "Invalid result format from agent"
                return TaskFailedEvent(reason=task["failure_reason"])
                
        except Exception as e:
            logger.error(f"Error during task execution: {e}")
            task["status"] = self.task_manager.STATUS_FAILED
            task["failure_reason"] = str(e)
            return TaskFailedEvent(reason=str(e))

    async def _get_llm_response(self, chat_history: List[ChatMessage]) -> ChatResponse:
        """Get streaming response from LLM."""
        if self.debug:
            logger.debug(f"  - Sending {len(chat_history)} messages to LLM.")
        
        # Check if there's a system message in the chat history
        has_system_message = any(msg.role == "system" for msg in chat_history)
        if not has_system_message:
            if self.debug:
                logger.debug("No system message found in chat history, adding system prompt.")
            chat_history = [self.system_message] + chat_history
        else:
            if self.debug:
                logger.debug("System message already exists in chat history, using existing.")
        
        # Add remembered information if available
        if hasattr(self.tools_instance, 'memory') and self.tools_instance.memory:
            memory_block = "\n### Remembered Information:\n"
            for idx, item in enumerate(self.tools_instance.memory, 1):
                memory_block += f"{idx}. {item}\n"
            
            # Find the first user message and inject memory before it
            for i, msg in enumerate(chat_history):
                if msg.role == "user":
                    if isinstance(msg.content, str):
                        # For text-only messages
                        updated_content = f"{memory_block}\n\n{msg.content}"
                        chat_history[i] = ChatMessage(role="user", content=updated_content)
                    elif isinstance(msg.content, list):
                        # For multimodal content (from llama_index.core.base.llms.types import TextBlock)
                        from llama_index.core.base.llms.types import TextBlock
                        memory_text_block = TextBlock(text=memory_block)
                        # Insert memory text block at beginning
                        content_blocks = [memory_text_block] + msg.content
                        chat_history[i] = ChatMessage(role="user", content=content_blocks)
                    break
        
        # Add UI elements, screenshot, and phone state
        chat_history = await add_screenshot_image_block(self.tools_instance, chat_history)
        chat_history = await add_ui_text_block(self.tools_instance, chat_history)
        chat_history = await add_phone_state_block(self.tools_instance, chat_history)
        
        # Create copies of messages to avoid modifying the originals due to bug in some llama_index llm integration
        messages_to_send = [message_copy(msg) for msg in chat_history]
        
        if self.debug:
            logger.debug(f"  - Final message count: {len(messages_to_send)}")
            response = await self.llm.achat(
            messages=messages_to_send
        )
        assert hasattr(response, "message"), f"LLM response does not have a message attribute.\nResponse: {response}"
        if self.debug:
            logger.debug("  - Received response from LLM.")
        return response