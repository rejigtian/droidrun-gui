import asyncio
import logging

logger = logging.getLogger("droidrun")


def wrap_async_tools(tools_dict: dict, loop=None) -> dict:
    """
    Wrap async tool functions with sync wrappers for exec() contexts.

    ExecutorAgent handles async natively via iscoroutinefunction checks.
    CodeActAgent needs sync wrappers since it runs code in threads via exec().

    Uses asyncio.run() to create an isolated event loop in the thread,
    avoiding deadlocks with the main event loop.

    Args:
        tools_dict: Dictionary of tool specifications with 'function' key
        loop: Deprecated parameter, kept for backward compatibility (ignored)

    Returns:
        Dictionary of wrapped tool specifications
    """
    wrapped = {}
    for tool_name, tool_spec in tools_dict.items():
        func = tool_spec["function"]

        if asyncio.iscoroutinefunction(func):
            logger.debug("Wrapping async tool: %s", tool_name)

            def sync_wrapper(tool_instance, *args, _func=func, **kwargs):
                return asyncio.run(_func(tool_instance, *args, **kwargs))

            wrapped[tool_name] = {
                **tool_spec,
                "function": sync_wrapper,
                "original_function": func,
            }
        else:
            wrapped[tool_name] = tool_spec

    return wrapped
