"""
Event handler for DroidRun CLI - handles streaming events from agents and converts them to user-friendly logs.
"""

from typing import List, Callable
from droidrun.agent.common.events import ScreenshotEvent
from droidrun.agent.planner.events import PlanInputEvent, PlanThinkingEvent, PlanCreatedEvent
from droidrun.agent.codeact.events import TaskInputEvent, TaskThinkingEvent, TaskExecutionEvent, TaskExecutionResultEvent, TaskEndEvent
from droidrun.agent.droid.events import CodeActExecuteEvent, CodeActResultEvent, ReasoningLogicEvent, TaskRunnerEvent, FinalizeEvent


class EventHandler:
    """Handles streaming events from DroidRun agents and converts them to user-friendly logs."""
    
    def __init__(self, logs: List[str]):
        """
        Initialize the event handler.
        
        Args:
            logs: List to append log messages to
            update_display_callback: Callback function to update the display
        """
        self.logs = logs
        self.current_step = "Initializing..."
        self.is_completed = False
        self.is_success = None
    
    def handle_event(self, event):
        """Handle streaming events from the agent workflow."""
        
        # Log different event types with proper names
        if isinstance(event, ScreenshotEvent):
            self.logs.append("📸 Taking screenshot...")
        
        # Planner events
        elif isinstance(event, PlanInputEvent):
            self.logs.append("💭 Planner receiving input...")
            self.current_step = "Planning..."
        
        elif isinstance(event, PlanThinkingEvent):
            if event.thoughts:
                thoughts_preview = event.thoughts[:150] + "..." if len(event.thoughts) > 150 else event.thoughts
                self.logs.append(f"🧠 Planning: {thoughts_preview}")
            if event.code:
                self.logs.append(f"📝 Generated plan code")
        
        elif isinstance(event, PlanCreatedEvent):
            if event.tasks:
                task_count = len(event.tasks) if event.tasks else 0
                self.logs.append(f"📋 Plan created with {task_count} tasks")
                for task in event.tasks:
                    self.logs.append(f"- {task["description"]}")
                self.current_step = f"Plan ready ({task_count} tasks)"
        
        # CodeAct events  
        elif isinstance(event, TaskInputEvent):
            self.logs.append("💬 Task input received...")
            self.current_step = "Processing task input..."
        
        elif isinstance(event, TaskThinkingEvent):
            if hasattr(event, 'thoughts') and event.thoughts:
                thoughts_preview = event.thoughts[:150] + "..." if len(event.thoughts) > 150 else event.thoughts
                self.logs.append(f"🧠 Thinking: {thoughts_preview}")
            if hasattr(event, 'code') and event.code:
                self.logs.append(f"💻 Executing action code")
        
        elif isinstance(event, TaskExecutionEvent):
            self.logs.append(f"⚡ Executing action...")
            self.current_step = "Executing action..."
        
        elif isinstance(event, TaskExecutionResultEvent):
            if hasattr(event, 'output') and event.output:
                output = str(event.output)
                if "Error" in output or "Exception" in output:
                    output_preview = output[:100] + "..." if len(output) > 100 else output
                    self.logs.append(f"❌ Action error: {output_preview}")
                else:
                    output_preview = output[:100] + "..." if len(output) > 100 else output
                    self.logs.append(f"⚡ Action result: {output_preview}")
        
        elif isinstance(event, TaskEndEvent):
            if hasattr(event, 'success') and hasattr(event, 'reason'):
                if event.success:
                    self.logs.append(f"✅ Task completed: {event.reason}")
                    self.current_step = f"Task completed successfully"
                else:
                    self.logs.append(f"❌ Task failed: {event.reason}")
                    self.current_step = f"Task failed"
        
        # Droid coordination events
        elif isinstance(event, CodeActExecuteEvent):
            self.logs.append(f"🔧 Starting task execution...")
            self.current_step = "Executing task..."
        
        elif isinstance(event, CodeActResultEvent):
            if hasattr(event, 'success') and hasattr(event, 'reason'):
                if event.success:
                    self.logs.append(f"✅ Task completed: {event.reason}")
                    self.current_step = f"Task completed successfully"
                else:
                    self.logs.append(f"❌ Task failed: {event.reason}")
                    self.current_step = f"Task failed"
        
        elif isinstance(event, ReasoningLogicEvent):
            self.logs.append(f"🤔 Planning next steps...")
            self.current_step = "Planning..."
        
        elif isinstance(event, TaskRunnerEvent):
            self.logs.append(f"🏃 Processing task queue...")
            self.current_step = "Processing tasks..."
        
        elif isinstance(event, FinalizeEvent):
            if hasattr(event, 'success') and hasattr(event, 'reason'):
                self.is_completed = True
                self.is_success = event.success
                if event.success:
                    self.logs.append(f"🎉 Goal achieved: {event.reason}")
                    self.current_step = f"Success: {event.reason}"
                else:
                    self.logs.append(f"❌ Goal failed: {event.reason}")
                    self.current_step = f"Failed: {event.reason}"
        
        else:
            self.logs.append(f"🔄 {event.__class__.__name__}")
        
        if len(self.logs) > 100:
            self.logs.pop(0)