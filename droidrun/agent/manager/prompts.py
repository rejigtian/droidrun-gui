"""
Prompts for the ManagerAgent.
"""

import re


def parse_manager_response(response: str) -> dict:
    """
    Parse manager LLM response into structured dict.

    Extracts XML-style tags from the response:
    - <thought>...</thought>
    - <add_memory>...</add_memory>
    - <plan>...</plan>
    - <request_accomplished>...</request_accomplished> (answer)

    Also derives:
    - current_subgoal: first line of plan (with list markers removed)

    Args:
        response: Raw LLM response text

    Returns:
        Dict with keys:
            - thought: str
            - memory: str
            - plan: str
            - current_subgoal: str (first line of plan, cleaned)
            - request_accomplished: str (from request_accomplished tag)
    """
    def extract(tag: str) -> str:
        """Extract content between XML-style tags."""
        if f"<{tag}>" in response and f"</{tag}>" in response:
            return response.split(f"<{tag}>", 1)[-1].split(f"</{tag}>", 1)[0].strip()
        return ""

    thought = extract("thought")
    memory_section = extract("add_memory")
    plan = extract("plan")
    answer = extract("request_accomplished")

    # Parse current subgoal from first line of plan
    current_goal_text = plan
    # Prefer newline-separated plans; take the first non-empty line
    plan_lines = [line.strip() for line in current_goal_text.splitlines() if line.strip()]
    if plan_lines:
        first_line = plan_lines[0]
    else:
        first_line = current_goal_text.strip()

    # Remove common list markers like "1.", "-", "*", or bullet characters
    first_line = re.sub(r"^\s*\d+\.\s*", "", first_line)  # Remove "1. ", "2. ", etc.
    first_line = re.sub(r"^\s*[-*]\s*", "", first_line)    # Remove "- " or "* "
    first_line = re.sub(r"^\s*•\s*", "", first_line)      # Remove bullet "• "

    current_subgoal = first_line.strip()

    return {
        "thought": thought,
        "plan": plan,
        "memory": memory_section,
        "current_subgoal": current_subgoal,
        "answer": answer,
    }
