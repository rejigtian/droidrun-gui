from llama_index.core.llms.llm import LLM
from droidrun.agent.context import EpisodicMemory
from droidrun.agent.context.reflection import Reflection
from llama_index.core.base.llms.types import ChatMessage
import json
from typing import Dict, Any
import logging
logger = logging.getLogger("droidrun")

class Reflector:
    def __init__(
        self,
        llm: LLM,
        *args,
        **kwargs
    ):
        self.llm = llm

    async def reflect_on_episodic_memory(self, episodic_memory: EpisodicMemory, goal: str) -> Reflection:
        """Analyze episodic memory and provide reflection on the agent's performance."""
        system_prompt_content = self._create_system_prompt(episodic_memory, goal)
        system_prompt = ChatMessage(role="system", content=system_prompt_content)

        episodic_memory_content = self._format_episodic_memory(episodic_memory)
        user_message = ChatMessage(
            role="user", 
            content=f"Goal: {goal}\n\nEpisodic Memory Steps:\n{episodic_memory_content}\n\nPlease evaluate if the goal was achieved and provide your analysis in the specified JSON format."
        )

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
    
    def _create_system_prompt(self, episodic_memory: EpisodicMemory, goal: str) -> str:
        """Create a system prompt that includes the actor agent's persona and reflection instructions."""
        persona = episodic_memory.persona
        
        system_prompt = f"""You are a Reflector AI that analyzes the performance of an Android Agent. Your role is to examine episodic memory steps and evaluate whether the agent achieved its goal.

        ACTOR AGENT PERSONA:
        - Name: {persona.name}
        - Description: {persona.description}
        - System Prompt: {persona.system_prompt}
        - Available Tools: {', '.join(persona.allowed_tools)}
        - Expertise Areas: {', '.join(persona.expertise_areas)}

        EVALUATION PROCESS:
        1. First, determine if the agent achieved the stated goal based on the episodic memory steps
        2. If the goal was achieved, acknowledge the success
        3. If the goal was NOT achieved, analyze what went wrong and provide direct advice

        ANALYSIS AREAS (for failed goals):
        - Missed opportunities or inefficient actions
        - Incorrect tool usage or navigation choices
        - Failure to understand context or user intent
        - Suboptimal decision-making patterns

        ADVICE GUIDELINES (for failed goals):
        - Address the agent directly using "you" form (e.g., "You should have...", "Next time, you need to...")
        - Be specific about what they did wrong
        - Provide clear, actionable guidance for what they should do differently next time
        - Focus on the most critical mistake that prevented goal achievement
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
            "advice": "Direct advice using 'you' form - be specific about what they did wrong and what they should do differently",
            "summary": "Brief summary of what happened"
        }}

        IMPORTANT: 
        - If goal_achieved is true, set advice to null
        - If goal_achieved is false, provide direct "you" form advice that specifically identifies the mistake and corrective action
        - Always include a brief summary of the agent's performance
        - Ensure the JSON is valid and parsable
        - ONLY return the JSON object, no additional text or formatting"""

        return system_prompt
    
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