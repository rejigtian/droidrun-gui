"""
Prompt loading utility for markdown-based prompts.

Supports variable substitution with escape sequences:
- {variable} → replaced with value
- {{variable}} → literal {variable}
- Missing variables → left as {variable}
"""

import re
from pathlib import Path
from typing import Any, Dict

from droidrun.config_manager.path_resolver import PathResolver


class PromptLoader:
    """Load and format markdown prompts with variable substitution."""

    @staticmethod
    def load_prompt(path: str, variables: Dict[str, Any] = None) -> str:
        """
        Load prompt from .md file and substitute variables.

        Path resolution:
        - Checks working directory first (for user overrides)
        - Falls back to project directory (for default prompts)
        - Example: "config/prompts/codeact/system.md"

        Variable substitution:
        - {variable} → replaced with value from variables dict
        - {{variable}} → becomes literal {variable} in output
        - Missing variables → left as {variable} (no error)

        Args:
            path: Path to prompt file (relative or absolute)
            variables: Dict of variable names to values

        Returns:
            Formatted prompt string

        Raises:
            FileNotFoundError: If prompt file doesn't exist
        """
        # Resolve path (checks working dir, then project dir)
        prompt_path = PathResolver.resolve(path, must_exist=True)

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
