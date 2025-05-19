import json
from pathlib import Path

class APIKeyManager:
    def __init__(self):
        self.key_file = Path.home() / ".droidrun-gui" / "apikeys.json"
        self.key_file.parent.mkdir(exist_ok=True)
        self.keys = self._load_keys()

    def _load_keys(self):
        if self.key_file.exists():
            with open(self.key_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_keys(self):
        with open(self.key_file, 'w', encoding='utf-8') as f:
            json.dump(self.keys, f, ensure_ascii=False, indent=2)

    def get_key(self, provider):
        return self.keys.get(provider.upper())

    def set_key(self, provider, key):
        self.keys[provider.upper()] = key
        self.save_keys()

    def all_keys(self):
        return self.keys.copy() 