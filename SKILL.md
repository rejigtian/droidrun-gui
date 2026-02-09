---
name: droidrun-docs
description: DroidRun documentation reference. Use when users ask about DroidRun setup, configuration, SDK usage, CLI commands, device setup, agents, architecture, app cards, credentials, tracing, Docker, migration, structured output, or any DroidRun "how do I..." questions.
---

# DroidRun

DroidRun is an open-source (MIT) framework for controlling Android and iOS devices through LLM agents.
It enables mobile automation using natural language commands.

- **GitHub**: https://github.com/droidrun/droidrun
- **Docs site**: https://docs.droidrun.ai
- **License**: MIT
- **Install**: `uv tool install droidrun` (Google Gemini, OpenAI, Ollama, OpenRouter included by default)
- **Optional extras**: `anthropic`, `deepseek`, `langfuse`
- **Requires**: Python 3.11+, ADB, Portal APK on device

## Architecture

DroidRun uses a multi-agent architecture coordinated by `DroidAgent`:

- **Reasoning mode** (`reasoning=True`): Manager plans → Executor acts → loop until done
- **Direct mode** (`reasoning=False`): CodeActAgent generates and executes Python code directly

Key agents: ManagerAgent (planning), ExecutorAgent (actions), CodeActAgent (direct execution),
ScripterAgent (off-device computation), StructuredOutputAgent (typed data extraction).

Atomic actions available to agents: `click`, `long_press`, `type`, `system_button`, `swipe`,
`open_app`, `get_state`, `take_screenshot`, `remember`, `complete`.

## Repository Structure

Source code is at `droidrun/` (Python package). Key locations:

| Path | Description |
|------|-------------|
| `droidrun/agent/droid/` | DroidAgent orchestrator |
| `droidrun/agent/codeact/` | CodeActAgent (direct mode) |
| `droidrun/agent/scripter/` | ScripterAgent (off-device scripts) |
| `droidrun/agent/oneflows/` | StructuredOutputAgent |
| `droidrun/agent/utils/` | Tools, executor, tracing, async utils |
| `droidrun/tools/` | Device tools (ADB, iOS, portal client) |
| `droidrun/cli/` | CLI entry point (click-based) |
| `droidrun/config/prompts/` | Jinja2 prompt templates per agent |
| `droidrun/config/app_cards/` | App-specific instruction cards |
| `droidrun/credential_manager/` | YAML-based credential storage |
| `droidrun/telemetry/` | Phoenix tracing integration |

## Documentation

Read the relevant file(s) from `docs/v4/` based on the user's question. Do not guess — always
read the doc before answering.

| Topic | File |
|-------|------|
| Overview | docs/v4/overview.mdx |
| Quickstart | docs/v4/quickstart.mdx |
| **Concepts** | |
| Architecture & agents | docs/v4/concepts/architecture.mdx |
| Events & workflows | docs/v4/concepts/events-and-workflows.mdx |
| Prompts | docs/v4/concepts/prompts.mdx |
| Scripter agent | docs/v4/concepts/scripter-agent.mdx |
| Shared state | docs/v4/concepts/shared-state.mdx |
| **Features** | |
| App cards | docs/v4/features/app-cards.mdx |
| Credentials | docs/v4/features/credentials.mdx |
| Custom tools | docs/v4/features/custom-tools.mdx |
| Custom variables | docs/v4/features/custom-variables.mdx |
| Structured output | docs/v4/features/structured-output.mdx |
| Telemetry | docs/v4/features/telemetry.mdx |
| Tracing | docs/v4/features/tracing.mdx |
| **Guides** | |
| CLI usage | docs/v4/guides/cli.mdx |
| Device setup | docs/v4/guides/device-setup.mdx |
| Docker | docs/v4/guides/docker.mdx |
| Migration v3→v4 | docs/v4/guides/migration-v3-to-v4.mdx |
| **SDK** | |
| DroidAgent | docs/v4/sdk/droid-agent.mdx |
| ADB tools | docs/v4/sdk/adb-tools.mdx |
| iOS tools | docs/v4/sdk/ios-tools.mdx |
| Base tools | docs/v4/sdk/base-tools.mdx |
| Configuration | docs/v4/sdk/configuration.mdx |
| API reference | docs/v4/sdk/reference.mdx |

For deeper implementation details, check the source code directly in `droidrun/`.
