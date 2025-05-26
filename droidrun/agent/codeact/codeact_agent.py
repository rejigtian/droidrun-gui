import logging
import re
import inspect
import time
import asyncio
from typing import List, Optional, Tuple, Union
from llama_index.core.base.llms.types import ChatMessage, ChatResponse, TextBlock
from llama_index.core.prompts import PromptTemplate
from llama_index.core.llms.llm import LLM
from llama_index.core.workflow import Workflow, StartEvent, StopEvent, Context, step
from llama_index.core.memory import ChatMemoryBuffer
from droidrun.agent.codeact.events import FinalizeEvent, InputEvent, ModelOutputEvent, ExecutionEvent, ExecutionResultEvent
from droidrun.agent.utils.chat_utils import add_screenshot_image_block, add_ui_text_block, message_copy
from droidrun.agent.utils.executer import SimpleCodeExecutor
from droidrun.agent.codeact.prompts import (
    DEFAULT_CODE_ACT_SYSTEM_PROMPT, 
    DEFAULT_CODE_ACT_USER_PROMPT, 
    DEFAULT_NO_THOUGHTS_PROMPT
)

from droidrun.tools import Tools
from typing import Optional, Dict, Tuple, List, Any, Callable


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
        tools_instance: 'Tools',
        tool_list: Dict[str, Callable[..., Any]],
        max_steps: int = 10, # Default max steps (kept for backwards compatibility but no longer enforced)
        system_prompt: Optional[str] = None,
        user_prompt: Optional[str] = None,
        debug: bool = False,
        *args,
        **kwargs
    ):
        # assert instead of if
        assert llm, "llm must be provided."
        super().__init__(*args, **kwargs)

        self.llm = llm
        self.max_steps = max_steps

        self.user_prompt = user_prompt
        self.no_thoughts_prompt = None
        self.memory = None 
        self.goal = None
        self.steps_counter = 0
        self.code_exec_counter = 0
        self.debug = debug

        self.tools = tools_instance
        self.tool_list = tool_list
        self.tool_descriptions = self.parse_tool_descriptions()

        self.system_prompt_content = (system_prompt or DEFAULT_CODE_ACT_SYSTEM_PROMPT).format(tool_descriptions=self.tool_descriptions)
        self.system_prompt = ChatMessage(role="system", content=self.system_prompt_content)
        

        self.executor = SimpleCodeExecutor(
            loop=asyncio.get_event_loop(),
            locals={},
            tools=self.tool_list,
            globals={"__builtins__": __builtins__}
        )

        logger.info("✅ CodeActAgent initialized successfully.")

    def parse_tool_descriptions(self) -> str:
        """Parses the available tools and their descriptions for the system prompt."""
        logger.info("🛠️ Parsing tool descriptions...")
        tool_descriptions = []
        
        for tool in self.tool_list.values():
            assert callable(tool), f"Tool {tool} is not callable."
            tool_name = tool.__name__
            tool_signature = inspect.signature(tool)
            tool_docstring = tool.__doc__ or "No description available."
            formatted_signature = f"def {tool_name}{tool_signature}:\n    \"\"\"{tool_docstring}\"\"\"\n..."
            tool_descriptions.append(formatted_signature)
            logger.debug(f"  - Parsed tool: {tool_name}")
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
    async def prepare_chat(self, ctx: Context, ev: StartEvent) -> InputEvent:
        """Prepare chat history from user input."""
        logger.info("💬 Preparing chat for task execution...")


        self.memory: ChatMemoryBuffer = await ctx.get(
            "memory", default=ChatMemoryBuffer.from_defaults(llm=self.llm)
        )
        user_input = ev.get("input", default=None)
        assert user_input, "User input cannot be empty."

        logger.debug("  - Adding goal to memory.")
        goal = user_input
        self.user_message = ChatMessage(role="user", content=PromptTemplate(self.user_prompt or DEFAULT_CODE_ACT_USER_PROMPT).format(goal=goal))
        self.no_thoughts_prompt = ChatMessage(role="user", content=PromptTemplate(DEFAULT_NO_THOUGHTS_PROMPT).format(goal=goal))
        await self.memory.aput(self.user_message)

        await ctx.set("memory", self.memory)
        input_messages = self.memory.get_all()
        return InputEvent(input=input_messages)
    @step
    async def handle_llm_input(self, ctx: Context, ev: InputEvent) -> ModelOutputEvent:
        """Handle LLM input."""
        # Get chat history from event
        chat_history = ev.input
        assert len(chat_history) > 0, "Chat history cannot be empty."

        self.steps_counter += 1
        logger.info(f"🧠 Step {self.steps_counter}: Thinking...")
        
        response = await self._get_llm_response(chat_history)
        await self.memory.aput(response.message)
        logger.debug("🤖 LLM response received.")
        code, thoughts = self._extract_code_and_thought(response.message.content)
        logger.debug(f"  - Thoughts: {'Yes' if thoughts else 'No'}, Code: {'Yes' if code else 'No'}")

        event = ModelOutputEvent(thoughts=thoughts, code=code)
        ctx.write_event_to_stream(event)
        return event

    @step
    async def handle_llm_output(self, ctx: Context, ev: ModelOutputEvent) -> Union[ExecutionEvent, InputEvent]:
        """Handle LLM output."""
        logger.debug("⚙️ Handling LLM output...")
        code = ev.code
        thoughts = ev.thoughts

        if not thoughts:
            logger.warning("🤔 LLM provided code without thoughts. Adding reminder prompt.")
            await self.memory.aput(self.no_thoughts_prompt)
        else:
            logger.info(f"🤔 Reasoning: {thoughts}")

        if code:
            return ExecutionEvent(code=code)
        else:
            message = ChatMessage(role="user", content="No code was provided. If you want to mark task as complete (whether it failed or succeeded), use complete(success:bool, reason:str) function within a code block ```pythn\n```.")
            await self.memory.aput(message)
            return InputEvent(input=self.memory.get_all()) 

    @step
    async def execute_code(self, ctx: Context, ev: ExecutionEvent) -> Union[ExecutionResultEvent, FinalizeEvent]:
        """Execute the code and return the result."""
        code = ev.code
        assert code, "Code cannot be empty."
        logger.info(f"⚡ Executing action...")
        logger.debug(f"Code to execute:\n```python\n{code}\n```")

        try:
            self.code_exec_counter += 1
            result = await self.executor.execute(code)
            logger.info(f"💡 Code execution successful. Result: {result}")

            if self.tools.finished == True:
                logger.debug("  - Task completed.")
                event = FinalizeEvent(success=self.tools.success, reason=self.tools.reason)
                ctx.write_event_to_stream(event)
                return event
            
            event = ExecutionResultEvent(output=str(result))
            ctx.write_event_to_stream(event)
            return event
        
        except Exception as e:
            logger.error(f"💥 Action failed: {e}")
            if self.debug:
                logger.error("Exception details:", exc_info=True)
            error_message = f"Error during execution: {e}"
  
            event = ExecutionResultEvent(output=error_message)
            ctx.write_event_to_stream(event)
            return event

    @step
    async def handle_execution_result(self, ctx: Context, ev: ExecutionResultEvent) -> InputEvent:
        """Handle the execution result. Currently it just returns InputEvent."""
        logger.debug("📊 Handling execution result...")
        # Get the output from the event
        output = ev.output
        if output is None:
            output = "Code executed, but produced no output."
            logger.warning("  - Execution produced no output.")
        else:
            logger.debug(f"  - Execution output: {output[:100]}..." if len(output) > 100 else f"  - Execution output: {output}") 
        # Add the output to memory as an user message (observation)
        observation_message = ChatMessage(role="user", content=f"Execution Result:\n```\n{output}\n```")
        await self.memory.aput(observation_message)
        
        inputEvent = InputEvent(input=self.memory.get_all())
        ctx.write_event_to_stream(inputEvent)
        return inputEvent
    

    @step
    async def finalize(self, ev: FinalizeEvent, ctx: Context) -> StopEvent:
        """Finalize the workflow."""
        self.tools.finished = False
        await ctx.set("memory", self.memory)
        
        result = ev.values() or {}
        result.update({
            "codeact_steps": self.steps_counter,
            "code_executions": self.code_exec_counter
        })
        
        event = StopEvent(result=result)
        ctx.write_event_to_stream(event)
        return event

    async def _get_llm_response(self, chat_history: List[ChatMessage]) -> ChatResponse:
        """Get streaming response from LLM."""
        logger.debug(f"  - Sending {len(chat_history)} messages to LLM.")

        model = self.llm.class_name()
        if model != "DeepSeek":
            chat_history = await add_screenshot_image_block(self.tools, chat_history)
        else:
            logger.warning("[yellow]DeepSeek doesnt support images. Disabling screenshots[/]")
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
        logger.debug("  - Received response from LLM.")
        return response
    
