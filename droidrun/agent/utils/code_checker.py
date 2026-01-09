"""Code checker hook for safe execution."""

from typing import Callable, Optional, Tuple, Set

CodeCheckerFn = Callable[[str], Tuple[bool, str]]
ToolsCallbackFn = Callable[[Set[str]], None]

_checker_fn: Optional[CodeCheckerFn] = None
_tools_callback: Optional[ToolsCallbackFn] = None


def set_code_checker(fn: CodeCheckerFn, tools_callback: ToolsCallbackFn = None) -> None:
    """Register a checker: fn(code) -> (is_safe, error_msg). Optional tools_callback receives tool names."""
    global _checker_fn, _tools_callback
    _checker_fn = fn
    _tools_callback = tools_callback


def clear_code_checker() -> None:
    """Remove the registered checker."""
    global _checker_fn, _tools_callback
    _checker_fn = None
    _tools_callback = None


def set_tools(tool_names: Set[str]) -> None:
    """Called by executor to inform checker of available tools."""
    if _tools_callback:
        _tools_callback(tool_names)


def check_code(code: str) -> Tuple[bool, str]:
    """Run checker if registered. Returns (True, "") if none."""
    if _checker_fn is None:
        return True, ""
    return _checker_fn(code)
