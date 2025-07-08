"""
Command-line interface for DroidRun macro replay.
"""

import asyncio
import click
import logging
import os
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from droidrun.macro.replay import MacroPlayer, replay_macro_file, replay_macro_folder
from droidrun.agent.utils.trajectory import Trajectory

console = Console()


def setup_logging(debug: bool = False):
    """Setup logging for the macro CLI."""
    logger = logging.getLogger("droidrun-macro")
    handler = logging.StreamHandler()
    
    if debug:
        level = logging.DEBUG
        formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s", "%H:%M:%S")
    else:
        level = logging.INFO
        formatter = logging.Formatter("%(message)s")
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False


@click.group()
def macro_cli():
    """Replay recorded automation sequences."""
    pass


@macro_cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--device", "-d", help="Device serial number", default=None)
@click.option("--delay", "-t", help="Delay between actions (seconds)", default=1.0, type=float)
@click.option("--start-from", "-s", help="Start from step number (1-based)", default=1, type=int)
@click.option("--max-steps", "-m", help="Maximum steps to execute", default=None, type=int)
@click.option("--debug", is_flag=True, help="Enable debug logging", default=False)
@click.option("--dry-run", is_flag=True, help="Show actions without executing", default=False)
def replay(path: str, device: str, delay: float, start_from: int, max_steps: int, debug: bool, dry_run: bool):
    """Replay a macro from a file or trajectory folder."""
    setup_logging(debug)
    
    console.print(Panel(f"🎬 [bold green]DroidRun Macro Replay[/bold green]", expand=False))
    
    # Convert start_from from 1-based to 0-based
    start_from_zero = max(0, start_from - 1)
    
    asyncio.run(_replay_async(path, device, delay, start_from_zero, max_steps, dry_run))


async def _replay_async(path: str, device: str, delay: float, start_from: int, max_steps: int, dry_run: bool):
    """Async function to handle macro replay."""
    try:
        # Determine if path is a file or folder
        if os.path.isfile(path):
            console.print(f"📄 Loading macro from file: {path}")
            player = MacroPlayer(device_serial=device, delay_between_actions=delay)
            macro_data = player.load_macro_from_file(path)
        elif os.path.isdir(path):
            console.print(f"📁 Loading macro from folder: {path}")
            player = MacroPlayer(device_serial=device, delay_between_actions=delay)
            macro_data = player.load_macro_from_folder(path)
        else:
            console.print(f"❌ [red]Invalid path: {path}[/red]")
            return
        
        if not macro_data:
            console.print("❌ [red]Failed to load macro data[/red]")
            return
        
        # Show macro information
        description = macro_data.get("description", "No description")
        total_actions = macro_data.get("total_actions", 0)
        version = macro_data.get("version", "unknown")
        
        console.print(f"\n📋 [bold]Macro Information:[/bold]")
        console.print(f"   Description: {description}")
        console.print(f"   Version: {version}")
        console.print(f"   Total actions: {total_actions}")
        console.print(f"   Device: {device or 'Auto-detect'}")
        console.print(f"   Delay between actions: {delay}s")
        
        if start_from > 0:
            console.print(f"   Starting from step: {start_from + 1}")
        if max_steps:
            console.print(f"   Maximum steps: {max_steps}")
        
        if dry_run:
            console.print(f"\n🔍 [yellow]DRY RUN MODE - Actions will be shown but not executed[/yellow]")
            await _show_dry_run(macro_data, start_from, max_steps)
        else:
            success = await player.replay_macro(macro_data, start_from_step=start_from, max_steps=max_steps)
            
            if success:
                console.print(f"\n🎉 [green]Macro replay completed successfully![/green]")
            else:
                console.print(f"\n💥 [red]Macro replay completed with errors[/red]")
    
    except Exception as e:
        console.print(f"❌ [red]Error: {e}[/red]")


async def _show_dry_run(macro_data: dict, start_from: int, max_steps: int):
    """Show what actions would be executed in dry run mode."""
    actions = macro_data.get("actions", [])
    
    # Apply filters
    if start_from > 0:
        actions = actions[start_from:]
    if max_steps:
        actions = actions[:max_steps]
    
    table = Table(title="Actions to Execute")
    table.add_column("Step", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Details", style="white")
    table.add_column("Description", style="yellow")
    
    for i, action in enumerate(actions, start=start_from + 1):
        action_type = action.get("action_type", action.get("type", "unknown"))
        details = ""
        
        if action_type == "tap":
            x, y = action.get("x", 0), action.get("y", 0)
            element_text = action.get("element_text", "")
            details = f"({x}, {y}) - '{element_text}'"
        elif action_type == "swipe":
            start_x, start_y = action.get("start_x", 0), action.get("start_y", 0)
            end_x, end_y = action.get("end_x", 0), action.get("end_y", 0)
            details = f"({start_x}, {start_y}) → ({end_x}, {end_y})"
        elif action_type == "input_text":
            text = action.get("text", "")
            details = f"'{text}'"
        elif action_type == "key_press":
            key_name = action.get("key_name", "UNKNOWN")
            details = f"{key_name}"
        
        description = action.get("description", "")
        table.add_row(str(i), action_type, details, description[:50] + "..." if len(description) > 50 else description)
    
    console.print(table)


@macro_cli.command()
@click.argument("directory", type=click.Path(exists=True), default="trajectories")
def list(directory: str):
    """List available trajectory folders in a directory."""
    setup_logging(False)
    
    console.print(f"📁 Scanning directory: {directory}")
    
    try:
        folders = []
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isdir(item_path):
                macro_file = os.path.join(item_path, "macro.json")
                if os.path.exists(macro_file):
                    # Load macro info
                    try:
                        macro_data = Trajectory.load_macro_sequence(item_path)
                        description = macro_data.get("description", "No description")
                        total_actions = macro_data.get("total_actions", 0)
                        folders.append((item, description, total_actions))
                    except:
                        folders.append((item, "Error loading", 0))
        
        if not folders:
            console.print("📭 No trajectory folders found")
            return
        
        table = Table(title=f"Available Trajectories in {directory}")
        table.add_column("Folder", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Actions", style="green")
        
        for folder, description, actions in sorted(folders):
            table.add_row(folder, description[:80] + "..." if len(description) > 80 else description, str(actions))
        
        console.print(table)
        console.print(f"\n💡 Use 'droidrun-macro replay {directory}/<folder>' to replay a trajectory")
    
    except Exception as e:
        console.print(f"❌ [red]Error: {e}[/red]")


if __name__ == "__main__":
    macro_cli() 