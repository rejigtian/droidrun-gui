---
title: Agent
---

<a id="droidrun.agent.droid.events"></a>

# droidrun.agent.droid.events

<a id="droidrun.agent.droid"></a>

# droidrun.agent.droid

Droidrun Agent Module.

This module provides a ReAct agent for automating Android devices using reasoning and acting.

<a id="droidrun.agent.droid.droid_agent"></a>

# droidrun.agent.droid.droid\_agent

DroidAgent - A wrapper class that coordinates the planning and execution of tasks
to achieve a user's goal on an Android device.

<a id="droidrun.agent.droid.droid_agent.DroidAgent"></a>

## droidrun.agent.droid.droid\_agent.DroidAgent

```python
class DroidAgent(Workflow)
```

A wrapper class that coordinates between PlannerAgent (creates plans) and 
    CodeActAgent (executes tasks) to achieve a user's goal.

<a id="droidrun.agent.droid.droid_agent.DroidAgent.__init__"></a>

#### \_\_init\_\_

```python
def __init__(
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
    save_trajectories: bool = False,
    *args,
    **kwargs
)
```

Initialize the DroidAgent wrapper.

**Arguments**:

- `goal` - The user's goal or command to execute
- `llm` - The language model to use for both agents
- `max_steps` - Maximum number of steps for both agents
- `timeout` - Timeout for agent execution in seconds
- `reasoning` - Whether to use the PlannerAgent for complex reasoning (True)
  or send tasks directly to CodeActAgent (False)
- `reflection` - Whether to reflect on steps the CodeActAgent did to give the PlannerAgent advice
- `enable_tracing` - Whether to enable Arize Phoenix tracing
- `debug` - Whether to enable verbose debug logging
- `**kwargs` - Additional keyword arguments to pass to the agents

<a id="droidrun.agent.droid.droid_agent.DroidAgent.execute_task"></a>

#### execute\_task

```python
async def execute_task(
    ctx: Context, ev: CodeActExecuteEvent
) -> CodeActResultEvent
```

Execute a single task using the CodeActAgent.

**Arguments**:

- `task` - Task dictionary with description and status
  

**Returns**:

  Tuple of (success, reason)

<a id="droidrun.agent.droid.droid_agent.DroidAgent.start_handler"></a>

#### start\_handler

```python
async def start_handler(
    ctx: Context, ev: StartEvent
) -> CodeActExecuteEvent | ReasoningLogicEvent
```

Main execution loop that coordinates between planning and execution.

**Returns**:

  Dict containing the execution result

<a id="droidrun.agent.context.agent_persona"></a>

# droidrun.agent.context.agent\_persona

<a id="droidrun.agent.context.agent_persona.AgentPersona"></a>

## droidrun.agent.context.agent\_persona.AgentPersona

```python
class AgentPersona()
```

Represents a specialized agent persona with its configuration.

<a id="droidrun.agent.context.reflection"></a>

# droidrun.agent.context.reflection

<a id="droidrun.agent.context.reflection.Reflection"></a>

## droidrun.agent.context.reflection.Reflection

```python
class Reflection()
```

Represents the result of a reflection analysis on episodic memory.

<a id="droidrun.agent.context.reflection.Reflection.from_dict"></a>

#### from\_dict

```python
def from_dict(cls, data: dict) -> 'Reflection'
```

Create a Reflection from a dictionary (e.g., parsed JSON).

<a id="droidrun.agent.context"></a>

# droidrun.agent.context

Agent Context Module - Provides specialized agent personas and context injection management.

This module contains:
- AgentPersona: Dataclass for defining specialized agent configurations
- ContextInjectionManager: Manager for handling different agent personas and their contexts

<a id="droidrun.agent.context.personas"></a>

# droidrun.agent.context.personas

<a id="droidrun.agent.context.personas.default"></a>

# droidrun.agent.context.personas.default

<a id="droidrun.agent.context.personas.app_starter"></a>

# droidrun.agent.context.personas.app\_starter

<a id="droidrun.agent.context.personas.ui_expert"></a>

# droidrun.agent.context.personas.ui\_expert

<a id="droidrun.agent.context.task_manager"></a>

# droidrun.agent.context.task\_manager

<a id="droidrun.agent.context.task_manager.Task"></a>

## droidrun.agent.context.task\_manager.Task

```python
class Task()
```

Represents a single task with its properties.

<a id="droidrun.agent.context.task_manager.TaskManager"></a>

## droidrun.agent.context.task\_manager.TaskManager

```python
class TaskManager()
```

Manages a list of tasks for an agent, each with a status and assigned specialized agent.

<a id="droidrun.agent.context.task_manager.TaskManager.__init__"></a>

#### \_\_init\_\_

```python
def __init__()
```

Initializes an empty task list.

<a id="droidrun.agent.context.task_manager.TaskManager.save_to_file"></a>

#### save\_to\_file

```python
def save_to_file()
```

Saves the current task list to a Markdown file.

<a id="droidrun.agent.context.task_manager.TaskManager.set_tasks_with_agents"></a>

#### set\_tasks\_with\_agents

```python
def set_tasks_with_agents(task_assignments: List[Dict[str, str]])
```

Clears the current task list and sets new tasks with their assigned agents.

**Arguments**:

- `task_assignments` - A list of dictionaries, each containing:
  - 'task': The task description string
  - 'agent': The agent type
  

**Example**:

  task_manager.set_tasks_with_agents([
- `{'task'` - 'Open Gmail app', 'agent': 'AppStarterExpert'},
- `{'task'` - 'Navigate to compose email', 'agent': 'UIExpert'}
  ])

<a id="droidrun.agent.context.task_manager.TaskManager.complete_goal"></a>

#### complete\_goal

```python
def complete_goal(message: str)
```

Marks the goal as completed, use this whether the task completion was successful or on failure.
This method should be called when the task is finished, regardless of the outcome.

**Arguments**:

- `message` - The message to be logged.

<a id="droidrun.agent.context.context_injection_manager"></a>

# droidrun.agent.context.context\_injection\_manager

Context Injection Manager - Manages specialized agent personas with dynamic tool and context injection.

This module provides the ContextInjectionManager class that manages different agent personas,
each with specific system prompts, contexts, and tool subsets tailored for specialized tasks.

<a id="droidrun.agent.context.context_injection_manager.ContextInjectionManager"></a>

## droidrun.agent.context.context\_injection\_manager.ContextInjectionManager

```python
class ContextInjectionManager()
```

Manages different agent personas with specialized contexts and tool subsets.

This class is responsible for:
- Defining agent personas with specific capabilities
- Injecting appropriate system prompts based on agent type
- Filtering tool lists to match agent specialization
- Providing context-aware configurations for CodeActAgent instances

<a id="droidrun.agent.context.context_injection_manager.ContextInjectionManager.__init__"></a>

#### \_\_init\_\_

```python
def __init__(personas: List[AgentPersona])
```

Initialize the Context Injection Manager with predefined personas.

<a id="droidrun.agent.context.context_injection_manager.ContextInjectionManager.get_persona"></a>

#### get\_persona

```python
def get_persona(agent_type: str) -> Optional[AgentPersona]
```

Get a specific agent persona by type.

**Arguments**:

- `agent_type` - The type of agent ("UIExpert" or "AppStarterExpert")
  

**Returns**:

  AgentPersona instance or None if not found

<a id="droidrun.agent.context.episodic_memory"></a>

# droidrun.agent.context.episodic\_memory

<a id="droidrun.agent.planner.events"></a>

# droidrun.agent.planner.events

<a id="droidrun.agent.planner.planner_agent"></a>

# droidrun.agent.planner.planner\_agent

<a id="droidrun.agent.planner.planner_agent.PlannerAgent"></a>

## droidrun.agent.planner.planner\_agent.PlannerAgent

```python
class PlannerAgent(Workflow)
```

<a id="droidrun.agent.planner.planner_agent.PlannerAgent.handle_llm_input"></a>

#### handle\_llm\_input

```python
async def handle_llm_input(
    ev: PlanInputEvent, ctx: Context
) -> PlanThinkingEvent
```

Handle LLM input.

<a id="droidrun.agent.planner.planner_agent.PlannerAgent.handle_llm_output"></a>

#### handle\_llm\_output

```python
async def handle_llm_output(
    ev: PlanThinkingEvent, ctx: Context
) -> Union[PlanInputEvent, PlanCreatedEvent]
```

Handle LLM output.

<a id="droidrun.agent.planner.planner_agent.PlannerAgent.finalize"></a>

#### finalize

```python
async def finalize(ev: PlanCreatedEvent, ctx: Context) -> StopEvent
```

Finalize the workflow.

<a id="droidrun.agent.planner"></a>

# droidrun.agent.planner

<a id="droidrun.agent.planner.prompts"></a>

# droidrun.agent.planner.prompts

Prompt templates for the PlannerAgent.

This module contains all the prompts used by the PlannerAgent,
separated from the workflow logic for better maintainability.

<a id="droidrun.agent.codeact.events"></a>

# droidrun.agent.codeact.events

<a id="droidrun.agent.codeact"></a>

# droidrun.agent.codeact

<a id="droidrun.agent.codeact.prompts"></a>

# droidrun.agent.codeact.prompts

Prompt templates for the CodeActAgent.

This module contains all the prompts used by the CodeActAgent,
separated from the workflow logic for better maintainability.

<a id="droidrun.agent.codeact.codeact_agent"></a>

# droidrun.agent.codeact.codeact\_agent

<a id="droidrun.agent.codeact.codeact_agent.CodeActAgent"></a>

## droidrun.agent.codeact.codeact\_agent.CodeActAgent

```python
class CodeActAgent(Workflow)
```

An agent that uses a ReAct-like cycle (Thought -> Code -> Observation)
to solve problems requiring code execution. It extracts code from
Markdown blocks and uses specific step types for tracking.

<a id="droidrun.agent.codeact.codeact_agent.CodeActAgent.prepare_chat"></a>

#### prepare\_chat

```python
async def prepare_chat(ctx: Context, ev: StartEvent) -> TaskInputEvent
```

Prepare chat history from user input.

<a id="droidrun.agent.codeact.codeact_agent.CodeActAgent.handle_llm_input"></a>

#### handle\_llm\_input

```python
async def handle_llm_input(
    ctx: Context, ev: TaskInputEvent
) -> TaskThinkingEvent | TaskEndEvent
```

Handle LLM input.

<a id="droidrun.agent.codeact.codeact_agent.CodeActAgent.handle_llm_output"></a>

#### handle\_llm\_output

```python
async def handle_llm_output(
    ctx: Context, ev: TaskThinkingEvent
) -> Union[TaskExecutionEvent, TaskInputEvent]
```

Handle LLM output.

<a id="droidrun.agent.codeact.codeact_agent.CodeActAgent.execute_code"></a>

#### execute\_code

```python
async def execute_code(
    ctx: Context, ev: TaskExecutionEvent
) -> Union[TaskExecutionResultEvent, TaskEndEvent]
```

Execute the code and return the result.

<a id="droidrun.agent.codeact.codeact_agent.CodeActAgent.handle_execution_result"></a>

#### handle\_execution\_result

```python
async def handle_execution_result(
    ctx: Context, ev: TaskExecutionResultEvent
) -> TaskInputEvent
```

Handle the execution result. Currently it just returns InputEvent.

<a id="droidrun.agent.codeact.codeact_agent.CodeActAgent.finalize"></a>

#### finalize

```python
async def finalize(ev: TaskEndEvent, ctx: Context) -> StopEvent
```

Finalize the workflow.

<a id="droidrun.agent.utils.executer"></a>

# droidrun.agent.utils.executer

<a id="droidrun.agent.utils.executer.SimpleCodeExecutor"></a>

## droidrun.agent.utils.executer.SimpleCodeExecutor

```python
class SimpleCodeExecutor()
```

A simple code executor that runs Python code with state persistence.

This executor maintains a global and local state between executions,
allowing for variables to persist across multiple code runs.

NOTE: not safe for production use! Use with caution.

<a id="droidrun.agent.utils.executer.SimpleCodeExecutor.__init__"></a>

#### \_\_init\_\_

```python
def __init__(
    loop: AbstractEventLoop,
    locals: Dict[str, Any] = {},
    globals: Dict[str, Any] = {},
    tools={},
    use_same_scope: bool = True
)
```

Initialize the code executor.

**Arguments**:

- `locals` - Local variables to use in the execution context
- `globals` - Global variables to use in the execution context
- `tools` - List of tools available for execution

<a id="droidrun.agent.utils.executer.SimpleCodeExecutor.execute"></a>

#### execute

```python
async def execute(ctx: Context, code: str) -> str
```

Execute Python code and capture output and return values.

**Arguments**:

- `code` - Python code to execute
  

**Returns**:

- `str` - Output from the execution, including print statements.

<a id="droidrun.agent.utils.async_utils"></a>

# droidrun.agent.utils.async\_utils

<a id="droidrun.agent.utils.async_utils.async_to_sync"></a>

#### droidrun.agent.utils.async\_utils.async\_to\_sync

```python
def async_to_sync(func)
```

Convert an async function to a sync function.

**Arguments**:

- `func` - Async function to convert
  

**Returns**:

- `Callable` - Synchronous version of the async function

<a id="droidrun.agent.utils"></a>

# droidrun.agent.utils

Utility modules for DroidRun agents.

<a id="droidrun.agent.utils.trajectory"></a>

# droidrun.agent.utils.trajectory

Trajectory utilities for DroidRun agents.

This module provides helper functions for working with agent trajectories,
including saving, loading, and analyzing them.

<a id="droidrun.agent.utils.trajectory.Trajectory"></a>

## droidrun.agent.utils.trajectory.Trajectory

```python
class Trajectory()
```

<a id="droidrun.agent.utils.trajectory.Trajectory.__init__"></a>

#### \_\_init\_\_

```python
def __init__()
```

Initializes an empty trajectory class.

<a id="droidrun.agent.utils.trajectory.Trajectory.create_screenshot_gif"></a>

#### create\_screenshot\_gif

```python
def create_screenshot_gif(output_path: str, duration: int = 1000) -> str
```

Create a GIF from a list of screenshots.

**Arguments**:

- `output_path` - Base path for the GIF (without extension)
- `duration` - Duration for each frame in milliseconds
  

**Returns**:

  Path to the created GIF file

<a id="droidrun.agent.utils.trajectory.Trajectory.save_trajectory"></a>

#### save\_trajectory

```python
def save_trajectory(directory: str = "trajectories") -> str
```

Save trajectory steps to a JSON file and create a GIF of screenshots if available.

**Arguments**:

- `directory` - Directory to save the trajectory files
  

**Returns**:

  Path to the saved trajectory file

<a id="droidrun.agent.utils.trajectory.Trajectory.get_trajectory_statistics"></a>

#### get\_trajectory\_statistics

```python
def get_trajectory_statistics(
    trajectory_data: Dict[str, Any]
) -> Dict[str, Any]
```

Get statistics about a trajectory.

**Arguments**:

- `trajectory_data` - The trajectory data dictionary
  

**Returns**:

  Dictionary with statistics about the trajectory

<a id="droidrun.agent.utils.trajectory.Trajectory.print_trajectory_summary"></a>

#### print\_trajectory\_summary

```python
def print_trajectory_summary(trajectory_data: Dict[str, Any]) -> None
```

Print a summary of a trajectory.

**Arguments**:

- `trajectory_data` - The trajectory data dictionary

<a id="droidrun.agent.utils.chat_utils"></a>

# droidrun.agent.utils.chat\_utils

<a id="droidrun.agent.utils.chat_utils.add_reflection_summary"></a>

#### droidrun.agent.utils.chat\_utils.add\_reflection\_summary

```python
async def add_reflection_summary(
    reflection: Reflection, chat_history: List[ChatMessage]
) -> List[ChatMessage]
```

Add reflection summary and advice to help the planner understand what went wrong and what to do differently.

<a id="droidrun.agent.utils.chat_utils.add_ui_text_block"></a>

#### droidrun.agent.utils.chat\_utils.add\_ui\_text\_block

```python
async def add_ui_text_block(
    ui_state: str,
    chat_history: List[ChatMessage],
    copy=True
) -> List[ChatMessage]
```

Add UI elements to the chat history without modifying the original.

<a id="droidrun.agent.utils.chat_utils.parse_tool_descriptions"></a>

#### droidrun.agent.utils.chat\_utils.parse\_tool\_descriptions

```python
def parse_tool_descriptions(tool_list) -> str
```

Parses the available tools and their descriptions for the system prompt.

<a id="droidrun.agent.utils.chat_utils.parse_persona_description"></a>

#### droidrun.agent.utils.chat\_utils.parse\_persona\_description

```python
def parse_persona_description(personas) -> str
```

Parses the available agent personas and their descriptions for the system prompt.

<a id="droidrun.agent.utils.chat_utils.extract_code_and_thought"></a>

#### droidrun.agent.utils.chat\_utils.extract\_code\_and\_thought

```python
def extract_code_and_thought(response_text: str) -> Tuple[Optional[str], str]
```

Extracts code from Markdown blocks (```python ... ```) and the surrounding text (thought),
handling indented code blocks.

**Returns**:

  Tuple[Optional[code_string], thought_string]

<a id="droidrun.agent.utils.llm_picker"></a>

# droidrun.agent.utils.llm\_picker

<a id="droidrun.agent.utils.llm_picker.load_llm"></a>

#### droidrun.agent.utils.llm\_picker.load\_llm

```python
def load_llm(provider_name: str, **kwargs: Any) -> LLM
```

Dynamically loads and initializes a LlamaIndex LLM.

Imports `llama_index.llms.<provider_name_lower>`, finds the class named
`provider_name` within that module, verifies it's an LLM subclass,
and initializes it with kwargs.

**Arguments**:

- `provider_name` - The case-sensitive name of the provider and the class
  (e.g., "OpenAI", "Ollama", "HuggingFaceLLM").
- `**kwargs` - Keyword arguments for the LLM class constructor.
  

**Returns**:

  An initialized LLM instance.
  

**Raises**:

- `ModuleNotFoundError` - If the provider's module cannot be found.
- `AttributeError` - If the class `provider_name` is not found in the module.
- `TypeError` - If the found class is not a subclass of LLM or if kwargs are invalid.
- `RuntimeError` - For other initialization errors.

<a id="droidrun.agent.oneflows.reflector"></a>

# droidrun.agent.oneflows.reflector

<a id="droidrun.agent.oneflows.reflector.Reflector"></a>

## droidrun.agent.oneflows.reflector.Reflector

```python
class Reflector()
```

<a id="droidrun.agent.oneflows.reflector.Reflector.reflect_on_episodic_memory"></a>

#### reflect\_on\_episodic\_memory

```python
async def reflect_on_episodic_memory(
    episodic_memory: EpisodicMemory, goal: str
) -> Reflection
```

Analyze episodic memory and provide reflection on the agent's performance.

<a id="droidrun.agent.common.events"></a>

# droidrun.agent.common.events

<a id="droidrun.agent.common.default"></a>

# droidrun.agent.common.default

