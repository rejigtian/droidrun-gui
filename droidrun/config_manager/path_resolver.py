"""
Unified path resolution for DroidRun.

This module provides a single path resolver that handles all file path resolution
with consistent priority: working directory first, then project directory.
"""

from pathlib import Path
from typing import Union


class PathResolver:
    """
    Unified path resolver for all DroidRun file operations.

    Resolution order:
    1. Absolute paths → use as-is
    2. Relative paths → check working dir first, then project dir
    3. For creation → prefer working dir
    """

    @staticmethod
    def get_project_root() -> Path:
        """
        Get the project root directory (where config.yaml lives).

        This is 2 parents up from this file's location:
        droidrun/config_manager/path_resolver.py -> droidrun/ (project root)
        """
        return Path(__file__).resolve().parents[2]

    @staticmethod
    def resolve(
        path: Union[str, Path],
        create_if_missing: bool = False,
        must_exist: bool = False
    ) -> Path:
        """
        Universal path resolver for all file operations.

        Resolution order:
        1. Absolute path → use as-is
        2. Relative path:
           - If creating: prefer working directory
           - If reading: check working dir first, then project dir
        3. If must_exist and not found → raise FileNotFoundError

        Args:
            path: Path to resolve (str or Path object)
            create_if_missing: If True, prefer working dir for relative paths (output mode)
            must_exist: If True, raise FileNotFoundError if path doesn't exist

        Returns:
            Resolved Path object

        Raises:
            FileNotFoundError: If must_exist=True and path not found in any location

        Examples:
            # Reading config (checks CWD first, then project dir)
            config_path = PathResolver.resolve("config.yaml")

            # Creating output (creates in CWD)
            output_dir = PathResolver.resolve("trajectories", create_if_missing=True)

            # Loading prompts (must exist, checks both locations)
            prompt = PathResolver.resolve("config/prompts/system.md", must_exist=True)

            # Absolute path (used as-is)
            abs_path = PathResolver.resolve("/tmp/output")
        """
        # Convert to Path and expand user home directory (~/)
        path = Path(path).expanduser()

        # Absolute paths: use as-is
        if path.is_absolute():
            if must_exist and not path.exists():
                raise FileNotFoundError(f"Path not found: {path}")
            return path

        # Relative paths: check working dir and project dir
        cwd_path = Path.cwd() / path
        project_path = PathResolver.get_project_root() / path

        # For creation, always prefer working directory (user's context)
        if create_if_missing:
            return cwd_path

        # For reading, check both locations (working dir first)
        if cwd_path.exists():
            return cwd_path
        if project_path.exists():
            return project_path

        # Not found in either location
        if must_exist:
            raise FileNotFoundError(
                f"Path not found in:\n"
                f"  - Working dir: {cwd_path}\n"
                f"  - Project dir: {project_path}"
            )

        # Default to working dir (user's context)
        return cwd_path
