
import asyncio
import contextvars
import threading
import time
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Any, Optional


def call_with_retries(llm, messages, retries=3, timeout=500, delay=1.0):
    last_exception = None

    for attempt in range(1, retries + 1):
        ctx = contextvars.copy_context()
        result_holder = {}
        error_holder = {}

        def _target():
            try:
                result_holder["response"] = ctx.run(llm.chat, messages=messages)  # noqa: B023
            except Exception as e:
                error_holder["error"] = e  # noqa: B023

        worker = threading.Thread(target=_target, daemon=True)
        worker.start()
        worker.join(timeout)

        if worker.is_alive():
            print(f"Attempt {attempt} timed out after {timeout} seconds")
            # Do not join; thread is daemon and won't block process exit
            last_exception = TimeoutError("Timed out")
        else:
            if "error" in error_holder:
                err = error_holder["error"]
                # Normalize FuturesTimeoutError if raised inside llm.chat
                if isinstance(err, FuturesTimeoutError):
                    print(f"Attempt {attempt} timed out inside LLM after {timeout} seconds")
                    last_exception = TimeoutError("Timed out")
                else:
                    print(f"Attempt {attempt} failed with error: {err!r}")
                    last_exception = err
            else:
                response = result_holder.get("response")
                if (
                    response is not None
                    and getattr(response, "message", None) is not None
                    and getattr(response.message, "content", None)
                ):
                    return response
                else:
                    print(f"Attempt {attempt} returned empty content")
                    last_exception = ValueError("Empty response content")

        if attempt < retries:
            time.sleep(delay * attempt)

    if last_exception:
        raise last_exception
    raise ValueError("All attempts returned empty response content")


async def acall_with_retries(
    llm,
    messages: list,
    retries: int = 3,
    timeout: float = 500,
    delay: float = 1.0
) -> Any:
    """
    Call LLM with retries and timeout handling.

    Args:
        llm: The LLM client instance
        messages: List of messages to send
        retries: Number of retry attempts
        timeout: Timeout in seconds for each attempt
        delay: Base delay between retries (multiplied by attempt number)

    Returns:
        The LLM response object
    """
    last_exception: Optional[Exception] = None

    for attempt in range(1, retries + 1):
        try:
            response = await asyncio.wait_for(
                llm.achat(messages=messages),  # Use achat() instead of chat()
                timeout=timeout
            )

            # Validate response
            if (
                response is not None
                and getattr(response, "message", None) is not None
                and getattr(response.message, "content", None)
            ):
                return response
            else:
                print(f"Attempt {attempt} returned empty content")
                last_exception = ValueError("Empty response content")

        except asyncio.TimeoutError:
            print(f"Attempt {attempt} timed out after {timeout} seconds")
            last_exception = TimeoutError("Timed out")

        except Exception as e:
            print(f"Attempt {attempt} failed with error: {e!r}")
            last_exception = e

        if attempt < retries:
            await asyncio.sleep(delay * attempt)

    if last_exception:
        raise last_exception
    raise ValueError("All attempts returned empty response content")
