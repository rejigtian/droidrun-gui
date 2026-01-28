"""Adapter to convert MCP tools to DroidRun custom tool format."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from droidrun.mcp.client import MCPClientManager


def schema_to_arguments(input_schema: dict) -> list[str]:
    """Extract argument list from JSON Schema."""
    properties = input_schema.get("properties", {})
    required = set(input_schema.get("required", []))

    arguments: list[str] = []
    for prop_name, prop_info in properties.items():
        if prop_name in required:
            arguments.append(prop_name)
        else:
            default = prop_info.get("default", "None")
            if isinstance(default, str):
                default = f'"{default}"'
            arguments.append(f"{prop_name}={default}")

    return arguments


def mcp_to_droidrun_tools(mcp_manager: "MCPClientManager") -> dict[str, dict[str, Any]]:
    """Convert discovered MCP tools to DroidRun custom tool format."""
    custom_tools: dict[str, dict[str, Any]] = {}

    for tool_name, tool_info in mcp_manager.tools.items():
        wrapper = _create_tool_wrapper(tool_name, mcp_manager)
        custom_tools[tool_name] = {
            "arguments": schema_to_arguments(tool_info.input_schema),
            "description": tool_info.description,
            "function": wrapper,
        }

    return custom_tools


def _create_tool_wrapper(tool_name: str, manager: "MCPClientManager"):
    """Create async wrapper function for an MCP tool."""

    async def mcp_tool_wrapper(*, tools=None, shared_state=None, **kwargs) -> str:
        result = await manager.call_tool(tool_name, kwargs)

        if hasattr(result, "content") and result.content:
            text_parts = []
            for block in result.content:
                if hasattr(block, "text") and block.text:
                    text_parts.append(block.text)
            if text_parts:
                return "\n".join(text_parts)

        return str(result)

    mcp_tool_wrapper.__name__ = f"mcp_{tool_name}"
    return mcp_tool_wrapper
