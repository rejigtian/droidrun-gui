"""DroidRun Terminal User Interface."""

from droidrun.cli.tui.app import DroidrunTUI


def run_tui():
    """Run the DroidRun TUI application."""
    app = DroidrunTUI()
    app.run()


__all__ = ["DroidrunTUI", "run_tui"]
