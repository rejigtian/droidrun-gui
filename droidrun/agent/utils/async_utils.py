import asyncio
import logging

logger = logging.getLogger("droidrun")


def wrap_async_tools(tools_dict: dict, loop) -> dict:
    """
    Wrap async tool functions with sync wrappers for exec() contexts.

    ExecutorAgent handles async natively via iscoroutinefunction checks.
    CodeActAgent needs sync wrappers since it runs code in threads via exec().
    """
    wrapped = {}
    for tool_name, tool_spec in tools_dict.items():
        func = tool_spec["function"]

        if asyncio.iscoroutinefunction(func):
            logger.debug("Wrapping async tool: %s", tool_name)

            def sync_wrapper(tool_instance, *args, _func=func, _loop=loop, **kwargs):
                future = asyncio.run_coroutine_threadsafe(
                    _func(tool_instance, *args, **kwargs),
                    _loop
                )
                return future.result(timeout=None)

            wrapped[tool_name] = {
                **tool_spec,
                "function": sync_wrapper,
                "original_function": func,
            }
        else:
            wrapped[tool_name] = tool_spec

    return wrapped
