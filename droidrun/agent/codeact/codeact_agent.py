import logging
import re
import inspect
import time
import asyncio
from typing import List, Optional, Tuple, Union
from llama_index.core.base.llms.types import ChatMessage, ChatResponse
from llama_index.core.prompts import PromptTemplate
from llama_index.core.llms.llm import LLM
from llama_index.core.workflow import Workflow, StartEvent, StopEvent, Context, step
from llama_index.core.memory import Memory
from droidrun.agent.codeact.events import TaskInputEvent, TaskEndEvent, TaskExecutionEvent, TaskExecutionResultEvent, TaskThinkingEvent
from droidrun.agent.common.events import ScreenshotEvent
from droidrun.agent.utils import chat_utils
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
        max_steps: int = 10,
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

        self.chat_memory = None
        self.episodic_memory = None

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

    @step
    async def prepare_chat(self, ctx: Context, ev: StartEvent) -> TaskInputEvent:
        """Prepare chat history from user input."""
        logger.info("💬 Preparing chat for task execution...")

        self.chat_memory: Memory = await ctx.get("chat_memory", default=Memory.from_defaults())
        self.episodic_memory = await ctx.get("episodic_memory", default=None)

        user_input = ev.get("input", default=None)
        assert user_input, "User input cannot be empty."

        logger.debug("  - Adding goal to memory.")
        goal = user_input
        self.user_message = ChatMessage(role="user", content=PromptTemplate(self.user_prompt or DEFAULT_CODE_ACT_USER_PROMPT).format(goal=goal))
        self.no_thoughts_prompt = ChatMessage(role="user", content=PromptTemplate(DEFAULT_NO_THOUGHTS_PROMPT).format(goal=goal))
        await self.chat_memory.aput(self.user_message)

        await ctx.set("chat_memory", self.chat_memory)
        input_messages = self.chat_memory.get_all()
        return TaskInputEvent(input=input_messages)
    @step
    async def handle_llm_input(self, ctx: Context, ev: TaskInputEvent) -> TaskThinkingEvent:
        """Handle LLM input."""
        chat_history = ev.input
        assert len(chat_history) > 0, "Chat history cannot be empty."

        self.steps_counter += 1
        logger.info(f"🧠 Step {self.steps_counter}: Thinking...")
        
        screenshot = (await self.tools.take_screenshot())[1]
        ctx.write_event_to_stream(ScreenshotEvent(screenshot=screenshot))
        await ctx.set("screenshot", screenshot)

        await ctx.set("ui_state", await self.tools.get_clickables())
        await ctx.set("phone_state", await self.tools.get_phone_state())
        await ctx.set("episodic_memory", self.episodic_memory)

        response = await self._get_llm_response(ctx, chat_history)
        await self.chat_memory.aput(response.message)

        code, thoughts = chat_utils.extract_code_and_thought(response.message.content)

        event = TaskThinkingEvent(thoughts=thoughts, code=code)
        ctx.write_event_to_stream(event)
        return event

    @step
    async def handle_llm_output(self, ctx: Context, ev: TaskThinkingEvent) -> Union[TaskExecutionEvent, TaskInputEvent]:
        """Handle LLM output."""
        logger.debug("⚙️ Handling LLM output...")
        code = ev.code
        thoughts = ev.thoughts

        if not thoughts:
            logger.warning("🤔 LLM provided code without thoughts. Adding reminder prompt.")
            await self.chat_memory.aput(self.no_thoughts_prompt)
        else:
            logger.info(f"🤔 Reasoning: {thoughts}")

        if code:
            return TaskExecutionEvent(code=code)
        else:
            message = ChatMessage(role="user", content="No code was provided. If you want to mark task as complete (whether it failed or succeeded), use complete(success:bool, reason:str) function within a code block ```pythn\n```.")
            await self.chat_memory.aput(message)
            return TaskInputEvent(input=self.chat_memory.get_all()) 

    @step
    async def execute_code(self, ctx: Context, ev: TaskExecutionEvent) -> Union[TaskExecutionResultEvent, TaskEndEvent]:
        """Execute the code and return the result."""
        code = ev.code
        assert code, "Code cannot be empty."
        logger.info(f"⚡ Executing action...")
        logger.debug(f"Code to execute:\n```python\n{code}\n```")

        try:
            self.code_exec_counter += 1
            result = await self.executor.execute(ctx, code)
            logger.info(f"💡 Code execution successful. Result: {result}")

            if self.tools.finished == True:
                logger.debug("  - Task completed.")
                event = TaskEndEvent(success=self.tools.success, reason=self.tools.reason)
                ctx.write_event_to_stream(event)
                return event
            
            event = TaskExecutionResultEvent(output=str(result))
            ctx.write_event_to_stream(event)
            return event
        
        except Exception as e:
            logger.error(f"💥 Action failed: {e}")
            if self.debug:
                logger.error("Exception details:", exc_info=True)
            error_message = f"Error during execution: {e}"
  
            event = TaskExecutionResultEvent(output=error_message)
            ctx.write_event_to_stream(event)
            return event

    @step
    async def handle_execution_result(self, ctx: Context, ev: TaskExecutionResultEvent) -> TaskInputEvent:
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
        await self.chat_memory.aput(observation_message)
        
        inputEvent = TaskInputEvent(input=self.chat_memory.get_all())
        ctx.write_event_to_stream(inputEvent)
        return inputEvent
    

    @step
    async def finalize(self, ev: TaskEndEvent, ctx: Context) -> StopEvent:
        """Finalize the workflow."""
        self.tools.finished = False
        await ctx.set("chat_memory", self.chat_memory)
        
        result = {}
        result.update({
            "success": ev.success,
            "reason": ev.reason,
            "codeact_steps": self.steps_counter,
            "code_executions": self.code_exec_counter
        })
        
        event = StopEvent(result=result)
        ctx.write_event_to_stream(event)
        return event

    async def _get_llm_response(self, ctx: Context, chat_history: List[ChatMessage]) -> ChatResponse:
        """Get streaming response from LLM."""
        logger.debug(f"  - Sending {len(chat_history)} messages to LLM.")

        model = self.llm.class_name()
        if model != "DeepSeek":
            chat_history = await chat_utils.add_screenshot_image_block(await ctx.get("screenshot"), chat_history)
        else:
            logger.warning("[yellow]DeepSeek doesnt support images. Disabling screenshots[/]")

        episodic_memory = await ctx.get("episodic_memory", default=None)
        if episodic_memory:
            chat_history = await chat_utils.add_memory_block(episodic_memory, chat_history)

        chat_history = await chat_utils.add_ui_text_block(await ctx.get("ui_state"), chat_history)
        chat_history = await chat_utils.add_phone_state_block(await ctx.get("phone_state"), chat_history)

        
        messages_to_send = [self.system_prompt] + chat_history 

        messages_to_send = [chat_utils.message_copy(msg) for msg in messages_to_send]
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
    
