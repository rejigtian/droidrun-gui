# DroidRun Desktop 快速开始

## ⚠️ 重要提示

如果你使用 **Homebrew 安装的 Python 3.13**，需要先安装 Tkinter 支持：

```bash
# 安装 Tkinter 支持（必需！）
brew install python-tk@3.13
```

或者使用 [python.org](https://www.python.org/downloads/) 的 Python 安装包（自带 Tkinter）。

详见：[故障排查.md](./故障排查.md)

---

## 🚀 3分钟快速体验

### 步骤0: 确保 Tkinter 可用（首次）

```bash
# 测试 Tkinter 是否可用
python3 -c "import tkinter; print('✅ Tkinter 可用')"

# 如果报错，执行：
brew install python-tk@3.13
```

### 步骤1: 安装依赖（首次）

```bash
# 进入目录
cd /Users/rejig/myproject/droidrun/desktop-app

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 步骤2: 运行应用

```bash
# 确保虚拟环境已激活
source venv/bin/activate

# 运行应用
python src/main.py
```

### 步骤3: 首次使用

1. **安装向导**
   - 应用会自动检查环境
   - 如果 DroidRun 未安装，会提供安装选项
   - 推荐选择 "pipx" 安装方式

2. **连接设备**
   - 进入"设备管理"页面
   - 点击"刷新设备"
   - 确保设备显示在列表中

3. **安装 Portal**
   - 在设备卡片中点击"安装 Portal"
   - 等待安装完成

4. **执行第一个任务**
   - 进入"执行任务"页面
   - 方法1：手动输入任务 `打开设置`
   - 方法2：点击"📋 任务模板"选择预设任务
   - 点击"▶️ 执行任务"
   - 执行中可点击"⏹️ 停止"中断

---

## 📋 系统要求

- **Python**: 3.11 或更高
- **操作系统**: macOS 10.14+ 或 Windows 10+
- **ADB**: Android Debug Bridge
- **设备**: Android 设备，已启用 USB 调试

---

## 💡 常见问题

### Q: 找不到 Python 3.11+？

```bash
# macOS
brew install python@3.11

# 验证
python3 --version
```

### Q: 虚拟环境激活后如何退出？

```bash
deactivate
```

### Q: 如何重新安装依赖？

```bash
pip install -r requirements.txt --force-reinstall
```

### Q: 应用闪退怎么办？

在终端运行应用查看错误信息：
```bash
cd /Users/rejig/myproject/droidrun/desktop-app
source venv/bin/activate
python src/main.py
```

---

## 🎨 界面预览

### 主界面
- **侧边栏**: 导航菜单
- **主内容区**: 功能面板
- **外观切换**: 支持深色/浅色模式

### 功能页面

1. **首页** - 欢迎页和快速开始
2. **设备管理** - 查看和管理连接的设备
3. **执行任务** - 输入任务并执行
   - 📜 历史任务：查看并重用历史任务
   - 📋 任务模板：10+ 预设任务模板
   - ⏹️ 停止按钮：随时中断任务
4. **设置** - 配置 API 密钥和偏好设置

---

## 🔧 高级用法

### 自定义配置

配置文件位置：`~/.droidrun-desktop/config.json`

```json
{
  "google_api_key": "your-key",
  "openai_api_key": "your-key",
  "default_provider": "GoogleGenAI",
  "max_steps": 15
}
```

### 打包成可执行文件

```bash
# 安装打包依赖
pip install pyinstaller

# 运行构建脚本
python build.py

# 可执行文件位于 dist/ 目录
```

---

## 📚 完整文档

- [README.md](./README.md) - 详细使用说明
- [桌面应用开发指南.md](../桌面应用开发指南.md) - 开发指南
- [使用指南.md](../使用指南.md) - DroidRun 完整指南

---

## 🆘 需要帮助？

- 💬 查看 [文档导航.md](../文档导航.md)
- 🐛 提交 [GitHub Issue](https://github.com/droidrun/droidrun/issues)
- 💡 加入 [Discord 社区](https://discord.gg/ZZbKEZZkwK)

---

**开始使用 DroidRun Desktop！** 🎉

