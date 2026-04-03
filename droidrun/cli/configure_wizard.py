from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import click
from rich.console import Console
from rich.panel import Panel

from droidrun.cli.configure_prompts import (
    SelectChoice,
    confirm_prompt,
    normalize_role_targets,
    select_prompt,
    text_prompt,
)
from droidrun.config_manager.env_keys import load_env_key_sources, resolve_env_key
from droidrun.config_manager import ConfigLoader
from droidrun.agent.providers.setup_service import (
    SetupSelection,
    apply_selection_to_roles,
    auth_mode_choices,
    family_choices,
    variant_models,
)

_BACK = "__back__"

_MAIN_AGENT_ROLES = ("manager", "executor", "fast_agent")
_HELPER_AGENT_ROLES = ("app_opener", "structured_output")
_ALL_CONFIG_ROLES = _MAIN_AGENT_ROLES + _HELPER_AGENT_ROLES
_VARIANT_ENV_KEY_SLOT = {
    "GoogleGenAI": "google",
    "OpenAI": "openai",
    "Anthropic": "anthropic",
    "ZAI": "zai",
    "ZAI_Coding": "zai",
}


@dataclass
class ConfigureWizardCallbacks:
    run_openai_oauth_login: Callable[..., None]
    save_anthropic_setup_token: Callable[[str, str], None]
    prompt_anthropic_setup_token: Callable[..., str]
    print_oauth_login_success: Callable[[str, str], None]
    run_gemini_oauth_login: Callable[..., None]


@dataclass
class ConfigureWizardState:
    family_id: str | None = None
    selected_auth_mode: str | None = None
    selected_model: str | None = None
    target_roles: tuple[str, ...] = _ALL_CONFIG_ROLES
    selected_api_key: str | None = None
    selected_api_key_source: str | None = None
    selected_base_url: str | None = None
    last_variant_id: str | None = None
    prepared_auth_variant_id: str | None = None
    used_advanced_settings: bool = False


def _with_back_choice(
    choices: list[SelectChoice], *, include_back: bool = True
) -> list[SelectChoice]:
    if not include_back:
        return choices
    return [*choices, SelectChoice(value=_BACK, label="Back")]


def _select_with_back(
    message: str,
    choices: list[SelectChoice],
    *,
    default: str | None = None,
    include_back: bool = True,
) -> str:
    return select_prompt(
        message,
        _with_back_choice(choices, include_back=include_back),
        default=default,
    )


def _print_configure_intro(console: Console) -> None:
    console.print(
        Panel(
            "Choose your provider, auth method, and model.\n"
            "Advanced agent settings are optional and can be changed at the end.",
            title="Droidrun Configure",
            border_style="cyan",
            padding=(1, 2),
        )
    )


def _print_configure_summary(
    console: Console,
    *,
    provider_label: str,
    variant_id: str,
    model: str,
    applied_to: str,
    used_advanced_settings: bool,
) -> None:
    advanced_line = "Yes" if used_advanced_settings else "No"
    console.print(
        Panel(
            f"Provider: {provider_label} ({variant_id})\n"
            f"Model: {model}\n"
            f"Applied to: {applied_to}\n"
            f"Advanced settings changed: {advanced_line}",
            title="Configuration Saved",
            border_style="green",
            padding=(1, 2),
        )
    )


def _prompt_int(console: Console, message: str, default: int) -> int:
    while True:
        value = text_prompt(message, default=str(default))
        try:
            return int(value)
        except ValueError:
            console.print("[red]Please enter a whole number.[/]")


def _prompt_float(console: Console, message: str, default: float) -> float:
    while True:
        value = text_prompt(message, default=str(default))
        try:
            return float(value)
        except ValueError:
            console.print("[red]Please enter a number.[/]")


def _resolve_variant(
    families: tuple[Any, ...], family_id: str, auth_mode: str
) -> Any:
    return next(
        variant
        for variant in next(f for f in families if f.id == family_id).variants
        if variant.auth_mode == auth_mode
    )


def _prompt_grouped_role_targets() -> tuple[str, ...] | None:
    choice = _select_with_back(
        "Apply this model configuration to",
        [
            SelectChoice(value="all", label="All", hint="Use this setup everywhere"),
            SelectChoice(
                value="main", label="Main agents", hint="Manager, executor, fast agent"
            ),
            SelectChoice(
                value="helper",
                label="Helper agents",
                hint="App opener and structured output",
            ),
        ],
        default="all",
    )
    if choice == _BACK:
        return None
    if choice == "main":
        return _MAIN_AGENT_ROLES
    if choice == "helper":
        return _HELPER_AGENT_ROLES
    return _ALL_CONFIG_ROLES


def _prompt_model_choice(
    models: list[str],
    *,
    default_model: str,
    allow_back: bool = True,
) -> str:
    if models:
        choice = _select_with_back(
            "Choose model",
            [
                *[SelectChoice(value=item, label=item) for item in models],
                SelectChoice(
                    value="enter_model",
                    label="Enter custom model",
                ),
            ],
            default=default_model or None,
            include_back=allow_back,
        )
        if choice in {_BACK, "enter_model"}:
            if choice == _BACK:
                return _BACK
            return text_prompt("Model", default=default_model)
        return choice

    choice = _select_with_back(
        "Choose model",
        [
            SelectChoice(
                value="enter_model",
                label="Enter custom model",
            )
        ],
        default="enter_model",
        include_back=allow_back,
    )
    if choice == _BACK:
        return _BACK
    return text_prompt("Model", default=default_model)


def _prompt_api_key_source(variant: Any) -> str:
    env_slot = _VARIANT_ENV_KEY_SLOT.get(variant.id)
    sources = load_env_key_sources().get(env_slot) if env_slot else None
    choices: list[SelectChoice] = []
    if sources and sources.shell:
        choices.append(
            SelectChoice(
                value="env",
                label="Use env key",
                hint=f"Read {env_slot.upper()} from the shell environment",
            )
        )
    if sources and sources.saved:
        choices.append(
            SelectChoice(
                value="file",
                label="Use saved key",
                hint="Use the key already stored in the credentials env file",
            )
        )
    choices.append(
        SelectChoice(
            value="paste",
            label="Paste new key",
            hint="Store a new key in the credentials env file",
        )
    )
    return _select_with_back("API key source", choices, default=choices[0].value)


def _prompt_api_key_for_variant(variant: Any) -> tuple[str, str]:
    env_slot = _VARIANT_ENV_KEY_SLOT.get(variant.id)
    if not env_slot:
        return text_prompt("API key", secret=True), "file"

    source = _prompt_api_key_source(variant)
    if source == _BACK:
        return "", _BACK
    if source == "env":
        return resolve_env_key(env_slot, "env"), "env"
    if source == "file":
        return resolve_env_key(env_slot, "file"), "file"
    return text_prompt("API key", secret=True), "file"


def _prompt_oauth_credential_action(credential_path: str) -> str:
    return _select_with_back(
        "OAuth credentials found",
        [
            SelectChoice(
                value="use_existing",
                label="Use existing login",
                hint=f"Keep credentials from {Path(credential_path).expanduser()}",
            ),
            SelectChoice(
                value="login_again",
                label="Log in again",
                hint="Authenticate with another account or refresh credentials",
            ),
        ],
        default="use_existing",
    )


def _target_role_label(target_roles: tuple[str, ...]) -> str:
    if target_roles == _MAIN_AGENT_ROLES:
        return "Main agents"
    if target_roles == _HELPER_AGENT_ROLES:
        return "Helper agents"
    if target_roles == _ALL_CONFIG_ROLES:
        return "All"
    return ", ".join(target_roles)


def _apply_model_selection(
    config,
    *,
    family_id: str,
    variant: Any,
    selected_auth_mode: str,
    selected_model: str,
    selected_api_key: str | None,
    selected_api_key_source: str | None,
    selected_base_url: str | None,
    credential_path: str | None,
    target_roles: tuple[str, ...],
) -> None:
    selection = SetupSelection(
        family_id=family_id,
        variant_id=variant.id,
        auth_mode=selected_auth_mode,
        model=selected_model,
        api_key=selected_api_key,
        api_key_source=selected_api_key_source or "auto",
        base_url=selected_base_url,
        credential_path=credential_path,
    )
    apply_selection_to_roles(config, selection, target_roles)


def _prepare_variant_auth(
    *,
    callbacks: ConfigureWizardCallbacks,
    variant: Any,
    credential_path: str | None,
    selected_model: str,
) -> None:
    if variant.id == "openai_oauth" and credential_path:
        callbacks.run_openai_oauth_login(
            credential_path=credential_path, model=selected_model
        )
    elif variant.id == "anthropic_oauth" and credential_path:
        callbacks.save_anthropic_setup_token(
            credential_path,
            callbacks.prompt_anthropic_setup_token(),
        )
        callbacks.print_oauth_login_success("Anthropic setup-token", credential_path)
    elif variant.id == "gemini_oauth_code_assist" and credential_path:
        callbacks.run_gemini_oauth_login(
            credential_path=credential_path, model=selected_model
        )


def _set_profile_max_tokens(profile: Any, value: int) -> None:
    profile.kwargs = dict(profile.kwargs)
    profile.kwargs["max_tokens"] = value


def _configure_advanced_settings(
    console: Console,
    config,
    target_roles: tuple[str, ...],
) -> tuple[str, ...]:
    default_selection = "apply_model_to"
    while True:
        selected = _select_with_back(
            "Advanced settings",
            [
                SelectChoice(
                    value="apply_model_to",
                    label=f"Apply model to ({_target_role_label(target_roles)})",
                    hint="Change which agent group uses this model setup",
                ),
                SelectChoice(
                    value="reasoning",
                    label="Reasoning mode",
                    hint="Planning mode for multi-step tasks",
                ),
                SelectChoice(
                    value="max_steps",
                    label="Maximum steps",
                    hint="Cap how long tasks can run",
                ),
                SelectChoice(
                    value="planning_vision",
                    label="Planning mode vision",
                    hint="Manager and executor can use screenshots",
                ),
                SelectChoice(
                    value="direct_vision",
                    label="Direct mode vision",
                    hint="Fast agent can use screenshots",
                ),
                SelectChoice(
                    value="manager_stateless",
                    label="Manager stateless mode",
                    hint="Rebuild planning context each turn",
                ),
                SelectChoice(
                    value="temperature",
                    label="Temperature",
                    hint="Adjust creativity for the selected agent group",
                ),
                SelectChoice(
                    value="max_tokens",
                    label="Max tokens",
                    hint="Limit response length for the selected agent group",
                ),
                SelectChoice(value="done", label="Done", hint="Save and finish"),
            ],
            default=default_selection,
        )

        if selected in {_BACK, "done"}:
            return target_roles

        if selected == "apply_model_to":
            updated_roles = _prompt_grouped_role_targets()
            if updated_roles is not None:
                target_roles = updated_roles
        elif selected == "reasoning":
            config.agent.reasoning = confirm_prompt(
                "Enable reasoning mode?", default=config.agent.reasoning
            )
        elif selected == "max_steps":
            config.agent.max_steps = _prompt_int(
                console, "Maximum steps", default=config.agent.max_steps
            )
        elif selected == "planning_vision":
            enabled = confirm_prompt(
                "Enable planning mode vision?",
                default=(config.agent.manager.vision or config.agent.executor.vision),
            )
            config.agent.manager.vision = enabled
            config.agent.executor.vision = enabled
        elif selected == "direct_vision":
            config.agent.fast_agent.vision = confirm_prompt(
                "Enable direct mode vision?",
                default=config.agent.fast_agent.vision,
            )
        elif selected == "manager_stateless":
            config.agent.manager.stateless = confirm_prompt(
                "Enable manager stateless mode?",
                default=config.agent.manager.stateless,
            )
        elif selected == "temperature":
            default_temp = config.llm_profiles[target_roles[0]].temperature
            value = _prompt_float(console, "Temperature", default=default_temp)
            for role in target_roles:
                config.llm_profiles[role].temperature = value
        elif selected == "max_tokens":
            current_value = config.llm_profiles[target_roles[0]].kwargs.get(
                "max_tokens", 1024
            )
            try:
                current_default = int(current_value)
            except (TypeError, ValueError):
                current_default = 1024
            value = _prompt_int(console, "Max tokens", default=current_default)
            for role in target_roles:
                _set_profile_max_tokens(config.llm_profiles[role], value)

        default_selection = selected


def run_configure_wizard(
    console: Console,
    callbacks: ConfigureWizardCallbacks,
    *,
    provider: str | None,
    auth_mode: str | None,
    model: str | None,
    api_key: str | None,
    base_url: str | None,
    apply_to_all: bool | None,
    roles: tuple[str, ...],
) -> None:
    config = ConfigLoader.load()
    _print_configure_intro(console)

    families = family_choices()
    family_ids = [family.id for family in families]
    family_labels = {family.id: family.display_name for family in families}
    state = ConfigureWizardState(
        selected_api_key=api_key,
        selected_api_key_source="file" if api_key else None,
        selected_base_url=base_url,
    )

    provider_is_fixed = provider is not None
    auth_mode_is_fixed = auth_mode is not None
    model_is_fixed = model is not None
    roles_are_fixed = apply_to_all is not None or bool(roles)

    if provider_is_fixed:
        state.family_id = click.Choice(family_ids, case_sensitive=False).convert(
            provider, None, None
        )
    if roles_are_fixed:
        state.target_roles = normalize_role_targets(apply_to_all, roles)

    while True:
        if state.family_id is None:
            state.family_id = _select_with_back(
                "Choose provider",
                [
                    SelectChoice(value=family.id, label=family.display_name)
                    for family in families
                ],
                default="gemini",
                include_back=False,
            )
        console.print(f"Selected provider family: {family_labels[state.family_id]}")

        modes = auth_mode_choices(state.family_id)
        if auth_mode_is_fixed:
            state.selected_auth_mode = click.Choice(
                list(modes), case_sensitive=False
            ).convert(auth_mode, None, None)
        else:
            while True:
                if len(modes) == 1:
                    state.selected_auth_mode = modes[0]
                    break
                state.selected_auth_mode = _select_with_back(
                    "Choose auth mode",
                    [
                        SelectChoice(value=mode, label=mode.replace("_", " "))
                        for mode in modes
                    ],
                    default=modes[0],
                )
                if state.selected_auth_mode == _BACK:
                    state.family_id = None
                    break
                break
            if state.selected_auth_mode is None:
                continue
            if state.selected_auth_mode == _BACK:
                state.family_id = None
                state.selected_auth_mode = None
                continue

        models = list(variant_models(state.family_id, state.selected_auth_mode))
        variant = _resolve_variant(families, state.family_id, state.selected_auth_mode)
        default_model = models[0] if models else (variant.default_model or "")

        if model_is_fixed:
            state.selected_model = model
        else:
            while True:
                state.selected_model = _prompt_model_choice(
                    models,
                    default_model=default_model,
                )
                if state.selected_model == _BACK:
                    state.selected_model = None
                    if auth_mode_is_fixed or len(modes) == 1:
                        if not provider_is_fixed:
                            state.family_id = None
                        if not auth_mode_is_fixed:
                            state.selected_auth_mode = None
                    else:
                        state.selected_auth_mode = None
                    break
                break
            if state.selected_model is None:
                continue
        credential_path: str | None = variant.credential_path

        if variant.id != state.last_variant_id:
            if api_key is None:
                state.selected_api_key = None
                state.selected_api_key_source = None
            if base_url is None:
                state.selected_base_url = None
            state.last_variant_id = variant.id
            state.prepared_auth_variant_id = None

        if variant.requires_api_key and not state.selected_api_key:
            selected_key, selected_source = _prompt_api_key_for_variant(variant)
            if selected_key == _BACK:
                if model_is_fixed:
                    break
                state.selected_model = None
                break
            state.selected_api_key = selected_key
            state.selected_api_key_source = selected_source
        if variant.requires_base_url and not state.selected_base_url:
            state.selected_base_url = text_prompt(
                "Base URL", default=variant.base_url or "", secret=False
            )
        if (
            credential_path
            and variant.auth_mode == "oauth"
            and state.prepared_auth_variant_id != variant.id
            and Path(credential_path).expanduser().exists()
        ):
            oauth_action = _prompt_oauth_credential_action(credential_path)
            if oauth_action == _BACK:
                if model_is_fixed:
                    break
                state.selected_model = None
                break
            if oauth_action == "use_existing":
                state.prepared_auth_variant_id = variant.id
        while True:
            action = _select_with_back(
                "Configuration complete",
                [
                    SelectChoice(value="finish", label="Finish", hint="Save and exit"),
                    SelectChoice(
                        value="advanced",
                        label="Advanced settings",
                        hint="Reasoning, vision, temperature, max tokens",
                    ),
                ],
                default="finish",
            )
            if action == _BACK:
                if model_is_fixed:
                    break
                state.selected_model = None
                break

            if action == "advanced":
                state.used_advanced_settings = True
                state.target_roles = _configure_advanced_settings(
                    console, config, state.target_roles
                )

            if credential_path and state.prepared_auth_variant_id != variant.id:
                _prepare_variant_auth(
                    callbacks=callbacks,
                    variant=variant,
                    credential_path=credential_path,
                    selected_model=state.selected_model,
                )
                state.prepared_auth_variant_id = variant.id

            _apply_model_selection(
                config,
                family_id=state.family_id,
                variant=variant,
                selected_auth_mode=state.selected_auth_mode,
                selected_model=state.selected_model,
                selected_api_key=state.selected_api_key,
                selected_api_key_source=state.selected_api_key_source,
                selected_base_url=state.selected_base_url,
                credential_path=credential_path,
                target_roles=state.target_roles,
            )

            ConfigLoader.save(config)
            _print_configure_summary(
                console,
                provider_label=family_labels[state.family_id],
                variant_id=variant.id,
                model=state.selected_model,
                applied_to=_target_role_label(state.target_roles),
                used_advanced_settings=state.used_advanced_settings,
            )
            return

        if state.selected_model is None:
            continue
