from llama_index.core.workflow import Workflow, Context, StartEvent, StopEvent, step
from llama_index.core.llms.llm import LLM
from llama_index.core.base.llms.types import ChatMessage
from droidrun.tools import Tools
from droidrun.agent.utils import chat_utils
import json
import re
from typing import Optional

class OpenApp(Workflow):
    def __init__(
            self,
            llm: LLM,
            tools: 'Tools',
            *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.tools = tools
        self.llm = llm

    @step
    async def open_app(self, context: Context, ev: StartEvent) -> StopEvent:
        """Main step that handles app opening requests."""
        
        # Get user query from the start event
        user_query = ev.get("query", "")
        if not user_query:
            return StopEvent(result={
                "success": False, 
                "message": "No app query provided"
            })
        
        # Get list of all installed packages
        packages = await self.tools.list_packages(True)
        
        # Create package list string for the LLM
        packages_str = "\n".join([f"- {pkg}" for pkg in packages])
        
        # Create system message
        system_msg = ChatMessage(role="system", content=f"""
You are an Android app opener assistant. Your only task is to open applications on an Android device.
You have access to a tool for opening apps and you have been provided with a list of all packages currently installed on the Android device.

Available packages on the device:
{packages_str}

When given a request to open an app:
1. Look through the available packages to find the most appropriate match
2. Identify the correct package name that matches the user's request
3. Respond with ONLY the exact package name, nothing else
4. If the exact app isn't found, suggest the closest alternative from the available packages
5. If no reasonable match is found, respond with "NO_MATCH_FOUND"

You should only respond with the package name - no explanations, no formatting, just the package name.""")
        
        # Create user message
        user_msg = ChatMessage(role="user", content=f"Open: {user_query}")
        
        # Get LLM response
        try:
            response = await self.llm.achat(messages=[system_msg, user_msg])
            package_name = response.message.content.strip()
            
            # Check if no match was found
            if package_name == "NO_MATCH_FOUND":
                return StopEvent(result={
                    "success": False,
                    "message": f"No matching app found for '{user_query}'"
                })
            
            # Validate that the suggested package exists
            if package_name not in packages:
                return StopEvent(result={
                    "success": False,
                    "message": f"Invalid package suggestion: {package_name}"
                })
            
            # Try to open the app
            result = await self.tools.start_app(package_name)
            
            return StopEvent(result={
                "success": True,
                "message": f"Successfully opened {package_name}",
                "package": package_name,
                "tool_result": result
            })
            
        except Exception as e:
            return StopEvent(result={
                "success": False,
                "message": f"Error opening app: {str(e)}"
            })