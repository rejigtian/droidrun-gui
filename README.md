# DroidRun GUI 使用说明

DroidRun GUI 是对 droidrun 命令行工具的可视化封装，支持一键操作 Android 设备，无需命令行基础。

## 主要功能
- 多设备管理与选择
- 任务输入与模板快捷填充
- 历史任务一键复用
- AI模型与API Key管理
- Portal APK/ADBKeyboard自动安装与环境检测
- 任务执行进度与结果实时输出

## 启动方式
1. 安装依赖并激活虚拟环境：
   ```bash
   pip install -r requirements.txt
   source ../venv/bin/activate
   ```
2. 一键运行 GUI：
   ```bash
   ./run_local_gui.sh
   ```
   或手动：
   ```bash
   PYTHONPATH=. python3 droidrun_gui/gui_main.py
   ```

## 亮点体验
- 支持中文/英文任务输入，自动适配输入法
- Portal APK/ADBKeyboard 一键安装与切换
- 任务执行全程可视化，历史可追溯

---

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

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://api.producthunt.com/widgets/embed-image/v1/top-post-badge.svg?post_id=983810&theme=dark&period=daily&t=1753948032207">
  <source media="(prefers-color-scheme: light)" srcset="https://api.producthunt.com/widgets/embed-image/v1/top-post-badge.svg?post_id=983810&theme=neutral&period=daily&t=1753948125523">
  <a href="https://www.producthunt.com/products/droidrun-framework-for-mobile-agent?embed=true&utm_source=badge-top-post-badge&utm_medium=badge&utm_source=badge-droidrun" target="_blank"><img src="https://api.producthunt.com/widgets/embed-image/v1/top-post-badge.svg?post_id=983810&theme=neutral&period=daily&t=1753948125523" alt="Droidrun - Give&#0032;AI&#0032;native&#0032;control&#0032;of&#0032;physical&#0032;&#0038;&#0032;virtual&#0032;phones&#0046; | Product Hunt" style="width: 200px; height: 54px;" width="200" height="54" /></a>
</picture>



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

   [![Droidrun Accommodation Booking Demo](https://img.youtube.com/vi/VUpCyq1PSXw/0.jpg)](https://youtu.be/VUpCyq1PSXw)

<br>

2. **Trend Hunter**: Let Droidrun hunt down trending posts

   [![Droidrun Trend Hunter Demo](https://img.youtube.com/vi/7V8S2f8PnkQ/0.jpg)](https://youtu.be/7V8S2f8PnkQ)

<br>

3. **Streak Saver**: Let Droidrun save your streak on your favorite language learning app

   [![Droidrun Streak Saver Demo](https://img.youtube.com/vi/B5q2B467HKw/0.jpg)](https://youtu.be/B5q2B467HKw)


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