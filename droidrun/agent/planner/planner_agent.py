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
import asyncio
from typing import List, Optional, Tuple, TYPE_CHECKING, Union
import inspect
from llama_index.core.base.llms.types import ChatMessage, ChatResponse
from llama_index.core.llms.llm import LLM
from llama_index.core.workflow import Workflow, StartEvent, StopEvent, Context, step
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.llms.llm import LLM
from droidrun.agent.utils.executer import SimpleCodeExecutor
from droidrun.agent.utils.chat_utils import add_ui_text_block, add_screenshot_image_block, add_phone_state_block, add_memory_block, message_copy
from droidrun.agent.utils.task_manager import TaskManager
from droidrun.tools import Tools
# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Setup logger
logger = logging.getLogger("droidrun")

if TYPE_CHECKING:
    from droidrun.tools import Tools

class PlannerAgent(Workflow):
    def __init__(self,
                 goal: str,
                 llm: LLM, 
                task_manager: TaskManager,
                tools_instance: Tools,
                system_prompt = None,
                user_prompt = None, 
                debug = False,
                trajectory_callback = None,
                *args,
                **kwargs
                ) -> None:
        super().__init__(*args, **kwargs)
        
            
        self.llm = llm
        self.goal = goal
        self.task_manager = task_manager
        self.debug = debug
        self.memory = None

        self.current_retry = 0
        self.steps_counter = 0
        
        self.trajectory_callback = trajectory_callback

        self.tools = [self.task_manager.set_tasks, self.task_manager.add_task, self.task_manager.get_all_tasks, self.task_manager.clear_tasks, self.task_manager.complete_goal, self.task_manager.start_agent]

        self.tools_description = self.parse_tool_descriptions()
        self.tools_instance = tools_instance

        self.system_prompt = system_prompt or DEFAULT_PLANNER_SYSTEM_PROMPT.format(tools_description=self.tools_description)
        self.user_prompt = user_prompt or DEFAULT_PLANNER_USER_PROMPT.format(goal=goal)
        self.system_message = ChatMessage(role="system", content=self.system_prompt)
        self.user_message = ChatMessage(role="user", content=self.user_prompt)
        

        self.executer = SimpleCodeExecutor(
            loop=asyncio.get_event_loop(),
            globals={},
            locals={},
            tools=self.tools
        )

            
    def parse_tool_descriptions(self) -> str:
        """Parses the available tools and their descriptions for the system prompt."""
        logger.debug("🛠️ Parsing tool descriptions for Planner Agent...")
        tool_descriptions = []
        for tool in self.tools:
            assert callable(tool), f"Tool {tool} is not callable."
            tool_name = tool.__name__
            tool_signature = inspect.signature(tool)
            tool_docstring = tool.__doc__ or "No description available."
            # Format the function signature and docstring
            formatted_signature = f"def {tool_name}{tool_signature}:\n    \"\"\"{tool_docstring}\"\"\"\n..."
            tool_descriptions.append(formatted_signature)
            logger.debug(f"  - Parsed tool: {tool_name}")
        # Join all tool descriptions into a single string
        descriptions = "\n".join(tool_descriptions)
        logger.debug(f"🔩 Found {len(tool_descriptions)} tools.")
        return descriptions
    

    def _extract_code_and_thought(self, response_text: str) -> Tuple[Optional[str], str]:
        """
        Extracts code from Markdown blocks (```python ... ```) and the surrounding text (thought),
        handling indented code blocks.

        Returns:
            Tuple[Optional[code_string], thought_string]
        """
        logger.debug("✂️ Extracting code and thought from response...")
        code_pattern = r"^\s*```python\s*\n(.*?)\n^\s*```\s*?$"
        code_matches = list(re.finditer(code_pattern, response_text, re.DOTALL | re.MULTILINE))

        if not code_matches:
            logger.debug("  - No code block found. Entire response is thought.")
            return None, response_text.strip()

        extracted_code_parts = []
        for match in code_matches:
             code_content = match.group(1)
             extracted_code_parts.append(code_content)

        extracted_code = "\n\n".join(extracted_code_parts)
        logger.debug(f"  - Combined extracted code:\n```python\n{extracted_code}\n```")


        thought_parts = []
        last_end = 0
        for match in code_matches:
            start, end = match.span(0)
            thought_parts.append(response_text[last_end:start])
            last_end = end
        thought_parts.append(response_text[last_end:])

        thought_text = "".join(thought_parts).strip()

        thought_preview = (thought_text[:100] + '...') if len(thought_text) > 100 else thought_text
        logger.debug(f"  - Extracted thought: {thought_preview}")

        return extracted_code, thought_text

    @step
    async def prepare_chat(self, ev: StartEvent, ctx: Context) -> InputEvent:
        logger.info("💬 Preparing planning session...")

        if not self.memory:
            logger.debug("  - Creating new memory buffer.")
            self.memory = ChatMemoryBuffer.from_defaults(llm=self.llm)
            await self.memory.aput(self.system_message)
        else:
            logger.debug("  - Using existing memory buffer with chat history.")

        task_history = ""
        completed_tasks = self.task_manager.get_all_completed_tasks()
        failed_tasks = self.task_manager.get_all_failed_tasks()
        
        remembered_info = ""
        if hasattr(self.tools_instance, 'memory') and self.tools_instance.memory:
            remembered_info = "\n### Remembered Information:\n"
            for idx, item in enumerate(self.tools_instance.memory, 1):
                remembered_info += f"{idx}. {item}\n"
        
        if completed_tasks or failed_tasks or remembered_info:
            task_history = "### Task Execution History:\n"
            
            if completed_tasks:
                task_history += "✅ Completed Tasks:\n"
                for task in completed_tasks:
                    task_history += f"- {task['description']}\n"

            if failed_tasks:
                task_history += "\n❌ Failed Tasks:\n"
                for task in failed_tasks:
                    failure_reason = task.get('failure_reason', 'Unknown reason')
                    task_history += f"- {task['description']} (Failed: {failure_reason})\n"
            
            if remembered_info:
                task_history += remembered_info
                
            task_history += "\n⚠️ Please use the above information in your planning. For example, if specific dates or locations were found, include them explicitly in your next tasks instead of just referring to 'the dates' or 'the location'.\n"
            
            user_msg = ChatMessage(
                role="user", 
                content=f"{self.user_prompt}\n\n{task_history}\n\nPlease consider the above task history and discovered information when creating your next plan. Incorporate specific data (dates, locations, etc.) directly into tasks rather than referring to them generally. Remember that previously completed or failed tasks will not be repeated."
            )
        
        # Validate we have either memory, input, or a user prompt
        assert len(self.memory.get_all()) > 0 or self.user_prompt, "Memory input, user prompt or user input cannot be empty."
        
        # Add user input to memory if provided or use the user prompt if this is a new conversation
        if self.user_prompt and len(self.memory.get_all()) <= 1:  # Only add user prompt if memory only has system message
            logger.debug("  - Adding goal to memory.")
            await self.memory.aput(ChatMessage(role="user", content=self.user_prompt))
        
        input_messages = self.memory.get_all()
        logger.debug(f"  - Memory contains {len(input_messages)} messages")
        return InputEvent(input=input_messages)
    
    @step
    async def handle_llm_input(self, ev: InputEvent, ctx: Context) -> ModelResponseEvent:
        """Handle LLM input."""
        # Get chat history from event
        chat_history = ev.input
        assert len(chat_history) > 0, "Chat history cannot be empty."

        self.steps_counter += 1
        logger.info(f"🧠 Thinking about how to plan the goal...")
        response = await self._get_llm_response(chat_history)
        await self.memory.aput(response.message)
        
        if self.trajectory_callback:
            trajectory_step = {
                "type": "planner_thought",
                "step": self.steps_counter,
                "content": response.message.content
            }
            await self.trajectory_callback(trajectory_step)
            
        return ModelResponseEvent(response=response.message.content)
    
    
    
    @step
    async def handle_llm_output(self, ev: ModelResponseEvent, ctx: Context) -> Union[InputEvent, StopEvent]:
        """Handle LLM output."""
        response = ev.response
        if response:
            logger.debug("🤖 LLM response received.")

        logger.debug("🤖 Processing planning output...")

        planner_step = await ctx.get("step", default=None)
        code, thoughts = self._extract_code_and_thought(response)
        logger.debug(f"  - Thoughts: {'Yes' if thoughts else 'No'}, Code: {'Yes' if code else 'No'}")   
        if code:
            # Execute code if present
            logger.debug(f"Response: {response}")
            result = await self.executer.execute(code)
            logger.info(f"📝 Planning complete")
            logger.debug(f"  - Planning code executed. Result: {result}")
            # Add result to memory
            await self.memory.aput(ChatMessage(role="user", content=f"Execution Result:\n```\n{result}\n```"))
            
            # Yield planner code execution trajectory step if callback is provided
            if self.trajectory_callback:
                trajectory_step = {
                    "type": "planner_plan_execution",
                    "step": self.steps_counter,
                    "code": code,
                    "result": result
                }
                await self.trajectory_callback(trajectory_step)
                    

            tasks = self.task_manager.get_all_tasks()
            if tasks:
                logger.info("📝 Plan created:")
                for i, task in enumerate(tasks, 1):
                    if task["status"] == self.task_manager.STATUS_PENDING:
                        logger.info(f"  {i}. {task['description']}")

                if self.trajectory_callback:
                    trajectory_step = {
                        "type": "planner_generated_plan",
                        "step": self.steps_counter,
                        "tasks": [task.copy() for task in tasks]
                    }
                    await self.trajectory_callback(trajectory_step)
                
            return StopEvent(tasks=tasks)
        else:
            # If no tasks were set, prompt the planner to set tasks or complete the goal
            await self.memory.aput(ChatMessage(role="user", content=f"Please either set new tasks using set_tasks() or mark the goal as complete using complete_goal() if done."))
            logger.debug("🔄 Waiting for next plan or completion.")
            return InputEvent(input=self.memory.get_all())
        

    async def _get_llm_response(self, chat_history: List[ChatMessage]) -> ChatResponse:
        """Get streaming response from LLM."""
        logger.debug(f"  - Sending {len(chat_history)} messages to LLM.")
        
        # Check if there's a system message in the chat history
        has_system_message = any(msg.role == "system" for msg in chat_history)
        if not has_system_message:
            logger.debug("No system message found in chat history, adding system prompt.")
            chat_history = [self.system_message] + chat_history
        else:
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
        model = self.llm.class_name()
        if model != "DeepSeek":
            chat_history = await add_screenshot_image_block(self.tools_instance, chat_history)
        chat_history = await add_memory_block(self.tools_instance, chat_history)
        chat_history = await add_ui_text_block(self.tools_instance, chat_history)
        chat_history = await add_phone_state_block(self.tools_instance, chat_history)
        
        # Create copies of messages to avoid modifying the originals due to bug in some llama_index llm integration
        messages_to_send = [message_copy(msg) for msg in chat_history]
        
        logger.debug(f"  - Final message count: {len(messages_to_send)}")

        response = await self.llm.achat(
            messages=messages_to_send
        )
        assert hasattr(response, "message"), f"LLM response does not have a message attribute.\nResponse: {response}"
        logger.debug("  - Received response from LLM.")
        return response