"""
Message conversion utilities for Manager Agent.

Converts between dict message format and llama-index ChatMessage format.
"""

from io import BytesIO
from pathlib import Path
from typing import Union

from llama_index.core.llms import ChatMessage, ImageBlock, TextBlock
from PIL import Image


def image_to_image_bytes(image_source: Union[str, Path, Image.Image, bytes]) -> bytes:
    """
    Convert image to bytes for ImageBlock.

    Args:
        image_source: Can be:
            - str/Path: path to image file
            - PIL.Image.Image: PIL Image object
            - bytes: bytes of image

    Returns:
        Image bytes in PNG format
    """
    if isinstance(image_source, (str, Path)):
        image = Image.open(image_source)
    elif isinstance(image_source, Image.Image):
        image = image_source
    elif isinstance(image_source, bytes):
        return image_source
    else:
        raise ValueError(f"Unsupported image source type: {type(image_source)}")

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def convert_messages_to_chatmessages(messages: list[dict]) -> list[ChatMessage]:
    """
    Convert dict messages to llama-index ChatMessage format.

    Dict format (input):
        {
            "role": "user" | "assistant" | "system",
            "content": [
                {"text": "some text"},
                {"image": "/path/to/image.png"}  # or PIL Image
            ]
        }

    ChatMessage format (output):
        ChatMessage(
            role="user",
            blocks=[
                TextBlock(text="some text"),
                ImageBlock(image=b"...bytes...")
            ]
        )

    Args:
        messages: List of message dicts

    Returns:
        List of ChatMessage objects
    """
    chat_messages = []

    for message in messages:
        blocks = []

        for item in message['content']:
            if 'text' in item:
                blocks.append(TextBlock(text=item['text']))
            elif 'image' in item:
                # Convert image to bytes
                image_bytes = image_to_image_bytes(item['image'])
                blocks.append(ImageBlock(image=image_bytes))

        chat_messages.append(ChatMessage(role=message['role'], blocks=blocks))

    return chat_messages
