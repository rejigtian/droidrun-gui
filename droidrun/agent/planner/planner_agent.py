from droidrun.agent.planner.events import *
from droidrun.agent.planner.prompts import (
    DEFAULT_PLANNER_SYSTEM_PROMPT,
    DEFAULT_PLANNER_USER_PROMPT,
)
import logging
import asyncio
from typing import List, TYPE_CHECKING, Union
import inspect
from llama_index.core.base.llms.types import ChatMessage, ChatResponse
from llama_index.core.prompts import PromptTemplate
from llama_index.core.llms.llm import LLM
from llama_index.core.workflow import Workflow, StartEvent, StopEvent, Context, step
from llama_index.core.memory import Memory
from llama_index.core.llms.llm import LLM
from droidrun.agent.utils.executer import SimpleCodeExecutor
from droidrun.agent.utils import chat_utils
from droidrun.agent.utils.task_manager import TaskManager
from droidrun.tools import Tools
from droidrun.agent.common.events import ScreenshotEvent
from droidrun.agent.planner.events import PlanInputEvent, PlanCreatedEvent, PlanThinkingEvent
from droidrun.agent.context.agent_persona import AgentPersona

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
                personas: List[AgentPersona],
                task_manager: TaskManager,
                tools_instance: Tools,
                system_prompt = None,
                user_prompt = None, 
                debug = False,
                *args,
                **kwargs
                ) -> None:
        super().__init__(*args, **kwargs)
        
            
        self.llm = llm
        self.goal = goal
        self.task_manager = task_manager
        self.debug = debug
        
        self.chat_memory = None
        self.episodic_memory = None

        self.current_retry = 0
        self.steps_counter = 0
        
        self.tools = [self.task_manager.set_tasks_with_agents]

        self.tools_description = self.parse_tool_descriptions()
        self.tools_instance = tools_instance

        self.personas = personas 

        self.system_prompt = system_prompt or DEFAULT_PLANNER_SYSTEM_PROMPT.format(
            tools_description=self.tools_description,
            agents=self.parse_persona_description()
        )
        self.user_prompt = user_prompt or DEFAULT_PLANNER_USER_PROMPT.format(goal=goal)
        self.system_message = ChatMessage(role="system", content=self.system_prompt)
        self.user_message = ChatMessage(role="user", content=self.user_prompt)
        

        self.executer = SimpleCodeExecutor(
            loop=asyncio.get_event_loop(),
            globals={},
            locals={},
            tools=self.tools
        )

    def parse_persona_description(self) -> str:
        """Parses the available agent personas and their descriptions for the system prompt."""
        logger.debug("👥 Parsing agent persona descriptions for Planner Agent...")
        
        if not self.personas:
            logger.warning("No agent personas provided to Planner Agent")
            return "No specialized agents available."
        
        persona_descriptions = []
        for persona in self.personas:
            # Format each persona with name, description, and expertise areas
            expertise_list = ", ".join(persona.expertise_areas) if persona.expertise_areas else "General tasks"
            formatted_persona = f"- **{persona.name}**: {persona.description}\n  Expertise: {expertise_list}"
            persona_descriptions.append(formatted_persona)
            logger.debug(f"  - Parsed persona: {persona.name}")
        
        # Join all persona descriptions into a single string
        descriptions = "\n".join(persona_descriptions)
        logger.debug(f"👤 Found {len(persona_descriptions)} agent personas.")
        return descriptions
    

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
    

    @step
    async def prepare_chat(self, ctx: Context, ev: StartEvent) -> PlanInputEvent:
        logger.info("💬 Preparing planning session...")

        self.chat_memory: Memory = await ctx.get("chat_memory", default=Memory.from_defaults())
        await self.chat_memory.aput(self.user_message)

        if ev.episodic_memory:
            self.episodic_memory = ev.episodic_memory
        
        assert len(self.chat_memory.get_all()) > 0 or self.user_prompt, "Memory input, user prompt or user input cannot be empty."
        
        await self.chat_memory.aput(ChatMessage(role="user", content=PromptTemplate(self.user_prompt or DEFAULT_PLANNER_USER_PROMPT.format(goal=self.goal))))
        
        input_messages = self.chat_memory.get_all()
        logger.debug(f"  - Memory contains {len(input_messages)} messages")
        return PlanInputEvent(input=input_messages)
    
    @step
    async def handle_llm_input(self, ev: PlanInputEvent, ctx: Context) -> PlanThinkingEvent:
        """Handle LLM input."""
        chat_history = ev.input
        assert len(chat_history) > 0, "Chat history cannot be empty."

        ctx.write_event_to_stream(ev)

        self.steps_counter += 1
        logger.info(f"🧠 Thinking about how to plan the goal...")

        screenshot = (await self.tools_instance.take_screenshot())[1]
        ctx.write_event_to_stream(ScreenshotEvent(screenshot=screenshot))
        await ctx.set("screenshot", screenshot)

        await ctx.set("ui_state", await self.tools_instance.get_clickables())
        await ctx.set("phone_state", await self.tools_instance.get_phone_state())
        await ctx.set("episodic_memory", self.episodic_memory)

        response = await self._get_llm_response(ctx, chat_history)
        await self.chat_memory.aput(response.message)
        
        code, thoughts = chat_utils.extract_code_and_thought(response.message.content)
            
        event = PlanThinkingEvent(thoughts=thoughts, code=code)
        ctx.write_event_to_stream(event)
        return event
    
    
    @step
    async def handle_llm_output(self, ev: PlanThinkingEvent, ctx: Context) -> Union[PlanInputEvent, PlanCreatedEvent]:
        """Handle LLM output."""
        logger.debug("🤖 Processing planning output...")
        code = ev.code
        thoughts = ev.thoughts

        if code:
            try:
                result = await self.executer.execute(ctx, code)
                logger.info(f"📝 Planning complete")
                logger.debug(f"  - Planning code executed. Result: {result}")

                await self.chat_memory.aput(ChatMessage(role="user", content=f"Execution Result:\n```\n{result}\n```"))

                self.episodic_memory = self.tools_instance.memory

                tasks = self.task_manager.get_all_tasks()
                logger.info(f"📋 Current plan created with {len(tasks)} tasks:")
                for i, task in enumerate(tasks):
                    logger.info(f"  Task {i}: [{task['status'].upper()}] [{task['agent_type']}] {task['description']}")
                    if 'context' in task:
                        logger.debug(f"    Context: {task['context']}")
                
                event = PlanCreatedEvent(tasks=tasks)
                ctx.write_event_to_stream(event)
                    
                return event
            
            except Exception as e:
                await self.chat_memory.aput(ChatMessage(role="user", content=f"Please either set new tasks using set_tasks_with_agents() or mark the goal as complete using complete_goal() if done."))
                logger.debug("🔄 Waiting for next plan or completion.")
                return PlanInputEvent(input=self.chat_memory.get_all())
        else:
            await self.chat_memory.aput(ChatMessage(role="user", content=f"Please either set new tasks using set_tasks_with_agents() or mark the goal as complete using complete_goal() if done."))
            logger.debug("🔄 Waiting for next plan or completion.")
            return PlanInputEvent(input=self.chat_memory.get_all())
        

    @step
    async def finalize(self, ev: PlanCreatedEvent, ctx: Context) -> StopEvent:
        """Finalize the workflow."""
        await ctx.set("chat_memory", self.chat_memory)
        
        result = {}
        result.update({
            "tasks": ev.tasks,
        })
        
        return StopEvent(result=result)


    async def _get_llm_response(self, ctx: Context, chat_history: List[ChatMessage]) -> ChatResponse:
        """Get streaming response from LLM."""
        logger.debug(f"  - Sending {len(chat_history)} messages to LLM.")

        model = self.llm.class_name()
        if model != "DeepSeek":
            chat_history = await chat_utils.add_screenshot_image_block(await ctx.get("screenshot"), chat_history)
        else:
            logger.warning("[yellow]DeepSeek doesnt support images. Disabling screenshots[/]")

        chat_history = await chat_utils.add_task_history_block(self.task_manager.get_completed_tasks(), self.task_manager.get_failed_tasks(), chat_history)

        episodic_memory = await ctx.get("episodic_memory", default=None)
        if episodic_memory:
            chat_history = await chat_utils.add_memory_block(episodic_memory, chat_history)

        chat_history = await chat_utils.add_ui_text_block(await ctx.get("ui_state"), chat_history)
        chat_history = await chat_utils.add_phone_state_block(await ctx.get("phone_state"), chat_history)

        
        messages_to_send = [self.system_message] + chat_history 
        messages_to_send = [chat_utils.message_copy(msg) for msg in messages_to_send]
        
        logger.debug(f"  - Final message count: {len(messages_to_send)}")

        response = await self.llm.achat(
            messages=messages_to_send
        )
        assert hasattr(response, "message"), f"LLM response does not have a message attribute.\nResponse: {response}"
        logger.debug("  - Received response from LLM.")
        return response