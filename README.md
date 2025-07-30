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

<a href="https://www.producthunt.com/products/droidrun-framework-for-mobile-agent?embed=true&utm_source=badge-featured&utm_medium=badge&utm_source=badge-droidrun&#0045;framework&#0045;for&#0045;mobile&#0045;ai&#0045;agents" target="_blank"><img src="https://api.producthunt.com/widgets/embed-image/v1/featured.svg?post_id=983810&theme=light&t=1751740003156" alt="Droidrun&#0032;Framework&#0032;for&#0032;mobile&#0032;AI&#0032;Agents&#0032; - Droidrun&#0032;–The&#0032;Missing&#0032;Bridge&#0032;Between&#0032;LLMs&#0032;and&#0032;Mobile&#0032;Devices | Product Hunt" style="width: 200px; height: 43px;" width="200" height="43" /></a>



DroidRun is a powerful framework for controlling Android and iOS devices through LLM agents. It allows you to automate device interactions using natural language commands. [Checkout our benchmark results](https://droidrun.ai/benchmark)

## Why Droidrun?

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

[![Quickstart Video](https://img.youtube.com/vi/4WT7FXJah2I/0.jpg)](https://www.youtube.com/watch?v=4WT7FXJah2I)

## 🎬 Demo Videos

1. **Accommodation booking**: Let Droidrun search for an apartment for you

   <img src="https://media.droidrun.ai/Droidrun_Expedia.gif" alt="Droidrun Accommodation Booking Demo on Expedia" width="600">

<br>

2. **Trend Hunter**: Let Droidrun hunt down trending posts

   <img src="https://media.droidrun.ai/Droidrun_Reddit.gif" alt="Droidrun Trend Hunter Demo on Reddit" width="600">

<br>

3. **Streak Saver**: Let Droidrun save your streak on your favorite language learning app

   <img src="https://media.droidrun.ai/Droidrun_Duolingo.gif" alt="Droidrun Streak Saver Demo on Duolingo" width="600">


## 💡 Example Use Cases

- Automated UI testing of mobile applications
- Creating guided workflows for non-technical users
- Automating repetitive tasks on mobile devices
- Remote assistance for less technical users
- Exploring mobile UI with natural language commands

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