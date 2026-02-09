---
name: droidrun-docs
description: DroidRun documentation reference. Use when users ask about DroidRun setup, configuration, SDK usage, CLI commands, device setup, agents, architecture, app cards, credentials, tracing, Docker, migration, structured output, or any DroidRun "how do I..." questions.
---

# DroidRun Documentation

DroidRun is an open-source (MIT) framework for controlling Android and iOS devices through LLM agents.
It enables mobile automation using natural language commands, with support for multiple LLM providers.

- **GitHub**: https://github.com/droidrun/droidrun
- **Docs site**: https://docs.droidrun.ai
- **License**: MIT
- **Install**: `uv tool install droidrun` (Google Gemini, OpenAI, Ollama, OpenRouter included by default)
- **Optional extras**: `anthropic`, `deepseek`, `langfuse`
- **Requires**: Python 3.11+, ADB, Portal APK on device
- The droidrun repo is cloned at `droidrun/`. You can check the source code for detailed information.

## Answering Questions

Read the relevant file(s) based on the user's question. Do not guess — always read the doc before answering.

| Topic | File |
|-------|------|
| Overview | overview.mdx |
| Quickstart | quickstart.mdx |
| **Concepts** | |
| Architecture & agents | concepts/architecture.mdx |
| Events & workflows | concepts/events-and-workflows.mdx |
| Prompts | concepts/prompts.mdx |
| Scripter agent | concepts/scripter-agent.mdx |
| Shared state | concepts/shared-state.mdx |
| **Features** | |
| App cards | features/app-cards.mdx |
| Credentials | features/credentials.mdx |
| Custom tools | features/custom-tools.mdx |
| Custom variables | features/custom-variables.mdx |
| Structured output | features/structured-output.mdx |
| Telemetry | features/telemetry.mdx |
| Tracing | features/tracing.mdx |
| **Guides** | |
| CLI usage | guides/cli.mdx |
| Device setup | guides/device-setup.mdx |
| Docker | guides/docker.mdx |
| Migration v3→v4 | guides/migration-v3-to-v4.mdx |
| **SDK** | |
| DroidAgent | sdk/droid-agent.mdx |
| ADB tools | sdk/adb-tools.mdx |
| iOS tools | sdk/ios-tools.mdx |
| Base tools | sdk/base-tools.mdx |
| Configuration | sdk/configuration.mdx |
| API reference | sdk/reference.mdx |
