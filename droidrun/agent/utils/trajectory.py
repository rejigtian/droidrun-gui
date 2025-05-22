"""
Trajectory utilities for DroidRun agents.

This module provides helper functions for working with agent trajectories,
including saving, loading, and analyzing them.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("droidrun")

def save_trajectory(trajectory_steps: List[Dict[str, Any]], 
                   goal: str, 
                   result: Dict[str, Any], 
                   directory: Optional[str] = None,
                   filename: Optional[str] = None) -> str:
    """
    Save a trajectory to a JSON file.
    
    Args:
        trajectory_steps: List of trajectory step dictionaries
        goal: The original goal of the run
        result: The result dictionary from the agent.run() method
        directory: Directory to save the trajectory (default: 'trajectories')
        filename: Optional filename (default: auto-generated timestamp name)
        
    Returns:
        Path to the saved trajectory file
    """
    # Create a directory to store trajectories
    if directory:
        trajectory_dir = Path(directory)
    else:
        trajectory_dir = Path("trajectories")
    trajectory_dir.mkdir(exist_ok=True)
    
    # Create a timestamped filename if none provided
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"trajectory_{timestamp}.json"
    
    filepath = trajectory_dir / filename
    
    # Create a dictionary with all the data
    trajectory_data = {
        "goal": goal,
        "success": result.get("success", False),
        "reason": result.get("reason", ""),
        "steps_taken": result.get("steps", 0),
        "trajectory_steps": trajectory_steps
    }
    
    # Save to JSON file
    with open(filepath, "w") as f:
        json.dump(trajectory_data, f, indent=2)
    
    logger.info(f"Trajectory saved to {filepath}")
    return str(filepath)

def load_trajectory(filepath: str) -> Dict[str, Any]:
    """
    Load a trajectory from a JSON file.
    
    Args:
        filepath: Path to the trajectory file
        
    Returns:
        Dictionary containing the trajectory data
    """
    with open(filepath, "r") as f:
        data = json.load(f)
    return data

def get_trajectory_statistics(trajectory_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get statistics about a trajectory.
    
    Args:
        trajectory_data: The trajectory data dictionary
        
    Returns:
        Dictionary with statistics about the trajectory
    """
    trajectory_steps = trajectory_data.get("trajectory_steps", [])
    
    # Count different types of steps
    step_types = {}
    for step in trajectory_steps:
        step_type = step.get("type", "unknown")
        step_types[step_type] = step_types.get(step_type, 0) + 1
    
    # Count planning vs execution steps
    planning_steps = sum(count for step_type, count in step_types.items() 
                        if step_type.startswith("planner_"))
    execution_steps = sum(count for step_type, count in step_types.items() 
                         if step_type.startswith("codeact_"))
    
    # Count successful vs failed executions
    successful_executions = sum(1 for step in trajectory_steps 
                              if step.get("type") == "codeact_execution" 
                              and step.get("success", False))
    failed_executions = sum(1 for step in trajectory_steps 
                          if step.get("type") == "codeact_execution" 
                          and not step.get("success", True))
    
    # Return statistics
    return {
        "total_steps": len(trajectory_steps),
        "step_types": step_types,
        "planning_steps": planning_steps,
        "execution_steps": execution_steps,
        "successful_executions": successful_executions,
        "failed_executions": failed_executions,
        "goal_achieved": trajectory_data.get("success", False)
    }

def print_trajectory_summary(trajectory_data: Dict[str, Any]) -> None:
    """
    Print a summary of a trajectory.
    
    Args:
        trajectory_data: The trajectory data dictionary
    """
    stats = get_trajectory_statistics(trajectory_data)
    
    print("=== Trajectory Summary ===")
    print(f"Goal: {trajectory_data.get('goal', 'Unknown')}")
    print(f"Success: {trajectory_data.get('success', False)}")
    print(f"Reason: {trajectory_data.get('reason', 'Unknown')}")
    print(f"Total steps: {stats['total_steps']}")
    print("Step breakdown:")
    for step_type, count in stats['step_types'].items():
        print(f"  - {step_type}: {count}")
    print(f"Planning steps: {stats['planning_steps']}")
    print(f"Execution steps: {stats['execution_steps']}")
    print(f"Successful executions: {stats['successful_executions']}")
    print(f"Failed executions: {stats['failed_executions']}")
    print("==========================")

def filter_trajectory_steps(trajectory_data: Dict[str, Any], 
                          step_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Filter trajectory steps by type.
    
    Args:
        trajectory_data: The trajectory data dictionary
        step_type: Optional type to filter by (e.g., 'planner_thought', 'codeact_execution')
        
    Returns:
        Filtered list of trajectory steps
    """
    trajectory_steps = trajectory_data.get("trajectory_steps", [])
    
    if step_type:
        return [step for step in trajectory_steps if step.get("type") == step_type]
    return trajectory_steps 