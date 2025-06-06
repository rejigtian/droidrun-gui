import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, replace, asdict
import copy

@dataclass
class Task:
    """
    Represents a single task with its properties.
    """
    description: str
    status: str
    agent_type: str
    

class TaskManager:
    """
    Manages a list of tasks for an agent, each with a status and assigned specialized agent.
    """
    STATUS_PENDING = "pending"      
    STATUS_ATTEMPTING = "attempting"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"

    VALID_STATUSES = {
        STATUS_PENDING,
        STATUS_ATTEMPTING,
        STATUS_COMPLETED,
        STATUS_FAILED
    }
    file_path = os.path.join(os.path.expanduser("~"), "Desktop", "todo.txt")
    def __init__(self):
        """Initializes an empty task list."""
        self.tasks: List[Task] = []
        self.goal_completed = False 
        self.message = None
        self.start_execution = False
        self.task_history = [] 
        self.persistent_completed_tasks = []
        self.persistent_failed_tasks = []
        self.file_path = os.path.join(os.path.expanduser("~"), "Desktop", "todo.txt")


    def get_task(self, index: int):
        """
        Retrieves a specific task by its index.

        Args:
            index: The integer index of the task.

        Returns:
            dict: The task dictionary {'description': str, 'status': str}.

        Raises:
            IndexError: If the index is out of bounds.
        """
        if 0 <= index < len(self.tasks):
            return self.tasks[index]
        else:
            raise IndexError(f"Task index {index} out of bounds.")

    def get_all_tasks(self) -> List[Task]:
        """
        Returns a copy of the entire list of tasks.

        Returns:
            list[dict]: A list containing all task dictionaries.
                      Returns an empty list if no tasks exist.
        """
        return self.tasks

    def update_status(self, index: int, new_status: str, result_info: Optional[Dict[str, Any]] = None):
        """
        Updates the status of a specific task.

        Args:
            index: The index of the task to update.
            new_status: The new status string (must be one of VALID_STATUSES).
            result_info: Optional dictionary with additional information about the task result.

        Raises:
            IndexError: If the index is out of bounds.
            ValueError: If the new_status is not a valid status.
        """
        if new_status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status '{new_status}'. Valid statuses are: {', '.join(self.VALID_STATUSES)}")

        # get_task will raise IndexError if index is invalid
        task = self.get_task(index)
        self.task_history.append(task)

        task.status = new_status
            
        # If the task is now completed or failed, add it to our persistent lists
        if new_status == self.STATUS_COMPLETED:
            # Make a copy to ensure it doesn't change if the original task is modified
            task_copy = copy.deepcopy(task)
            if task_copy not in self.persistent_completed_tasks:
                self.persistent_completed_tasks.append(task_copy)
        elif new_status == self.STATUS_FAILED:
            # Make a copy to ensure it doesn't change if the original task is modified
            task_copy = copy.deepcopy(task)
            if task_copy not in self.persistent_failed_tasks:
                self.persistent_failed_tasks.append(task_copy)
            
        self.save_to_file()

    def get_tasks_by_status(self, status: str):
        """
        Filters and returns tasks matching a specific status.

        Args:
            status: The status string to filter by.

        Returns:
            list[dict]: A list of tasks matching the status.

        Raises:
            ValueError: If the status is not a valid status.
        """
        if status not in self.VALID_STATUSES:
             raise ValueError(f"Invalid status '{status}'. Valid statuses are: {', '.join(self.VALID_STATUSES)}")
        return [task for task in self.tasks if task.status == status]

    # --- Convenience methods for specific statuses ---
    def get_pending_tasks(self) -> list[dict]:
        return self.get_tasks_by_status(self.STATUS_PENDING)

    def get_attempting_task(self) -> dict | None:
        attempting_tasks = self.get_tasks_by_status(self.STATUS_ATTEMPTING)
        if attempting_tasks:
            return attempting_tasks[0]
        else:
            return None

    def get_completed_tasks(self) -> list[dict]:
        return self.get_tasks_by_status(self.STATUS_COMPLETED)

    def get_failed_tasks(self) -> dict | None:
        attempting_tasks = self.get_tasks_by_status(self.STATUS_FAILED)
        if attempting_tasks:
            return attempting_tasks[0]
        else:
            return None

    def save_to_file(self, filename=file_path):
        """Saves the current task list to a Markdown file."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(str(self))
            #print(f"Tasks saved to {filename}.")
        except Exception as e:
            print(f"Error saving tasks to file: {e}")

    def complete_goal(self, message: str):
        """
        Marks the goal as completed, use this whether the task completion was successful or on failure.
        This method should be called when the task is finished, regardless of the outcome.

        Args:
            message: The message to be logged.
        """
        self.goal_completed = True
        self.message = message
        print(f"Goal completed: {message}")

    def start_agent(self):
        """Starts the sub-agent to perform the tasks if there are any tasks to perform.
        Use this function after setting the tasks.
        Args:
        None"""
        if len(self.tasks) == 0:
            print("No tasks to perform.")
            return
        self.start_execution = True

    def get_task_history(self):
        """
        Returns the history of task status changes.
        
        Returns:
            list: A list of dictionaries with historical task information.
        """
        return self.task_history


    def set_tasks_with_agents(self, task_assignments: List[Dict[str, str]]):
        """
        Clears the current task list and sets new tasks with their assigned agents.
        
        Args:
            task_assignments: A list of dictionaries, each containing:
                            - 'task': The task description string
                            - 'agent': The agent type
                            
        Example:
            task_manager.set_tasks_with_agents([
                {'task': 'Open Gmail app', 'agent': 'AppStarterExpert'},
                {'task': 'Navigate to compose email', 'agent': 'UIExpert'}
            ])
        """
        try:
            # Save any completed or failed tasks before clearing the list
            for task in self.tasks:
                if task.status == self.STATUS_COMPLETED and task not in self.persistent_completed_tasks:
                    self.persistent_completed_tasks.append(copy.deepcopy(task))
                elif task.status == self.STATUS_FAILED and task not in self.persistent_failed_tasks:
                    self.persistent_failed_tasks.append(copy.deepcopy(task))
            
            # Clear the task list and add new tasks
            self.tasks = []
            for i, assignment in enumerate(task_assignments):
                if not isinstance(assignment, dict) or 'task' not in assignment:
                    raise ValueError(f"Each task assignment must be a dictionary with 'task' key at index {i}.")
                
                task_description = assignment['task']
                if not isinstance(task_description, str) or not task_description.strip():
                    raise ValueError(f"Task description must be a non-empty string at index {i}.")
                
                # Get agent type, default to UIExpert if not specified or invalid
                agent_type = assignment.get('agent', 'UIExpert')
                
                task_obj = Task(
                    description=task_description.strip(),
                    status=self.STATUS_PENDING,
                    agent_type=agent_type
                )
                
                self.tasks.append(task_obj)
            
            print(f"Tasks set with agents: {len(self.tasks)} tasks added.")
            self.save_to_file()
        except Exception as e:
            print(f"Error setting tasks with agents: {e}")