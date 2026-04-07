#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Iterable

import yaml

from droidrun.agent.providers.registry import list_provider_families
from droidrun.agent.providers.setup_service import (
    ENV_KEY_SLOTS_BY_VARIANT,
    SetupSelection,
    apply_selection_to_roles,
)
from droidrun.config_manager.config_manager import DroidConfig
from droidrun.config_manager.env_keys import API_KEY_ENV_VARS, load_env_keys
from droidrun.config_manager.loader import ConfigLoader
from droidrun.config_manager.migrations import CURRENT_VERSION


SCRIPT_ENV_KEY_SLOTS_BY_VARIANT = dict(ENV_KEY_SLOTS_BY_VARIANT)
SCRIPT_ENV_KEY_SLOTS_BY_VARIANT["MiniMax"] = "minimax"

SCRIPT_API_KEY_ENV_VARS = dict(API_KEY_ENV_VARS)
SCRIPT_API_KEY_ENV_VARS["minimax"] = "MINIMAX_API_KEY"

DEFAULT_DROIDRUN_BIN = (
    str((Path.cwd() / ".venv" / "bin" / "droidrun").resolve())
    if (Path.cwd() / ".venv" / "bin" / "droidrun").exists()
    else (shutil.which("droidrun") or "droidrun")
)


@dataclass(frozen=True)
class Candidate:
    family_id: str
    family_name: str
    variant_id: str
    auth_mode: str
    model: str
    env_slot: str | None = None
    credential_path: str | None = None


@dataclass
class SmokeTestResult:
    family_id: str
    family_name: str
    variant_id: str
    auth_mode: str
    model: str
    env_slot: str
    configure_ok: bool
    run_ok: bool
    elapsed_seconds: float
    return_code: int
    stderr_tail: str
    stdout_tail: str
    configure_mode: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Smoke test Droidrun provider/model combinations by configuring a "
            "temporary config and running a single CLI command for each model."
        )
    )
    parser.add_argument(
        "--command",
        default="hello",
        help='Command to pass to `droidrun run`. Default: "hello".',
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Per-run timeout in seconds. Default: no timeout.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("smoke_cli_models_results.json"),
        help="Where to save the JSON results summary.",
    )
    parser.add_argument(
        "--provider-family",
        action="append",
        default=[],
        help="Limit to one or more provider family ids, e.g. --provider-family openai.",
    )
    parser.add_argument(
        "--model",
        action="append",
        default=[],
        help="Limit to one or more exact model ids.",
    )
    parser.add_argument(
        "--auth-mode",
        action="append",
        default=[],
        help="Limit to one or more auth modes, e.g. --auth-mode oauth.",
    )
    parser.add_argument(
        "--droidrun-bin",
        default=DEFAULT_DROIDRUN_BIN,
        help="Path to the droidrun executable.",
    )
    parser.add_argument(
        "--keep-temp-config",
        action="store_true",
        help="Keep the generated temporary config files for inspection.",
    )
    parser.add_argument(
        "--configure-mode",
        choices=("cli", "direct"),
        default="cli",
        help=(
            "How to apply provider/model selection before each run. "
            "`cli` exercises `droidrun configure`; `direct` uses internal setup logic."
        ),
    )
    parser.add_argument(
        "--vision",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Run droidrun with vision enabled or disabled.",
    )
    parser.add_argument(
        "--reasoning",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Run droidrun with reasoning enabled or disabled.",
    )
    return parser.parse_args()


def tail_text(text: str, lines: int = 20) -> str:
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")
    parts = text.strip().splitlines()
    if not parts:
        return ""
    return "\n".join(parts[-lines:])


def write_temp_config(path: Path) -> None:
    config = ConfigLoader.load()
    payload = config.to_dict()
    payload["_version"] = CURRENT_VERSION
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def save_config_to_path(config: DroidConfig, path: Path) -> None:
    payload = config.to_dict()
    payload["_version"] = CURRENT_VERSION
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def configure_temp_config(
    config_path: Path,
    candidate: Candidate,
    api_key: str,
) -> None:
    config = DroidConfig.from_yaml(str(config_path))
    selection = SetupSelection(
        family_id=candidate.family_id,
        variant_id=candidate.variant_id,
        auth_mode=candidate.auth_mode,
        model=candidate.model,
        api_key=api_key,
        api_key_source="env",
        base_url=None,
        credential_path=None,
    )
    apply_selection_to_roles(config, selection, roles=tuple(config.llm_profiles.keys()))
    save_config_to_path(config, config_path)


def iter_candidates(
    allowed_families: set[str],
    allowed_models: set[str],
    allowed_auth_modes: set[str],
) -> Iterable[Candidate]:
    env_keys = load_env_keys()
    for slot, env_var in SCRIPT_API_KEY_ENV_VARS.items():
        env_value = os.environ.get(env_var, "") or ""
        if env_value:
            env_keys[slot] = env_value
    for family in list_provider_families():
        if allowed_families and family.id not in allowed_families:
            continue
        if family.id == "zai":
            coding_variant = next(
                (variant for variant in family.variants if variant.auth_mode == "coding_api"),
                None,
            )
            if coding_variant is None:
                continue
            if allowed_auth_modes and coding_variant.auth_mode not in allowed_auth_modes:
                continue
            env_slot = ENV_KEY_SLOTS_BY_VARIANT.get(coding_variant.id)
            if not env_slot or not env_keys.get(env_slot):
                continue
            seen_models: set[str] = set()
            for variant in family.variants:
                for model in variant.models:
                    if model.id in seen_models:
                        continue
                    seen_models.add(model.id)
                    if allowed_models and model.id not in allowed_models:
                        continue
                    yield Candidate(
                        family_id=family.id,
                        family_name=family.display_name,
                        variant_id=coding_variant.id,
                        auth_mode=coding_variant.auth_mode,
                        model=model.id,
                        env_slot=env_slot,
                        credential_path=coding_variant.credential_path,
                    )
            continue
        for variant in family.variants:
            if allowed_auth_modes and variant.auth_mode not in allowed_auth_modes:
                continue
            env_slot = SCRIPT_ENV_KEY_SLOTS_BY_VARIANT.get(variant.id)
            credential_path = variant.credential_path
            if variant.auth_mode == "oauth":
                if not credential_path or not Path(credential_path).expanduser().exists():
                    continue
            else:
                if not env_slot:
                    continue
                if not env_keys.get(env_slot):
                    continue
            if not variant.models:
                continue
            for model in variant.models:
                if allowed_models and model.id not in allowed_models:
                    continue
                yield Candidate(
                    family_id=family.id,
                    family_name=family.display_name,
                    variant_id=variant.id,
                    auth_mode=variant.auth_mode,
                    model=model.id,
                    env_slot=env_slot,
                    credential_path=credential_path,
                )


def run_subprocess(
    args: list[str],
    *,
    env: dict[str, str],
    timeout: float | None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def smoke_test_candidate(
    candidate: Candidate,
    *,
    droidrun_bin: str,
    command: str,
    timeout: float | None,
    keep_temp_config: bool,
    configure_mode: str,
    vision: bool,
    reasoning: bool,
) -> SmokeTestResult:
    env = os.environ.copy()
    api_key: str | None = None
    if candidate.auth_mode != "oauth":
        env_keys = load_env_keys()
        for slot, env_var in SCRIPT_API_KEY_ENV_VARS.items():
            env_value = os.environ.get(env_var, "") or ""
            if env_value:
                env_keys[slot] = env_value
        if not candidate.env_slot:
            raise ValueError(f"Missing env slot for non-oauth candidate {candidate}")
        api_key = env_keys[candidate.env_slot]
        env_var = SCRIPT_API_KEY_ENV_VARS.get(candidate.env_slot)
        if env_var:
            env[env_var] = api_key

    temp_dir: Path | None = None
    temp_config_path: Path | None = None
    if configure_mode == "direct":
        temp_dir = Path(tempfile.mkdtemp(prefix="droidrun-bench-"))
        temp_config_path = temp_dir / "config.yaml"
        write_temp_config(temp_config_path)
        env["DROIDRUN_CONFIG"] = str(temp_config_path)
        try:
            configure_temp_config(temp_config_path, candidate, api_key)
        except Exception as exc:
            if temp_dir and not keep_temp_config:
                shutil.rmtree(temp_dir, ignore_errors=True)
            return SmokeTestResult(
                family_id=candidate.family_id,
                family_name=candidate.family_name,
                variant_id=candidate.variant_id,
                auth_mode=candidate.auth_mode,
                model=candidate.model,
                env_slot=candidate.env_slot,
                configure_ok=False,
                run_ok=False,
                elapsed_seconds=0.0,
                return_code=1,
                stderr_tail=tail_text(str(exc)),
                stdout_tail="",
                configure_mode=configure_mode,
            )
    else:
        configure_args = [
            droidrun_bin,
            "configure",
            "--provider",
            candidate.family_id,
            "--auth-mode",
            candidate.auth_mode,
            "--model",
            candidate.model,
        ]
        if api_key:
            configure_args.extend(["--api-key", api_key])
        configured = run_subprocess(configure_args, env=env, timeout=timeout)
        if configured.returncode != 0:
            return SmokeTestResult(
                family_id=candidate.family_id,
                family_name=candidate.family_name,
                variant_id=candidate.variant_id,
                auth_mode=candidate.auth_mode,
                model=candidate.model,
                env_slot=candidate.env_slot,
                configure_ok=False,
                run_ok=False,
                elapsed_seconds=0.0,
                return_code=configured.returncode,
                stderr_tail=tail_text(configured.stderr),
                stdout_tail=tail_text(configured.stdout),
                configure_mode=configure_mode,
            )

    run_args = [
        droidrun_bin,
        "run",
        command,
        "--vision" if vision else "--no-vision",
        "--reasoning" if reasoning else "--no-reasoning",
        "--no-stream",
    ]
    started = time.perf_counter()
    try:
        completed = run_subprocess(run_args, env=env, timeout=timeout)
        elapsed = time.perf_counter() - started
    except subprocess.TimeoutExpired as exc:
        elapsed = time.perf_counter() - started
        if temp_dir and not keep_temp_config:
            shutil.rmtree(temp_dir, ignore_errors=True)
        return SmokeTestResult(
            family_id=candidate.family_id,
            family_name=candidate.family_name,
            variant_id=candidate.variant_id,
            auth_mode=candidate.auth_mode,
            model=candidate.model,
            env_slot=candidate.env_slot,
            configure_ok=True,
            run_ok=False,
            elapsed_seconds=elapsed,
            return_code=124,
            stderr_tail=tail_text(exc.stderr or ""),
            stdout_tail=tail_text(exc.stdout or ""),
            configure_mode=configure_mode,
        )

    if temp_dir and not keep_temp_config:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return SmokeTestResult(
        family_id=candidate.family_id,
        family_name=candidate.family_name,
        variant_id=candidate.variant_id,
        auth_mode=candidate.auth_mode,
        model=candidate.model,
        env_slot=candidate.env_slot,
        configure_ok=True,
        run_ok=completed.returncode == 0,
        elapsed_seconds=elapsed,
        return_code=completed.returncode,
        stderr_tail=tail_text(completed.stderr),
        stdout_tail=tail_text(completed.stdout),
        configure_mode=configure_mode,
    )


def print_plan(candidates: list[Candidate]) -> None:
    print(f"Found {len(candidates)} model candidates with saved API keys.")
    for candidate in candidates:
        print(
            f"- {candidate.family_id}/{candidate.auth_mode}/{candidate.model} "
            f"[variant={candidate.variant_id}, key={candidate.env_slot}]"
        )


def print_summary(results: list[SmokeTestResult], output_path: Path) -> int:
    successes = [result for result in results if result.run_ok]
    failures = [result for result in results if not result.run_ok]

    print()
    print(f"Completed {len(results)} runs.")
    print(f"Successful runs: {len(successes)}")
    print(f"Failed runs: {len(failures)}")

    print()
    print(f"Results saved to {output_path}")

    if successes:
        print()
        print("Working models:")
        for result in successes:
            print(
                f"- {result.family_id}/{result.auth_mode}/{result.model} "
                f"(variant={result.variant_id})"
            )

    if failures:
        print()
        print("Failures:")
        for result in failures:
            reason = result.stderr_tail or result.stdout_tail or f"exit={result.return_code}"
            print(
                f"- {result.family_id}/{result.auth_mode}/{result.model}: "
                f"{reason.splitlines()[-1]}"
            )

    return 0 if successes else 1


def main() -> int:
    args = parse_args()
    allowed_families = {item.strip() for item in args.provider_family if item.strip()}
    allowed_models = {item.strip() for item in args.model if item.strip()}
    allowed_auth_modes = {item.strip() for item in args.auth_mode if item.strip()}

    candidates = list(iter_candidates(allowed_families, allowed_models, allowed_auth_modes))
    if not candidates:
        print("No benchmark candidates found.")
        print("Check that you have saved API keys for supported providers.")
        return 1

    print_plan(candidates)

    results: list[SmokeTestResult] = []
    for index, candidate in enumerate(candidates, start=1):
        print()
        print(
            f"[{index}/{len(candidates)}] Testing "
            f"{candidate.family_id}/{candidate.auth_mode}/{candidate.model}"
        )
        result = smoke_test_candidate(
            candidate,
            droidrun_bin=args.droidrun_bin,
            command=args.command,
            timeout=args.timeout,
            keep_temp_config=args.keep_temp_config,
            configure_mode=args.configure_mode,
            vision=args.vision,
            reasoning=args.reasoning,
        )
        results.append(result)
        status = "ok" if result.run_ok else "failed"
        print(f"Result: {status} in {result.elapsed_seconds:.2f}s (exit={result.return_code})")

    payload = {
        "command": args.command,
        "timeout_seconds": args.timeout,
        "vision": args.vision,
        "reasoning": args.reasoning,
        "results": [asdict(result) for result in results],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return print_summary(results, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
