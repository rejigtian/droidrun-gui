"""MAI-UI External Agent - Exact implementation matching MAI-UI prompts and behavior.

This agent replicates MAI-UI's exact prompts, message building, and trajectory
management while using DroidRun's AdbTools for execution.
"""

import asyncio
import base64
import copy
import json
import logging
import re
from dataclasses import dataclass, field
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image
from jinja2 import Template

from droidrun.agent.utils.chat_utils import to_chat_messages
from droidrun.agent.utils.inference import acall_with_retries
from droidrun.agent.utils.llm_picker import load_llm

logger = logging.getLogger("droidrun")

# =============================================================================
# Constants
# =============================================================================

SCALE_FACTOR = 999

# =============================================================================
# Default Configuration (agent-specific only, NOT LLM)
# =============================================================================

DEFAULT_CONFIG: Dict[str, Any] = {
    # Agent-specific settings matching MAI-UI defaults
    "history_n": 3,  # Number of history steps with images
    # Note: vision is always True for MAI-UI (screenshot-based agent)
}


# =============================================================================
# Trajectory Memory (matches MAI-UI's unified_memory.py)
# =============================================================================


@dataclass
class TrajStep:
    """
    Single step in an agent's trajectory.

    Attributes:
        screenshot_bytes: Screenshot as PNG bytes
        prediction: Raw LLM response text
        action: Parsed action dictionary
        thought: Extracted thinking/reasoning
        step_index: Index of this step
        structured_action: {"action_json": action} for history reconstruction
        ask_user_response: Response from user when ask_user action was used
    """

    screenshot_bytes: bytes
    prediction: str
    action: Dict[str, Any]
    thought: str
    step_index: int
    structured_action: Dict[str, Any]
    ask_user_response: Optional[str] = None


@dataclass
class TrajMemory:
    """
    Container for complete trajectory.

    Attributes:
        task_goal: The instruction/goal for this trajectory
        steps: List of trajectory steps
    """

    task_goal: str
    steps: List[TrajStep] = field(default_factory=list)


# =============================================================================
# System Prompt (exact MAI-UI prompt with MCP template - renders without MCP when no tools passed)
# =============================================================================

# fmt: off
MAI_MOBILE_SYS_PROMPT_TEMPLATE = Template(
    "You are a GUI agent. You are given a task and your action history, with screenshots. You need to perform the next action to complete the task. \n"
    "\n"
    "## Output Format\n"
    "For each function call, return the thinking process in <thinking> </thinking> tags, and a json object with function name and arguments within <tool_call></tool_call> XML tags:\n"
    "```\n"
    "<thinking>\n"
    "...\n"
    "</thinking>\n"
    "<tool_call>\n"
    "{\"name\": \"mobile_use\", \"arguments\": <args-json-object>}\n"
    "</tool_call>\n"
    "```\n"
    "\n"
    "## Action Space\n"
    "\n"
    "{\"action\": \"click\", \"coordinate\": [x, y]}\n"
    "{\"action\": \"long_press\", \"coordinate\": [x, y]}\n"
    "{\"action\": \"type\", \"text\": \"\"}\n"
    "{\"action\": \"swipe\", \"direction\": \"up or down or left or right\", \"coordinate\": [x, y]} # \"coordinate\" is optional. Use the \"coordinate\" if you want to swipe a specific UI element.\n"
    "{\"action\": \"open\", \"text\": \"app_name\"}\n"
    "{\"action\": \"drag\", \"start_coordinate\": [x1, y1], \"end_coordinate\": [x2, y2]}\n"
    "{\"action\": \"system_button\", \"button\": \"button_name\"} # Options: back, home, menu, enter \n"
    "{\"action\": \"wait\"}\n"
    "{\"action\": \"terminate\", \"status\": \"success or fail\"} \n"
    "{\"action\": \"answer\", \"text\": \"xxx\"} # Use escape characters \\', \\\", and \\n in text part to ensure we can parse the text in normal python string format.\n"
    "{\"action\": \"ask_user\", \"text\": \"xxx\"} # you can ask user for more information to complete the task.\n"
    "{\"action\": \"double_click\", \"coordinate\": [x, y]}\n"
    "\n"
    "{% if tools %}"
    "## MCP Tools\n"
    "You are also provided with MCP tools, you can use them to complete the task.\n"
    "{{ tools }}\n"
    "\n"
    "If you want to use MCP tools, you must output as the following format:\n"
    "```\n"
    "<thinking>\n"
    "...\n"
    "</thinking>\n"
    "<tool_call>\n"
    "{\"name\": <function-name>, \"arguments\": <args-json-object>}\n"
    "</tool_call>\n"
    "```\n"
    "{% endif %}"
    "## Note\n"
    "- Available Apps: `{{ apps_list }}`.\n"
    "- Write a small plan and finally summarize your next action (with its target element) in one sentence in <thinking></thinking> part."
)
# fmt: on


# =============================================================================
# Parsing Functions (matches MAI-UI's parsing)
# =============================================================================


def parse_tagged_text(text: str) -> Dict[str, Any]:
    """
    Parse text containing <thinking> and <tool_call> tags.

    Handles both standard format and thinking model format (</think>).

    Args:
        text: Raw model output

    Returns:
        Dictionary with "thinking" and "tool_call" keys
    """
    text = text.strip()

    # Handle thinking model output format (uses </think> instead of </thinking>)
    if "</think>" in text and "</thinking>" not in text:
        text = text.replace("</think>", "</thinking>")
        text = "<thinking>" + text

    result: Dict[str, Any] = {
        "thinking": None,
        "tool_call": None,
    }

    # Extract thinking content
    think_pattern = r"<thinking>(.*?)</thinking>"
    think_match = re.search(think_pattern, text, re.DOTALL)
    if think_match:
        result["thinking"] = think_match.group(1).strip()

    # Extract tool_call content
    call_pattern = r"<tool_call>(.*?)</tool_call>"
    call_match = re.search(call_pattern, text, re.DOTALL)
    if call_match:
        try:
            result["tool_call"] = json.loads(call_match.group(1).strip())
        except json.JSONDecodeError:
            result["tool_call"] = None

    return result


def parse_action(text: str) -> Dict[str, Any]:
    """
    Parse model output into structured action format.

    Normalizes coordinates from SCALE_FACTOR (0-999) to 0-1 range,
    matching MAI-UI's parse_action_to_structure_output behavior.

    Args:
        text: Raw model output

    Returns:
        Dictionary with "thinking" and "action_json" keys

    Raises:
        ValueError: If parsing fails
    """
    parsed = parse_tagged_text(text)

    if not parsed["tool_call"]:
        raise ValueError("No valid tool_call found in response")

    action = parsed["tool_call"].get("arguments", {})

    # Normalize coordinates from SCALE_FACTOR range to [0, 1]
    # This matches MAI-UI's parse_action_to_structure_output behavior
    for coord_key in ["coordinate", "start_coordinate", "end_coordinate"]:
        if coord_key in action:
            coordinates = action[coord_key]
            if len(coordinates) == 2:
                point_x, point_y = coordinates
            elif len(coordinates) == 4:
                # Handle bounding box format (x1, y1, x2, y2) -> center point
                x1, y1, x2, y2 = coordinates
                point_x = (x1 + x2) / 2
                point_y = (y1 + y2) / 2
            else:
                raise ValueError(
                    f"Invalid {coord_key} format: expected 2 or 4 values, got {len(coordinates)}"
                )
            action[coord_key] = [point_x / SCALE_FACTOR, point_y / SCALE_FACTOR]

    return {
        "thinking": parsed["thinking"],
        "action_json": action,
    }


# =============================================================================
# Helper Functions
# =============================================================================


def pil_to_base64(image: Image.Image) -> str:
    """Convert PIL Image to base64 string."""
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def bytes_to_base64(image_bytes: bytes) -> str:
    """Convert image bytes to base64 string."""
    return base64.b64encode(image_bytes).decode("utf-8")


async def resolve_app_name(tools, app_name: str) -> str:
    """
    Resolve friendly app name to package name.

    Args:
        tools: DroidRun Tools instance
        app_name: Friendly app name (e.g., "Settings", "Chrome")

    Returns:
        Package name (e.g., "com.android.settings")
    """
    try:
        apps = await tools.get_apps(include_system=True)

        # Try exact label match (case-insensitive)
        for app in apps:
            if app.get("label", "").lower() == app_name.lower():
                return app["package"]

        # Try partial match
        for app in apps:
            if app_name.lower() in app.get("label", "").lower():
                return app["package"]

        # Return as-is (might already be a package name)
        return app_name

    except Exception as e:
        logger.warning(f"Failed to resolve app name '{app_name}': {e}")
        return app_name


async def get_available_apps(tools) -> str:
    """
    Get list of available apps for the prompt.

    Returns:
        Formatted string of app names
    """
    try:
        apps = await tools.get_apps(include_system=False)
        app_names = [app.get("label", app.get("package", "")) for app in apps[:30]]
        return json.dumps(app_names)
    except Exception:
        # Fallback to generic list
        return '["Settings", "Chrome", "Camera", "Files", "Contacts", "Messages", "Phone", "Calendar", "Clock", "Calculator"]'


# =============================================================================
# Message Building (matches MAI-UI's _build_messages)
# =============================================================================


def mem2response(step: TrajStep) -> str:
    """
    Reconstruct assistant response from trajectory step.

    Converts stored action back to the format the LLM expects in history.

    Args:
        step: Trajectory step

    Returns:
        Formatted response string with <thinking> and <tool_call> tags
    """
    thinking = step.thought or ""
    structured_action = step.structured_action

    if not structured_action:
        return f"<thinking>\n{thinking}\n</thinking>\n<tool_call>\n{{}}\n</tool_call>"

    action_json = copy.deepcopy(structured_action.get("action_json", {}))

    # Convert normalized coordinates back to SCALE_FACTOR range for history
    # NOTE: Original MAI-UI only converts "coordinate", NOT start_coordinate/end_coordinate
    # This matches the behavior in mai_naivigation_agent.py mem2response()
    if "coordinate" in action_json:
        coords = action_json["coordinate"]
        if len(coords) == 2:
            # Coordinates are stored normalized (0-1), convert to 0-999
            action_json["coordinate"] = [
                int(coords[0] * SCALE_FACTOR),
                int(coords[1] * SCALE_FACTOR),
            ]

    tool_call_dict = {
        "name": "mobile_use",
        "arguments": action_json,
    }
    tool_call_json = json.dumps(tool_call_dict, separators=(",", ":"))

    return f"<thinking>\n{thinking}\n</thinking>\n<tool_call>\n{tool_call_json}\n</tool_call>"


def build_messages(
    instruction: str,
    system_prompt: str,
    traj_memory: TrajMemory,
    current_screenshot_bytes: bytes,
    history_n: int = 3,
) -> List[Dict[str, Any]]:
    """
    Build multi-turn messages matching MAI-UI's format.

    Message structure:
    1. System prompt
    2. User instruction
    3. For each history step:
       - Image (only for last history_n-1 steps)
       - Assistant response
    4. Current screenshot

    Args:
        instruction: Task instruction
        system_prompt: System prompt text
        traj_memory: Trajectory memory with history
        current_screenshot_bytes: Current screenshot as bytes
        history_n: Number of history images to include

    Returns:
        List of message dictionaries
    """
    messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": system_prompt}],
        },
        {
            "role": "user",
            "content": [{"type": "text", "text": instruction}],
        },
    ]

    steps = traj_memory.steps
    image_idx = 0

    if len(steps) > 0:
        # Calculate which steps get images (last history_n - 1 steps)
        start_image_idx = max(0, len(steps) - (history_n - 1))

        # Collect history images
        history_images = []
        for i, step in enumerate(steps):
            if i >= start_image_idx:
                history_images.append(step.screenshot_bytes)

        for history_idx, step in enumerate(steps):
            should_include_image = history_idx >= start_image_idx

            if should_include_image and image_idx < len(history_images):
                # Add image before assistant response
                encoded = bytes_to_base64(history_images[image_idx])
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{encoded}"},
                    }],
                })
                image_idx += 1

            # Add assistant response
            history_response = mem2response(step)
            messages.append({
                "role": "assistant",
                "content": [{"type": "text", "text": history_response}],
            })

            # Add ask_user_response if present (matches MAI-UI behavior)
            if step.ask_user_response:
                messages.append({
                    "role": "user",
                    "content": [{"type": "text", "text": step.ask_user_response}],
                })

    # Add current screenshot
    current_encoded = bytes_to_base64(current_screenshot_bytes)
    messages.append({
        "role": "user",
        "content": [{
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{current_encoded}"},
        }],
    })

    return messages


# =============================================================================
# Action Execution
# =============================================================================


async def execute_action(
    tools,
    action: Dict[str, Any],
    screen_width: int,
    screen_height: int,
) -> Tuple[bool, str]:
    """
    Execute a MAI-UI action using DroidRun tools.

    Args:
        tools: DroidRun Tools instance
        action: Parsed action dictionary with normalized coordinates (0-1 range)
        screen_width: Screen width in pixels
        screen_height: Screen height in pixels

    Returns:
        Tuple of (success, result_message)
    """
    action_type = action.get("action", "")
    w, h = screen_width, screen_height

    try:
        if action_type == "click":
            # Coordinates are normalized (0-1), convert to pixels
            coord = action.get("coordinate", [0, 0])
            x = int(coord[0] * w)
            y = int(coord[1] * h)
            result = await tools.tap_by_coordinates(x, y)
            return True, f"click ({x},{y}): {result}"

        elif action_type == "long_press":
            coord = action.get("coordinate", [0, 0])
            x = int(coord[0] * w)
            y = int(coord[1] * h)
            await tools.swipe(x, y, x, y, 1000)
            return True, f"long_press ({x},{y})"

        elif action_type == "double_click":
            coord = action.get("coordinate", [0, 0])
            x = int(coord[0] * w)
            y = int(coord[1] * h)
            await tools.tap_by_coordinates(x, y)
            await asyncio.sleep(0.1)
            await tools.tap_by_coordinates(x, y)
            return True, f"double_click ({x},{y})"

        elif action_type == "type":
            text = action.get("text", "")
            result = await tools.input_text(text)
            return True, f"type '{text[:30]}...': {result}" if len(text) > 30 else f"type '{text}': {result}"

        elif action_type == "swipe":
            direction = action.get("direction", "up")
            # Default to center if no coordinate provided (0.5, 0.5 normalized)
            coord = action.get("coordinate", [0.5, 0.5])

            # Start position (normalized to pixels)
            sx = int(coord[0] * w)
            sy = int(coord[1] * h)

            # Direction offsets (proportional to screen size)
            offsets = {
                "up": (0, -h // 3),
                "down": (0, h // 3),
                "left": (-w // 3, 0),
                "right": (w // 3, 0),
            }
            dx, dy = offsets.get(direction, (0, 0))

            # Clamp end coordinates to screen bounds
            ex = max(0, min(w - 1, sx + dx))
            ey = max(0, min(h - 1, sy + dy))

            await tools.swipe(sx, sy, ex, ey, 300)
            return True, f"swipe {direction} from ({sx},{sy}) to ({ex},{ey})"

        elif action_type == "drag":
            start_coord = action.get("start_coordinate", [0, 0])
            end_coord = action.get("end_coordinate", [0, 0])

            sx = int(start_coord[0] * w)
            sy = int(start_coord[1] * h)
            ex = int(end_coord[0] * w)
            ey = int(end_coord[1] * h)

            # Use longer duration for drag semantics
            await tools.swipe(sx, sy, ex, ey, 2000)
            return True, f"drag from ({sx},{sy}) to ({ex},{ey})"

        elif action_type == "open":
            app_name = action.get("text", "")
            package = await resolve_app_name(tools, app_name)
            result = await tools.start_app(package)
            return True, f"open '{app_name}' ({package}): {result}"

        elif action_type == "system_button":
            button = action.get("button", "back")
            keycodes = {
                "back": 4,
                "home": 3,
                "enter": 66,
                "menu": 82,
            }
            keycode = keycodes.get(button, 4)
            result = await tools.press_key(keycode)
            return True, f"{button}: {result}"

        elif action_type == "wait":
            await asyncio.sleep(1.0)
            return True, "wait 1s"

        elif action_type == "terminate":
            # Handled in main loop
            return True, "terminate"

        elif action_type == "answer":
            # Handled in main loop
            return True, f"answer: {action.get('text', '')}"

        elif action_type == "ask_user":
            # Handled in main loop - returns special marker
            return True, "ask_user"

        else:
            return False, f"unknown action: {action_type}"

    except Exception as e:
        logger.error(f"Action execution failed: {e}")
        return False, f"error: {e}"


# =============================================================================
# Main Run Function
# =============================================================================


async def run(
    tools,
    instruction: str,
    config: Dict[str, Any],
    max_steps: int = 15,
) -> Dict[str, Any]:
    """
    Run MAI-UI agent with exact MAI-UI behavior.

    Args:
        tools: DroidRun Tools instance (AdbTools)
        instruction: Task to complete
        config: Configuration dictionary:
            llm: Dict passed directly to load_llm() with:
                provider: LLM provider (default: "OpenAI")
                model, temperature, base_url, api_key, max_tokens, top_p, top_k, etc.
            history_n: Number of history images (default: 3)
            vision: Whether to use screenshots (default: True)
        max_steps: Maximum iterations

    Returns:
        Dictionary with: success, reason, steps, answer (if answer action)
    """
    # Validate LLM config - must be provided by user
    llm_cfg = config.get("llm")
    if not llm_cfg or not isinstance(llm_cfg, dict):
        raise ValueError(
            "MAI-UI requires 'llm' configuration. "
            "Please configure external_agents.mai_ui.llm in your config.yaml"
        )

    if "provider" not in llm_cfg:
        raise ValueError(
            "MAI-UI requires 'llm.provider' to be specified. "
            "Example: provider: OpenAI"
        )

    if "model" not in llm_cfg:
        raise ValueError(
            "MAI-UI requires 'llm.model' to be specified. "
            "Example: model: mai-ui-8b"
        )

    # Load LLM - pass config directly to load_llm
    llm_cfg = dict(llm_cfg)  # Copy to avoid mutating
    provider = llm_cfg.pop("provider")
    llm = load_llm(provider, **llm_cfg)

    # Agent-specific configuration (defaults from DEFAULT_CONFIG)
    history_n = config.get("history_n", DEFAULT_CONFIG["history_n"])

    # Initialize trajectory memory
    traj_memory = TrajMemory(task_goal=instruction)

    # Get available apps for prompt and render system prompt
    # No MCP tools passed - the MCP section will not appear in the prompt
    apps_list = await get_available_apps(tools)
    system_prompt = MAI_MOBILE_SYS_PROMPT_TEMPLATE.render(
        apps_list=apps_list,
        tools=None,  # No MCP tools - section won't render
    )

    logger.info(f"MAI-UI agent starting: {instruction}")

    for step in range(max_steps):
        logger.info(f"Step {step + 1}/{max_steps}")

        # Get screen dimensions
        try:
            await tools.get_state()
            w, h = tools.screen_width, tools.screen_height
        except Exception as e:
            logger.error(f"Failed to get state: {e}")
            w, h = 1080, 2400  # Fallback dimensions

        # Take screenshot (MAI-UI is vision-based, always requires screenshots)
        try:
            _, screenshot_bytes = await tools.take_screenshot()
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            continue

        if not screenshot_bytes:
            logger.error("No screenshot available")
            continue

        # Build messages
        messages = build_messages(
            instruction=instruction,
            system_prompt=system_prompt,
            traj_memory=traj_memory,
            current_screenshot_bytes=screenshot_bytes,
            history_n=history_n,
        )

        # Call LLM
        try:
            response = await acall_with_retries(llm, to_chat_messages(messages))
            response_text = str(response)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            continue

        # Parse response
        try:
            parsed = parse_action(response_text)
            thinking = parsed["thinking"] or ""
            action_json = parsed["action_json"]
        except ValueError as e:
            logger.error(f"Failed to parse response: {e}")
            logger.debug(f"Raw response: {response_text[:500]}")
            continue

        logger.info(f"Thinking: {thinking[:150]}...")
        logger.info(f"Action: {action_json.get('action', 'unknown')}")

        # Check for terminal actions first (before storing step)
        action_type = action_json.get("action", "")

        if action_type == "terminate":
            # Store step before returning
            traj_step = TrajStep(
                screenshot_bytes=screenshot_bytes,
                prediction=response_text,
                action=action_json,
                thought=thinking,
                step_index=step,
                structured_action={"action_json": action_json},
            )
            traj_memory.steps.append(traj_step)

            success = action_json.get("status") == "success"
            reason = action_json.get("message", "Task terminated")
            logger.info(f"Terminated: success={success}, reason={reason}")
            return {"success": success, "reason": reason, "steps": step + 1}

        if action_type == "answer":
            # Store step before returning
            traj_step = TrajStep(
                screenshot_bytes=screenshot_bytes,
                prediction=response_text,
                action=action_json,
                thought=thinking,
                step_index=step,
                structured_action={"action_json": action_json},
            )
            traj_memory.steps.append(traj_step)

            answer_text = action_json.get("text", "")
            logger.info(f"Answer: {answer_text}")
            return {
                "success": True,
                "reason": "Task completed with answer",
                "steps": step + 1,
                "answer": answer_text,
            }

        if action_type == "ask_user":
            # Get user input via stdin
            question = action_json.get("text", "Please provide input:")
            logger.info(f"Agent asks: {question}")
            print(f"\n🤖 Agent asks: {question}")
            user_response = input("Your response: ").strip()
            logger.info(f"User response: {user_response}")

            # Store step with ask_user_response
            traj_step = TrajStep(
                screenshot_bytes=screenshot_bytes,
                prediction=response_text,
                action=action_json,
                thought=thinking,
                step_index=step,
                structured_action={"action_json": action_json},
                ask_user_response=user_response,
            )
            traj_memory.steps.append(traj_step)

            # Continue to next iteration (no device action needed)
            await asyncio.sleep(0.5)
            continue

        # Store step in trajectory (for non-terminal, non-ask_user actions)
        # action_json already has normalized coordinates (0-1) from parse_action
        traj_step = TrajStep(
            screenshot_bytes=screenshot_bytes,
            prediction=response_text,
            action=action_json,
            thought=thinking,
            step_index=step,
            structured_action={"action_json": action_json},
        )
        traj_memory.steps.append(traj_step)

        # Execute action
        success, result_msg = await execute_action(tools, action_json, w, h)
        logger.info(f"Execution: {result_msg}")

        # Brief pause between steps
        await asyncio.sleep(0.5)

    # Max steps reached
    return {"success": False, "reason": "Max steps reached", "steps": max_steps}
