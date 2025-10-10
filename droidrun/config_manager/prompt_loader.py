"""
Prompt loading utility for markdown-based prompts.

Supports variable substitution with escape sequences:
- {variable} → replaced with value
- {{variable}} → literal {variable}
- Missing variables → left as {variable}
"""

from pathlib import Path
from typing import Dict, Any
import re


class PromptLoader:
    """Load and format markdown prompts with variable substitution."""

    @staticmethod
    def get_project_root() -> Path:
        """Get project root directory (where config.yaml lives)."""
        # This file is at droidrun/config_manager/prompt_loader.py
        # Project root is 2 parents up
        return Path(__file__).resolve().parents[2]

    @staticmethod
    def load_prompt(path: str, variables: Dict[str, Any] = None) -> str:
        """
        Load prompt from .md file and substitute variables.

        Path is relative to project root. For example:
        - "config/prompts/codeact/system.md"

        Variable substitution:
        - {variable} → replaced with value from variables dict
        - {{variable}} → becomes literal {variable} in output
        - Missing variables → left as {variable} (no error)

        Args:
            path: Path relative to project root
            variables: Dict of variable names to values

        Returns:
            Formatted prompt string

        Raises:
            FileNotFoundError: If prompt file doesn't exist
        """
        # Resolve path from project root
        project_root = PromptLoader.get_project_root()
        prompt_path = project_root / path

        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Prompt file not found: {prompt_path}\n"
                f"(resolved from project root: {project_root})\n"
                f"(relative path: {path})"
            )

        prompt_text = prompt_path.read_text(encoding="utf-8")

        if variables is None:
            return prompt_text

        # Handle escaped braces: {{variable}} → {variable}
        # Strategy: Replace {{...}} with placeholder, do substitution, restore
        escaped_pattern = re.compile(r'\{\{([^}]+)\}\}')
        placeholders = {}
        counter = [0]

        def escape_replacer(match):
            placeholder = f"__ESCAPED_{counter[0]}__"
            placeholders[placeholder] = "{" + match.group(1) + "}"
            counter[0] += 1
            return placeholder

        prompt_text = escaped_pattern.sub(escape_replacer, prompt_text)

        # Substitute variables
        for key, value in variables.items():
            prompt_text = prompt_text.replace(f"{{{key}}}", str(value))

        # Restore escaped braces
        for placeholder, original in placeholders.items():
            prompt_text = prompt_text.replace(placeholder, original)

        return prompt_text
