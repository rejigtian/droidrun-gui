import logging
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Tuple, Union

from PIL import Image
from llama_index.core.base.llms.types import ChatMessage, ImageBlock, TextBlock

logger = logging.getLogger("droidrun")


# ============================================================================
# CONVERSION TO CHATMESSAGE (call right before LLM)
# ============================================================================


def _ensure_image_bytes(image_source: Union[str, Path, Image.Image, bytes]) -> bytes:
    """Convert image to bytes."""
    if isinstance(image_source, bytes):
        return image_source
    if isinstance(image_source, (str, Path)):
        image = Image.open(image_source)
    elif isinstance(image_source, Image.Image):
        image = image_source
    else:
        raise ValueError(f"Unsupported image type: {type(image_source)}")

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def to_chat_messages(messages: list[dict]) -> list[ChatMessage]:
    """
    Convert dict messages to ChatMessage list.

    Args:
        messages: List of message dicts

    Returns:
        List of ChatMessage objects
    """
    chat_messages = []

    for msg in messages:
        blocks = []
        for item in msg.get("content", []):
            if "text" in item:
                blocks.append(TextBlock(text=item["text"]))
            elif "image" in item:
                image_bytes = _ensure_image_bytes(item["image"])
                blocks.append(ImageBlock(image=image_bytes))

        chat_messages.append(ChatMessage(role=msg["role"], blocks=blocks))

    return chat_messages


# ============================================================================
# CODE EXTRACTION
# ============================================================================


def extract_code_and_thought(response_text: str) -> Tuple[Optional[str], str]:
    """
    Extract code from Markdown blocks (```python ... ```) and the surrounding text (thought).

    Returns:
        Tuple[Optional[code_string], thought_string]
    """
    first_backticks = response_text.find("```")
    if first_backticks == -1:
        return None, response_text.strip()

    last_backticks = response_text.rfind("```")
    if first_backticks == last_backticks:
        return None, response_text.strip()

    code_block = response_text[first_backticks : last_backticks + 3]

    if code_block.startswith("```python"):
        code_content = code_block[9:]
    elif code_block.startswith("```py"):
        code_content = code_block[5:]
    else:
        code_content = code_block[3:]

    if code_content.endswith("```"):
        code_content = code_content[:-3]

    extracted_code = code_content.strip()

    thought_before = response_text[:first_backticks].strip()
    thought_after = response_text[last_backticks + 3 :].strip()
    thought_text = (thought_before + " " + thought_after).strip()

    return extracted_code, thought_text


# ============================================================================
# MESSAGE UTILITIES
# ============================================================================


def has_content(message: dict) -> bool:
    for item in message.get("content", []):
        if "text" in item and item["text"].strip():
            return True
        if "image" in item and item["image"]:
            return True
    return False


def filter_empty_messages(messages: list[dict]) -> list[dict]:
    return [msg for msg in messages if has_content(msg)]


def limit_history(messages: list[dict], max_messages: int, preserve_first: bool = True) -> list[dict]:
    if len(messages) <= max_messages:
        return messages

    if preserve_first and messages:
        first = messages[0]
        tail = messages[-max_messages + 1:]
        if first not in tail:
            return [first] + tail
        return tail

    return messages[-max_messages:]
