"""
DroidRun CLI - Command line interface for controlling Android devices through LLM agents.
"""

import asyncio
import click
import os
from rich.console import Console
from rich import print as rprint
from droidrun.tools import DeviceManager
from droidrun.agent import run_agent
from functools import wraps

console = Console()
device_manager = DeviceManager()

def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper

# Define the run command as a standalone function to be used as both a command and default
@coro
async def run_command(command: str, device: str | None, provider: str, model: str, debug: bool, steps: int):
    """Run a command on your Android device using natural language."""
    console.print(f"[bold blue]Executing command:[/] {command}")
    
    # Auto-detect Gemini if model starts with "gemini-"
    if model and model.startswith("gemini-"):
        provider = "gemini"
    
    # Get API keys from environment variables
    api_key = None
    if provider.lower() == 'openai':
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            console.print("[bold red]Error:[/] OPENAI_API_KEY environment variable not set")
            return
        if not model:
            model = "gpt-4-turbo"
    elif provider.lower() == 'anthropic':
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            console.print("[bold red]Error:[/] ANTHROPIC_API_KEY environment variable not set")
            return
        if not model:
            model = "claude-3-sonnet-20240229"
    elif provider.lower() == 'gemini':
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            console.print("[bold red]Error:[/] GEMINI_API_KEY environment variable not set")
            return
        if not model:
            model = "gemini-2.0-flash"
    else:
        console.print(f"[bold red]Error:[/] Unsupported provider: {provider}")
        return
    
    try:
        # Try to find a device if none specified
        if not device:
            devices = await device_manager.list_devices()
            if not devices:
                console.print("[yellow]No devices connected.[/]")
                return
            
            device = devices[0].serial
            console.print(f"[blue]Using device:[/] {device}")
        
        # Set the device serial in the environment variable
        os.environ["DROIDRUN_DEVICE_SERIAL"] = device
        console.print(f"[blue]Set DROIDRUN_DEVICE_SERIAL to:[/] {device}")
        
        # Run the agent
        console.print("[bold blue]Running ReAct agent...[/]")
        console.print("[yellow]Press Ctrl+C to stop execution[/]")
        
        steps = await run_agent(
            task=command,
            device_serial=device,  # Still pass for backward compatibility
            llm_provider=provider,
            model_name=model,
            api_key=api_key,
            debug=debug
        )
        
        # Final message
        console.print(f"[bold green]Execution completed with {len(steps)} steps[/]")
        
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        if debug:
            import traceback
            traceback.print_exc()

# Custom Click multi-command class to handle both subcommands and default behavior
class DroidRunCLI(click.Group):
    def parse_args(self, ctx, args):
        # Check if the first argument might be a task rather than a command
        if args and not args[0].startswith('-') and args[0] not in self.commands:
            # Insert the 'run' command before the first argument if it's not a known command
            args.insert(0, 'run')
        return super().parse_args(ctx, args)

@click.group(cls=DroidRunCLI)
def cli():
    """DroidRun - Control your Android device through LLM agents."""
    pass

@cli.command()
@click.argument('command', type=str)
@click.option('--device', '-d', help='Device serial number or IP address', default=None)
@click.option('--provider', '-p', help='LLM provider (openai, anthropic, or gemini)', default='openai')
@click.option('--model', '-m', help='LLM model name', default=None)
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.option('--steps', type=int, help='Maximum number of steps', default=15)
def run(command: str, device: str | None, provider: str, model: str, debug: bool, steps: int):
    """Run a command on your Android device using natural language."""
    # Call our standalone function
    return run_command(command, device, provider, model, debug, steps)

@cli.command()
@coro
async def devices():
    """List connected Android devices."""
    try:
        devices = await device_manager.list_devices()
        if not devices:
            console.print("[yellow]No devices connected.[/]")
            return

        console.print(f"[green]Found {len(devices)} connected device(s):[/]")
        for device in devices:
            console.print(f"  • [bold]{device.serial}[/]")
    except Exception as e:
        console.print(f"[red]Error listing devices: {e}[/]")

@cli.command()
@click.argument('ip_address')
@click.option('--port', '-p', default=5555, help='ADB port (default: 5555)')
@coro
async def connect(ip_address: str, port: int):
    """Connect to a device over TCP/IP."""
    try:
        device = await device_manager.connect(ip_address, port)
        if device:
            console.print(f"[green]Successfully connected to {ip_address}:{port}[/]")
        else:
            console.print(f"[red]Failed to connect to {ip_address}:{port}[/]")
    except Exception as e:
        console.print(f"[red]Error connecting to device: {e}[/]")

@cli.command()
@click.argument('serial')
@coro
async def disconnect(serial: str):
    """Disconnect from a device."""
    try:
        success = await device_manager.disconnect(serial)
        if success:
            console.print(f"[green]Successfully disconnected from {serial}[/]")
        else:
            console.print(f"[yellow]Device {serial} was not connected[/]")
    except Exception as e:
        console.print(f"[red]Error disconnecting from device: {e}[/]")

if __name__ == '__main__':
    cli() 