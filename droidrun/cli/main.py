"""
DroidRun CLI - Command line interface for controlling Android devices through LLM agents.
"""
if __name__ == "__main__":
    import sys
    import os
    _project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    sys.path.insert(0, _project_root)
    __package__ = "droidrun.cli"


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
from ..tools import DeviceManager, Tools, load_tools
from ..agent.droid import DroidAgent
from ..agent.utils.llm_picker import load_llm
from functools import wraps
console = Console()
device_manager = DeviceManager()

log_queue = queue.Queue()
current_step = "Initializing..."
spinner = Spinner("dots")

class RichHandler(logging.Handler):
    def emit(self, record):
        log_record = self.format(record)
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
        Layout(name="logs"),
        Layout(name="goal", size=3),
        Layout(name="status", size=3)
    )
    return layout

def update_layout(layout, log_list, step_message, current_time, goal=None, completed=False, success=None):
    """Update the layout with current logs and step information"""
    from rich.text import Text
    import shutil
    
    terminal_height = shutil.get_terminal_size().lines
    other_components_height = 3 + 3 + 4 + 1 + 4
    available_log_lines = max(5, terminal_height - other_components_height)
    
    visible_logs = log_list[-available_log_lines:] if len(log_list) > available_log_lines else log_list
    
    log_content = "\n".join(visible_logs)
    
    layout["logs"].update(Panel(
        log_content,
        title=f"Logs (showing {len(visible_logs)} most recent of {len(log_list)} total)", 
        border_style="blue",
        title_align="left",
        padding=(0, 1),
    ))
    
    if goal:
        goal_text = Text(goal, style="bold")
        layout["goal"].update(Panel(
            goal_text,
            title="Goal", 
            border_style="magenta",
            title_align="left",
            padding=(0, 1)
        ))
    
    step_display = Text()
    
    if completed:
        if success:
            step_display.append("✓  ", style="bold green")
            panel_title = "Completed Successfully"
            panel_style = "green"
        else:
            step_display.append("✗  ", style="bold red")
            panel_title = "Failed"
            panel_style = "red"
    else:
        step_display.append(spinner.render(current_time))
        step_display.append(" ")
        panel_title = "Current Action"
        panel_style = "green"
    
    step_display.append(step_message)
    
    layout["status"].update(Panel(
        step_display, 
        title=panel_title, 
        border_style=panel_style,
        title_align="left",
        padding=(0, 1)
    ))

@coro
async def run_command(command: str, device: str | None, provider: str, model: str, steps: int, base_url: str, reasoning: bool, tracing: bool, debug: bool, **kwargs):
    """Run a command on your Android device using natural language."""
    configure_logging(debug)
    
    global current_step
    current_step = "Initializing..."
    logs = []
    max_log_history = 1000
    is_completed = False
    is_success = None
    
    layout = create_layout()
    
    with Live(layout, refresh_per_second=20, console=console) as live:
        def update_display():
            current_time = time.time()
            update_layout(
                layout, 
                logs, 
                current_step, 
                current_time, 
                goal=command, 
                completed=is_completed,
                success=is_success
            )
            live.refresh()
        
        def process_new_logs():
            log_count = 0
            while not log_queue.empty():
                try:
                    log = log_queue.get_nowait()
                    logs.append(log)
                    log_count += 1
                    if len(logs) > max_log_history:
                        logs.pop(0)
                except queue.Empty:
                    break
            return log_count > 0
        
        async def process_logs():
            global current_step
            iteration = 0
            while True:
                if is_completed:
                    process_new_logs()
                    if iteration % 10 == 0:
                        update_display()
                    iteration += 1
                    await asyncio.sleep(0.1)
                    continue
                
                new_logs_added = process_new_logs()
                
                # Improve detection of the latest action from logs
                latest_task = None
                for log in reversed(logs[-50:]):  # Search from most recent logs first
                    if "🔧 Executing task:" in log:
                        task_desc = log.split("🔧 Executing task:", 1)[1].strip()
                        
                        if "Goal:" in task_desc:
                            goal_part = task_desc.split("Goal:", 1)[1].strip()
                            latest_task = goal_part
                        else:
                            latest_task = task_desc
                        break  # Stop at the most recent task
                        
                if latest_task:
                    current_step = f"Executing: {latest_task}"
                
                if new_logs_added or iteration % 5 == 0:
                    update_layout(
                        layout, 
                        logs, 
                        current_step, 
                        time.time(), 
                        goal=command, 
                        completed=is_completed,
                        success=is_success
                    )
                
                iteration += 1
                await asyncio.sleep(0.05)
        
        try:
            update_display()
            logs.append(f"Executing command: {command}")
            
            if not kwargs.get("temperature"):
                kwargs["temperature"] = 0
                
            current_step = "Setting up tools..."
            update_display()
            
            tool_list, tools_instance = await load_tools(serial=device)

            if debug:
                logs.append(f"Tools: {list(tool_list.keys())}")
                update_display()
                
            device_serial = tools_instance.serial
            logs.append(f"Using device: {device_serial}")
            update_display()

            os.environ["DROIDRUN_DEVICE_SERIAL"] = device_serial
            
            current_step = "Initializing LLM..."
            update_display()
            
            llm = load_llm(provider_name=provider, model=model, base_url=base_url, **kwargs)

            current_step = "Initializing DroidAgent..."
            update_display()
            
            if reasoning:
                logs.append("Using planning mode with reasoning")
            else:
                logs.append("Using direct execution mode without planning")
                
            if tracing:
                logs.append("Arize Phoenix tracing enabled")
            
            update_display()
            
            droid_agent = DroidAgent(
                goal=command,
                llm=llm,
                tools_instance=tools_instance,
                tool_list=tool_list,
                max_steps=steps,
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
                log_task = asyncio.create_task(process_logs())
                result = None
                try:
                    result = await droid_agent.run()
                    
                    if result.get("success", False):
                        is_completed = True
                        is_success = True
                        
                        if result.get("output"):
                            success_output = f"🎯 FINAL ANSWER: {result.get('output')}"
                            logs.append(success_output)
                            current_step = f"{result.get('output')}"
                        else:
                            current_step = result.get("reason", "Success")
                    else:
                        is_completed = True
                        is_success = False
                        
                        current_step = result.get("reason", "Failed") if result else "Failed"
                    
                    update_layout(
                        layout, 
                        logs, 
                        current_step, 
                        time.time(), 
                        goal=command, 
                        completed=is_completed, 
                        success=is_success
                    )
                    
                    await asyncio.sleep(2)
                finally:
                    log_task.cancel()
                    try:
                        await log_task
                    except asyncio.CancelledError:
                        pass
                    
                    for _ in range(20):
                        process_new_logs()
                        await asyncio.sleep(0.05)
                    
                    update_layout(
                        layout, 
                        logs, 
                        current_step, 
                        time.time(), 
                        goal=command, 
                        completed=is_completed, 
                        success=is_success
                    )
                    
                    live.refresh()
                    
                    await asyncio.sleep(3)

            except KeyboardInterrupt:
                logs.append("Execution stopped by user.")
                current_step = "Stopped by user"
                
                is_completed = True
                is_success = False
                
                update_layout(
                    layout, 
                    logs, 
                    current_step, 
                    time.time(), 
                    goal=command, 
                    completed=is_completed, 
                    success=is_success
                )
                
            except ValueError as e:
                logs.append(f"Configuration Error: {e}")
                current_step = f"Error: {e}"
                
                is_completed = True
                is_success = False
                
                update_layout(
                    layout, 
                    logs, 
                    current_step, 
                    time.time(), 
                    goal=command, 
                    completed=is_completed, 
                    success=is_success
                )
                
            except Exception as e:
                logs.append(f"An unexpected error occurred during agent execution: {e}")
                current_step = f"Error: {e}"
                if debug:
                    import traceback
                    logs.append(traceback.format_exc())
                
                is_completed = True
                is_success = False
                
                update_layout(
                    layout, 
                    logs, 
                    current_step, 
                    time.time(), 
                    goal=command, 
                    completed=is_completed, 
                    success=is_success
                )
            
            update_display()
            await asyncio.sleep(1)

        except ValueError as e:
            logs.append(f"Error: {e}")
            current_step = f"Error: {e}"
            
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
            if debug:
                import traceback
                logs.append(traceback.format_exc())
                
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
    
    rich_handler = RichHandler()
    
    formatter = logging.Formatter('%(message)s') 
    rich_handler.setFormatter(formatter)
    
    if debug:
        rich_handler.setLevel(logging.DEBUG)
        droidrun_logger.setLevel(logging.DEBUG)
        root_logger.setLevel(logging.INFO)
    else:
        rich_handler.setLevel(logging.INFO)
        droidrun_logger.setLevel(logging.INFO)
        root_logger.setLevel(logging.WARNING)
    
    droidrun_logger.addHandler(rich_handler)
    
    log_queue.put(f"Logging level set to: {logging.getLevelName(droidrun_logger.level)}")


class DroidRunCLI(click.Group):
    def parse_args(self, ctx, args):
        if args and not args[0].startswith('-') and args[0] not in self.commands:
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
@click.option('--base_url', '-u', help='Base URL for API (e.g., OpenRouter or Ollama)', default=None)
@click.option('--reasoning/--no-reasoning', is_flag=True, help='Enable/disable planning with reasoning', default=False)
@click.option('--tracing', is_flag=True, help='Enable Arize Phoenix tracing', default=False)
@click.option('--debug', is_flag=True, help='Enable verbose debug logging', default=False)
def run(command: str, device: str | None, provider: str, model: str, steps: int, base_url: str, temperature: float, reasoning: bool, tracing: bool, debug: bool):
    """Run a command on your Android device using natural language."""
    # Call our standalone function
    return run_command(command, device, provider, model, steps, base_url, reasoning, tracing, debug, temperature=temperature)

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
        if not os.path.exists(path):
            console.print(f"[bold red]Error:[/] APK file not found at {path}")
            return
            
        if not device:
            devices = await device_manager.list_devices()
            if not devices:
                console.print("[yellow]No devices connected.[/]")
                return
            
            device = devices[0].serial
            console.print(f"[blue]Using device:[/] {device}")
        
        os.environ["DROIDRUN_DEVICE_SERIAL"] = device
        console.print(f"[blue]Set DROIDRUN_DEVICE_SERIAL to:[/] {device}")
        
        device_obj = await device_manager.get_device(device)
        if not device_obj:
            console.print(f"[bold red]Error:[/] Could not get device object for {device}")
            return
        tools = Tools(serial=device)
        console.print(f"[bold blue]Step 1/2: Installing APK:[/] {path}")
        result = await tools.install_app(path, False, True)
        
        if "Error" in result:
            console.print(f"[bold red]Installation failed:[/] {result}")
            return
        else:
            console.print(f"[bold green]Installation successful![/]")
        
        console.print(f"[bold blue]Step 2/2: Enabling accessibility service[/]")
        
        package = "com.droidrun.portal"
        
        try:
            await device_obj._adb.shell(device, "settings put secure enabled_accessibility_services com.droidrun.portal/com.droidrun.portal.DroidrunPortalService")
            
            await device_obj._adb.shell(device, "settings put secure accessibility_enabled 1")
            
            console.print("[green]Accessibility service enabled successfully![/]")
            console.print("\n[bold green]Setup complete![/] The DroidRun Portal is now installed and ready to use.")
            
        except Exception as e:
            console.print(f"[yellow]Could not automatically enable accessibility service: {e}[/]")
            console.print("[yellow]Opening accessibility settings for manual configuration...[/]")
            
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


if __name__ == "__main__":
    command = "Open the settings app"
    device = None
    provider = "GoogleGenAI"
    model = "models/gemini-2.5-flash-preview-05-20"
    temperature = 0
    api_key = os.getenv("GEMINI_API_KEY")
    steps = 15
    reasoning = True
    tracing = True
    debug = True
    base_url = None
    run_command(command=command, device=device, provider=provider, model=model, steps=steps, temperature=temperature, reasoning=reasoning, tracing=tracing, debug=debug, base_url=base_url, api_key=api_key)