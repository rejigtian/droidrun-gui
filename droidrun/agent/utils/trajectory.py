"""
Trajectory utilities for DroidRun agents.

This module provides helper functions for working with agent trajectories,
including saving, loading, and analyzing them.
"""

import json
import logging
import os
import time
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
from PIL import Image
import io

logger = logging.getLogger("droidrun")

def create_screenshot_gif(screenshots: List[Dict[str, Any]], output_path: str, duration: int = 1000) -> str:
    """
    Create a GIF from a list of screenshots.
    
    Args:
        screenshots: List of screenshot dictionaries with timestamp and image_data
        output_path: Base path for the GIF (without extension)
        duration: Duration for each frame in milliseconds
    
    Returns:
        Path to the created GIF file
    """
    if not screenshots:
        return None
        
    # Convert screenshots to PIL Images
    images = []
    for screenshot in screenshots:
        img_data = screenshot['image_data']
        img = Image.open(io.BytesIO(img_data))
        images.append(img)
    
    # Save as GIF
    gif_path = f"{output_path}.gif"
    images[0].save(
        gif_path,
        save_all=True,
        append_images=images[1:],
        duration=duration,
        loop=0
    )
    
    return gif_path

def save_trajectory(
    trajectory_steps: List[Dict],
    goal: str,
    result: Dict,
    directory: str = "trajectories",
    screenshots: List[Dict[str, Any]] = None
) -> str:
    """
    Save trajectory steps to a JSON file and create a GIF of screenshots if available.
    
    Args:
        trajectory_steps: List of trajectory step dictionaries
        goal: The original goal/command
        result: The final result dictionary
        directory: Directory to save the trajectory files
        screenshots: List of screenshots with timestamps (optional)
    
    Returns:
        Path to the saved trajectory file
    """
    # Create directory if it doesn't exist
    os.makedirs(directory, exist_ok=True)
    
    # Generate timestamp for filename
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    base_path = os.path.join(directory, f"trajectory_{timestamp}")
    
    # Create trajectory data
    trajectory_data = {
        "goal": goal,
        "success": result.get("success", False),
        "reason": result.get("reason", ""),
        "steps_taken": result.get("steps", 0),
        "trajectory_steps": trajectory_steps
    }
    
    # Save trajectory JSON
    json_path = f"{base_path}.json"
    with open(json_path, "w") as f:
        json.dump(trajectory_data, f, indent=2)
    
    # Create GIF if screenshots are available
    gif_path = None
    if screenshots:
        gif_path = create_screenshot_gif(screenshots, base_path)
        if gif_path:
            # Add GIF path to trajectory data and update JSON
            trajectory_data["screenshot_gif"] = os.path.basename(gif_path)
            with open(json_path, "w") as f:
                json.dump(trajectory_data, f, indent=2)
    
    return json_path

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