import asyncio
import nest_asyncio
nest_asyncio_applied = False


def async_to_sync(func):
    """
    Convert an async function to a sync function.

    Args:
        func: Async function to convert

    Returns:
        Callable: Synchronous version of the async function
    """

    def wrapper(*args, **kwargs):
        global nest_asyncio_applied # Declare modification of global at the start of the scope
        coro = func(*args, **kwargs)
        try:
            # Try to get the running event loop.
            loop = asyncio.get_running_loop()

            # If the loop is running, apply nest_asyncio if available and needed.
            # Removed global declaration from here
            if nest_asyncio and not nest_asyncio_applied:
                nest_asyncio.apply()
                nest_asyncio_applied = True
            # Run the coroutine to completion within the running loop.
            # This requires nest_asyncio to work correctly in nested scenarios.
            # Changed from ensure_future to run_until_complete to make it truly synchronous.
            return loop.run_until_complete(coro)

        except RuntimeError:
            # No running event loop found.
            try:
                # Check if there's a loop policy and a current event loop set, even if not running.
                loop = asyncio.get_event_loop_policy().get_event_loop()
                if loop.is_running():
                     # This case should ideally be caught by get_running_loop(),
                     # but as a fallback, handle similarly if loop is running.
                     # Removed global declaration from here
                     if nest_asyncio and not nest_asyncio_applied:
                         nest_asyncio.apply()
                         nest_asyncio_applied = True
                     return loop.run_until_complete(coro)
                else:
                    # Loop exists but is not running, run until complete.
                    return loop.run_until_complete(coro)
            except RuntimeError:
                 # If get_event_loop() also fails (no loop set at all for this thread),
                 # use asyncio.run() which creates a new loop.
                 return asyncio.run(coro)


    return wrapper