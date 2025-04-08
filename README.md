# DroidRun

DroidRun is an innovative framework that connects your Android device with LLM agents, allowing you to control your device through natural language commands.

## Features

- Control your Android device using natural language
- Built on top of the powerful DroidMind framework
- Simple command-line interface
- Core UI interaction tools:
  - Tap on screen coordinates
  - Swipe gestures
  - Text input
  - Key presses
  - App launching

## Installation

```bash
# Using uv (recommended)
uv pip install droidrun

# Using pip
pip install droidrun
```

## Prerequisites

- Python 3.10 or higher
- Android Debug Bridge (adb) installed and in your PATH
- An Android device with USB debugging enabled

## Quick Start

1. Connect your Android device:
```bash
# Over USB
droidrun devices

# Over TCP/IP
droidrun connect 192.168.1.100
```

2. Run commands:
```bash
# Basic device control
droidrun run "Open the Settings app"
droidrun run "Take a screenshot"
droidrun run "Scroll down"
```

## Available Commands

- `droidrun devices` - List connected devices
- `droidrun connect <ip> [--port PORT]` - Connect to a device over TCP/IP
- `droidrun disconnect <serial>` - Disconnect from a device
- `droidrun run <command>` - Execute a natural language command

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 