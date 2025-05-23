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

# DroidRun GUI

DroidRun GUI 是一个图形界面应用程序，它封装了 DroidRun 的功能，让用户可以通过简单的点击操作来控制 Android 设备。

## 功能特点

- 简单的图形用户界面
- 自动检测已连接的 Android 设备
- 支持多个 AI 模型（OpenAI GPT-4、Anthropic Claude、Google Gemini）
- 实时显示任务执行进度和结果
- 无需命令行操作

## 安装要求

- Python 3.8 或更高版本
- ADB（Android Debug Bridge）已安装并配置
- Android 设备已启用 USB 调试
- 至少一个 AI 模型的 API 密钥

## 安装步骤

1. 克隆仓库：
```bash
git clone https://github.com/droidrun/droidrun-gui.git
cd droidrun-gui
```

2. 安装依赖：
```bash
pip install -e .
```

3. 配置 API 密钥：
创建 `.env` 文件并添加你的 API 密钥：
```
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

## 使用方法

1. 启动应用程序：
```bash
droidrun-gui
```

2. 连接 Android 设备：
   - 使用 USB 线连接设备
   - 确保设备已启用 USB 调试
   - 点击"刷新设备列表"按钮

3. 执行任务：
   - 在文本框中输入任务描述
   - 选择要使用的 AI 模型
   - 点击"执行任务"按钮

## 常见问题

1. 设备未检测到
   - 确保设备已启用 USB 调试
   - 检查 USB 连接
   - 运行 `adb devices` 确认设备连接状态

2. API 密钥错误
   - 确保在 `.env` 文件中正确设置了 API 密钥
   - 检查 API 密钥是否有效

3. 任务执行失败
   - 检查任务描述是否清晰
   - 确保设备屏幕已解锁
   - 查看输出区域的错误信息

## 贡献

欢迎提交 Pull Request 或创建 Issue！

## 许可证

MIT License 