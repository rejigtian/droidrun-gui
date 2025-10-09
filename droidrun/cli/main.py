"""
DroidRun CLI - Command line interface for controlling Android devices through LLM agents.
"""

import asyncio
import logging
import os
import warnings
from contextlib import nullcontext
from functools import wraps

import click
from adbutils import adb
from rich.console import Console

from droidrun.agent.context.personas import BIG_AGENT, DEFAULT
from droidrun.agent.droid import DroidAgent
from droidrun.agent.utils.llm_picker import load_llm
from droidrun.cli.logs import LogHandler
from droidrun.macro.cli import macro_cli
from droidrun.portal import (
    PORTAL_PACKAGE_NAME,
    download_portal_apk,
    enable_portal_accessibility,
    ping_portal,
    ping_portal_content,
    ping_portal_tcp,
)
from droidrun.telemetry import print_telemetry_message
from droidrun.tools import AdbTools, IOSTools
from droidrun.config_manager import config
from droidrun.config_manager.config_manager import VisionConfig

# Suppress all warnings
warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["GRPC_ENABLE_FORK_SUPPORT"] = "false"

console = Console()


def configure_logging(goal: str, debug: bool):
    logger = logging.getLogger("droidrun")
    logger.handlers = []

    handler = LogHandler(goal)
    handler.setFormatter(
        logging.Formatter("%(levelname)s %(name)s %(message)s", "%H:%M:%S")
        if debug
        else logging.Formatter("%(message)s", "%H:%M:%S")
    )
    logger.addHandler(handler)

    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.propagate = False

    if debug:
        tools_logger = logging.getLogger("droidrun-tools")
        tools_logger.addHandler(handler)
        tools_logger.propagate = False
        tools_logger.setLevel(logging.DEBUG if debug else logging.INFO)

    return handler


def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


@coro
async def run_command(
    command: str,
    device: str | None,
    provider: str | None,
    model: str | None,
    steps: int | None,
    base_url: str | None,
    api_base: str | None,
    vision: bool | None,
    manager_vision: bool | None,
    executor_vision: bool | None,
    codeact_vision: bool | None,
    reasoning: bool | None,
    tracing: bool | None,
    debug: bool | None,
    use_tcp: bool | None,
    save_trajectory: str | None = None,
    ios: bool = False,
    allow_drag: bool | None = None,
    temperature: float | None = None,
    **kwargs,
):
    """Run a command on your Android device using natural language."""
    # Initialize logging first (use config default if debug not specified)
    debug_mode = debug if debug is not None else config.logging.debug
    log_handler = configure_logging(command, debug_mode)
    logger = logging.getLogger("droidrun")

    log_handler.update_step("Initializing...")

    with log_handler.render():
        try:
            logger.info(f"🚀 Starting: {command}")
            print_telemetry_message()

            # ================================================================
            # STEP 1: Load base configuration from config.yaml
            # ================================================================
            
            max_steps = config.agent.max_steps
            reasoning_mode = config.agent.reasoning
            vision_config = config.agent.vision
            device_serial = config.device.serial
            use_tcp_mode = config.device.use_tcp
            debug_mode = config.logging.debug
            save_traj = config.logging.save_trajectory
            tracing_enabled = config.tracing.enabled
            allow_drag_tool = config.tools.allow_drag
            
            # ================================================================
            # STEP 2: Apply CLI overrides if explicitly specified
            # ================================================================
            
            if steps is not None:
                max_steps = steps
                logger.debug(f"CLI override: max_steps={max_steps}")
            
            if reasoning is not None:
                reasoning_mode = reasoning
                logger.debug(f"CLI override: reasoning={reasoning_mode}")
            
            if debug is not None:
                debug_mode = debug
                logger.debug(f"CLI override: debug={debug_mode}")
            
            if tracing is not None:
                tracing_enabled = tracing
                logger.debug(f"CLI override: tracing={tracing_enabled}")
            
            if save_trajectory is not None:
                save_traj = save_trajectory
                logger.debug(f"CLI override: save_trajectory={save_traj}")
            
            if use_tcp is not None:
                use_tcp_mode = use_tcp
                logger.debug(f"CLI override: use_tcp={use_tcp_mode}")
            
            if device is not None:
                device_serial = device
                logger.debug(f"CLI override: device={device_serial}")
            
            if allow_drag is not None:
                allow_drag_tool = allow_drag
                logger.debug(f"CLI override: allow_drag={allow_drag_tool}")
            
            # Override vision settings
            if vision is not None:
                # User specified --vision, apply to all agents
                vision_config = VisionConfig(manager=vision, executor=vision, codeact=vision)
                logger.debug(f"CLI override: vision={vision} (all agents)")
            else:
                # Check for per-agent vision overrides
                vision_config = VisionConfig(
                    manager=vision_config.manager,
                    executor=vision_config.executor,
                    codeact=vision_config.codeact
                )
                if manager_vision is not None:
                    vision_config.manager = manager_vision
                    logger.debug(f"CLI override: manager_vision={manager_vision}")
                
                if executor_vision is not None:
                    vision_config.executor = executor_vision
                    logger.debug(f"CLI override: executor_vision={executor_vision}")
                
                if codeact_vision is not None:
                    vision_config.codeact = codeact_vision
                    logger.debug(f"CLI override: codeact_vision={codeact_vision}")
            
            # ================================================================
            # STEP 3: Load LLMs
            # ================================================================
            
            log_handler.update_step("Loading LLMs...")
            
            # Check if user wants custom LLM for all agents
            if provider is not None or model is not None:
                # User specified custom provider/model - use for all agents
                logger.info("🔧 Using custom LLM for all agents")
                
                # Use provided values or fall back to first profile's defaults
                if provider is None:
                    provider = list(config.llm_profiles.values())[0].provider
                if model is None:
                    model = list(config.llm_profiles.values())[0].model
                
                # Build kwargs
                llm_kwargs = {}
                if temperature is not None:
                    llm_kwargs['temperature'] = temperature
                else:
                    llm_kwargs['temperature'] = kwargs.get('temperature', 1)
                if base_url is not None:
                    llm_kwargs['base_url'] = base_url
                if api_base is not None:
                    llm_kwargs['api_base'] = api_base
                llm_kwargs.update(kwargs)
                
                # Load single LLM for all agents
                custom_llm = load_llm(
                    provider_name=provider,
                    model=model,
                    **llm_kwargs
                )
                
                # Use same LLM for all agents
                llms = {
                    'manager': custom_llm,
                    'executor': custom_llm,
                    'codeact': custom_llm,
                    'text_manipulator': custom_llm,
                    'app_opener': custom_llm,
                }
                logger.info(f"🧠 Custom LLM ready: {provider}/{model}")
            else:
                # No custom provider/model - use profiles from config
                logger.info("📋 Loading LLMs from config profiles...")
                
                profile_names = ['manager', 'executor', 'codeact', 'text_manipulator', 'app_opener']
                
                # Apply temperature override to all profiles if specified
                overrides = {}
                if temperature is not None:
                    overrides = {name: {'temperature': temperature} for name in profile_names}
                
                llms = config.load_all_llms(profile_names=profile_names, **overrides)
                logger.info(f"🧠 Loaded {len(llms)} agent-specific LLMs from profiles")
            
            # ================================================================
            # STEP 4: Setup device and tools
            # ================================================================
            
            log_handler.update_step("Setting up tools...")
            
            if device_serial is None and not ios:
                logger.info("🔍 Finding connected device...")
                devices = adb.list()
                if not devices:
                    raise ValueError("No connected devices found.")
                device_serial = devices[0].serial
                logger.info(f"📱 Using device: {device_serial}")
            elif device_serial is None and ios:
                raise ValueError(
                    "iOS device not specified. Please specify device base url via --device"
                )
            else:
                logger.info(f"📱 Using device: {device_serial}")
            
            tools = (
                AdbTools(
                    serial=device_serial,
                    use_tcp=use_tcp_mode,
                    app_opener_llm=llms.get('app_opener'),
                    text_manipulator_llm=llms.get('text_manipulator')
                )
                if not ios
                else IOSTools(url=device_serial)
            )
            
            # Set excluded tools based on config/CLI
            excluded_tools = [] if allow_drag_tool else ["drag"]
            
            # Select personas based on drag flag
            personas = [BIG_AGENT] if allow_drag_tool else [DEFAULT]
            
            # ================================================================
            # STEP 5: Initialize DroidAgent with all settings
            # ================================================================
            
            log_handler.update_step("Initializing DroidAgent...")
            
            mode = "planning with reasoning" if reasoning_mode else "direct execution"
            logger.info(f"🤖 Agent mode: {mode}")
            logger.info(f"👁️  Vision settings: Manager={vision_config.manager}, "
                       f"Executor={vision_config.executor}, CodeAct={vision_config.codeact}")
            
            if tracing_enabled:
                logger.info("🔍 Tracing enabled")
            
            droid_agent = DroidAgent(
                goal=command,
                llms=llms,
                vision=vision_config,
                tools=tools,
                personas=personas,
                excluded_tools=excluded_tools,
                max_steps=max_steps,
                timeout=1000,
                reasoning=reasoning_mode,
                enable_tracing=tracing_enabled,
                debug=debug_mode,
                save_trajectories=save_traj,
            )
            
            # ================================================================
            # STEP 6: Run agent
            # ================================================================
            
            logger.info("▶️  Starting agent execution...")
            logger.info("Press Ctrl+C to stop")
            log_handler.update_step("Running agent...")

            try:
                handler = droid_agent.run()

                async for event in handler.stream_events():
                    log_handler.handle_event(event)
                result = await handler  # noqa: F841

            except KeyboardInterrupt:
                log_handler.is_completed = True
                log_handler.is_success = False
                log_handler.current_step = "Stopped by user"
                logger.info("⏹️ Stopped by user")

            except Exception as e:
                log_handler.is_completed = True
                log_handler.is_success = False
                log_handler.current_step = f"Error: {e}"
                logger.error(f"💥 Error: {e}")
                if debug_mode:
                    import traceback

                    logger.debug(traceback.format_exc())

        except Exception as e:
            log_handler.current_step = f"Error: {e}"
            logger.error(f"💥 Setup error: {e}")
            if debug_mode:
                import traceback

                logger.debug(traceback.format_exc())


class DroidRunCLI(click.Group):
    def parse_args(self, ctx, args):
        # If the first arg is not an option and not a known command, treat as 'run'
        if args and """not args[0].startswith("-")""" and args[0] not in self.commands:
            args.insert(0, "run")

        return super().parse_args(ctx, args)


@click.option("--device", "-d", help="Device serial number or IP address", default=None)
@click.option(
    "--provider",
    "-p",
    help="LLM provider (OpenAI, Ollama, Anthropic, GoogleGenAI, DeepSeek)",
    default="GoogleGenAI",
)
@click.option(
    "--model",
    "-m",
    help="LLM model name",
    default="models/gemini-2.5-flash",
)
@click.option("--temperature", type=float, help="Temperature for LLM", default=0.2)
@click.option("--steps", type=int, help="Maximum number of steps", default=15)
@click.option(
    "--base_url",
    "-u",
    help="Base URL for API (e.g., OpenRouter or Ollama)",
    default=None,
)
@click.option(
    "--api_base",
    help="Base URL for API (e.g., OpenAI, OpenAI-Like)",
    default=None,
)
@click.option(
    "--vision",
    is_flag=True,
    help="Enable vision capabilites by using screenshots",
    default=False,
)
@click.option(
    "--reasoning", is_flag=True, help="Enable planning with reasoning", default=False
)

@click.option(
    "--tracing", is_flag=True, help="Enable Arize Phoenix tracing", default=False
)
@click.option(
    "--debug", is_flag=True, help="Enable verbose debug logging", default=False
)
@click.option(
    "--use-tcp",
    is_flag=True,
    help="Use TCP communication for device control",
    default=False,
)
@click.option(
    "--save-trajectory",
    type=click.Choice(["none", "step", "action"]),
    help="Trajectory saving level: none (no saving), step (save per step), action (save per action)",
    default="none",
)
@click.group(cls=DroidRunCLI)
def cli(
    device: str | None,
    provider: str,
    model: str,
    steps: int,
    base_url: str,
    api_base: str,
    temperature: float,
    vision: bool,
    reasoning: bool,
    tracing: bool,
    debug: bool,
    use_tcp: bool,
    save_trajectory: str = "none",
):
    """DroidRun - Control your Android device through LLM agents."""
    pass


@cli.command()
@click.argument("command", type=str)
@click.option("--device", "-d", help="Device serial number or IP address", default=None)
@click.option(
    "--provider",
    "-p",
    help="LLM provider (OpenAI, Ollama, Anthropic, GoogleGenAI, DeepSeek)",
    default=None,
)
@click.option(
    "--model",
    "-m",
    help="LLM model name",
    default=None,
)
@click.option("--temperature", type=float, help="Temperature for LLM", default=None)
@click.option("--steps", type=int, help="Maximum number of steps", default=None)
@click.option(
    "--base_url",
    "-u",
    help="Base URL for API (e.g., OpenRouter or Ollama)",
    default=None,
)
@click.option(
    "--api_base",
    help="Base URL for API (e.g., OpenAI or OpenAI-Like)",
    default=None,
)
@click.option(
    "--vision",
    type=bool,
    default=None,
    help="Enable vision capabilites by using screenshots for all agents.",
)
@click.option(
    "--manager-vision",
    type=bool,
    default=None,
    help="Enable vision for Manager agent only",
)
@click.option(
    "--executor-vision",
    type=bool,
    default=None,
    help="Enable vision for Executor agent only",
)
@click.option(
    "--codeact-vision",
    type=bool,
    default=None,
    help="Enable vision for CodeAct agent only",
)
@click.option(
    "--reasoning", type=bool, default=None, help="Enable planning with reasoning"
)
@click.option(
    "--tracing", type=bool, default=None, help="Enable Arize Phoenix tracing"
)
@click.option(
    "--debug", type=bool, default=None, help="Enable verbose debug logging"
)
@click.option(
    "--use-tcp",
    type=bool,
    default=None,
    help="Use TCP communication for device control",
)
@click.option(
    "--save-trajectory",
    type=click.Choice(["none", "step", "action"]),
    help="Trajectory saving level: none (no saving), step (save per step), action (save per action)",
    default=None,
)
@click.option(
    "--drag",
    "allow_drag",
    type=bool,
    default=None,
    help="Enable drag tool",
)
@click.option("--ios", type=bool, default=None, help="Run on iOS device")
def run(
    command: str,
    device: str | None,
    provider: str | None,
    model: str | None,
    steps: int | None,
    base_url: str | None,
    api_base: str | None,
    temperature: float | None,
    vision: bool | None,
    manager_vision: bool | None,
    executor_vision: bool | None,
    codeact_vision: bool | None,
    reasoning: bool | None,
    tracing: bool | None,
    debug: bool | None,
    use_tcp: bool | None,
    save_trajectory: str | None,
    allow_drag: bool | None,
    ios: bool | None,
):
    """Run a command on your Android device using natural language."""
    # Call our standalone function
    return run_command(
        command,
        device,
        provider,
        model,
        steps,
        base_url,
        api_base,
        vision,
        manager_vision,
        executor_vision,
        codeact_vision,
        reasoning,
        tracing,
        debug,
        use_tcp,
        temperature=temperature,
        save_trajectory=save_trajectory,
        allow_drag=allow_drag,
        ios=ios if ios is not None else False,
    )


@cli.command()
def devices():
    """List connected Android devices."""
    try:
        devices = adb.list()
        if not devices:
            console.print("[yellow]No devices connected.[/]")
            return

        console.print(f"[green]Found {len(devices)} connected device(s):[/]")
        for device in devices:
            console.print(f"  • [bold]{device.serial}[/]")
    except Exception as e:
        console.print(f"[red]Error listing devices: {e}[/]")


@cli.command()
@click.argument("serial")
def connect(serial: str):
    """Connect to a device over TCP/IP."""
    try:
        device = adb.connect(serial)
        if device.count("already connected"):
            console.print(f"[green]Successfully connected to {serial}[/]")
        else:
            console.print(f"[red]Failed to connect to {serial}: {device}[/]")
    except Exception as e:
        console.print(f"[red]Error connecting to device: {e}[/]")


@cli.command()
@click.argument("serial")
def disconnect(serial: str):
    """Disconnect from a device."""
    try:
        success = adb.disconnect(serial, raise_error=True)
        if success:
            console.print(f"[green]Successfully disconnected from {serial}[/]")
        else:
            console.print(f"[yellow]Device {serial} was not connected[/]")
    except Exception as e:
        console.print(f"[red]Error disconnecting from device: {e}[/]")


@cli.command()
@click.option("--device", "-d", help="Device serial number or IP address", default=None)
@click.option(
    "--path",
    help="Path to the Droidrun Portal APK to install on the device. If not provided, the latest portal apk version will be downloaded and installed.",
    default=None,
)
@click.option(
    "--debug", is_flag=True, help="Enable verbose debug logging", default=False
)
def setup(path: str | None, device: str | None, debug: bool):
    """Install and enable the DroidRun Portal on a device."""
    try:
        if not device:
            devices = adb.list()
            if not devices:
                console.print("[yellow]No devices connected.[/]")
                return

            device = devices[0].serial
            console.print(f"[blue]Using device:[/] {device}")

        device_obj = adb.device(device)
        if not device_obj:
            console.print(
                f"[bold red]Error:[/] Could not get device object for {device}"
            )
            return

        if not path:
            console.print("[bold blue]Downloading DroidRun Portal APK...[/]")
            apk_context = download_portal_apk(debug)
        else:
            console.print(f"[bold blue]Using provided APK:[/] {path}")
            apk_context = nullcontext(path)

        with apk_context as apk_path:
            if not os.path.exists(apk_path):
                console.print(f"[bold red]Error:[/] APK file not found at {apk_path}")
                return

            console.print(f"[bold blue]Step 1/2: Installing APK:[/] {apk_path}")
            try:
                device_obj.install(
                    apk_path, uninstall=True, flags=["-g"], silent=not debug
                )
            except Exception as e:
                console.print(f"[bold red]Installation failed:[/] {e}")
                return

            console.print("[bold green]Installation successful![/]")

            console.print("[bold blue]Step 2/2: Enabling accessibility service[/]")

            try:
                enable_portal_accessibility(device_obj)

                console.print("[green]Accessibility service enabled successfully![/]")
                console.print(
                    "\n[bold green]Setup complete![/] The DroidRun Portal is now installed and ready to use."
                )

            except Exception as e:
                console.print(
                    f"[yellow]Could not automatically enable accessibility service: {e}[/]"
                )
                console.print(
                    "[yellow]Opening accessibility settings for manual configuration...[/]"
                )

                device_obj.shell("am start -a android.settings.ACCESSIBILITY_SETTINGS")

                console.print(
                    "\n[yellow]Please complete the following steps on your device:[/]"
                )
                console.print(
                    f"1. Find [bold]{PORTAL_PACKAGE_NAME}[/] in the accessibility services list"
                )
                console.print("2. Tap on the service name")
                console.print(
                    "3. Toggle the switch to [bold]ON[/] to enable the service"
                )
                console.print("4. Accept any permission dialogs that appear")

                console.print(
                    "\n[bold green]APK installation complete![/] Please manually enable the accessibility service using the steps above."
                )

    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")

        if debug:
            import traceback

            traceback.print_exc()


@cli.command()
@click.option("--device", "-d", help="Device serial number or IP address", default=None)
@click.option(
    "--use-tcp",
    is_flag=True,
    help="Use TCP communication for device control",
    default=False,
)
@click.option(
    "--debug", is_flag=True, help="Enable verbose debug logging", default=False
)
def ping(device: str | None, use_tcp: bool, debug: bool):
    """Ping a device to check if it is ready and accessible."""
    try:
        device_obj = adb.device(device)
        if not device_obj:
            console.print(f"[bold red]Error:[/] Could not find device {device}")
            return

        ping_portal(device_obj, debug)

        if use_tcp:
            ping_portal_tcp(device_obj, debug)
        else:
            ping_portal_content(device_obj, debug)

        console.print(
            "[bold green]Portal is installed and accessible. You're good to go![/]"
        )
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        if debug:
            import traceback

            traceback.print_exc()


# Add macro commands as a subgroup
cli.add_command(macro_cli, name="macro")


if __name__ == "__main__":
    command = "Download clash royale app"
    device = None
    provider = "GoogleGenAI"
    model = "models/gemini-2.5-flash"
    temperature = 0
    api_key = os.getenv("GOOGLE_API_KEY")
    steps = 15
    vision = True
    reasoning = True
    tracing = True
    debug = True
    use_tcp = False
    base_url = None
    api_base = None
    ios = False
    save_trajectory = "none"
    allow_drag = False
    run_command(
        command=command
    )
