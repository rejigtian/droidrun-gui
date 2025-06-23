<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./static/droidrun-dark.png">
  <source media="(prefers-color-scheme: light)" srcset="./static/droidrun.png">
  <img src="./static/droidrun.png"  width="full">
</picture>

[![GitHub stars](https://img.shields.io/github/stars/droidrun/droidrun?style=social)](https://github.com/droidrun/droidrun/stargazers)
[![Discord](https://img.shields.io/discord/1360219330318696488?color=7289DA&label=Discord&logo=discord&logoColor=white)](https://discord.gg/ZZbKEZZkwK)
[![Documentation](https://img.shields.io/badge/Documentation-📕-blue)](https://docs.droidrun.ai)
[![Benchmark](https://img.shields.io/badge/Benchmark-🏅-teal)](https://droidrun.ai/benchmark)
[![Twitter Follow](https://img.shields.io/twitter/follow/droid_run?style=social)](https://x.com/droid_run)



DroidRun is a powerful framework for controlling Android and iOS devices through LLM agents. It allows you to automate device interactions using natural language commands. [Checkout our benchmark results](https://droidrun.ai/benchmark)

- 🤖 Control Android and iOS devices with natural language commands
- 🔀 Supports multiple LLM providers (OpenAI, Anthropic, Gemini, Ollama, DeepSeek)
- 🧠 Planning capabilities for complex multi-step tasks
- 💻 Easy to use CLI with enhanced debugging features
- 🐍 Extendable Python API for custom automations
- 📸 Screenshot analysis for visual understanding of the device
- 🫆 Execution tracing with Arize Phoenix

## 📦 Installation

```bash
pip install droidrun
```

## 🚀 Quickstart
Read on how to get droidrun up and running within seconds in [our docs](https://docs.droidrun.ai/v3/quickstart)!


## 🎬 Demo Videos

1. **Shopping Assistant**: Watch how DroidRun searches Amazon for headphones and sends the top 3 products to a colleague on WhatsApp.
   
   Prompt: "Go to Amazon, search for headphones and write the top 3 products to my colleague on WhatsApp."
   
   [![Shopping Assistant Demo](https://img.youtube.com/vi/VQK3JcifgwU/0.jpg)](https://www.youtube.com/watch?v=VQK3JcifgwU)

2. **Social Media Automation**: See DroidRun open X (Twitter) and post "Hello World".
   
   Prompt: "Open up X and post Hello World."
   
   [![Social Media Automation Demo](https://img.youtube.com/vi/i4-sDQhzt_M/0.jpg)](https://www.youtube.com/watch?v=i4-sDQhzt_M)

## 💡 Example Use Cases

- Automated UI testing of mobile applications
- Creating guided workflows for non-technical users
- Automating repetitive tasks on mobile devices
- Remote assistance for less technical users
- Exploring mobile UI with natural language commands

## 🗺️ Roadmap

### 🤖 Agent:
- **Improve memory**: Enhance context retention for complex multi-step tasks
- **Expand planning capabilities**: Add support for more complex reasoning strategies
- **Add Integrations**: Support more LLM providers and agent frameworks (LangChain, Agno etc.)

### ⚙️ Automations:
- **Create Automation Scripts**: Generate reusable scripts from agent actions that can be scheduled or shared

### ☁️ Cloud:
- **Hosted version**: Remote device control via web interface without local setup
- **Add-Ons**: Marketplace for extensions serving specific use cases
- **Proxy Hours**: Cloud compute time with tiered pricing for running automations
- **Droidrun AppStore**: Simple installation of Apps on your hosted devices

## 👥 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details. 

## Security Checks

To ensure the security of the codebase, we have integrated security checks using `bandit` and `safety`. These tools help identify potential security issues in the code and dependencies.

### Running Security Checks

Before submitting any code, please run the following security checks:

1. **Bandit**: A tool to find common security issues in Python code.
   ```bash
   bandit -r droidrun
   ```

2. **Safety**: A tool to check your installed dependencies for known security vulnerabilities.
   ```bash
   safety scan
   ```