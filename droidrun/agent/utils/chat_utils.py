import base64
import json
import logging
from typing import List, TYPE_CHECKING
from llama_index.core.base.llms.types import ChatMessage, ImageBlock, TextBlock

if TYPE_CHECKING:
    from droidrun.tools import Tools

logger = logging.getLogger("droidrun")
logging.basicConfig(level=logging.INFO)

def message_copy(message: ChatMessage, deep = True) -> ChatMessage:
    if deep:
        copied_message = message.model_copy()
        copied_message.blocks = [block.model_copy () for block in message.blocks]

        return copied_message
    copied_message = message.model_copy()

    # Create a new, independent list containing the same block references
    copied_message.blocks = list(message.blocks) # or original_message.blocks[:]

    return copied_message

async def add_ui_text_block(tools: 'Tools', chat_history: List[ChatMessage], retry = 5, copy = True) -> List[ChatMessage]:
    """Add UI elements to the chat history without modifying the original."""
    ui_elements = None
    for i in range(retry):
        try:
            ui_elements = await tools.get_clickables()
            if ui_elements:
                break
        except Exception as e:
            if i < 4:
                logger.warning(f"  - Error getting UI elements: {e}. Retrying...")
            else:
                logger.error(f"  - Error getting UI elements: {e}. No UI elements will be sent.")
    if ui_elements:
        ui_block = TextBlock(text="\nCurrent Clickable UI elements from the device using the custom TopViewService:\n```json\n" + json.dumps(ui_elements) + "\n```\n")
        if copy:
            chat_history = chat_history.copy()
            chat_history[-1] = message_copy(chat_history[-1])
        chat_history[-1].blocks.append(ui_block)
    return chat_history

async def add_screenshot_image_block(tools: 'Tools', chat_history: List[ChatMessage], retry: int = 5, copy = True) -> None:
    screenshot = await take_screenshot(tools, retry)
    if screenshot:
        image_block = ImageBlock(image=base64.b64encode(screenshot))
        if copy:
            chat_history = chat_history.copy()  # Create a copy of chat history to avoid modifying the original
            chat_history[-1] = message_copy(chat_history[-1])
        chat_history[-1].blocks.append(image_block)
    return chat_history


async def take_screenshot(tools: 'Tools', retry: int = 5) -> None:
    """Take a screenshot and return the image."""
    # Retry taking screenshot
    tools.last_screenshot = None
    for i in range(retry):
        try:
            await tools.take_screenshot()
            if tools.last_screenshot:
                break
        except Exception as e:
            if i < 4:
                logger.warning(f"  - Error taking screenshot: {e}. Retrying...")
            else:
                logger.error(f"  - Error taking screenshot: {e}. No screenshot will be sent.")
                return None
    screenshot = tools.last_screenshot
    tools.last_screenshot = None # Reset last screenshot after taking it
    return screenshot

async def add_screenshot(chat_history: List[ChatMessage], screenshot, copy = True) -> List[ChatMessage]:
    """Add a screenshot to the chat history."""
    image_block = ImageBlock(image=base64.b64encode(screenshot))
    if copy:
        chat_history[-1] = message_copy(chat_history[-1])
        chat_history = chat_history.copy()  # Create a copy of chat history to avoid modifying the original
    chat_history[-1].blocks.append(image_block)
    return chat_history

async def add_phone_state_block(tools: 'Tools', chat_history: List[ChatMessage]) -> List[ChatMessage]:
    phone_state = await tools.get_phone_state()
    ui_block = TextBlock(text=f"\nCurrent Phone state: {phone_state}\n```\n")
    chat_history = chat_history.copy()
    chat_history[-1] = message_copy(chat_history[-1])
    chat_history[-1].blocks.append(ui_block)
    return chat_history