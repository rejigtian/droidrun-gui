"""
Prompts for the ManagerAgent.
"""

import re


def build_manager_system_prompt(
    instruction: str,
    has_text_to_modify: bool = False,
    app_card: str = "",
    device_date: str = "",
    important_notes: str = "",
    error_flag: bool = False,
    error_history: list = [],  # noqa: B006
    custom_tools_descriptions: str = ""
) -> str:
    """
    Build the manager system prompt with all context.

    Args:
        instruction: User's goal/task
        has_text_to_modify: Whether focused text field has editable content
        app_card: App-specific instructions (TODO: implement app card system)
        device_date: Current device date (TODO: implement via adb shell date)
        important_notes: Additional important information
        error_flag: Whether consecutive errors occurred
        error_history: List of recent errors if error_flag=True
        custom_tools_descriptions: Formatted descriptions of custom tools available to executor

    Returns:
        Complete system prompt for Manager
    """
    prompt = (
        "You are an agent who can operate an Android phone on behalf of a user. "
        "Your goal is to track progress and devise high-level plans to achieve the user's requests.\n\n"
        "<user_request>\n"
        f"{instruction}\n"
        "</user_request>\n\n"
    )


    if device_date.strip():
        prompt += f"<device_date>\n{device_date}\n</device_date>\n\n"




    if app_card.strip():
        prompt += "App card gives information on how to operate the app and perform actions.\n"
        prompt += f"<app_card>\n{app_card.strip()}\n</app_card>\n\n"

    # Important notes
    if important_notes:
        prompt += "<important_notes>\n"
        prompt += f"{important_notes}\n"
        prompt += "</important_notes>\n\n"

    # Error escalation
    if error_flag and error_history:
        prompt += (
            "<potentially_stuck>\n"
            "You have encountered several failed attempts. Here are some logs:\n"
        )
        for error in error_history:
            prompt += (
                f"- Attempt: Action: {error['action']} | "
                f"Description: {error['summary']} | "
                f"Outcome: Failed | "
                f"Feedback: {error['error']}\n"
            )
        prompt += "</potentially_stuck>\n\n"

    # Guidelines
    prompt += """<guidelines>
The following guidelines will help you plan this request.
General:
1. Use the `open_app` action whenever you want to open an app, do not use the app drawer to open an app.
2. Use search to quickly find a file or entry with a specific name, if search function is applicable.
3. Only use copy to clipboard actions when the task specifically requires copying text to clipboard. Do not copy text just to use it later - use the Memory section instead.
4. When you need to remember information for later use, store it in the Memory section (using <add_memory> tags) with step context (e.g., "At step X, I obtained [information] from [source]").
5. File names in the user request must always match the exact file name you are working with, make that reflect in the plan too.
6. Make sure names and titles are not cutoff. If the request is to check who sent a message, make sure to check the message sender's full name not just what appears in the notification because it might be cut off.
7. Dates and file names must match the user query exactly.
8. Don't do more than what the user asks for."""

    # Text manipulation guidelines (conditional)
    if has_text_to_modify:
        prompt += """

<text_manipulation>
1. Use **TEXT_TASK:** prefix in your plan when you need to modify text in the currently focused text input field
2. TEXT_TASK is for editing, formatting, or transforming existing text content in text boxes using Python code
3. Do not use TEXT_TASK for extracting text from messages, typing new text, or composing messages
4. The focused text field contains editable text that you can modify
5. Example plan item: 'TEXT_TASK: Add "Hello World" at the beginning of the text'
6. Always use TEXT_TASK for modifying text, do not try to select the text to copy/cut/paste or adjust the text
</text_manipulation>"""

    prompt += """

Memory Usage:
- Always include step context: "At step [number], I obtained [actual content] from [source]"
- Store the actual content you observe, not just references (e.g., store full recipe text, not "found recipes")
- Use memory instead of copying text unless specifically requested
- Memory is append-only: whatever you put in <add_memory> tags gets added to existing memory, not replaced
- Update memory to track progress on multi-step tasks

</guidelines>"""

    # Add custom tools section if custom tools are provided
    if custom_tools_descriptions.strip():
        prompt += """

<custom_actions>
The executor has access to these additional custom actions beyond the standard actions (click, type, swipe, etc.):
""" + custom_tools_descriptions + """

You can reference these custom actions or tell the Executer agent to use them in your plan when they help achieve the user's goal.
</custom_actions>"""

    prompt += """
---
Carefully assess the current status and the provided screenshot. Check if the current plan needs to be revised.
Determine if the user request has been fully completed. If you are confident that no further actions are required, use the request_accomplished tag with a message in it. If the user request is not finished, update the plan and don't use it. If you are stuck with errors, think step by step about whether the overall plan needs to be revised to address the error.
NOTE: 1. If the current situation prevents proceeding with the original plan or requires clarification from the user, make reasonable assumptions and revise the plan accordingly. Act as though you are the user in such cases. 2. Please refer to the helpful information and steps in the Guidelines first for planning. 3. If the first subgoal in plan has been completed, please update the plan in time according to the screenshot and progress to ensure that the next subgoal is always the first item in the plan. 4. If the first subgoal is not completed, please copy the previous round's plan or update the plan based on the completion of the subgoal.
Provide your output in the following format, which contains four or five parts:

<thought>
An explanation of your rationale for the updated plan and current subgoal.
</thought>

<add_memory>
Store important information here with step context for later reference. Always include "At step X, I obtained [actual content] from [source]".
Examples:
- At step 5, I obtained recipe details from recipes.jpg: Recipe 1 "Chicken Pasta" - ingredients: chicken, pasta, cream. Instructions: Cook pasta, sauté chicken, add cream.
or
- At step 12, I successfully added Recipe 1 to Broccoli app. Still need to add Recipe 2 and Recipe 3 from memory.
Store important information here with step context for later reference.
</add_memory>

<plan>
Please update or copy the existing plan according to the current page and progress. Please pay close attention to the historical operations. Please do not repeat the plan of completed content unless you can judge from the screen status that a subgoal is indeed not completed.
</plan>

<request_accomplished>
Use this tag ONLY after actually completing the user's request through concrete actions, not at the beginning or for planning.

1. Always include a message inside this tag confirming what you accomplished
2. Ensure both opening and closing tags are present
3. Use exclusively for signaling completed user requests
</request_accomplished>"""

    return prompt


def parse_manager_response(response: str) -> dict:
    """
    Parse manager LLM response into structured dict.

    Extracts XML-style tags from the response:
    - <thought>...</thought>
    - <add_memory>...</add_memory>
    - <plan>...</plan>
    - <request_accomplished>...</request_accomplished> (answer)
    - <historical_operations>...</historical_operations> (optional, for completed plan)

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
            - completed_subgoal: str
            - answer: str (from request_accomplished tag)
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

    # Extract completed subgoal (optional historical_operations tag)
    if "<historical_operations>" in response:
        completed_subgoal = extract("historical_operations")
    else:
        completed_subgoal = "No completed subgoal."

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
        "completed_subgoal": completed_subgoal,
        "plan": plan,
        "memory": memory_section,
        "current_subgoal": current_subgoal,
        "answer": answer,
    }
