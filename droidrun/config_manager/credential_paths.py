from __future__ import annotations

from pathlib import Path

import platformdirs

APP_NAME = "droidrun"
USER_CONFIG_DIR = Path(platformdirs.user_config_dir(APP_NAME))
OAUTH_CREDENTIAL_DIR = USER_CONFIG_DIR / "credentials"

OPENAI_OAUTH_CREDENTIAL_PATH = OAUTH_CREDENTIAL_DIR / "openai_oauth.json"
ANTHROPIC_OAUTH_CREDENTIAL_PATH = OAUTH_CREDENTIAL_DIR / "anthropic_oauth.json"
GEMINI_OAUTH_CREDENTIAL_PATH = OAUTH_CREDENTIAL_DIR / "gemini_oauth.json"
API_KEY_ENV_FILE = OAUTH_CREDENTIAL_DIR / "api_keys.env"
