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


import asyncio
import click
import os
import logging
import time
import queue
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.spinner import Spinner
from rich.align import Align
from ..tools import DeviceManager, Tools, load_tools # Import the loader
from ..agent.droidagent import DroidAgent
from ..agent.utils.llm_picker import load_llm
from functools import wraps
# Import the install_app function directly for the setup command
console = Console()
device_manager = DeviceManager()

# Custom queue for log messages
log_queue = queue.Queue()
# Store the current step for display
current_step = "Initializing..."
# Global spinner for animation
spinner = Spinner("dots")

class RichHandler(logging.Handler):
    def emit(self, record):
        log_record = self.format(record)
        # Add log to our queue for the live display to process
        log_queue.put(log_record)

def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper

def create_layout():
    """Create a layout with logs at top and status at bottom"""
    layout = Layout()
    layout.split(
        Layout(name="logs"),  # Fixed size in lines for logs
        Layout(name="goal", size=3),   # Goal display box
        Layout(name="status", size=3)   # Status size at 3 lines
    )
    return layout

def update_layout(layout, log_list, step_message, current_time, goal=None):
    """Update the layout with current logs and step information"""
    from rich.console import Group
    
    # Maximum number of the *most recent* log lines to actually render in the panel.
    max_visible_log_lines = 50 # For example, always show the latest 50 logs.
    
    # Get the most recent logs, limited by max_visible_log_lines, for display.
    # Always show the most recent logs by taking the last 'max_visible_log_lines' items
    visible_logs = log_list[-max_visible_log_lines:] if len(log_list) > max_visible_log_lines else log_list
    
    # Create Text objects only for the logs we intend to display.
    log_texts = [Text(log) for log in visible_logs]
    log_group = Group(*log_texts) # This group is at most max_visible_log_lines tall.
    
    # Align this smaller group to the bottom-left of the panel to ensure newest logs are visible
    aligned_log_content = Align(log_group, vertical="bottom", align="left")
    
    # Update logs panel
    layout["logs"].update(Panel(
        aligned_log_content,
        title=f"Logs ({len(log_list)} total, showing last {len(visible_logs)})", 
        border_style="blue",
        title_align="left",
        padding=(0, 1), # Reduced vertical padding (top/bottom)
    ))
    
    # Update goal panel if goal is provided
    if goal:
        goal_text = Text(goal, style="bold")
        layout["goal"].update(Panel(
            Align(goal_text, vertical="middle", align="center"),
            title="Goal", 
            border_style="magenta",
            title_align="left",
            padding=(0, 1)
        ))
    
    # Create status panel with spinner
    global spinner
    # Create a Text object first, then add spinner text
    step_display = Text()
    step_display.append(spinner.render(current_time))  # Use current time for animation
    step_display.append(" ")
    step_display.append(step_message)
    
    layout["status"].update(Panel(
        step_display, 
        title="Current Action", 
        border_style="green",
        title_align="left",
        padding=(0, 1) # Reduced vertical padding
    ))

# Define the run command as a standalone function to be used as both a command and default
@coro
async def run_command(command: str, device: str | None, provider: str, model: str, steps: int, vision: bool, base_url: str, reasoning: bool, tracing: bool, debug: bool, **kwargs):
    """Run a command on your Android device using natural language."""
    # Configure logging based on debug flag
    configure_logging(debug)
    
    global current_step
    current_step = "Initializing..."
    logs = []
    
    # Create live display
    layout = create_layout()
    
    with Live(layout, refresh_per_second=10, console=console) as live:
        def update_display():
            # Update the layout with current logs and status
            current_time = time.time()  # Get current time for spinner animation
            update_layout(layout, logs, current_step, current_time, goal=command)  # Pass current time and goal
            live.refresh()
        
        try:
            update_display()
            logs.append(f"Executing command: {command}")
            
            if not kwargs.get("temperature"):
                kwargs["temperature"] = 0
                
            # Setting up tools for the agent using the loader
            current_step = "Setting up tools..."
            update_display()
            
            # Pass the 'device' argument from the CLI options to load_tools
            tool_list, tools_instance = await load_tools(serial=device, vision=vision)

            if debug:
                logs.append(f"Tools: {list(tool_list.keys())}")
                update_display()
                
            # Get the actual serial used (either provided or auto-detected)
            device_serial = tools_instance.serial
            logs.append(f"Using device: {device_serial}")
            update_display()

            # Set the device serial in the environment variable (optional, depends if needed elsewhere)
            os.environ["DROIDRUN_DEVICE_SERIAL"] = device_serial
            
            # Create LLM reasoner
            current_step = "Initializing LLM..."
            update_display()
            
            llm = load_llm(provider_name=provider, model=model, base_url=base_url, **kwargs)

            # Create and run the DroidAgent (wrapper for CodeActAgent and PlannerAgent)
            current_step = "Initializing DroidAgent..."
            update_display()
            
            # Log the reasoning mode
            if reasoning:
                logs.append("Using planning mode with reasoning")
            else:
                logs.append("Using direct execution mode without planning")
                
            # Log tracing status
            if tracing:
                logs.append("Arize Phoenix tracing enabled")
            
            update_display()
            
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
                enable_tracing=tracing,
                debug=debug
            )
            
            logs.append("Press Ctrl+C to stop execution")
            current_step = "Running agent..."
            update_display()

            try:
                # Start log processor task
                async def process_logs():
                    global current_step
                    while True:
                        # Check if there are new logs that contain "Executing task"
                        while not log_queue.empty():
                            try:
                                log = log_queue.get_nowait()
                                logs.append(log)
                                # If this is an "Executing task" message, update the current_step
                                if "🔧 Executing task:" in log:
                                    # Extract the task description
                                    task_desc = log.split("🔧 Executing task:", 1)[1].strip()
                                    
                                    # Extract only the "Goal" part if it exists
                                    if "Goal:" in task_desc:
                                        goal_part = task_desc.split("Goal:", 1)[1].strip()
                                        current_step = f"Executing: {goal_part}"
                                    else:
                                        # If no "Goal:" pattern, just use the full description
                                        current_step = f"Executing: {task_desc}"
                            except queue.Empty:
                                break
                        update_display()
                        await asyncio.sleep(0.1)
                
                # Run both the agent and log processor concurrently
                log_task = asyncio.create_task(process_logs())
                result = None
                try:
                    result = await droid_agent.run()
                    
                    # Set completion status but keep spinner active for a moment
                    if result.get("success", False):
                        success_str = f"✅ Goal completed: {result.get('reason', 'Success')}"
                        logs.append(success_str)
                        current_step = f"✅ {result.get('reason', 'Success')}"
                    else:
                        err_str = f"❌ Execution failed: {result.get('reason', 'Unknown reason')}"
                        logs.append(err_str)
                        current_step = f"❌ {result.get('reason', 'Unknown reason')}"
                    
                    # Continue updating for a moment to show final state with animation
                    await asyncio.sleep(2)
                finally:
                    # Make sure we cancel the log processing task
                    log_task.cancel()
                    try:
                        await log_task
                    except asyncio.CancelledError:
                        pass
                    
                    # Final display update with a static indicator instead of spinner
                    if result and result.get("success", False):
                        # Create success indicator
                        step_display = Text()
                        step_display.append("✓ ", style="bold green")
                        step_display.append(current_step)
                        
                        layout["status"].update(Panel(
                            step_display, 
                            title="Completed Successfully", 
                            border_style="green",
                            title_align="left",
                            padding=(0, 1)
                        ))
                    else:
                        # Create failure indicator
                        step_display = Text()
                        step_display.append("✗ ", style="bold red")
                        step_display.append(current_step)
                        
                        layout["status"].update(Panel(
                            step_display, 
                            title="Failed", 
                            border_style="red",
                            title_align="left",
                            padding=(0, 1)
                        ))
                    
                    live.refresh()
                    # One more pause to show the final state
                    await asyncio.sleep(1)

            except KeyboardInterrupt:
                logs.append("Execution stopped by user.")
                current_step = "Stopped by user"
                
                # Show stopped indicator
                step_display = Text()
                step_display.append("⚠ ", style="bold yellow")
                step_display.append(current_step)
                
                layout["status"].update(Panel(
                    step_display, 
                    title="Execution Stopped", 
                    border_style="yellow",
                    title_align="left",
                    padding=(0, 1)
                ))
                
            except ValueError as e:
                logs.append(f"Configuration Error: {e}")
                current_step = f"Error: {e}"
                
                # Show error indicator
                step_display = Text()
                step_display.append("⚠ ", style="bold red")
                step_display.append(current_step)
                
                layout["status"].update(Panel(
                    step_display, 
                    title="Error", 
                    border_style="red",
                    title_align="left",
                    padding=(0, 1)
                ))
                
            except Exception as e:
                logs.append(f"An unexpected error occurred during agent execution: {e}")
                current_step = f"Error: {e}"
                # Consider adding traceback logging here for debugging
                if debug:
                    import traceback
                    logs.append(traceback.format_exc())
                
                # Show error indicator
                step_display = Text()
                step_display.append("⚠ ", style="bold red")
                step_display.append(current_step)
                
                layout["status"].update(Panel(
                    step_display, 
                    title="Error", 
                    border_style="red",
                    title_align="left",
                    padding=(0, 1)
                ))
            
            update_display()
            # Final pause to show the completion status
            await asyncio.sleep(1)

        except ValueError as e: # Catch ValueError from load_tools (no device found)
            logs.append(f"Error: {e}")
            current_step = f"Error: {e}"
            
            # Show error indicator
            step_display = Text()
            step_display.append("⚠ ", style="bold red")
            step_display.append(current_step)
            
            layout["status"].update(Panel(
                step_display, 
                title="Error", 
                border_style="red",
                title_align="left",
                padding=(0, 1)
            ))
            update_display()
            
        except Exception as e:
            logs.append(f"An unexpected error occurred during setup: {e}")
            current_step = f"Error: {e}"
            # Consider adding traceback logging here for debugging
            if debug:
                import traceback
                logs.append(traceback.format_exc())
                
            # Show error indicator
            step_display = Text()
            step_display.append("⚠ ", style="bold red")
            step_display.append(current_step)
            
            layout["status"].update(Panel(
                step_display, 
                title="Error", 
                border_style="red",
                title_align="left",
                padding=(0, 1)
            ))
            update_display()
            await asyncio.sleep(1)

def configure_logging(debug: bool):
    """Configure logging verbosity based on debug flag."""
    root_logger = logging.getLogger()
    droidrun_logger = logging.getLogger("droidrun")
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    for handler in droidrun_logger.handlers[:]:
        droidrun_logger.removeHandler(handler)
    
    # Create a Rich handler that will put logs in our queue
    rich_handler = RichHandler()
    
    # Set format
    formatter = logging.Formatter('%(message)s')  # Simpler format for the panel
    rich_handler.setFormatter(formatter)
    
    # Set log levels based on debug flag
    if debug:
        rich_handler.setLevel(logging.DEBUG)
        droidrun_logger.setLevel(logging.DEBUG)
        root_logger.setLevel(logging.INFO)
    else:
        # In normal mode, still show INFO level logs for droidrun logger
        rich_handler.setLevel(logging.INFO)
        droidrun_logger.setLevel(logging.INFO)
        root_logger.setLevel(logging.WARNING)
    
    # Add the handler
    droidrun_logger.addHandler(rich_handler)
    
    # Capture the initialization message in our queue instead of printing directly
    log_queue.put(f"Logging level set to: {logging.getLevelName(droidrun_logger.level)}")


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
@click.option('--provider', '-p', help='LLM provider (openai, ollama, anthropic, gemini, deepseek)', default='Gemini')
@click.option('--model', '-m', help='LLM model name', default="models/gemini-2.5-pro-preview-05-06")
@click.option('--temperature', type=float, help='Temperature for LLM', default=0.2)
@click.option('--steps', type=int, help='Maximum number of steps', default=15)
@click.option('--vision', is_flag=True, help='Enable vision capabilities', default=True)
@click.option('--base_url', '-u', help='Base URL for API (e.g., OpenRouter or Ollama)', default=None)
@click.option('--reasoning/--no-reasoning', is_flag=True, help='Enable/disable planning with reasoning', default=False)
@click.option('--tracing', is_flag=True, help='Enable Arize Phoenix tracing', default=False)
@click.option('--debug', is_flag=True, help='Enable verbose debug logging', default=False)
def run(command: str, device: str | None, provider: str, model: str, steps: int, vision: bool, base_url: str, temperature: float, reasoning: bool, tracing: bool, debug: bool):
    """Run a command on your Android device using natural language."""
    # Call our standalone function
    return run_command(command, device, provider, model, steps, vision, base_url, reasoning, tracing, debug, temperature=temperature)

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