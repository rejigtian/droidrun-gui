"""
App card loading utility for package-specific prompts.

Supports flexible file path resolution and caches loaded content.
"""

import json
from pathlib import Path
from typing import Dict, Optional

from droidrun.config_manager.path_resolver import PathResolver


class AppCardLoader:
    """Load app cards based on package names with content caching."""

    _mapping_cache: Optional[Dict[str, str]] = None
    _cache_dir: Optional[str] = None
    _content_cache: Dict[str, str] = {}

    @staticmethod
    def load_app_card(
        package_name: str, app_cards_dir: str = "config/app_cards"
    ) -> str:
        """
        Load app card for a package name.

        Path resolution:
        - Checks working directory first (for user overrides)
        - Falls back to project directory (for default cards)
        - Supports absolute paths (used as-is)

        File loading from app_cards.json:
        1. Relative to app_cards_dir (most common):
           {"com.google.gm": "gmail.md"}
           → {app_cards_dir}/gmail.md

        2. Relative path (checks working dir, then project dir):
           {"com.google.gm": "config/custom_cards/gmail.md"}

        3. Absolute path:
           {"com.google.gm": "/usr/share/droidrun/cards/gmail.md"}

        Args:
            package_name: Android package name (e.g., "com.google.android.gm")
            app_cards_dir: Directory path (relative or absolute)

        Returns:
            App card content or empty string if not found
        """
        if not package_name:
            return ""

        # Check content cache first (key: package_name:app_cards_dir)
        cache_key = f"{package_name}:{app_cards_dir}"
        if cache_key in AppCardLoader._content_cache:
            return AppCardLoader._content_cache[cache_key]

        # Load mapping (with cache)
        mapping = AppCardLoader._load_mapping(app_cards_dir)

        # Get file path from mapping
        if package_name not in mapping:
            # Cache the empty result to avoid repeated lookups
            AppCardLoader._content_cache[cache_key] = ""
            return ""

        file_path_str = mapping[package_name]
        file_path = Path(file_path_str)

        # Determine resolution strategy
        if file_path.is_absolute():
            # Absolute path: use as-is
            app_card_path = file_path
        elif file_path_str.startswith(("config/", "prompts/", "docs/")):
            # Project-relative path: resolve with unified resolver
            app_card_path = PathResolver.resolve(file_path_str)
        else:
            # App_cards-relative: resolve dir first, then append filename
            cards_dir_resolved = PathResolver.resolve(app_cards_dir)
            app_card_path = cards_dir_resolved / file_path_str

        # Read file
        try:
            if not app_card_path.exists():
                # Cache the empty result
                AppCardLoader._content_cache[cache_key] = ""
                return ""

            content = app_card_path.read_text(encoding="utf-8")
            # Cache the content
            AppCardLoader._content_cache[cache_key] = content
            return content
        except Exception:
            # Cache the empty result on error
            AppCardLoader._content_cache[cache_key] = ""
            return ""

    @staticmethod
    def _load_mapping(app_cards_dir: str) -> Dict[str, str]:
        """Load and cache the app_cards.json mapping."""
        # Cache invalidation: if dir changed, reload
        if (
            AppCardLoader._mapping_cache is not None
            and AppCardLoader._cache_dir == app_cards_dir
        ):
            return AppCardLoader._mapping_cache

        # Resolve app cards directory
        cards_dir_resolved = PathResolver.resolve(app_cards_dir)
        mapping_path = cards_dir_resolved / "app_cards.json"

        try:
            if not mapping_path.exists():
                AppCardLoader._mapping_cache = {}
                AppCardLoader._cache_dir = app_cards_dir
                return {}

            with open(mapping_path, "r", encoding="utf-8") as f:
                mapping = json.load(f)

            AppCardLoader._mapping_cache = mapping
            AppCardLoader._cache_dir = app_cards_dir
            return mapping
        except Exception:
            AppCardLoader._mapping_cache = {}
            AppCardLoader._cache_dir = app_cards_dir
            return {}

    @staticmethod
    def clear_cache() -> None:
        """Clear all caches (useful for testing or runtime reloading)."""
        AppCardLoader._mapping_cache = None
        AppCardLoader._cache_dir = None
        AppCardLoader._content_cache.clear()

    @staticmethod
    def get_cache_stats() -> Dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats (useful for debugging)
        """
        return {
            "mapping_cached": 1 if AppCardLoader._mapping_cache is not None else 0,
            "content_entries": len(AppCardLoader._content_cache),
        }
