#!/usr/bin/env python3
"""
DroidRun - Gemini Example

This script demonstrates how to use DroidRun with Google's Gemini AI.
Make sure to set up your GEMINI_API_KEY in the environment before running.

Usage:
1. Create a .env file with your Gemini API key:
   GEMINI_API_KEY=your_api_key_here

2. Run the script:
   python run_with_gemini.py "Open the calculator app"
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
from droidrun.agent.react_agent import ReActAgent, run_agent
from droidrun.agent.llm_reasoning import LLMReasoner

# Load environment variables from .env file
load_dotenv()

# Check for Gemini API key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY not found in environment")
    print("Please create a .env file with GEMINI_API_KEY=your_api_key_here")
    sys.exit(1)

async def run_with_gemini(task: str, debug: bool = False):
    """
    Run DroidRun with Gemini AI.
    
    Args:
        task: The task to perform
        debug: Whether to enable debug mode
    """
    print(f"Running task with Gemini: {task}")
    
    # Create an LLMReasoner with Gemini
    llm = LLMReasoner(
        llm_provider="gemini",  # This must be explicitly "gemini"
        model_name="gemini-2.0-flash",  # or another Gemini model
        api_key=GEMINI_API_KEY,
        temperature=0.2,
        max_tokens=2000
    )
    
    # Create and run the agent
    print("Initializing ReAct agent...")
    agent = ReActAgent(
        task=task,
        llm=llm,  # Pass the Gemini LLM instance
        debug=debug
    )
    
    print("Running agent...")
    steps = await agent.run()
    
    print(f"\nExecution completed with {len(steps)} steps")
    return steps

if __name__ == "__main__":
    # Get task from command line argument or use default
    task = sys.argv[1] if len(sys.argv) > 1 else "Open the settings app and check the Android version"
    
    # Run with Gemini
    asyncio.run(run_with_gemini(task, debug=True)) 