from llama_index.core.llms.llm import LLM
from droidrun.agent.context import EpisodicMemory
from droidrun.agent.context.reflection import Reflection
from llama_index.core.base.llms.types import ChatMessage, ImageBlock
from droidrun.agent.utils.chat_utils import add_screenshot_image_block
from droidrun.agent.context.agent_persona import AgentPersona
import json
from typing import Dict, Any, List, Optional
import logging
from PIL import Image, ImageDraw, ImageFont
import io

logger = logging.getLogger("droidrun")

class Reflector:
    def __init__(
        self,
        llm: LLM,
        debug: bool = False,
        *args,
        **kwargs
    ):
        self.llm = llm
        self.debug = debug

    async def reflect_on_episodic_memory(self, episodic_memory: EpisodicMemory, goal: str) -> Reflection:
        """Analyze episodic memory and provide reflection on the agent's performance."""
        system_prompt_content = self._create_system_prompt()
        system_prompt = ChatMessage(role="system", content=system_prompt_content)

        episodic_memory_content = self._format_episodic_memory(episodic_memory)
        persona_content = self._format_persona(episodic_memory.persona)
        
        # Create user message content with persona information
        user_content = f"{persona_content}\n\nGoal: {goal}\n\nEpisodic Memory Steps:\n{episodic_memory_content}\n\nPlease evaluate if the goal was achieved and provide your analysis in the specified JSON format."
        
        # Create user message
        user_message = ChatMessage(role="user", content=user_content)
        
        # Create the screenshots grid and add as ImageBlock if screenshots exist
        screenshots_grid = self._create_screenshots_grid(episodic_memory)
        
        if screenshots_grid:
            # Use the add_screenshot_image_block function to properly add the image
            messages_list = [system_prompt, user_message]
            messages_list = await add_screenshot_image_block(screenshots_grid, messages_list, copy=False)
            messages = messages_list
        else:
            messages = [system_prompt, user_message]
        response = await self.llm.achat(messages=messages)

        logger.info(f"REFLECTION {response.message.content}")
        
        try:
            # Clean the response content to handle markdown code blocks
            content = response.message.content.strip()
            
            # Remove markdown code block formatting if present
            if content.startswith('```json'):
                content = content[7:]  # Remove ```json
            elif content.startswith('```'):
                content = content[3:]   # Remove ```
            
            if content.endswith('```'):
                content = content[:-3]  # Remove trailing ```
            
            content = content.strip()
            
            parsed_response = json.loads(content)
            return Reflection.from_dict(parsed_response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse reflection response: {e}")
            logger.error(f"Raw response: {response.message.content}")
            return await self.reflect_on_episodic_memory(episodic_memory=episodic_memory, goal=goal)
    
    def _create_screenshots_grid(self, episodic_memory: EpisodicMemory) -> Optional[bytes]:
        """Create a 3x2 grid of screenshots from episodic memory steps."""
        # Extract screenshots from steps
        screenshots = []
        for step in episodic_memory.steps:
            if step.screenshot:
                try:
                    # Convert bytes to PIL Image
                    screenshot_image = Image.open(io.BytesIO(step.screenshot))
                    screenshots.append(screenshot_image)
                except Exception as e:
                    logger.warning(f"Failed to load screenshot: {e}")
                    continue
        
        if not screenshots:
            return None
        
        num_screenshots = min(len(screenshots), 6)
        cols, rows = num_screenshots, 1
        
        screenshots = screenshots[:num_screenshots]
        
        if not screenshots:
            return None
        
        if screenshots:
            cell_width = screenshots[0].width // 2
            cell_height = screenshots[0].height // 2
        else:
            return None
        
        # Define header bar height
        header_height = 60
        
        # Create the grid image with space for header bars
        grid_width = cols * cell_width
        grid_height = rows * (cell_height + header_height)
        grid_image = Image.new('RGB', (grid_width, grid_height), color='white')
        
        # Set up font for step text
        draw = ImageDraw.Draw(grid_image)
        try:
            # Use larger font for header text
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        except:
            font = ImageFont.load_default()
        
        # Place screenshots in the grid with header bars
        for i, screenshot in enumerate(screenshots):
            row = i // cols
            col = i % cols
            
            # Calculate positions
            x = col * cell_width
            header_y = row * (cell_height + header_height)
            screenshot_y = header_y + header_height
            
            # Create header bar
            header_rect = [x, header_y, x + cell_width, header_y + header_height]
            draw.rectangle(header_rect, fill='#2c3e50')  # Dark blue header
            
            # Draw step text in header bar
            text = f"Step {i+1}"
            # Get text dimensions for centering
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Center text in header bar
            text_x = x + (cell_width - text_width) // 2
            text_y = header_y + (header_height - text_height) // 2
            
            draw.text((text_x, text_y), text, fill='white', font=font)
            
            # Resize and place screenshot below header
            resized_screenshot = screenshot.resize((cell_width, cell_height), Image.Resampling.LANCZOS)
            grid_image.paste(resized_screenshot, (x, screenshot_y))
        
        # Save grid to disk for debugging (only if debug flag is enabled)
        if self.debug:
            import os
            from datetime import datetime
            
            # Create debug directory if it doesn't exist
            debug_dir = "reflection_screenshots"
            os.makedirs(debug_dir, exist_ok=True)
            
            # Save with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_filename = os.path.join(debug_dir, f"screenshot_grid_{timestamp}.png")
            grid_image.save(debug_filename)
            logger.info(f"Screenshot grid saved to: {debug_filename}")
        
        # Convert to bytes for use with add_screenshot_image_block
        buffer = io.BytesIO()
        grid_image.save(buffer, format='PNG')
        buffer.seek(0)
        
        return buffer.getvalue()

    def _create_system_prompt(self) -> str:
        """Create a system prompt with reflection instructions."""
        system_prompt = """You are a Reflector AI that analyzes the performance of an Android Agent. Your role is to examine episodic memory steps and evaluate whether the agent achieved its goal.

        EVALUATION PROCESS:
        1. First, determine if the agent achieved the stated goal based on the episodic memory steps
        2. If the goal was achieved, acknowledge the success
        3. If the goal was NOT achieved, analyze what went wrong and provide direct advice
        4. Use the provided screenshots (if any) to understand the visual context of each step
        The screenshots show a screen the agent saw. It is in chronological order from left to right

        ANALYSIS AREAS (for failed goals):
        - Missed opportunities or inefficient actions
        - Incorrect tool usage or navigation choices
        - Failure to understand context or user intent
        - Suboptimal decision-making patterns

        ADVICE GUIDELINES (for failed goals):
        - Address the agent directly using "you" form with present/future focus (e.g., "You need to...", "Look for...", "Focus on...")
        - Provide situational awareness advice that helps with the current state after the failed attempt
        - Give actionable guidance for what to do NOW when retrying the goal, not what went wrong before
        - Consider the current app state and context the agent will face when retrying
        - Focus on the key strategy or approach needed for success in the current situation
        - Keep it concise but precise (1-2 sentences)

        OUTPUT FORMAT:
        You MUST respond with a valid JSON object in this exact format:

        {{
            "goal_achieved": true,
            "advice": null,
            "summary": "Brief summary of what happened"
        }}

        OR

        {{
            "goal_achieved": false,
            "advice": "Direct advice using 'you' form focused on current situation - what you need to do NOW when retrying",
            "summary": "Brief summary of what happened"
        }}

        IMPORTANT: 
        - If goal_achieved is true, set advice to null
        - If goal_achieved is false, provide direct "you" form advice focused on what to do NOW in the current situation when retrying
        - Advice should be forward-looking and situational, not retrospective about past mistakes
        - Always include a brief summary of the agent's performance
        - Ensure the JSON is valid and parsable
        - ONLY return the JSON object, no additional text or formatting"""

        return system_prompt
    
    def _format_persona(self, persona: AgentPersona) -> str:
        """Format the agent persona information for the user prompt."""
        persona_content = f"""ACTOR AGENT PERSONA:
        - Name: {persona.name}
        - Description: {persona.description}
        - Available Tools: {', '.join(persona.allowed_tools)}
        - Expertise Areas: {', '.join(persona.expertise_areas)}
        - System Prompt: {persona.system_prompt}"""
                
        return persona_content
    
    def _format_episodic_memory(self, episodic_memory: EpisodicMemory) -> str:
        """Format the episodic memory steps into a readable format for analysis."""
        formatted_steps = []
        
        for i, step in enumerate(episodic_memory.steps, 1):
            try:
                # Parse the JSON strings to get the original content without escape characters
                chat_history = json.loads(step.chat_history)
                response = json.loads(step.response)
                
                
                formatted_step = f"""Step {i}:
            Chat History: {json.dumps(chat_history, indent=2)}
            Response: {json.dumps(response, indent=2)}
            Timestamp: {step.timestamp}
            ---"""
            except json.JSONDecodeError as e:
                # Fallback to original format if JSON parsing fails
                logger.warning(f"Failed to parse JSON for step {i}: {e}")
                formatted_step = f"""Step {i}:
            Chat History: {step.chat_history}
            Response: {step.response}
            Timestamp: {step.timestamp}
            ---"""
            formatted_steps.append(formatted_step)
        
        return "\n".join(formatted_steps)