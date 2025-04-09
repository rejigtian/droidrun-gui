"""
ReAct Agent - Reasoning + Acting agent for controlling Android devices.

This module implements a ReAct agent that can control Android devices through
reasoning about the current state and taking appropriate actions.
"""

import asyncio
import json
import time
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Callable

# Import tools
from droidrun.tools import (
    DeviceManager,
    tap,
    swipe,
    input_text,
    press_key,
    start_app,
    install_app,
    uninstall_app,
    take_screenshot,
    list_packages,
    get_ui_elements,
    get_clickables,
    complete,
)

# Import LLM reasoning
from .llm_reasoning import LLMReasoner

# Set up logger
logger = logging.getLogger("droidrun")

class ReActStepType(Enum):
    """Types of steps in a ReAct agent's reasoning and acting process."""
    THOUGHT = "thought"  # Internal reasoning step
    ACTION = "action"    # Taking an action
    OBSERVATION = "observation"  # Observing the result
    PLAN = "plan"        # Planning future steps
    GOAL = "goal"        # Setting or refining the goal

class ReActStep:
    """A single step in the ReAct agent's process."""
    
    def __init__(
        self, 
        step_type: ReActStepType, 
        content: str, 
    ):
        """Initialize a ReAct step.
        
        Args:
            step_type: The type of step (thought, action, observation)
            content: The content of the step
        """
        self.step_type = step_type
        self.content = content
        self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the step to a dictionary.
        
        Returns:
            Dict representation of the step
        """
        return {
            "type": self.step_type.value,
            "content": self.content,
            "timestamp": self.timestamp
        }
    
    def __str__(self) -> str:
        """String representation of the step.
        
        Returns:
            Formatted string representation
        """
        type_str = self.step_type.value.upper()
        
        # Format based on step type
        if self.step_type == ReActStepType.THOUGHT:
            return f"🤔 THOUGHT: {self.content}"
        elif self.step_type == ReActStepType.ACTION:
            return f"🔄 ACTION: {self.content}"
        elif self.step_type == ReActStepType.OBSERVATION:
            return f"👁️ OBSERVATION: {self.content}"
        elif self.step_type == ReActStepType.PLAN:
            return f"📝 PLAN: {self.content}"
        elif self.step_type == ReActStepType.GOAL:
            return f"🎯 GOAL: {self.content}"
        
        return f"{type_str}: {self.content}"

class ReActAgent:
    """ReAct agent for Android device automation."""
    
    def __init__(
        self, 
        device_serial: Optional[str] = None,
        goal: Optional[str] = None,
        max_steps: int = 100,
        llm_provider: str = "openai",
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        debug: bool = False
    ):
        """Initialize the ReAct agent.
        
        Args:
            device_serial: Serial number of the Android device to control
            goal: Initial automation goal
            max_steps: Maximum number of steps to take
            llm_provider: LLM provider ('openai' or 'anthropic')
            model_name: Model name to use
            api_key: API key for the LLM provider
            debug: Whether to enable debug logging
        """
        self.device_serial = device_serial
        self.goal = goal
        self.max_steps = max_steps
        self.debug = debug
        
        # Initialize steps list
        self.steps: List[ReActStep] = []
        
        # Initialize screenshot storage
        self._last_screenshot: Optional[bytes] = None
        
        # Configure logging
        if debug:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)
        
        # Define available tools and their functions
        self.tools: Dict[str, Callable] = {
            # UI interaction
            "tap": tap,
            "swipe": swipe,
            "input_text": input_text,
            "press_key": press_key,
            
            # App management
            "start_app": start_app,
            #"install_app": install_app,
            #"uninstall_app": uninstall_app,
            "list_packages": list_packages,
            
            # UI analysis
            #"get_ui_elements": get_ui_elements,
            "get_clickables": get_clickables,
            
            # Media
            "take_screenshot": take_screenshot,
            
            # Goal management
            "complete": complete,
        }
        
        # Initialize device manager
        self.device_manager = DeviceManager()
        
        # Initialize LLM reasoner
        try:
            self.reasoner = LLMReasoner(
                llm_provider=llm_provider,
                model_name=model_name,
                api_key=api_key,
                temperature=0.2,
                max_tokens=2000
            )
            self.use_llm = True
        except (ImportError, ValueError) as e:
            logger.warning(f"LLM reasoning not available: {e}")
            self.reasoner = None
            self.use_llm = False
    
    async def connect(self) -> bool:
        """Connect to the specified device.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            devices = await self.device_manager.list_devices()
            
            if not self.device_serial:
                # If no device specified, use the first one available
                if not devices:
                    logger.error("No devices found")
                    return False
                
                self.device_serial = devices[0].serial
                logger.info(f"Using first available device: {self.device_serial}")
            
            # Check if specified device exists
            device_exists = False
            for device in devices:
                if device.serial == self.device_serial:
                    device_exists = True
                    break
            
            if not device_exists:
                logger.error(f"Device {self.device_serial} not found")
                return False
            
            logger.info(f"Connected to device: {self.device_serial}")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to device: {e}")
            return False
    
    async def add_step(
        self, 
        step_type: ReActStepType, 
        content: str,
    ) -> ReActStep:
        """Add a step to the agent's reasoning process.
        
        Args:
            step_type: Type of step
            content: Content of the step
        
        Returns:
            The created ReActStep
        """
        # Create the step
        step = ReActStep(step_type, content)
        
        # Add to steps list
        self.steps.append(step)
        
        # Log the step
        logger.info(str(step))
        
        return step
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """Execute a tool by name with the given arguments.
        
        Args:
            tool_name: Name of the tool to execute
            **kwargs: Arguments to pass to the tool
        
        Returns:
            The result of tool execution
        
        Raises:
            ValueError: If tool not found or parameter validation fails
        """
        import inspect
        from typing import get_type_hints
        
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not found")
        
        tool_func = self.tools[tool_name]
        
        # Add serial number if needed and not provided
        sig = inspect.signature(tool_func)
        if 'serial' in sig.parameters and 'serial' not in kwargs:
            kwargs['serial'] = self.device_serial
            
        try:
            # Execute the tool and capture the result
            result = await tool_func(**kwargs)
            
            # Special handling for formatted results
            if tool_name == "list_packages" and isinstance(result, dict):
                # Format package list for better readability
                message = result.get("message", "")
                packages = result.get("packages", [])
                package_list = "\n".join([f"- {pkg.get('package', '')}" for pkg in packages])
                
                return f"{message}\n{package_list}"
            elif tool_name == "get_clickables" and isinstance(result, dict):
                # Format clickable elements for better readability
                message = result.get("message", "")
                clickable = result.get("clickable_elements", [])
                return clickable
                
                summary = message
                if clickable:
                    summary += "\n\nClickable elements:"
                    for elem in clickable:
                        elem_text = elem.get("text", "") or elem.get("content_desc", "") or "no text"
                        elem_class = elem.get("class", "").split(".")[-1]
                        elem_bounds = elem.get("bounds", "")
                        summary += f"\n- {elem_text} ({elem_class}) at {elem_bounds}"
                
                return summary
            elif tool_name == "get_ui_elements" and isinstance(result, dict):
                # Summarize UI elements for better readability
                clickable = result.get("clickable_elements", [])
                text = result.get("text_elements", [])
                summary = f"Found {len(clickable)} clickable elements and {len(text)} text elements on screen."
                
                # Include a limited list of elements (to avoid overwhelming output)
                if clickable:
                    summary += "\n\nClickable elements:"
                    for i, elem in enumerate(clickable[:5]):
                        elem_text = elem.get("text", "") or elem.get("content_desc", "") or "no text"
                        elem_class = elem.get("class", "").split(".")[-1]
                        elem_bounds = elem.get("bounds", "")
                        summary += f"\n- {elem_text} ({elem_class}) at {elem_bounds}"
                    
                    if len(clickable) > 5:
                        summary += f"\n... and {len(clickable) - 5} more clickable elements"
                        
                if text:
                    summary += "\n\nText elements:"
                    for i, elem in enumerate(text[:5]):
                        elem_text = elem.get("text", "") or "no text"
                        elem_class = elem.get("class", "").split(".")[-1]
                        summary += f"\n- {elem_text} ({elem_class})"
                    
                    if len(text) > 5:
                        summary += f"\n... and {len(text) - 5} more text elements"
                
                return summary
            elif tool_name == "take_screenshot":
                # For screenshots, store the image data for the LLM and return the path
                if isinstance(result, tuple) and len(result) >= 2:
                    path, image_data = result
                    # Store the screenshot data for the next LLM call
                    self._last_screenshot = image_data
                    return f"Screenshot captured and available for analysis"
                return str(result)
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return f"Error: {str(e)}"
    
    async def run(self) -> List[ReActStep]:
        """Run the ReAct agent to achieve the goal.
        
        Returns:
            List of steps taken during execution
        """
        if not self.goal:
            raise ValueError("No goal specified")
        
        # Connect to device
        if not await self.connect():
            await self.add_step(
                ReActStepType.OBSERVATION, 
                "Failed to connect to device"
            )
            return self.steps
        
        # Add initial goal step
        await self.add_step(ReActStepType.GOAL, self.goal)
        
        # Continue with ReAct loop
        step_count = 0
        goal_achieved = False
        
        while step_count < self.max_steps and not goal_achieved:
            # Generate next step using LLM reasoning
            if self.use_llm and self.reasoner:
                try:
                    # Convert steps to dictionaries for the LLM
                    history = [step.to_dict() for step in self.steps]
                    
                    # Get available tool names
                    available_tools = list(self.tools.keys())
                    
                    # Get LLM reasoning, passing the last screenshot if available
                    reasoning_result = await self.reasoner.reason(
                        goal=self.goal,
                        history=history,
                        available_tools=available_tools,
                        screenshot_data=self._last_screenshot
                    )
                    
                    # Clear the screenshot after using it
                    self._last_screenshot = None
                    
                    # Extract thought, action, and parameters
                    thought = reasoning_result.get("thought", "")
                    action = reasoning_result.get("action", "")
                    parameters = reasoning_result.get("parameters", {})
                    
                    # Add thought step
                    thought_step = await self.add_step(
                        ReActStepType.THOUGHT, 
                        thought,
                    )
                    
                    # Add action step
                    action_description = f"{action}({', '.join(f'{k}={v}' for k, v in parameters.items())})"
                    action_step = await self.add_step(ReActStepType.ACTION, action_description)
                    
                    # Execute the action if it's a valid tool
                    result = "No action taken"
                    if action in self.tools:
                        try:
                            # Execute the tool
                            result = await self.execute_tool(action, **parameters)
                            
                            # Check if the complete tool was called
                            if action == "complete":
                                goal_achieved = True
                            
                            if isinstance(result, bytes):
                                result = f"Binary data ({len(result)} bytes)"
                            elif isinstance(result, tuple) and len(result) == 2 and isinstance(result[1], bytes):
                                # For screenshot which returns (path, bytes)
                                result = f"Screenshot saved to {result[0]} ({len(result[1])} bytes)"
                        except Exception as e:
                            result = f"Error: {str(e)}"
                    else:
                        result = f"Invalid action: {action}"
                    
                    # Add the observation step with the result
                    await self.add_step(
                        ReActStepType.OBSERVATION,
                        str(result)
                    )
                    
                    # Check if goal is achieved (let the LLM determine this)
                    if "goal achieved" in thought.lower() or "goal complete" in thought.lower():
                        goal_achieved = True
                    
                except Exception as e:
                    logger.error(f"Error in LLM reasoning: {e}")
                    await self.add_step(
                        ReActStepType.OBSERVATION, 
                        f"Error in LLM reasoning: {e}"
                    )
            # Increment step count
            step_count += 1
        
        # Add final step if goal achieved
        if goal_achieved:
            await self.add_step(
                ReActStepType.OBSERVATION, 
                f"Goal achieved in {step_count} steps."
            )
        elif step_count >= self.max_steps:
            await self.add_step(
                ReActStepType.OBSERVATION, 
                f"Maximum steps ({self.max_steps}) reached without achieving goal."
            )
        
        return self.steps

async def run_agent(
    goal: str, 
    device_serial: Optional[str] = None,
    llm_provider: str = "openai",
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    debug: bool = False
) -> List[ReActStep]:
    """Run the ReAct agent with the given goal.
    
    Args:
        goal: The automation goal
        device_serial: Optional device serial number
        llm_provider: LLM provider ('openai', 'anthropic', or 'gemini')
        model_name: Model name to use
        api_key: API key for the LLM provider
        debug: Whether to enable debug logging
        
    Returns:
        List of steps taken by the agent
    """
    # Auto-detect Gemini if model starts with "gemini-"
    if model_name and model_name.startswith("gemini-"):
        llm_provider = "gemini"
        
    agent = ReActAgent(
        device_serial=device_serial, 
        goal=goal,
        llm_provider=llm_provider,
        model_name=model_name,
        api_key=api_key,
        debug=debug
    )
    
    steps = await agent.run()
    
    # Print summary
    print("\n--------- Execution Summary ---------")
    print(f"Goal: {goal}")
    print(f"Steps taken: {len(steps)}")
    
    # Print steps
    for i, step in enumerate(steps):
        print(f"\nStep {i+1}: {str(step)}")
    
    return steps 