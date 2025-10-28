import asyncio
import logging

logger = logging.getLogger("droidrun")


def wrap_async_tools(tools_dict: dict, loop=None) -> dict:
    """
    Wrap async tool functions with sync wrappers for exec() contexts.

    ExecutorAgent handles async natively via iscoroutinefunction checks.
    CodeActAgent needs sync wrappers since it runs code in threads via exec().

    Uses asyncio.run_coroutine_threadsafe() to schedule coroutines on the
    existing event loop from the thread, avoiding event loop conflicts.

    Args:
        tools_dict: Dictionary of tool specifications with 'function' key
        loop: Event loop to use for scheduling async functions (required for async tools)

    Returns:
        Dictionary of wrapped tool specifications
    """
    wrapped = {}
    for tool_name, tool_spec in tools_dict.items():
        func = tool_spec["function"]

        if asyncio.iscoroutinefunction(func):
            logger.debug("Wrapping async tool: %s", tool_name)

            if loop is None:
                logger.warning(
                    f"Async tool '{tool_name}' requires an event loop but none was provided. "
                    "This may cause 'attached to a different loop' errors."
                )

            def sync_wrapper(tool_instance, *args, _func=func, _loop=loop, **kwargs):
                if _loop is None:
                    # Fallback to asyncio.run() if no loop provided (legacy behavior)
                    return asyncio.run(_func(tool_instance, *args, **kwargs))
                else:
                    # Schedule on the existing event loop from the thread
                    future = asyncio.run_coroutine_threadsafe(
                        _func(tool_instance, *args, **kwargs), _loop
                    )
                    return future.result()  # Block until complete

            wrapped[tool_name] = {
                **tool_spec,
                "function": sync_wrapper,
                "original_function": func,
            }
        else:
            wrapped[tool_name] = tool_spec

    return wrapped
