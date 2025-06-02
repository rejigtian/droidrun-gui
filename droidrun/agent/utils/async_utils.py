import asyncio
import threading

def async_to_sync(func):
    """
    Convert an async function to a sync function.

    Args:
        func: Async function to convert

    Returns:
        Callable: Synchronous version of the async function
    """

    def wrapper(*args, **kwargs):
        coro = func(*args, **kwargs)

        result_container = {}
        def runner():
            result = asyncio.run(coro)
            result_container['result'] = result

        t = threading.Thread(target=runner)
        t.start()
        t.join()
        return result_container['result']

    return wrapper