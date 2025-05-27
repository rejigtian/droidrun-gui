import base64
import json
import logging
from typing import List, TYPE_CHECKING, Dict, Any, Optional
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

async def add_ui_text_block(ui_state: str, chat_history: List[ChatMessage], copy = True) -> List[ChatMessage]:
    """Add UI elements to the chat history without modifying the original."""
    if ui_state:
        ui_block = TextBlock(text="\nCurrent Clickable UI elements from the device using the custom TopViewService:\n```json\n" + json.dumps(ui_state) + "\n```\n")
        if copy:
            chat_history = chat_history.copy()
            chat_history[-1] = message_copy(chat_history[-1])
        chat_history[-1].blocks.append(ui_block)
    return chat_history

async def add_screenshot_image_block(screenshot, chat_history: List[ChatMessage], copy = True) -> None:
    if screenshot:
        image_block = ImageBlock(image=base64.b64encode(screenshot))
        if copy:
            chat_history = chat_history.copy()  # Create a copy of chat history to avoid modifying the original
            chat_history[-1] = message_copy(chat_history[-1])
        chat_history[-1].blocks.append(image_block)
    return chat_history


async def add_phone_state_block(phone_state, chat_history: List[ChatMessage]) -> List[ChatMessage]:
    
    ui_block = TextBlock(text=f"\nCurrent Phone state: {phone_state}\n```\n")
    chat_history = chat_history.copy()
    chat_history[-1] = message_copy(chat_history[-1])
    chat_history[-1].blocks.append(ui_block)
    return chat_history

async def add_memory_block(memory: List[str], chat_history: List[ChatMessage]) -> List[ChatMessage]:
        memory_block = "\n### Remembered Information:\n"
        for idx, item in enumerate(memory, 1):
            memory_block += f"{idx}. {item}\n"
        
        for i, msg in enumerate(chat_history):
            if msg.role == "user":
                if isinstance(msg.content, str):
                    updated_content = f"{memory_block}\n\n{msg.content}"
                    chat_history[i] = ChatMessage(role="user", content=updated_content)
                elif isinstance(msg.content, list):
                    memory_text_block = TextBlock(text=memory_block)
                    content_blocks = [memory_text_block] + msg.content
                    chat_history[i] = ChatMessage(role="user", content=content_blocks)
                break