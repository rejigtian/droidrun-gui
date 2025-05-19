"""
DroidRun CLI - Command line interface for controlling Android devices through LLM agents.
"""
if __name__ == "__main__":
    import sys
    import os
    # Calculate the path to the project root directory (the one containing the 'droidrun' folder)
    _project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    # Add the project root to the beginning of sys.path
    sys.path.insert(0, _project_root)
    # Manually set the package context so relative imports work
    __package__ = "droidrun.cli" # Set this based on the script's location within the package


try:
    from . import patch_apis # patch to use multiple api keys
except Exception as e:
    pass

import asyncio
import click
import os
from rich.console import Console
from ..tools import DeviceManager, Tools, load_tools # Import the loader
from ..agent.droidagent import DroidAgent
from ..agent.utils.llm_picker import load_llm
from functools import wraps
# Import the install_app function directly for the setup command
console = Console()
device_manager = DeviceManager()

def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper

# Define the run command as a standalone function to be used as both a command and default
@coro
async def run_command(command: str, device: str | None, provider: str, model: str, steps: int, vision: bool, base_url: str, reasoning: bool, tracing: bool, **kwargs):
    """Run a command on your Android device using natural language."""
    console.print(f"[bold blue]Executing command:[/] {command}")

    if not kwargs.get("temperature"):
        kwargs["temperature"] = 0
    try:
        # Setting up tools for the agent using the loader
        console.print("[bold blue]Setting up tools...[/]")
        # Pass the 'device' argument from the CLI options to load_tools
        tool_list, tools_instance = await load_tools(serial=device, vision=vision)

        console.print(f"[blue] tools:{tool_list}")
        # Get the actual serial used (either provided or auto-detected)
        device_serial = tools_instance.serial
        console.print(f"[blue]Using device:[/] {device_serial}")


        # Set the device serial in the environment variable (optional, depends if needed elsewhere)
        os.environ["DROIDRUN_DEVICE_SERIAL"] = device_serial
        console.print(f"[blue]Set DROIDRUN_DEVICE_SERIAL to:[/] {device_serial}")

        # Create LLM reasoner
        console.print("[bold blue]Initializing LLM...[/]")
        llm = load_llm(provider_name=provider, model=model, base_url=base_url, **kwargs)

        # Create and run the DroidAgent (wrapper for CodeActAgent and PlannerAgent)
        console.print("[bold blue]Initializing DroidAgent...[/]")
        
        # Log the reasoning mode
        if reasoning:
            console.print("[blue]Using planning mode with reasoning[/]")
        else:
            console.print("[blue]Using direct execution mode without planning[/]")
            
        # Log tracing status
        if tracing:
            console.print("[blue]Arize Phoenix tracing enabled[/]")
        
        droid_agent = DroidAgent(
            goal=command,
            llm=llm,
            tools_instance=tools_instance,
            tool_list=tool_list,
            max_steps=steps,
            vision=vision,
            timeout=1000,
            max_retries=3,
            reasoning=reasoning,
            enable_tracing=tracing
        )
        
        console.print("[yellow]Press Ctrl+C to stop execution[/]")

        try:
            await droid_agent.run()
        except KeyboardInterrupt:
            console.print("\n[bold red]Execution stopped by user.[/]")
        except ValueError as e:
            console.print(f"[bold red]Configuration Error:[/] {e}")
        except Exception as e:
            console.print(f"[bold red]An unexpected error occurred during agent execution:[/] {e}")
            # Consider adding traceback logging here for debugging
            # import traceback
            # console.print(traceback.format_exc())


    except ValueError as e: # Catch ValueError from load_tools (no device found)
        console.print(f"[bold red]Error:[/] {e}")
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred during setup:[/] {e}")
        # Consider adding traceback logging here for debugging
        import traceback
        console.print(traceback.format_exc())



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
@click.option('--provider', '-p', help='LLM provider (openai, ollama, anthropic, gemini,deepseek)', default='Gemini')
@click.option('--model', '-m', help='LLM model name', default="models/gemini-2.5-pro-preview-05-06")
@click.option('--temperature', type=float, help='Temperature for LLM', default=0.2)
@click.option('--steps', type=int, help='Maximum number of steps', default=15)
@click.option('--vision', is_flag=True, help='Enable vision capabilities', default=True)
@click.option('--base_url', '-u', help='Base URL for API (e.g., OpenRouter or Ollama)', default=None)
@click.option('--reasoning/--no-reasoning', is_flag=True, help='Enable/disable planning with reasoning', default=False)
@click.option('--tracing', is_flag=True, help='Enable Arize Phoenix tracing', default=False)
def run(command: str, device: str | None, provider: str, model: str, steps: int, vision: bool, base_url: str, temperature: float, reasoning: bool, tracing: bool):
    """Run a command on your Android device using natural language."""
    # Call our standalone function
    return run_command(command, device, provider, model, steps, vision, base_url, reasoning, tracing, temperature=temperature)

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

@cli.command()
@click.option('--path', required=True, help='Path to the APK file to install')
@click.option('--device', '-d', help='Device serial number or IP address', default=None)
@coro
async def setup(path: str, device: str | None):
    """Install an APK file and enable it as an accessibility service."""
    try:
        # Check if APK file exists
        if not os.path.exists(path):
            console.print(f"[bold red]Error:[/] APK file not found at {path}")
            return
            
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
        
        # Get a device object for ADB commands
        device_obj = await device_manager.get_device(device)
        if not device_obj:
            console.print(f"[bold red]Error:[/] Could not get device object for {device}")
            return
        tools = Tools(serial=device)
        # Step 1: Install the APK file
        console.print(f"[bold blue]Step 1/2: Installing APK:[/] {path}")
        result = await tools.install_app(path, False, True)
        
        if "Error" in result:
            console.print(f"[bold red]Installation failed:[/] {result}")
            return
        else:
            console.print(f"[bold green]Installation successful![/]")
        
        # Step 2: Enable the accessibility service with the specific command
        console.print(f"[bold blue]Step 2/2: Enabling accessibility service[/]")
        
        # Package name for reference in error message
        package = "com.droidrun.portal"
        
        try:
            # Use the exact command provided
            await device_obj._adb.shell(device, "settings put secure enabled_accessibility_services com.droidrun.portal/com.droidrun.portal.DroidrunPortalService")
            
            # Also enable accessibility services globally
            await device_obj._adb.shell(device, "settings put secure accessibility_enabled 1")
            
            console.print("[green]Accessibility service enabled successfully![/]")
            console.print("\n[bold green]Setup complete![/] The DroidRun Portal is now installed and ready to use.")
            
        except Exception as e:
            console.print(f"[yellow]Could not automatically enable accessibility service: {e}[/]")
            console.print("[yellow]Opening accessibility settings for manual configuration...[/]")
            
            # Fallback: Open the accessibility settings page
            await device_obj._adb.shell(device, "am start -a android.settings.ACCESSIBILITY_SETTINGS")
            
            console.print("\n[yellow]Please complete the following steps on your device:[/]")
            console.print(f"1. Find [bold]{package}[/] in the accessibility services list")
            console.print("2. Tap on the service name")
            console.print("3. Toggle the switch to [bold]ON[/] to enable the service")
            console.print("4. Accept any permission dialogs that appear")
            
            console.print("\n[bold green]APK installation complete![/] Please manually enable the accessibility service using the steps above.")
            
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        import traceback
        traceback.print_exc()