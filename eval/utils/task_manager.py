"""
Task management utilities for AndroidWorld benchmarks.
"""

import asyncio
import logging
import random
from typing import Dict, Any, List, Tuple, Optional, Callable

# Import from AndroidWorld
from android_world import registry
from android_world.task_evals import task_eval
from android_world.env import env_launcher

logger = logging.getLogger("android_world_bench")

class TaskRegistry:
    """Manages the registry of AndroidWorld tasks."""
    
    def __init__(self, task_family: str = registry.TaskRegistry.ANDROID_WORLD_FAMILY):
        """Initialize the task registry.
        
        Args:
            task_family: The task family to use
        """
        self.task_family = task_family
        self.registry = registry.TaskRegistry()
        self.task_dict = self.registry.get_registry(family=task_family)
        self.task_id_to_name = {}
        
        # Build task ID to name mapping
        for i, task_name in enumerate(sorted(self.task_dict.keys()), 1):
            self.task_id_to_name[i] = task_name
        
        logger.info(f"Found {len(self.task_id_to_name)} tasks in registry")
    
    def get_task_ids(self) -> Dict[int, str]:
        """Get the mapping of task IDs to task names.
        
        Returns:
            Dict mapping task IDs to task names
        """
        return self.task_id_to_name
    
    def get_task_class(self, task_name: str) -> Optional[type]:
        """Get the task class for a task name.
        
        Args:
            task_name: Name of the task
            
        Returns:
            Task class or None if not found
        """
        return self.task_dict.get(task_name)
    
    def get_task_by_id(self, task_id: int) -> Optional[str]:
        """Get the task name for a task ID.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Task name or None if not found
        """
        return self.task_id_to_name.get(task_id)
    
    def create_task_instance(self, task_name: str, random_seed: int = 42) -> Optional[task_eval.TaskEval]:
        """Create an instance of a task.
        
        Args:
            task_name: Name of the task
            random_seed: Random seed for parameter generation
            
        Returns:
            Task instance or None if task could not be created
        """
        task_class = self.get_task_class(task_name)
        if not task_class:
            logger.warning(f"Task {task_name} not found in registry")
            return None
        
        try:
            # Generate random parameters
            random.seed(random_seed)
            params = task_class.generate_random_params()
            params["seed"] = random_seed
            
            # Create and return task instance
            task_instance = task_class(params)
            logger.info(f"Created task instance for {task_name}")
            return task_instance
        except NotImplementedError:
            logger.warning(f"Task {task_name} does not implement generate_random_params()")
            return None
        except Exception as e:
            logger.exception(f"Error creating instance for task {task_name}: {e}")
            return None
    
    def filter_tasks(self, task_ids: Optional[List[int]] = None, 
                    task_names: Optional[List[str]] = None) -> Dict[str, type]:
        """Filter tasks based on task IDs or names.
        
        Args:
            task_ids: List of task IDs to filter
            task_names: List of task names to filter
            
        Returns:
            Dictionary of filtered tasks
        """
        filtered_tasks = {}
        
        # Filter by task IDs
        if task_ids:
            for task_id in task_ids:
                if task_id in self.task_id_to_name:
                    task_name = self.task_id_to_name[task_id]
                    if task_name in self.task_dict:
                        filtered_tasks[task_name] = self.task_dict[task_name]
                    else:
                        logger.warning(f"Task {task_name} (ID: {task_id}) not found in registry")
                else:
                    logger.warning(f"Task ID {task_id} not found in registry")
        
        # Filter by task names
        if task_names:
            for task_name in task_names:
                if task_name in self.task_dict:
                    filtered_tasks[task_name] = self.task_dict[task_name]
                else:
                    logger.warning(f"Task {task_name} not found in registry")
        
        # If no filters applied, use all tasks
        if not filtered_tasks and not task_ids and not task_names:
            filtered_tasks = self.task_dict
        
        return filtered_tasks
    
    def create_task_suite(self, task_ids: Optional[List[int]] = None,
                          task_names: Optional[List[str]] = None,
                          n_combinations: int = 1,
                          random_seed: int = 42) -> List[Tuple[str, task_eval.TaskEval]]:
        """Create a suite of tasks to benchmark.
        
        Args:
            task_ids: List of task IDs to include
            task_names: List of task names to include
            n_combinations: Number of parameter combinations per task
            random_seed: Random seed for reproducibility
            
        Returns:
            List of (task_name, task_instance) tuples
        """
        # Filter tasks based on IDs or names
        filtered_tasks = self.filter_tasks(task_ids, task_names)
        
        # Create task instances
        task_suite = []
        random.seed(random_seed)
        
        logger.info(f"Creating task suite with {len(filtered_tasks)} tasks...")
        
        for task_name, task_class in filtered_tasks.items():
            for i in range(n_combinations):
                try:
                    # Generate random parameters for the task
                    params = task_class.generate_random_params()
                    # Add a seed for reproducibility
                    params["seed"] = random_seed + i
                    # Create task instance
                    task_instance = task_class(params)
                    task_suite.append((task_name, task_instance))
                    
                    logger.info(f"Created task: {task_name} (instance {i+1}/{n_combinations})")
                except Exception as e:
                    logger.error(f"Error creating task {task_name}: {e}")
                    continue
                
        logger.info(f"Created task suite with {len(task_suite)} task instances")
        return task_suite

async def initialize_task(env, task_instance: task_eval.TaskEval) -> bool:
    """Initialize a task in the environment.
    
    Args:
        env: AndroidWorld environment
        task_instance: Task instance to initialize
        
    Returns:
        True if initialization was successful, False otherwise
    """
    task_name = task_instance.__class__.__name__
    logger.info(f"Initializing task: {task_name}")
    
    # Reset environment for the task
    env.reset(go_home=True)
    
    # Initialize the task
    try:
        # First try to use initialize_task() which is standard in AndroidWorld
        if hasattr(task_instance, 'initialize_task') and callable(getattr(task_instance, 'initialize_task')):
            task_instance.initialize_task(env)
            logger.info(f"Task initialized using initialize_task() method")
            return True
        # Fall back to setup() if it exists
        elif hasattr(task_instance, 'setup') and callable(getattr(task_instance, 'setup')):
            task_instance.setup(env)
            logger.info(f"Task initialized using setup() method")
            return True
        else:
            logger.error(f"Task {task_name} has no initialize_task() or setup() method")
            return False
    except Exception as e:
        logger.error(f"Error initializing task {task_name}: {e}")
        return False

def get_task_description(task_instance: task_eval.TaskEval) -> str:
    """Get the description for a task.
    
    Args:
        task_instance: Task instance
        
    Returns:
        Task description
    """
    task_name = task_instance.__class__.__name__
    
    try:
        # First try to use get_instruction() if available
        if hasattr(task_instance, 'get_instruction') and callable(getattr(task_instance, 'get_instruction')):
            return task_instance.get_instruction()
        # Fall back to goal property which is common in AndroidWorld tasks
        elif hasattr(task_instance, 'goal'):
            return task_instance.goal
        else:
            # If neither is available, use a default message with the task name
            logger.warning(f"Task {task_name} has no get_instruction() method or goal property")
            return f"Complete the '{task_name}' task"
    except Exception as e:
        logger.error(f"Error getting task description for {task_name}: {e}")
        return f"Complete the '{task_name}' task"

def check_task_success(env, task_instance: task_eval.TaskEval) -> bool:
    """Check if a task was completed successfully.
    
    Args:
        env: AndroidWorld environment
        task_instance: Task instance
        
    Returns:
        True if task was successful, False otherwise
    """
    task_name = task_instance.__class__.__name__
    
    try:
        # First try to use check_success() if available
        if hasattr(task_instance, 'check_success') and callable(getattr(task_instance, 'check_success')):
            return task_instance.check_success(env)
        # Fall back to is_successful() which is common in some AndroidWorld tasks
        elif hasattr(task_instance, 'is_successful') and callable(getattr(task_instance, 'is_successful')):
            return task_instance.is_successful(env)
        else:
            # If neither is available, mark as failed
            logger.warning(f"Task {task_name} has no check_success() or is_successful() method")
            return False
    except Exception as e:
        logger.error(f"Error checking task success for {task_name}: {e}")
        return False

def teardown_task(env, task_instance: task_eval.TaskEval) -> bool:
    """Tear down a task.
    
    Args:
        env: AndroidWorld environment
        task_instance: Task instance
        
    Returns:
        True if teardown was successful, False otherwise
    """
    task_name = task_instance.__class__.__name__
    
    try:
        if hasattr(task_instance, 'tear_down') and callable(getattr(task_instance, 'tear_down')):
            task_instance.tear_down(env)
            logger.info(f"Task {task_name} torn down using tear_down() method")
            return True
        elif hasattr(task_instance, 'teardown') and callable(getattr(task_instance, 'teardown')):
            task_instance.teardown(env)
            logger.info(f"Task {task_name} torn down using teardown() method")
            return True
        else:
            logger.warning(f"Task {task_name} has no tear_down() or teardown() method")
            return False
    except Exception as e:
        logger.error(f"Error during task teardown for {task_name}: {e}")
        return False 