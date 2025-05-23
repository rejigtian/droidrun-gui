import logging
import re
import inspect
import time
from typing import Awaitable, Callable, List, Optional, Dict, Any, Tuple, TYPE_CHECKING, Union
from llama_index.core.base.llms.types import ChatMessage, ChatResponse, TextBlock
from llama_index.core.prompts import PromptTemplate
from llama_index.core.llms.llm import LLM
from llama_index.core.workflow import Workflow, StartEvent, StopEvent, Context, step
from llama_index.core.memory import ChatMemoryBuffer
from .events import FinalizeEvent, InputEvent, ModelOutputEvent, ExecutionEvent, ExecutionResultEvent
from ..utils.chat_utils import add_screenshot, add_screenshot_image_block, add_ui_text_block, message_copy
from .prompts import (
    DEFAULT_CODE_ACT_SYSTEM_PROMPT, 
    DEFAULT_CODE_ACT_USER_PROMPT, 
    DEFAULT_NO_THOUGHTS_PROMPT
)

if TYPE_CHECKING:
    from ...tools import Tools

logger = logging.getLogger("droidrun")


class CodeActAgent(Workflow):
    """
    An agent that uses a ReAct-like cycle (Thought -> Code -> Observation)
    to solve problems requiring code execution. It extracts code from
    Markdown blocks and uses specific step types for tracking.
    """
    def __init__(
        self,
        llm: LLM,
        code_execute_fn: Callable[[str], Awaitable[Dict[str, Any]]],
        tools: 'Tools',
        available_tools: List = [],
        max_steps: int = 10, # Default max steps (kept for backwards compatibility but no longer enforced)
        system_prompt: Optional[str] = None,
        user_prompt: Optional[str] = None,
        debug: bool = False,
        trajectory_callback = None,
        *args,
        **kwargs
    ):
        # assert instead of if
        assert llm, "llm must be provided."
        assert code_execute_fn, "code_execute_fn must be provided"
        super().__init__(*args, **kwargs)

        self.llm = llm
        self.code_execute_fn = code_execute_fn
        self.available_tools = available_tools or []
        self.tools = tools
        self.max_steps = max_steps  # Kept for backwards compatibility but not enforced
        self.tool_descriptions = self.parse_tool_descriptions() # Parse tool descriptions once at initialization
        self.system_prompt_content = (system_prompt or DEFAULT_CODE_ACT_SYSTEM_PROMPT).format(tool_descriptions=self.tool_descriptions)
        self.system_prompt = ChatMessage(role="system", content=self.system_prompt_content)
        self.user_prompt = user_prompt
        self.no_thoughts_prompt = None
        self.memory = None 
        self.goal = None
        self.steps_counter = 0 # Initialize step counter (kept for tracking purposes)
        self.code_exec_counter = 0 # Initialize execution counter
        self.debug = debug
        self.trajectory_callback = trajectory_callback
        logger.info("✅ CodeActAgent initialized successfully.")

    def parse_tool_descriptions(self) -> str:
        """Parses the available tools and their descriptions for the system prompt."""
        logger.info("🛠️ Parsing tool descriptions...")
        # self.available_tools is a list of functions, we need to get their docstrings, names, and signatures and display them as `def name(args) -> return_type:\n"""docstring"""    ...\n`
        tool_descriptions = []
        excluded_tools = ["take_screenshot"]  # List of tools to exclude
        
        for tool in self.available_tools:
            assert callable(tool), f"Tool {tool} is not callable."
            tool_name = tool.__name__
            
            # Skip excluded tools
            if tool_name in excluded_tools:
                logger.debug(f"  - Skipping excluded tool: {tool_name}")
                continue
                
            tool_signature = inspect.signature(tool)
            tool_docstring = tool.__doc__ or "No description available."
            # Format the function signature and docstring
            formatted_signature = f"def {tool_name}{tool_signature}:\n    \"\"\"{tool_docstring}\"\"\"\n..."
            tool_descriptions.append(formatted_signature)
            logger.debug(f"  - Parsed tool: {tool_name}")
        # Join all tool descriptions into a single string
        descriptions = "\n".join(tool_descriptions)
        logger.info(f"🔩 Found {len(tool_descriptions)} tools.")
        return descriptions

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

    @step
    async def prepare_chat(self, ev: StartEvent, ctx: Context) -> InputEvent:
        """Prepare chat history from user input."""
        logger.info("💬 Preparing chat for task execution...")
        # Get or create memory
        self.memory: ChatMemoryBuffer = await ctx.get(
            "memory", default=ChatMemoryBuffer.from_defaults(llm=self.llm)
        )
        user_input = ev.get("input", default=None)
        assert user_input, "User input cannot be empty."
        # Add user input to memory
        if self.debug:
            logger.debug("  - Adding goal to memory.")
        goal = user_input
        self.user_message = ChatMessage(role="user", content=PromptTemplate(self.user_prompt or DEFAULT_CODE_ACT_USER_PROMPT).format(goal=goal))
        self.no_thoughts_prompt = ChatMessage(role="user", content=PromptTemplate(DEFAULT_NO_THOUGHTS_PROMPT).format(goal=goal))
        await self.memory.aput(self.user_message)
        # Update context
        await ctx.set("memory", self.memory)
        input_messages = self.memory.get_all()
        return InputEvent(input=input_messages)
    @step
    async def handle_llm_input(self, ev: InputEvent, ctx: Context) -> Union[ModelOutputEvent, FinalizeEvent]:
        """Handle LLM input."""
        # Get chat history from event
        chat_history = ev.input
        assert len(chat_history) > 0, "Chat history cannot be empty."

        self.steps_counter += 1
        logger.info(f"🧠 Step {self.steps_counter}: Thinking...")
        
        # Get LLM response
        response = await self._get_llm_response(chat_history)
        # Add response to memory
        await self.memory.aput(response.message)
        if self.debug:
            logger.debug("🤖 LLM response received.")
        code, thoughts = self._extract_code_and_thought(response.message.content)
        if self.debug:
            logger.debug(f"  - Thoughts: {'Yes' if thoughts else 'No'}, Code: {'Yes' if code else 'No'}")
            
        # Yield thought trajectory if callback is provided
        if self.trajectory_callback:
            trajectory_step = {
                "type": "codeact_thought",
                "step": self.steps_counter,
                "thoughts": thoughts,
                "code": code
            }
            await self.trajectory_callback(trajectory_step)
            
        return ModelOutputEvent(thoughts=thoughts, code=code)

    @step
    async def handle_llm_output(self, ev: ModelOutputEvent, ctx: Context) -> Union[ExecutionEvent, FinalizeEvent]:
        """Handle LLM output."""
        if self.debug:
            logger.debug("⚙️ Handling LLM output...")
        # Get code and thoughts from event
        code = ev.code
        thoughts = ev.thoughts

        # Warning if no thoughts are provided
        if not thoughts:
            logger.warning("🤔 LLM provided code without thoughts. Adding reminder prompt.")
            await self.memory.aput(self.no_thoughts_prompt)
        else:
            # print thought but start with emoji at the start of the log
            logger.info(f"🤔 Reasoning: {thoughts}")

        # If code is present, execute it
        if code:
            return ExecutionEvent(code=code)
        else:
            message = ChatMessage(role="user", content="No code was provided. If you want to mark task as complete (whether it failed or succeeded), use complete(success:bool, reason:str) function within a code block ```pythn\n```.")
            await self.memory.aput(message)
            return InputEvent(input=self.memory.get_all()) 

    @step
    async def execute_code(self, ev: ExecutionEvent, ctx: Context) -> ExecutionResultEvent:
        """Execute the code and return the result."""
        code = ev.code
        assert code, "Code cannot be empty."
        logger.info(f"⚡ Executing action...")
        if self.debug:
            logger.debug(f"Code to execute:\n```python\n{code}\n```")
        # Execute the code using the provided function
        try:
            self.code_exec_counter += 1
            result = await self.code_execute_fn(code)
            logger.info(f"💡 Code execution successful. Result: {result}")
            
            # Yield code execution trajectory if callback is provided
            if self.trajectory_callback:
                trajectory_step = {
                    "type": "codeact_execution",
                    "step": self.steps_counter,
                    "code": code,
                    "result": result,
                    "success": True
                }
                await self.trajectory_callback(trajectory_step)
                
            if self.tools.finished == True:
                logger.debug("  - Task completed.")
                return FinalizeEvent(result={'success': self.tools.success, 'reason': self.tools.reason})
            return ExecutionResultEvent(output=str(result)) # Ensure output is string
        except Exception as e:
            logger.error(f"💥 Action failed: {e}")
            if self.debug:
                logger.error("Exception details:", exc_info=True)
            error_message = f"Error during execution: {e}"
            
            # Yield failed code execution trajectory if callback is provided
            if self.trajectory_callback:
                trajectory_step = {
                    "type": "codeact_execution",
                    "step": self.steps_counter,
                    "code": code,
                    "result": error_message,
                    "success": False
                }
                await self.trajectory_callback(trajectory_step)
                
            return ExecutionResultEvent(output=error_message) # Return error message as output

    @step
    async def handle_execution_result(self, ev: ExecutionResultEvent, ctx: Context) -> InputEvent:
        """Handle the execution result. Currently it just returns InputEvent."""
        if self.debug:
            logger.debug("📊 Handling execution result...")
        # Get the output from the event
        output = ev.output
        if output is None:
            output = "Code executed, but produced no output."
            logger.warning("  - Execution produced no output.")
        else:
             if self.debug:
                 logger.debug(f"  - Execution output: {output[:100]}..." if len(output) > 100 else f"  - Execution output: {output}") 
        # Add the output to memory as an user message (observation)
        observation_message = ChatMessage(role="user", content=f"Execution Result:\n```\n{output}\n```")
        await self.memory.aput(observation_message)
        
        return InputEvent(input=self.memory.get_all())
    

    @step
    async def finalize(self, ev: FinalizeEvent, ctx: Context) -> StopEvent:
        """Finalize the workflow."""
        self.tools.finished = False # Reset finished flag
        await ctx.set("memory", self.memory) # Ensure memory is set in context
        
        # Include steps and code execution information in the result
        result = ev.result or {}
        result.update({
            "codeact_steps": self.steps_counter,
            "code_executions": self.code_exec_counter
        })
        
        return StopEvent(result=result)

    async def _get_llm_response(self, chat_history: List[ChatMessage]) -> ChatResponse:
        """Get streaming response from LLM."""
        if self.debug:
            logger.debug(f"  - Sending {len(chat_history)} messages to LLM.")
        # add screenshot to prompt
        chat_history = await add_screenshot_image_block(self.tools, chat_history)        
        # always add ui
        chat_history = await add_ui_text_block(self.tools, chat_history)
        
        # Add remembered information if available
        if hasattr(self.tools, 'memory') and self.tools.memory:
            memory_block = "\n### Remembered Information:\n"
            for idx, item in enumerate(self.tools.memory, 1):
                memory_block += f"{idx}. {item}\n"
            
            # Find the first user message and inject memory before it
            for i, msg in enumerate(chat_history):
                if msg.role == "user":
                    if isinstance(msg.content, str):
                        # For text-only messages
                        updated_content = f"{memory_block}\n\n{msg.content}"
                        chat_history[i] = ChatMessage(role="user", content=updated_content)
                    elif isinstance(msg.content, list):
                        # For multimodal content
                        memory_text_block = TextBlock(text=memory_block)
                        # Insert memory text block at beginning
                        content_blocks = [memory_text_block] + msg.content
                        chat_history[i] = ChatMessage(role="user", content=content_blocks)
                    break
        
        messages_to_send = [self.system_prompt] + chat_history 

        messages_to_send = [message_copy(msg) for msg in messages_to_send]
        try:
            response = await self.llm.achat(
                messages=messages_to_send
            )
            assert hasattr(response, "message"), f"LLM response does not have a message attribute.\nResponse: {response}"
        except Exception as e:
            if self.llm.class_name() == "Gemini_LLM" and "You exceeded your current quota" in str(e):
                    s = str(e._details[2])
                    match = re.search(r'seconds:\s*(\d+)', s)
                    if match:
                        seconds = int(match.group(1)) + 1
                        logger.error(f"Rate limit error. Retrying in {seconds} seconds...")
                        time.sleep(seconds)
                    else:
                        logger.error(f"Rate limit error. Retrying in 5 seconds...")
                        time.sleep(40)
                    response = await self.llm.achat(
                        messages=messages_to_send
                    )
            else:
                logger.error(f"Error getting LLM response: {e}")
                return StopEvent(result={'finished': True, 'message': f"Error getting LLM response: {e}", 'steps': self.steps_counter, 'code_executions': self.code_exec_counter}) # Return final message and steps
        if self.debug:
            logger.debug("  - Received response from LLM.")
        return response
    
