from typing import Any, Dict, List, Tuple


def format_phone_state(phone_state: Dict[str, Any]) -> str:
    """
    Format phone state data into a readable text block.

    Args:
        phone_state: Dictionary containing phone state information

    Returns:
        Formatted phone state text
    """
    if isinstance(phone_state, dict) and 'error' not in phone_state:
        current_app = phone_state.get('currentApp', '')
        package_name = phone_state.get('packageName', 'Unknown')
        focused_element = phone_state.get('focusedElement')
        is_editable = phone_state.get('isEditable', False)

        # Format the focused element - just show the text content
        if focused_element and focused_element.get('text'):
            focused_desc = f"'{focused_element.get('text', '')}'"
        else:
            focused_desc = "''"

        phone_state_text = f"""**Current Phone State:**
• **App:** {current_app} ({package_name})
• **Keyboard:** {'Visible' if is_editable else 'Hidden'}
• **Focused Element:** {focused_desc}"""
    else:
        # Handle error cases or malformed data
        if isinstance(phone_state, dict) and 'error' in phone_state:
            phone_state_text = f"📱 **Phone State Error:** {phone_state.get('message', 'Unknown error')}"
        else:
            phone_state_text = f"📱 **Phone State:** {phone_state}"

    return phone_state_text


def format_ui_elements(ui_data: List[Dict[str, Any]], level: int = 0) -> str:
    """
    Format UI elements in the exact format: index. className: "resourceId", "text" - (bounds)

    Args:
        ui_data: List of UI element dictionaries
        level: Indentation level for nested elements

    Returns:
        Formatted UI elements text
    """
    if not ui_data:
        return ""

    formatted_lines = []
    indent = "  " * level  # Indentation for nested elements

    # Handle both list and single element
    elements = ui_data if isinstance(ui_data, list) else [ui_data]

    for element in elements:
        if not isinstance(element, dict):
            continue

        # Extract element properties
        index = element.get('index', '')
        class_name = element.get('className', '')
        resource_id = element.get('resourceId', '')
        text = element.get('text', '')
        bounds = element.get('bounds', '')
        children = element.get('children', [])

        # Format the line: index. className: "resourceId", "text" - (bounds)
        line_parts = []
        if index != '':
            line_parts.append(f"{index}.")
        if class_name:
            line_parts.append(class_name + ":")

        # Build the quoted details section
        details = []
        if resource_id:
            details.append(f'"{resource_id}"')
        if text:
            details.append(f'"{text}"')

        if details:
            line_parts.append(", ".join(details))

        if bounds:
            line_parts.append(f"- ({bounds})")

        formatted_line = f"{indent}{' '.join(line_parts)}"
        formatted_lines.append(formatted_line)

        # Recursively format children with increased indentation
        if children:
            child_formatted = format_ui_elements(children, level + 1)
            if child_formatted:
                formatted_lines.append(child_formatted)

    return "\n".join(formatted_lines)


def get_device_state_exact_format(state: Dict[str, Any]) -> Tuple[str, str]:
    """
    Get device state in exactly the format requested:

    **Current Phone State:**
    • **App:** App Name (package.name)
    • **Keyboard:** Hidden/Visible
    • **Focused Element:** 'text'

    Current Clickable UI elements from the device in the schema 'index. className: resourceId, text - bounds(x1,y1,x2,y2)':
    1. ClassName: "resourceId", "text" - (x1, y1, x2, y2)

    Args:
        state: Dictionary containing device state data from collector.get_device_state()

    Returns:
        Tuple of (formatted_string, focused_text) where focused_text is the actual
        text content of the focused element, or empty string if none.
    """
    try:
        if "error" in state:
            return (f"Error getting device state: {state.get('message', 'Unknown error')}", "")

        # Extract focused element text
        phone_state = state.get("phone_state", {})
        focused_element = phone_state.get('focusedElement')
        focused_text = ""
        if focused_element:
            focused_text = focused_element.get('text', '')

        # Format the state data
        phone_state_text = format_phone_state(phone_state)
        ui_data = state.get("a11y_tree", [])
        if ui_data:
            formatted_ui = format_ui_elements(ui_data)
            ui_elements_text = f"Current Clickable UI elements from the device in the schema 'index. className: resourceId, text - bounds(x1,y1,x2,y2)':\n{formatted_ui}"
        else:
            ui_elements_text = "Current Clickable UI elements from the device in the schema 'index. className: resourceId, text - bounds(x1,y1,x2,y2)':\nNo UI elements found"

        formatted_string = f"{phone_state_text}\n        \n\n{ui_elements_text}"

        return (formatted_string, focused_text)
    except Exception as e:
        return (f"Error getting device state: {e}", "")


def main():
    """Small test"""
    example_state = {
        "phone_state": {
            "currentApp": "Settings",
            "packageName": "com.android.settings",
            "isEditable": False,
            "focusedElement": {"text": "Search settings"}
        },
        "a11y_tree": [
            {
                "index": 1,
                "className": "android.widget.TextView",
                "resourceId": "com.android.settings:id/title",
                "text": "Wi‑Fi",
                "bounds": "100,200,300,250"
            }
        ]
    }

    formatted_string, focused_text = get_device_state_exact_format(example_state)
    print("Formatted String:")
    print(formatted_string)
    print(f"\nFocused Text: '{focused_text}'")


if __name__ == "__main__":
    main()
