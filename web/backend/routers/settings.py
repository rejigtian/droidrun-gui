"""
/api/settings  — read and update LLM configuration
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from core.settings_manager import get_all, update as settings_update

router = APIRouter(prefix="/api")


class SettingsOut(BaseModel):
    default_provider: str
    gemini_model: str
    openai_model: str
    anthropic_model: str
    deepseek_model: str
    zhipu_model: str
    ollama_model: str
    ollama_base_url: str
    max_steps: int
    # Keys are returned masked
    google_api_key: str
    openai_api_key: str
    anthropic_api_key: str
    deepseek_api_key: str
    zhipu_api_key: str


class SettingsUpdate(BaseModel):
    default_provider: Optional[str] = None
    gemini_model: Optional[str] = None
    openai_model: Optional[str] = None
    anthropic_model: Optional[str] = None
    deepseek_model: Optional[str] = None
    zhipu_model: Optional[str] = None
    ollama_model: Optional[str] = None
    ollama_base_url: Optional[str] = None
    max_steps: Optional[int] = None
    google_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    zhipu_api_key: Optional[str] = None


def _mask(key: str) -> str:
    """Return a masked version of an API key for display."""
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return key[:4] + "****" + key[-4:]


@router.get("/settings", response_model=SettingsOut)
async def get_settings():
    data = get_all()
    return SettingsOut(
        default_provider=data.get("default_provider", "GoogleGenAI"),
        gemini_model=data.get("gemini_model", "gemini-2.0-flash"),
        openai_model=data.get("openai_model", "gpt-4o"),
        anthropic_model=data.get("anthropic_model", "claude-sonnet-4-6"),
        deepseek_model=data.get("deepseek_model", "deepseek-chat"),
        zhipu_model=data.get("zhipu_model", "glm-4-plus"),
        ollama_model=data.get("ollama_model", "llama3.2"),
        ollama_base_url=data.get("ollama_base_url", "http://localhost:11434"),
        max_steps=int(data.get("max_steps", 15)),
        google_api_key=_mask(data.get("google_api_key", "")),
        openai_api_key=_mask(data.get("openai_api_key", "")),
        anthropic_api_key=_mask(data.get("anthropic_api_key", "")),
        deepseek_api_key=_mask(data.get("deepseek_api_key", "")),
        zhipu_api_key=_mask(data.get("zhipu_api_key", "")),
    )


@router.put("/settings", response_model=SettingsOut)
async def update_settings(body: SettingsUpdate):
    API_KEY_FIELDS = {
        'google_api_key', 'openai_api_key', 'anthropic_api_key',
        'deepseek_api_key', 'zhipu_api_key',
    }
    updates = {}
    for k, v in body.model_dump().items():
        if v is None:
            continue
        # Skip empty or masked API keys — don't overwrite stored secrets
        if k in API_KEY_FIELDS and (not v or '****' in v):
            continue
        updates[k] = v
    settings_update(updates)
    return await get_settings()
