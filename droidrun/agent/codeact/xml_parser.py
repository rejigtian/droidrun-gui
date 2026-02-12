"""XML tool-call parsing and result formatting.

Parses LLM responses containing <function_calls> blocks into structured
ToolCall objects, and formats tool results as <function_results> XML
for injection back into the conversation.
"""

import json
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("droidrun")

OPEN_TAG = "<function_calls>"
CLOSE_TAG = "</function_calls>"

# Built-in tool parameters (remember, complete) that aren't in the signature dicts.
_BUILTIN_PARAM_TYPES: Dict[str, str] = {
    "success": "boolean",
    "reason": "string",
    "message": "string",
    "information": "string",
}

_PARAM_RE = re.compile(
    r'(<parameter\s+name="[^"]*">)(.*?)(</parameter>)',
    re.DOTALL,
)


@dataclass
class ToolCall:
    """A parsed tool invocation from the LLM response."""

    name: str
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    """Result from executing a single tool."""

    name: str
    output: str
    is_error: bool = False


def build_param_types(tools: dict) -> Dict[str, str]:
    """Build a flat {param_name: type_string} map from tool signature dicts.

    Reads the "parameters" field from each tool signature. Also includes
    built-in params for remember/complete.

    Note: parameter names are global (not per-tool). If two tools share a
    param name, they must share the same type.

    Args:
        tools: Merged dict of tool signatures (atomic + custom).

    Returns:
        Flat dict mapping parameter name to type string.
    """
    param_types: Dict[str, str] = {}

    for _tool_name, spec in tools.items():
        parameters = spec.get("parameters", {})
        for param_name, param_info in parameters.items():
            param_types[param_name] = param_info.get("type", "string")

    # Add built-in tool params
    param_types.update(_BUILTIN_PARAM_TYPES)

    return param_types


def parse_tool_calls(
    text: str, param_types: Optional[Dict[str, str]] = None
) -> Tuple[str, List[ToolCall]]:
    """Parse tool calls from LLM response text.

    Args:
        text: Raw LLM response text.
        param_types: Optional {param_name: type_string} map for coercion.
                     If None, all values are kept as strings.

    Returns:
        Tuple of (text_before_tool_calls, list_of_tool_calls).
        If no tool calls found, returns (full_text, []).
    """
    if OPEN_TAG not in text:
        return text.strip(), []

    parts = text.split(OPEN_TAG)
    text_before = parts[0].strip()

    calls: List[ToolCall] = []
    for part in parts[1:]:
        close_idx = part.find(CLOSE_TAG)
        if close_idx == -1:
            continue  # Malformed — no closing tag, skip

        block = part[:close_idx].strip()
        if not block:
            continue

        block = _sanitize_param_content(block)

        try:
            root = ET.fromstring(f"<root>{block}</root>")
        except ET.ParseError:
            logger.warning("Failed to parse tool call XML block, skipping")
            continue

        for invoke in root.findall("invoke"):
            name = invoke.get("name", "")
            if not name:
                continue

            params: Dict[str, Any] = {}
            for param in invoke.findall("parameter"):
                param_name = param.get("name", "")
                param_value = param.text or ""
                if param_name:
                    params[param_name] = _coerce_param(
                        param_name, param_value, param_types
                    )

            calls.append(ToolCall(name=name, parameters=params))

    return text_before, calls


def format_tool_results(results: List[ToolResult]) -> str:
    """Format tool results as XML for injection into conversation.

    Args:
        results: List of tool results to format.

    Returns:
        XML string with <function_results> wrapper.
    """
    lines = ["<function_results>"]

    for result in results:
        if result.is_error:
            lines.append(
                f"<result>\n<name>{result.name}</name>\n"
                f"<error>{result.output}</error>\n</result>"
            )
        else:
            lines.append(
                f"<result>\n<name>{result.name}</name>\n"
                f"<output>{result.output}</output>\n</result>"
            )

    lines.append("</function_results>")
    return "\n".join(lines)


def _sanitize_param_content(block: str) -> str:
    """Escape XML-unsafe characters inside parameter values.

    Parameter values often contain raw code or text with <, >, &
    which would break XML parsing. This escapes content inside
    <parameter> tags only, leaving the XML structure intact.
    """

    def _escape(m: re.Match) -> str:
        pre, content, post = m.group(1), m.group(2), m.group(3)
        clean = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return pre + clean + post

    return _PARAM_RE.sub(_escape, block)


def _coerce_param(
    name: str, value: str, param_types: Optional[Dict[str, str]] = None
) -> Any:
    """Coerce string parameter value to expected type.

    Args:
        name: Parameter name.
        value: Raw string value from XML.
        param_types: Optional type map. If None, returns value as-is.
    """
    if param_types is None:
        return value

    expected = param_types.get(name, "string")

    if expected == "boolean":
        return value.strip().lower() == "true"

    if expected == "number":
        value = value.strip()
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value  # Fallback: keep as string

    if expected == "list":
        value = value.strip()
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass
        return value  # Fallback: keep as string

    return value


def _spec_to_json(name: str, spec: dict) -> str:
    """Convert a tool spec to compact JSON for the <function> tag."""
    parameters = spec.get("parameters", {})
    properties = {}
    required = []
    for param_name, param_info in parameters.items():
        properties[param_name] = {"type": param_info.get("type", "string")}
        if param_info.get("description"):
            properties[param_name]["description"] = param_info["description"]
        if param_info.get("required", True):
            required.append(param_name)
        if "default" in param_info:
            properties[param_name]["default"] = param_info["default"]

    tool_dict = {
        "name": name,
        "description": spec.get("description", f"Tool: {name}"),
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }
    return json.dumps(tool_dict, separators=(",", ":"))


# Built-in tools (FastAgent-specific, not in signature dicts)
_BUILTIN_TOOLS = {
    "remember": {
        "parameters": {
            "information": {"type": "string", "required": True},
        },
        "description": "Remember information for later use",
    },
    "complete": {
        "parameters": {
            "success": {"type": "boolean", "required": True},
            "message": {"type": "string", "required": True},
        },
        "description": (
            "Mark task as complete. "
            "success=true if task succeeded, false if failed. "
            "message contains the result, answer, or explanation."
        ),
    },
}


def build_tool_definitions_xml(
    atomic_tools: dict,
    custom_tools: Optional[dict] = None,
) -> str:
    """Build XML tool definitions for the system prompt.

    Outputs a <functions> block with each tool as compact JSON inside
    <function> tags, following the XML tool-calling protocol.

    Args:
        atomic_tools: Dict of atomic action signatures.
        custom_tools: Optional dict of custom tool signatures.

    Returns:
        XML string with <functions> wrapper containing all tool definitions.
    """
    all_tools = {**atomic_tools, **(custom_tools or {}), **_BUILTIN_TOOLS}

    lines = ["<functions>"]
    for tool_name, spec in all_tools.items():
        lines.append(f"<function>{_spec_to_json(tool_name, spec)}</function>")
    lines.append("</functions>")

    return "\n".join(lines)
