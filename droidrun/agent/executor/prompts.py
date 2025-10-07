"""
Prompts for the ExecutorAgent.
"""

# TODO: Port and adapt prompts from mobile_agent_v3.py Executor class
# Reference: android_world/agents/mobile_agent_v3_agent.py Executor.get_prompt()

DEFAULT_EXECUTOR_SYSTEM_PROMPT = """
TODO: Implement Executor system prompt

The Executor is responsible for:
- Taking a specific subgoal from the Manager
- Analyzing the current UI state
- Selecting the appropriate action to take
- Executing actions on the device

Available actions:
- open_app: Open an application
- click: Click on a UI element by index
- long_press: Long press on a UI element
- type: Enter text (with optional element index to click first)
- swipe: Swipe in a direction
- system_button: Press Enter/Back/Home
- copy: Copy text
- paste: Paste into a field
- answer: Provide an answer (for information retrieval tasks)
- done: Mark task as complete

Output format should include:
- <thought>: reasoning about the current state and what action to take
- <action>: JSON formatted action
- <description>: human-readable description of the action
"""


DEFAULT_EXECUTOR_USER_PROMPT = """
TODO: Implement Executor user prompt template

Should include:
- Current subgoal: {subgoal}
- Device state and UI elements
- Action history
- Additional knowledge/tips
"""


DETAILED_TIPS = (
    'General:\n'
    '- For any pop-up window, such as a permission request, you need to close it (e.g., by clicking `Don\'t Allow` or `Accept & continue`) before proceeding. Never choose to add any account or log in.\n'
    'Action Related:\n'
    '- Use the `open_app` action whenever you want to open an app'
    ' (nothing will happen if the app is not installed), do not use the'
    ' app drawer to open an app.\n'
    '- Consider exploring the screen by using the `swipe`'
    ' action with different directions to reveal additional content. Or use search to quickly find a specific entry, if applicable.\n'
    '- If you cannot change the page content by swiping in the same direction continuously, the page may have been swiped to the bottom. Please try another operation to display more content.\n'
    '- For some horizontally distributed tags, you can swipe horizontally to view more.\n'
    'Text Related Operations:\n'
    '- Activated input box: If an input box is activated, it may have a cursor inside it and the keyboard is visible. If there is no cursor on the screen but the keyboard is visible, it may be because the cursor is blinking. The color of the activated input box will be highlighted. If you are not sure whether the input box is activated, click it before typing.\n'
    '- To input some text: first click the input box that you want to input, make sure the correct input box is activated and the keyboard is visible, then use `type` action to enter the specified text.\n'
    '- To clear the text: long press the backspace button in the keyboard.\n'
    '- To copy some text: first long press the text you want to copy, then click the `copy` button in bar.\n'
    '- To paste text into a text box: first long press the'
    ' text box, then click the `paste`'
    ' button in bar.'
)


def build_executor_prompt(
    subgoal: str,
    device_state: str,
    action_history: list,
    additional_knowledge: str = "",
) -> str:
    """
    Build the executor prompt with current context.

    TODO: Implement prompt building logic from mobile_agent_v3.py
    """
    return DEFAULT_EXECUTOR_USER_PROMPT.format(
        subgoal=subgoal,
        # Add more context as needed
    )
