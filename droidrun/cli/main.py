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

from droidrun.agent.droid import DroidAgent
from droidrun.agent.utils.llm_picker import load_llm, load_llms_from_profiles
from droidrun.cli.logs import LogHandler
from droidrun.config_manager import ConfigManager
from droidrun.config_manager.config_manager import (
    AgentConfig,
    CodeActConfig,
    DeviceConfig,
    ExecutorConfig,
    LoggingConfig,
    ManagerConfig,
    ToolsConfig,
    TracingConfig,
)
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

# Suppress all warnings
warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["GRPC_ENABLE_FORK_SUPPORT"] = "false"

console = Console()


def configure_logging(goal: str, debug: bool, rich_text: bool = True):
    logger = logging.getLogger("droidrun")
    logger.handlers = []

    handler = LogHandler(goal, rich_text=rich_text)
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
    config_path: str | None = None,
    device: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    steps: int | None = None,
    base_url: str | None = None,
    api_base: str | None = None,
    vision: bool | None = None,
    manager_vision: bool | None = None,
    executor_vision: bool | None = None,
    codeact_vision: bool | None = None,
    reasoning: bool | None = None,
    tracing: bool | None = None,
    debug: bool | None = None,
    use_tcp: bool | None = None,
    save_trajectory: str | None = None,
    ios: bool = False,
    allow_drag: bool | None = None,
    temperature: float | None = None,
    **kwargs,
):
    """Run a command on your Android device using natural language."""
    # Load custom config if provided
    config = ConfigManager(config_path)
    # Initialize logging first (use config default if debug not specified)
    debug_mode = debug if debug is not None else config.logging.debug
    log_handler = configure_logging(command, debug_mode, config.logging.rich_text)
    logger = logging.getLogger("droidrun")

    log_handler.update_step("Initializing...")

    with log_handler.render():
        try:
            logger.info(f"🚀 Starting: {command}")
            print_telemetry_message()

            # ================================================================
            # STEP 1: Build config objects with CLI overrides
            # ================================================================

            # Build agent-specific configs with vision overrides
            if vision is not None:
                # --vision flag overrides all agents
                manager_vision_val = vision
                executor_vision_val = vision
                codeact_vision_val = vision
                logger.debug(f"CLI override: vision={vision} (all agents)")
            else:
                # Use individual overrides or config defaults
                manager_vision_val = manager_vision if manager_vision is not None else config.agent.manager.vision
                executor_vision_val = executor_vision if executor_vision is not None else config.agent.executor.vision
                codeact_vision_val = codeact_vision if codeact_vision is not None else config.agent.codeact.vision

            manager_cfg = ManagerConfig(
                vision=manager_vision_val,
                system_prompt=config.agent.manager.system_prompt
            )

            executor_cfg = ExecutorConfig(
                vision=executor_vision_val,
                system_prompt=config.agent.executor.system_prompt
            )

            codeact_cfg = CodeActConfig(
                vision=codeact_vision_val,
                system_prompt=config.agent.codeact.system_prompt,
                user_prompt=config.agent.codeact.user_prompt
            )

            agent_cfg = AgentConfig(
                max_steps=steps if steps is not None else config.agent.max_steps,
                reasoning=reasoning if reasoning is not None else config.agent.reasoning,
                after_sleep_action=config.agent.after_sleep_action,
                wait_for_stable_ui=config.agent.wait_for_stable_ui,
                prompts_dir=config.agent.prompts_dir,
                manager=manager_cfg,
                executor=executor_cfg,
                codeact=codeact_cfg,
                app_cards=config.agent.app_cards,
            )

            device_cfg = DeviceConfig(
                serial=device if device is not None else config.device.serial,
                use_tcp=use_tcp if use_tcp is not None else config.device.use_tcp,
            )

            tools_cfg = ToolsConfig(
                allow_drag=allow_drag if allow_drag is not None else config.tools.allow_drag,
            )

            logging_cfg = LoggingConfig(
                debug=debug if debug is not None else config.logging.debug,
                save_trajectory=save_trajectory if save_trajectory is not None else config.logging.save_trajectory,
                rich_text=config.logging.rich_text,
            )

            tracing_cfg = TracingConfig(
                enabled=tracing if tracing is not None else config.tracing.enabled,
            )

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
                    llm_kwargs['temperature'] = kwargs.get('temperature', 0.3)
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

                llms = load_llms_from_profiles(config.llm_profiles, profile_names=profile_names, **overrides)
                logger.info(f"🧠 Loaded {len(llms)} agent-specific LLMs from profiles")

            # ================================================================
            # STEP 4: Setup device and tools
            # ================================================================

            log_handler.update_step("Setting up tools...")

            device_serial = device_cfg.serial
            if device_serial is None and not ios:
                logger.info("🔍 Finding connected device...")
                devices = adb.list()
                if not devices:
                    raise ValueError("No connected devices found.")
                device_serial = devices[0].serial
                device_cfg = DeviceConfig(serial=device_serial, use_tcp=device_cfg.use_tcp)
                logger.info(f"📱 Using device: {device_serial}")
            elif device_serial is None and ios:
                raise ValueError("iOS device not specified. Please specify device base url via --device")
            else:
                logger.info(f"📱 Using device: {device_serial}")

            tools = (
                AdbTools(
                    serial=device_serial,
                    use_tcp=device_cfg.use_tcp,
                    app_opener_llm=llms.get('app_opener'),
                    text_manipulator_llm=llms.get('text_manipulator')
                )
                if not ios
                else IOSTools(url=device_serial)
            )

            excluded_tools = [] if tools_cfg.allow_drag else ["drag"]

            # ================================================================
            # STEP 5: Initialize DroidAgent with all settings
            # ================================================================

            log_handler.update_step("Initializing DroidAgent...")

            mode = "planning with reasoning" if agent_cfg.reasoning else "direct execution"
            logger.info(f"🤖 Agent mode: {mode}")
            logger.info(f"👁️  Vision settings: Manager={agent_cfg.manager.vision}, "
                       f"Executor={agent_cfg.executor.vision}, CodeAct={agent_cfg.codeact.vision}")

            if tracing_cfg.enabled:
                logger.info("🔍 Tracing enabled")

            droid_agent = DroidAgent(
                goal=command,
                llms=llms,
                tools=tools,
                config=config,
                agent_config=agent_cfg,
                device_config=device_cfg,
                tools_config=tools_cfg,
                logging_config=logging_cfg,
                tracing_config=tracing_cfg,
                excluded_tools=excluded_tools,
                timeout=1000,
                runtype="cli"
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
                if logging_cfg.debug:
                    import traceback
                    logger.debug(traceback.format_exc())

        except Exception as e:
            log_handler.current_step = f"Error: {e}"
            logger.error(f"💥 Setup error: {e}")
            debug_mode = debug if debug is not None else config.logging.debug
            if debug_mode:
                import traceback
                logger.debug(traceback.format_exc())


class DroidRunCLI(click.Group):
    def parse_args(self, ctx, args):
        # If the first arg is not an option and not a known command, treat as 'run'
        if args and """not args[0].startswith("-")""" and args[0] not in self.commands: # TODO: the string always evaluates to True
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
@click.option("--config", "-c", help="Path to custom config file", default=None)
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
    config: str | None,
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

    try:
        run_command(
            command,
            config,
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
    finally:
        # Disable DroidRun keyboard after execution
        # Note: Port forwards are managed automatically and persist until device disconnect
        try:
            if not (ios if ios is not None else False):
                device_obj = adb.device(device)
                if device_obj:
                    device_obj.shell("ime disable com.droidrun.portal/.DroidrunKeyboardIME")
        except Exception:
            click.echo("Failed to disable DroidRun keyboard")


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
    from droidrun.config_manager.path_resolver import PathResolver

    # Ensure config.yaml exists (check working dir, then package dir)
    try:
        config_path = PathResolver.resolve("config.yaml")
        console.print(f"[blue]Using existing config: {config_path}[/]")
    except FileNotFoundError:
        # Config not found, try to create from example
        try:
            example_path = PathResolver.resolve("config_example.yaml")
            config_path = PathResolver.resolve("config.yaml", create_if_missing=True)

            import shutil
            shutil.copy2(example_path, config_path)
            console.print(f"[blue]Created config.yaml from example at: {config_path}[/]")
        except FileNotFoundError:
            console.print("[yellow]Warning: config_example.yaml not found, config.yaml not created[/]")
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


async def test(command: str):
    config = ConfigManager(path="config.yaml")
    # Initialize logging first (use config default if debug not specified)
    debug_mode = debug if debug is not None else config.logging.debug
    log_handler = configure_logging(command, debug_mode, config.logging.rich_text)
    logger = logging.getLogger("droidrun")

    log_handler.update_step("Initializing...")

    with log_handler.render():
        try:
            logger.info(f"🚀 Starting: {command}")
            print_telemetry_message()

            # ================================================================
            # STEP 1: Build config objects with CLI overrides
            # ================================================================

            # Build agent-specific configs with vision overrides
            if vision is not None:
                # --vision flag overrides all agents
                manager_vision_val = vision
                executor_vision_val = vision
                codeact_vision_val = vision
                logger.debug(f"CLI override: vision={vision} (all agents)")
            else:
                # Use individual overrides or config defaults
                manager_vision_val = config.agent.manager.vision
                executor_vision_val = config.agent.executor.vision
                codeact_vision_val = config.agent.codeact.vision

            manager_cfg = ManagerConfig(
                vision=manager_vision_val,
                system_prompt="rev1.jinja2"
            )

            executor_cfg = ExecutorConfig(
                vision=executor_vision_val,
                system_prompt="rev1.jinja2"
            )

            codeact_cfg = CodeActConfig(
                vision=codeact_vision_val,
                system_prompt=config.agent.codeact.system_prompt,
                user_prompt=config.agent.codeact.user_prompt
            )

            agent_cfg = AgentConfig(
                max_steps=steps if steps is not None else config.agent.max_steps,
                reasoning=reasoning if reasoning is not None else config.agent.reasoning,
                after_sleep_action=config.agent.after_sleep_action,
                wait_for_stable_ui=config.agent.wait_for_stable_ui,
                prompts_dir=config.agent.prompts_dir,
                manager=manager_cfg,
                executor=executor_cfg,
                codeact=codeact_cfg,
                app_cards=config.agent.app_cards,
            )

            device_cfg = DeviceConfig(
                serial=device if device is not None else config.device.serial,
                use_tcp=use_tcp if use_tcp is not None else config.device.use_tcp,
            )

            tools_cfg = ToolsConfig(
                allow_drag=allow_drag if allow_drag is not None else config.tools.allow_drag,
            )

            logging_cfg = LoggingConfig(
                debug=debug if debug is not None else config.logging.debug,
                save_trajectory=save_trajectory if save_trajectory is not None else config.logging.save_trajectory,
                rich_text=config.logging.rich_text,
            )

            tracing_cfg = TracingConfig(
                enabled=tracing if tracing is not None else config.tracing.enabled,
            )

            # ================================================================
            # STEP 3: Load LLMs
            # ================================================================

            log_handler.update_step("Loading LLMs...")

            # No custom provider/model - use profiles from config
            logger.info("📋 Loading LLMs from config profiles...")

            profile_names = ['manager', 'executor', 'codeact', 'text_manipulator', 'app_opener']

            # Apply temperature override to all profiles if specified
            overrides = {}
            if temperature is not None:
                overrides = {name: {'temperature': temperature} for name in profile_names}

            llms = load_llms_from_profiles(config.llm_profiles, profile_names=profile_names, **overrides)
            logger.info(f"🧠 Loaded {len(llms)} agent-specific LLMs from profiles")

            # ================================================================
            # STEP 4: Setup device and tools
            # ================================================================

            log_handler.update_step("Setting up tools...")

            device_serial = device_cfg.serial
            if device_serial is None and not ios:
                logger.info("🔍 Finding connected device...")
                devices = adb.list()
                if not devices:
                    raise ValueError("No connected devices found.")
                device_serial = devices[0].serial
                device_cfg = DeviceConfig(serial=device_serial, use_tcp=device_cfg.use_tcp)
                logger.info(f"📱 Using device: {device_serial}")
            elif device_serial is None and ios:
                raise ValueError("iOS device not specified. Please specify device base url via --device")
            else:
                logger.info(f"📱 Using device: {device_serial}")

            tools = (
                AdbTools(
                    serial=device_serial,
                    use_tcp=device_cfg.use_tcp,
                    app_opener_llm=llms.get('app_opener'),
                    text_manipulator_llm=llms.get('text_manipulator')
                )
                if not ios
                else IOSTools(url=device_serial)
            )

            excluded_tools = [] if tools_cfg.allow_drag else ["drag"]

            # ================================================================
            # STEP 5: Initialize DroidAgent with all settings
            # ================================================================

            log_handler.update_step("Initializing DroidAgent...")

            mode = "planning with reasoning" if agent_cfg.reasoning else "direct execution"
            logger.info(f"🤖 Agent mode: {mode}")
            logger.info(f"👁️  Vision settings: Manager={agent_cfg.manager.vision}, "
                       f"Executor={agent_cfg.executor.vision}, CodeAct={agent_cfg.codeact.vision}")

            if tracing_cfg.enabled:
                logger.info("🔍 Tracing enabled")

            droid_agent = DroidAgent(
                goal=command,
                llms=llms,
                tools=tools,
                config=config,
                agent_config=agent_cfg,
                device_config=device_cfg,
                tools_config=tools_cfg,
                logging_config=logging_cfg,
                tracing_config=tracing_cfg,
                excluded_tools=excluded_tools,
                timeout=1000,
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
                if logging_cfg.debug:
                    import traceback
                    logger.debug(traceback.format_exc())

        except Exception as e:
            log_handler.current_step = f"Error: {e}"
            logger.error(f"💥 Setup error: {e}")
            debug_mode = debug if debug is not None else config.logging.debug
            if debug_mode:
                import traceback
                logger.debug(traceback.format_exc())



if __name__ == "__main__":
    command = "set gboard to the default keyboard"
    device = None
    provider = "GoogleGenAI"
    model = "models/gemini-2.5-flash"
    temperature = 0
    api_key = os.getenv("GOOGLE_API_KEY")
    steps = 15
    vision = True
    reasoning = False
    tracing = True
    debug = True
    use_tcp = False
    base_url = None
    api_base = None
    ios = False
    save_trajectory = "none"
    allow_drag = False
    asyncio.run(
        test(command)
    )
