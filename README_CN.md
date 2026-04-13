# DroidRun - Android/iOS 智能自动化框架

<div align="center">

[![文档](https://img.shields.io/badge/文档-📕-0D9373?style=for-the-badge)](https://docs.droidrun.ai)
[![云端](https://img.shields.io/badge/云端-☁️-0D9373?style=for-the-badge)](http://cloud.droidrun.ai)

[![GitHub stars](https://img.shields.io/github/stars/droidrun/droidrun?style=social)](https://github.com/droidrun/droidrun/stargazers)
[![Discord](https://img.shields.io/discord/1360219330318696488?color=white&label=Discord&logo=discord&logoColor=white)](https://discord.gg/ZZbKEZZkwK)
[![基准测试](https://img.shields.io/badge/基准测试-91.4﹪-white)](https://droidrun.ai/benchmark)

</div>

---

## 🌟 什么是 DroidRun？

DroidRun 是一个强大的框架，通过 LLM（大语言模型）代理控制 Android 和 iOS 设备。它允许你使用**自然语言命令**自动化设备交互。[查看我们的基准测试结果](https://droidrun.ai/benchmark)

简单来说：**用人类语言命令你的手机做事**！

---

## ✨ 为什么选择 DroidRun？

- 🤖 **自然语言控制** - 用日常语言控制 Android 和 iOS 设备
- 🔀 **多 LLM 支持** - 支持 OpenAI、Anthropic、Gemini、Ollama、DeepSeek 等
- 🧠 **智能规划** - 自动分解复杂的多步骤任务
- 💻 **简单易用** - 命令行工具，增强的调试功能
- 🐍 **可扩展** - Python API，自定义自动化
- 📸 **视觉理解** - 截图分析，理解设备界面
- 🫆 **执行追踪** - 使用 Arize Phoenix 追踪执行过程

---

## 📦 快速安装

```bash
# 使用 uv (推荐，更快)
uv tool install 'droidrun[google,anthropic,openai,deepseek,ollama]'

# 或使用 pip
pip install 'droidrun[google,anthropic,openai,deepseek,ollama]'
```

---

## 🚀 3分钟快速开始

### 1️⃣ 安装 Portal 应用到设备

```bash
# 自动下载并安装
droidrun setup
```

### 2️⃣ 测试连接

```bash
droidrun ping
# 应该看到: ✓ Portal is running
```

### 3️⃣ 设置 API 密钥

```bash
# Google Gemini (推荐)
export GOOGLE_API_KEY=your-api-key

# 或 OpenAI
export OPENAI_API_KEY=your-api-key

# 或 Anthropic Claude
export ANTHROPIC_API_KEY=your-api-key
```

### 4️⃣ 运行你的第一个命令

```bash
# 简单任务
droidrun "打开设置"

# 复杂任务
droidrun "打开设置并告诉我Android版本"

# 使用视觉功能
droidrun "当前屏幕显示什么？" --vision

# 多步骤任务（推理模式）
droidrun "找到联系人John并发送邮件" --reasoning
```

---

## 🎬 演示视频

### 1. 住宿预订：让 Droidrun 帮你搜索公寓

[![Droidrun 住宿预订演示](https://img.youtube.com/vi/VUpCyq1PSXw/0.jpg)](https://youtu.be/VUpCyq1PSXw)

### 2. 趋势猎手：让 Droidrun 寻找热门帖子

[![Droidrun 趋势猎手演示](https://img.youtube.com/vi/7V8S2f8PnkQ/0.jpg)](https://youtu.be/7V8S2f8PnkQ)

### 3. 打卡助手：让 Droidrun 保存你在语言学习应用中的连续打卡

[![Droidrun 打卡助手演示](https://img.youtube.com/vi/B5q2B467HKw/0.jpg)](https://youtu.be/B5q2B467HKw)

---

## 💡 使用场景

- ✅ **自动化 UI 测试** - 移动应用的自动化测试
- ✅ **工作流程自动化** - 为非技术用户创建引导式工作流程
- ✅ **重复任务自动化** - 自动化设备上的重复性任务
- ✅ **远程协助** - 为技术水平较低的用户提供远程协助
- ✅ **UI 探索** - 使用自然语言命令探索移动界面
- ✅ **社交媒体自动化** - 自动发帖、点赞、评论等
- ✅ **数据采集** - 从应用中提取结构化数据
- ✅ **性能监控** - 自动检查应用性能和状态

---

## 📚 详细文档

本项目提供了完整的中文文档：

### 📖 主要文档

1. **[使用指南.md](./使用指南.md)** - 完整的使用指南
   - 安装步骤详解
   - 基础和高级使用
   - 故障排查
   - 实用示例

2. **[快速参考.md](./快速参考.md)** - 命令速查手册
   - 常用命令速查
   - CLI 和 Python API 速查
   - 故障排查速查表
   - 最佳实践

### 🎓 示例代码

`examples/` 目录包含丰富的示例：

1. **[basic_example.py](./examples/basic_example.py)** - 基础示例
   - 简单任务执行
   - 视觉功能使用
   - 多步骤任务
   - 推理模式

2. **[structured_output_example.py](./examples/structured_output_example.py)** - 结构化输出
   - 提取电池信息
   - 获取设备信息
   - 通知摘要
   - 自定义数据提取

3. **[multi_device_example.py](./examples/multi_device_example.py)** - 多设备控制
   - 并行控制多个设备
   - 不同任务分配
   - 批量健康检查

### 🚀 快速启动工具

运行快速启动脚本，自动检查环境并引导你使用：

```bash
# Linux/macOS
./start.sh

# Windows
start.bat
```

---

## 🔥 使用示例

### 命令行 (CLI)

```bash
# 基础命令
droidrun "打开设置"
droidrun "检查电池电量"

# 指定 LLM 提供商
droidrun "打开设置" --provider GoogleGenAI --model models/gemini-2.5-flash
droidrun "检查电池" --provider OpenAI --model gpt-4o

# 启用视觉和推理
droidrun "描述当前屏幕" --vision
droidrun "找联系人John并发邮件" --reasoning

# 调试模式
droidrun "复杂任务" --debug --save-trajectory action

# 多设备
droidrun "清除通知" --device emulator-5554
```

### Python API

```python
import asyncio
from droidrun import DroidAgent
from droidrun.config_manager.config_manager import DroidrunConfig

async def main():
    # 创建配置
    config = DroidrunConfig()
    
    # 创建代理
    agent = DroidAgent(
        goal="打开设置并检查电池电量",
        config=config,
    )
    
    # 运行代理
    result = await agent.run()
    
    # 查看结果
    print(f"成功: {result.success}")
    print(f"结果: {result.reason}")

asyncio.run(main())
```

### 结构化输出

```python
from pydantic import BaseModel, Field

class BatteryInfo(BaseModel):
    level: int = Field(description="电池电量百分比")
    is_charging: bool = Field(description="是否正在充电")

agent = DroidAgent(
    goal="检查电池状态",
    config=config,
    output_schema=BatteryInfo
)

result = await agent.run()
battery: BatteryInfo = result.structured_output
print(f"电量: {battery.level}%")
print(f"充电中: {battery.is_charging}")
```

### 多设备并行控制

```python
from adbutils import adb

async def control_device(serial, task):
    device_config = DeviceConfig(serial=serial)
    config = DroidrunConfig(device=device_config)
    agent = DroidAgent(goal=task, config=config)
    return await agent.run()

# 并行控制所有设备
devices = adb.list()
tasks = [control_device(dev.serial, "打开设置") for dev in devices]
results = await asyncio.gather(*tasks)
```

---

## 🛠 高级功能

### 宏录制和回放

```bash
# 录制操作序列
droidrun "登录流程" --save-trajectory action

# 查看已保存的宏
droidrun macro list

# 回放宏
droidrun macro replay trajectories/2025-10-28_10-30-45

# 自定义回放
droidrun macro replay trajectories/login-flow \
  --device emulator-5554 \
  --delay 0.5 \
  --start-from 5
```

### 无线调试

```bash
# 启用无线模式 (Android 11+)
# 设置 > 开发者选项 > 无线调试

# 或通过 USB 启用 (Android 10及以下)
adb tcpip 5555
adb shell ip route | awk '{print $9}'  # 获取IP
adb connect 192.168.1.100:5555

# 使用无线设备
droidrun "打开设置" --device 192.168.1.100:5555 --tcp
```

### 自定义工具和凭证管理

详见 [官方文档](https://docs.droidrun.ai/features/custom-tools)

---

## 📊 性能优化建议

### 选择合适的模型

| 场景 | 推荐模型 | 原因 |
|------|---------|------|
| 简单任务 | `gemini-2.5-flash` | 快速、便宜 |
| 复杂任务 | `gemini-2.5-pro` | 更强推理能力 |
| 精确理解 | `gpt-4o` | 高准确度 |
| 本地/离线 | `llama3.3:70b` | 免费、隐私 |

### 成本优化

```bash
# ❌ 不必要的视觉调用
droidrun "打开设置" --vision

# ✅ 只在需要时使用视觉
droidrun "打开设置"
droidrun "描述当前屏幕" --vision  # 需要时才用

# ❌ 简单任务用推理模式
droidrun "打开设置" --reasoning

# ✅ 复杂任务才用推理
droidrun "找联系人John并发邮件" --reasoning
```

---

## 🔧 故障排查

| 问题 | 解决方案 |
|------|---------|
| 找不到设备 | `adb kill-server && adb start-server` |
| Portal 未安装 | `droidrun setup` |
| 无障碍服务未启用 | 设置 > 无障碍 > Droidrun Portal > 打开 |
| API 密钥错误 | `export GOOGLE_API_KEY=your-key` |
| 命令超时 | 添加 `--steps 30` 或 `--reasoning` |
| TCP 连接失败 | `adb forward --remove-all && droidrun ping --tcp` |

详细故障排查请查看 [使用指南.md](./使用指南.md#常见问题)

---

## 🌐 支持的 LLM 提供商

| 提供商 | 安装 | 环境变量 | 推荐模型 |
|--------|------|---------|---------|
| **Google Gemini** | `pip install 'droidrun[google]'` | `GOOGLE_API_KEY` | `models/gemini-2.5-flash` |
| **OpenAI** | `pip install 'droidrun[openai]'` | `OPENAI_API_KEY` | `gpt-4o` |
| **Anthropic** | `pip install 'droidrun[anthropic]'` | `ANTHROPIC_API_KEY` | `claude-sonnet-4-5-latest` |
| **DeepSeek** | `pip install 'droidrun[deepseek]'` | `DEEPSEEK_API_KEY` | `deepseek-chat` |
| **Ollama** (本地) | `pip install 'droidrun[ollama]'` | 无 | `llama3.3:70b` |

---

## 📖 更多资源

- 📕 [官方文档](https://docs.droidrun.ai)
- ☁️ [云端环境](https://cloud.droidrun.ai) - 无需设置，直接使用
- 🎯 [基准测试](https://droidrun.ai/benchmark)
- 💬 [Discord 社区](https://discord.gg/ZZbKEZZkwK)
- 🐛 [问题反馈](https://github.com/droidrun/droidrun/issues)
- 🐦 [Twitter](https://x.com/droid_run)

---

## 👥 贡献

欢迎贡献！请随时提交 Pull Request。

查看 [CONTRIBUTING.md](./CONTRIBUTING.md) 了解详情。

---

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](./LICENSE) 文件。

---

## 🔒 安全检查

在提交代码前，请运行安全检查：

```bash
# 检查代码安全问题
bandit -r droidrun

# 检查依赖安全漏洞
safety scan
```

---

## 🎉 开始使用

```bash
# 1. 安装
pip install 'droidrun[google,openai,anthropic]'

# 2. 设置设备
droidrun setup

# 3. 设置 API 密钥
export GOOGLE_API_KEY=your-key

# 4. 开始使用！
droidrun "打开设置并告诉我Android版本"
```

### 或者使用快速启动脚本

```bash
# Linux/macOS
./start.sh

# Windows
start.bat
```

---

<div align="center">

**🌟 如果觉得有用，请给我们一个 Star！🌟**

[⭐ Star on GitHub](https://github.com/droidrun/droidrun)

</div>

