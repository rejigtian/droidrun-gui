# DroidRun 🤖

A powerful framework for controlling Android devices through LLM agents.

[![PyPI version](https://badge.fury.io/py/droidrun.svg)](https://badge.fury.io/py/droidrun)
[![Python Version](https://img.shields.io/pypi/pyversions/droidrun.svg)](https://pypi.org/project/droidrun/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚀 Quick Start

Install DroidRun using pip:

```bash
pip install droidrun
```

Basic usage example:

```python
from droidrun import Agent
from droidrun.llm import OpenAILLM

# Initialize the agent
agent = Agent(
    task="Open WhatsApp and send a message to John",
    llm=OpenAILLM(model="gpt-4"),
)

# Run the agent
agent.run()
```

## 🔧 Requirements

- Python 3.10 or higher
- Android Debug Bridge (ADB) installed and configured
- Connected Android device or emulator
- OpenAI API key (or other supported LLM provider)

## 📚 Documentation

For detailed documentation, visit [droidrun.readthedocs.io](https://droidrun.readthedocs.io/).

### Features

- 🤖 Control Android devices using natural language
- 📱 Support for multiple Android devices
- 🔌 Extensible LLM provider support (OpenAI, Anthropic, etc.)
- 🛠️ Rich API for custom automation tasks
- 📝 Detailed logging and error handling

## 💡 Examples

Check out the [examples directory](./examples) for more usage examples:

- WhatsApp automation
- App testing
- UI navigation
- Custom device actions

## 🛠️ Development

To set up the development environment:

```bash
# Clone the repository
git clone https://github.com/yourusername/droidrun.git
cd droidrun

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev,test]"
```

### Running Tests

```bash
pytest tests/
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Thanks to all contributors who have helped shape DroidRun
- Inspired by browser-use and other automation frameworks 