import os
from typing import List, Dict, Any, Optional

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
        self.tasks = []
        self.task_completed = False 
        self.message = None
        self.start_execution = False
        self.task_history = [] 
        self.persistent_completed_tasks = []
        self.persistent_failed_tasks = []
        self.file_path = os.path.join(os.path.expanduser("~"), "Desktop", "todo.txt")

    # self.tasks is a property, make a getter and setter for it
    def set_tasks(self, tasks: List[str], task_contexts: Optional[List[Dict[str, Any]]] = None, agent_types: Optional[List[str]] = None):
        """
        Clears the current task list and sets new tasks from a list.
        Each task should be a string with an optional assigned specialized agent.

        Args:
            tasks: A list of strings, each representing a task.
            task_contexts: Optional list of context dictionaries for each task.
            agent_types: Optional list of specialized agent types for each task.
        """
        try:
            # Save any completed or failed tasks before clearing the list
            for task in self.tasks:
                if task["status"] == self.STATUS_COMPLETED and task not in self.persistent_completed_tasks:
                    # Store a copy to prevent modifications
                    self.persistent_completed_tasks.append(task.copy())
                elif task["status"] == self.STATUS_FAILED and task not in self.persistent_failed_tasks:
                    # Store a copy to prevent modifications
                    self.persistent_failed_tasks.append(task.copy())
            
            # Now clear the task list and add new tasks
            self.tasks = []
            for i, task in enumerate(tasks):
                if not isinstance(task, str) or not task.strip():
                    raise ValueError("Each task must be a non-empty string.")
                
                # Determine the agent type for this task
                agent_type = "UIExpert"  # Default agent
                if agent_types and i < len(agent_types):
                        agent_type = agent_types[i]
                
                task_dict = {
                    "description": task.strip(), 
                    "status": self.STATUS_PENDING,
                    "agent_type": agent_type
                }
                
                # Add context if provided
                if task_contexts and i < len(task_contexts):
                    task_dict["context"] = task_contexts[i]
                
                self.tasks.append(task_dict)
 
            print(f"Tasks set: {len(self.tasks)} tasks added with specialized agents.")
            self.save_to_file()
        except Exception as e:
            print(f"Error setting tasks: {e}")

    def add_task(self, task_description: str, task_context: Optional[Dict[str, Any]] = None, agent_type: str = "UIExpert"):
        """
        Adds a new task to the list with a 'pending' status and assigned specialized agent.

        Args:
            task_description: The string describing the task.
            task_context: Optional dictionary with context for the task.
            agent_type: The specialized agent type to handle this task. 

        Returns:
            int: The index of the newly added task.

        Raises:
            ValueError: If the task_description is empty or not a string, or if agent_type is invalid.
        """
        if not isinstance(task_description, str) or not task_description.strip():
            raise ValueError("Task description must be a non-empty string.")
            

        task = {
            "description": task_description.strip(),
            "status": self.STATUS_PENDING,
            "agent_type": agent_type
        }
        
        # Add context if provided
        if task_context:
            task["context"] = task_context

        self.tasks.append(task)
        self.save_to_file()
        print(f"Task added: {task_description} (Agent: {agent_type}, Status: {self.STATUS_PENDING})")
        
        return len(self.tasks) - 1 # Return the index of the new task

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

    def get_all_tasks(self):
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
        old_status = task["status"]
        task["status"] = new_status
        
        # Add result information if provided
        if result_info:
            for key, value in result_info.items():
                task[key] = value
        
        # Store task history when status changes
        if old_status != new_status:
            history_entry = {
                "index": index,
                "description": task["description"],
                "old_status": old_status,
                "new_status": new_status,
                "result_info": result_info
            }
            self.task_history.append(history_entry)
            
            # If the task is now completed or failed, add it to our persistent lists
            if new_status == self.STATUS_COMPLETED:
                # Make a copy to ensure it doesn't change if the original task is modified
                task_copy = task.copy()
                if task_copy not in self.persistent_completed_tasks:
                    self.persistent_completed_tasks.append(task_copy)
            elif new_status == self.STATUS_FAILED:
                # Make a copy to ensure it doesn't change if the original task is modified
                task_copy = task.copy()
                if task_copy not in self.persistent_failed_tasks:
                    self.persistent_failed_tasks.append(task_copy)
            
        self.save_to_file()
        # No need to re-assign task to self.tasks[index] as dictionaries are mutable

    def delete_task(self, index: int):
        """
        Deletes a task by its index.

        Args:
            index: The index of the task to delete.

        Raises:
            IndexError: If the index is out of bounds.
        """
        if 0 <= index < len(self.tasks):
            del self.tasks[index]
            self.save_to_file()
        else:
            raise IndexError(f"Task index {index} out of bounds.")

    def clear_tasks(self):
        """Removes all tasks from the list."""
        self.tasks = []
        print("All tasks cleared.")
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
        return [task for task in self.tasks if task["status"] == status]

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

    # --- Utility methods ---
    def __len__(self):
        """Returns the total number of tasks."""
        return len(self.tasks)

    def __str__(self):
        """Provides a user-friendly string representation of the task list."""
        if not self.tasks:
            return "Task List (empty)"

        output = "Task List:\n"
        output += "----------\n"
        for i, task in enumerate(self.tasks):
            agent_type = task.get("agent_type", "UIExpert")
            output += f"{i}: [{task['status'].upper():<10}] [{agent_type}] {task['description']}\n"
        output += "----------"
        return output

    def __repr__(self):
        """Provides a developer-friendly representation."""
        return f"<TaskManager(task_count={len(self.tasks)}, completed={self.get_completed_tasks()}, attempting={self.get_attempting_task()}, pending={self.get_pending_tasks()})>"
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
        self.task_completed = True
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

    def get_all_completed_tasks(self) -> List[Dict]:
        """
        Returns all completed tasks, including those from previous planning cycles.
        
        Returns:
            List of completed task dictionaries
        """
        # Get currently active completed tasks
        current_completed = self.get_completed_tasks()
        
        # Create a combined list, ensuring no duplicates
        all_completed = []
        
        # Add current completed tasks
        for task in current_completed:
            if task not in all_completed:
                all_completed.append(task)
        
        # Add historical completed tasks
        for task in self.persistent_completed_tasks:
            # Check if task is already in the list based on description
            if not any(t["description"] == task["description"] for t in all_completed):
                all_completed.append(task)
        
        return all_completed

    def get_all_failed_tasks(self) -> List[Dict]:
        """
        Returns all failed tasks, including those from previous planning cycles.
        
        Returns:
            List of failed task dictionaries
        """
        # Get currently active failed tasks
        current_failed = self.get_tasks_by_status(self.STATUS_FAILED)
        
        # Create a combined list, ensuring no duplicates
        all_failed = []
        
        # Add current failed tasks
        for task in current_failed:
            if task not in all_failed:
                all_failed.append(task)
        
        # Add historical failed tasks
        for task in self.persistent_failed_tasks:
            # Check if task is already in the list based on description
            if not any(t["description"] == task["description"] for t in all_failed):
                all_failed.append(task)
        
        return all_failed

    def get_tasks_by_agent_type(self, agent_type: str):
        """
        Filters and returns tasks assigned to a specific agent type.

        Args:
            agent_type: The agent type to filter by.

        Returns:
            list[dict]: A list of tasks assigned to the specified agent type.

        Raises:
            ValueError: If the agent_type is not valid.
        """
        return [task for task in self.tasks if task.get("agent_type") == agent_type]

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
                if task["status"] == self.STATUS_COMPLETED and task not in self.persistent_completed_tasks:
                    self.persistent_completed_tasks.append(task.copy())
                elif task["status"] == self.STATUS_FAILED and task not in self.persistent_failed_tasks:
                    self.persistent_failed_tasks.append(task.copy())
            
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
                
                task_dict = {
                    "description": task_description.strip(),
                    "status": self.STATUS_PENDING,
                    "agent_type": agent_type
                }
                
                self.tasks.append(task_dict)
            
            print(f"Tasks set with agents: {len(self.tasks)} tasks added.")
            self.save_to_file()
        except Exception as e:
            print(f"Error setting tasks with agents: {e}")