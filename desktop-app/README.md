# DroidRun Desktop

一个现代化的桌面应用程序，用于管理和控制 Android 设备的 DroidRun 自动化工具。

## ⚠️ macOS 用户必读

如果你使用 Homebrew 安装的 Python 3.13，运行前需要安装 Tkinter 支持：

```bash
brew install python-tk@3.13
```

**或者**下载 [python.org](https://www.python.org/downloads/) 的 Python 安装包（自带 Tkinter，推荐）。

详见：[故障排查.md](./故障排查.md#-modulenotfounderror-no-module-named-_tkinter)

---

## ✨ 特性

- 🎯 **可视化界面** - 简洁直观的现代化 UI，配有酷炫的 Android 机器人图标 🤖
- 📦 **开箱即用** - DroidRun 已内置，无需额外安装
- 🖥️ **跨平台支持** - 支持 macOS、Windows、Linux
- 📱 **设备管理** - 管理多个 Android 设备
- ⚡ **任务执行** - 使用自然语言执行自动化任务
- 📜 **任务历史** - 自动保存历史任务，快速重用
- 📋 **任务模板** - 10+ 预设常用任务模板
- 🛑 **停止控制** - 随时中断正在执行的任务
- ⚙️ **配置管理** - 管理 LLM API 密钥和设置
- 🛠️ **SDK 路径管理** - 自动检测或手动配置工具路径（根据平台显示不同选项）
- 🌓 **深色/浅色模式** - 支持外观切换

## 📦 安装

### 从源代码运行

#### 快速启动（推荐）

```bash
cd desktop-app
./run_dev.sh
```

此脚本会自动：
- 创建/激活虚拟环境
- 安装依赖
- 启动应用

**注意**：开发模式与打包版本行为**完全一致**，都通过 subprocess 调用系统安装的 `droidrun` CLI。

#### 手动启动

1. 克隆仓库并进入目录：
```bash
cd desktop-app
```

2. 创建虚拟环境：
```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

4. 运行应用：
```bash
python src/main.py
```

### 从可执行文件运行（推荐）

下载适合你系统的可执行文件并直接运行。

**✨ 已内置（无需安装）**：
- ✅ DroidRun 核心引擎
- ✅ Python 运行环境
- ✅ 所有依赖库

**🎯 智能环境检测**：
- 🔍 **自动检测 ADB** - 首次启动自动检查
- 📦 **安装向导** - 未检测到时提供：
  - 🚀 自动安装（推荐）- macOS/Linux 一键安装
  - ⚙️ 手动配置路径 - 已安装 ADB 但路径不标准
  - ⏭️ 跳过 - 稍后在设置中配置
- ✅ **智能保存** - 自动记住配置的路径

**⚙️ 首次启动需要配置**：
- 🔑 LLM API Key（在设置页面）

## 🔨 打包

### macOS

```bash
# 安装依赖
pip install -r requirements.txt

# 构建应用
python build.py

# 可执行文件位于: dist/DroidRun Desktop.app
```

创建 DMG 安装包：
```bash
brew install create-dmg

create-dmg \
  --volname "DroidRun Desktop" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --app-drop-link 600 185 \
  "DroidRun-Desktop.dmg" \
  "dist/DroidRun Desktop.app"
```

### Windows

```bash
# 安装依赖
pip install -r requirements.txt

# 构建应用
python build.py

# 可执行文件位于: dist\DroidRun Desktop.exe
```

## 💻 系统要求

### ✅ 已内置（打包版本自带）
- Python 3.13 运行环境
- DroidRun 核心引擎
- 所有 Python 依赖库

### ⚠️ 需要单独安装

#### 1. **ADB (Android Debug Bridge)** - 必需！

**为什么需要**：用于与 Android 设备通信，这是 DroidRun 工作的基础。

**安装方式**：

**macOS**:
```bash
# 推荐：使用 Homebrew
brew install android-platform-tools

# 验证安装
adb version
```

**Windows**:
1. 下载 [Android SDK Platform Tools](https://developer.android.com/studio/releases/platform-tools)
2. 解压到任意目录（如 `C:\platform-tools`）
3. 将该目录添加到系统 PATH
4. 重启命令提示符，运行 `adb version` 验证

**Linux**:
```bash
# Ubuntu/Debian
sudo apt-get install android-tools-adb

# Arch Linux
sudo pacman -S android-tools
```

**或者**：安装 [Android Studio](https://developer.android.com/studio)（自带 ADB）

#### 2. **LLM API Key** - 必需！

**支持的提供商**：
- Google Gemini（推荐，有免费额度）
- 智谱AI（国内推荐）
- OpenAI
- Anthropic
- DeepSeek
- Ollama（本地运行）

### 📱 Android 设备要求
- Android 7.0 (API 24) 或更高
- 开启 USB 调试模式
- USB 数据线（或无线 ADB 连接）

### ✅ 环境检查清单

在首次运行应用前，请确认：

```bash
# 1. 检查 ADB 是否安装
adb version
# 期望输出：Android Debug Bridge version x.x.x

# 2. 检查设备连接
adb devices
# 期望输出：至少一个设备显示为 "device" 状态

# 3. 测试设备通信
adb shell echo "Hello"
# 期望输出：Hello
```

如果以上命令都成功，说明环境已就绪！✅

## 🚀 使用指南

### 1. 首次启动

首次启动应用时，会自动进行环境检测：

#### 步骤 1：ADB 环境检测（自动）

应用会自动检测 ADB 是否已安装：

**✅ 如果已安装**：
- 自动识别并保存 ADB 路径
- 直接进入主界面

**❌ 如果未安装**：
- 显示 ADB 安装向导，提供三种选项：
  
  1. **🚀 自动安装（推荐）**
     - macOS: 通过 Homebrew 自动安装
     - Linux: 通过包管理器自动安装
     - Windows: 提供下载链接和配置指南
  
  2. **⚙️ 手动配置路径**
     - 如果你已经安装了 ADB（如 Android Studio）
     - 手动指定 ADB 可执行文件路径
     - 应用会验证路径并保存
  
  3. **⏭️ 跳过**
     - 稍后在"设置"页面配置
     - 功能会受限，直到配置 ADB

#### 步骤 2：配置 API Key（必需）

进入主界面后：
- 点击"⚙️ 设置"页面
- 选择 LLM 提供商（Google Gemini / 智谱AI 等）
- 输入对应的 API Key
- 点击"保存设置"

#### 步骤 3：连接设备

- USB 连接 Android 设备
- 开启"USB 调试"模式
- 在"📱 设备管理"页面确认设备已连接

**💡 提示**：
- DroidRun 已内置到应用中，无需额外安装
- SDK 路径（Python、Homebrew）会自动检测，通常无需手动配置
- 如果自动检测失败，可以在"设置"页面手动配置

### 2. 设备管理

在"设备管理"页面：
- 查看所有连接的设备
- 检查 Portal 应用状态
- 安装或更新 Portal 应用
- 测试设备连接

### 3. 执行任务

在"执行任务"页面：

#### 基本使用
1. 选择目标设备（或自动检测）
2. 输入任务描述，例如："打开设置并告诉我Android版本"
3. 可选：启用视觉功能或推理模式
4. 点击"▶️ 执行任务"
5. 执行过程中可点击"⏹️ 停止"按钮中断任务

#### 📜 使用历史任务
- 点击"📜 历史任务"按钮查看之前执行过的任务
- 支持搜索、一键重用、删除历史记录
- 显示执行次数和成功/失败状态

#### 📋 使用任务模板
- 点击"📋 任务模板"按钮浏览预设模板
- 10+ 常用任务模板（打开应用、发送消息、搜索等）
- 按分类筛选（基础操作、社交、办公、系统、娱乐）
- 点击"使用"自动填充到输入框

### 4. 配置设置

在"设置"页面：

#### LLM 设置
- 配置 LLM API 密钥（Google、OpenAI、Anthropic、DeepSeek、智谱AI）
- 选择默认的 LLM 提供商
- 选择模型（Gemini/智谱AI 模型）

**推荐配置：**
- 国内用户：智谱AI（访问快，中文好）
- 国外用户：Gemini 1.5-flash（便宜快速）
- 本地免费：Ollama（无需 API Key）

#### SDK 路径设置 ⭐️ 新功能
- **自动检测工具路径**：一键检测 ADB、Python、Homebrew
- **手动配置路径**：解决从 Applications 启动时的路径问题
- **路径验证**：确保工具可用并显示版本信息
- **一键安装 ADB**：📦 如果在向导中跳过，可在此安装
- **重置功能**：恢复到自动检测状态

**每个工具路径旁的按钮：**
- 📁 **浏览** - 手动选择文件
- 🔍 **检测** - 自动查找路径
- ✓ **验证** - 验证路径有效性
- 📦 **安装** - 一键安装工具（仅 ADB）
- ↺ **重置** - 清除配置

**使用方法：**
1. 滚动到"SDK 路径设置"部分
2. 点击"🔍 自动检测所有路径"
3. 验证所有工具显示 ✅ 已找到
4. **如果 ADB 未找到**：点击 📦 按钮一键安装
5. 点击"💾 保存设置"

**为什么需要这个功能？**
- 从 Applications 启动和命令行启动的环境变量不同
- 自动检测可以找到工具的绝对路径
- 如果在安装向导中选择"跳过"，可以稍后在此安装
- 确保无论从哪里启动应用都能正常工作

---

## 🖥️ 平台差异说明

### macOS 🍎

**显示的 SDK 路径配置**：
- ✅ ADB 路径（带 📦 安装按钮）
- ✅ Python 路径（仅用于调试）
- ✅ **Homebrew 路径**（带 📦 安装按钮）⭐️ macOS 特有

**特点**：
- 可以一键安装 Homebrew
- 通过 Homebrew 安装 ADB 等工具
- 完整的包管理器支持

### Windows 🪟

**显示的 SDK 路径配置**：
- ✅ ADB 路径（带 📦 安装按钮）
- ✅ Python 路径（仅用于调试）
- ❌ **无 Homebrew 配置**（Windows 不支持）

**特点**：
- 界面更简洁
- ADB 安装引导提供 Windows 专用下载链接
- 可能支持 Chocolatey（未来）

### Linux 🐧

**显示的 SDK 路径配置**：
- ✅ ADB 路径（带 📦 安装按钮）
- ✅ Python 路径（仅用于调试）
- ✅ Homebrew 路径（部分发行版支持）

**特点**：
- 通过系统包管理器安装 ADB（apt/yum/pacman）
- 根据发行版显示不同选项

**详细说明**：见 [跨平台界面说明.md](./跨平台界面说明.md)

---

## 📁 项目结构

```
desktop-app/
├── src/
│   ├── main.py              # 主程序入口
│   ├── ui/                  # UI 组件
│   │   ├── main_window.py   # 主窗口
│   │   ├── install_wizard.py  # 安装向导
│   │   ├── task_panel.py    # 任务面板
│   │   ├── device_manager.py  # 设备管理
│   │   └── settings.py      # 设置界面
│   ├── core/                # 核心功能
│   │   ├── installer.py     # 安装器
│   │   ├── task_runner.py   # 任务运行器
│   │   └── device_checker.py  # 设备检查器
│   └── utils/               # 工具模块
│       ├── config.py        # 配置管理
│       ├── task_history.py  # 任务历史
│       └── task_templates.py # 任务模板
├── resources/               # 资源文件
├── requirements.txt         # 依赖列表
├── build.py                 # 构建脚本
└── README.md               # 本文档
```

## 🎨 技术栈

- **UI 框架**: CustomTkinter（现代化的 Tkinter）
- **核心库**: DroidRun、ADBUtils
- **打包工具**: PyInstaller

## 🔍 调试指南

### 开发模式与打包模式一致性

本应用的**开发模式**和**打包模式**行为完全一致：

- ✅ 都通过 subprocess 调用系统安装的 `droidrun` CLI
- ✅ 都使用相同的配置文件路径（`~/.droidrun/config.yaml`）
- ✅ 都显示相同的命令和环境变量

这意味着你可以通过开发模式来调试任何问题！

### 调试步骤

1. **启动开发模式**：
```bash
./run_dev.sh
# 或手动: python src/main.py
```

2. **查看完整命令**：
   应用会在输出中显示完整的可执行命令，包括：
   - 配置文件路径（智谱AI）
   - 环境变量（其他提供商）
   - 完整的 droidrun 命令

3. **在终端手动运行**：
   复制应用显示的命令，直接在终端运行：
```bash
# 示例 - 智谱AI
cat ~/.droidrun/config.yaml  # 查看配置
droidrun run "打开设置" --device 5ad854b8

# 示例 - Google Gemini
export GOOGLE_API_KEY='your_key'
droidrun run "打开设置" --provider GoogleGenAI --model gemini-1.5-flash
```

4. **对比输出**：
   - 如果终端运行成功，但应用失败 → 检查应用日志
   - 如果都失败 → DroidRun 或配置问题
   - 如果都成功 → 应用工作正常

### 常用调试命令

```bash
# 检查 droidrun 是否安装
which droidrun
droidrun --help

# 检查配置文件
cat ~/.droidrun/config.yaml

# 检查环境变量
echo $GOOGLE_API_KEY
echo $ZHIPUAI_API_KEY

# 检查设备连接
adb devices

# 查看应用日志
# 应用输出窗口会显示所有日志
```

## 🐛 故障排查

### 应用无法启动

1. 检查 Python 版本：`python --version`（需要 3.11+）
2. 重新安装依赖：`pip install -r requirements.txt`
3. 查看终端输出的错误信息

### 找不到设备

1. 确保设备已连接并启用 USB 调试
2. 运行 `adb devices` 检查设备是否被识别
3. 在设备上授权此计算机

### Portal 安装失败

1. 确保设备已授权 USB 调试
2. 手动运行：`droidrun setup --device DEVICE_SERIAL`
3. 检查网络连接（需要下载 Portal APK）

### API 密钥无效

1. 检查密钥是否正确
2. 确认 API 密钥有足够的配额
3. 尝试使用其他 LLM 提供商（如智谱AI或Ollama）

### 任务无法停止

1. 等待 3-5 秒（底层操作可能需要时间）
2. 检查设备状态是否正常
3. 必要时重启应用

### 历史记录/模板不显示

1. 检查文件是否存在：`~/.droidrun-desktop/task_history.json`
2. 删除损坏的文件后重启应用（会自动重建）
3. 检查应用是否有读写权限

## 📚 相关资源

- [DroidRun 官方文档](https://docs.droidrun.ai)
- [CustomTkinter 文档](https://customtkinter.tomschimansky.com/)
- [PyInstaller 文档](https://pyinstaller.org/)

## 📦 打包应用

### 为最终用户打包

如果您想将应用打包成可执行文件分发给用户：

```bash
# 安装打包依赖
pip install pyinstaller

# 执行打包
python build.py
```

**输出文件**：
- **macOS**: `dist/DroidRun-Desktop.app/`
- **Windows**: `dist/DroidRun-Desktop.exe`
- **Linux**: `dist/DroidRun-Desktop`

**macOS 用户注意**：打包后需要修复签名问题
```bash
./fix_macos_app.sh
```

详细说明：
- [打包指南.md](打包指南.md)
- [macOS打包问题修复.md](macOS打包问题修复.md)

### 用户安装指南

打包后的应用分发给用户时，请附带 [用户安装指南.md](用户安装指南.md)，帮助用户快速上手。

---

## 🤝 贡献

欢迎贡献！请提交 Issue 或 Pull Request。

## 📤 分发应用

### 🚀 一键打包发布

使用一键脚本快速创建分发包：

```bash
# 创建 v1.0.0 版本的发布包
./quick_release.sh 1.0.0
```

这会自动完成：
1. ✅ 构建应用
2. ✅ 修复 macOS 签名
3. ✅ 打包一键修复脚本到 DMG（用户双击即可解决权限问题）
4. ✅ 创建 ZIP 压缩包
5. ✅ 创建 DMG 安装包（如果安装了 create-dmg）
6. ✅ 生成校验和、安装说明、发布说明

### 📦 分发文件

打包完成后，在 `dist/` 目录会生成：

- `SmartDroid-1.0.0-macOS.dmg` - DMG 安装包（推荐，内含一键修复脚本）
- `SmartDroid-1.0.0-macOS.zip` - ZIP 压缩包（备选）
- `安装说明.txt` - 给用户的安装指南
- `RELEASE_NOTES.txt` - 发布说明
- `checksums.txt` - SHA-256 校验和

### 🍎 macOS 分发方案

**当前使用：一键修复脚本（推荐开源项目）**

DMG 中自动包含 `修复权限.command` 脚本，用户只需：
1. 打开 DMG
2. 双击 `修复权限.command` 脚本
3. 输入管理员密码
4. 完成！应用可以正常运行

**优点**：
- ✅ 无需 Apple Developer 账号
- ✅ 用户操作简单（双击一次）
- ✅ 完全自动化

**其他方案**：
- 🏢 商业分发：代码签名 + 公证（需要 $99/年 开发者账号）
- 👨‍💻 技术用户：手动终端命令

详见：[macOS分发方案对比.md](./macOS分发方案对比.md)

### 📖 详细分发指南

查看完整的分发流程和最佳实践：

```bash
cat 分发指南.md
```

包含：
- 📦 快速分发（ZIP）
- 💿 创建 DMG 安装包
- 📖 用户安装文档模板
- 🪟 Windows 打包指南
- 📊 版本管理和发布流程

---

## 📄 许可证

MIT License

## 🆘 获取帮助

- [Discord 社区](https://discord.gg/ZZbKEZZkwK)
- [GitHub Issues](https://github.com/droidrun/droidrun/issues)
- [官方网站](https://droidrun.ai)

---

**使用愉快！** 🎉

