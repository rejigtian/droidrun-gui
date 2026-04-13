# DroidRun 示例代码

这个目录包含了 DroidRun 的各种使用示例，帮助你快速上手。

## 📋 示例列表

### 1. `basic_example.py` - 基础示例
演示 DroidRun 的基本功能：

- ✅ 执行简单任务
- 🖼️ 使用视觉功能（发送截图给LLM）
- 🔄 执行复杂的多步骤任务
- 📱 控制特定设备
- 🧠 使用推理模式（Manager-Executor工作流）

**运行方式：**
```bash
python examples/basic_example.py
```

---

### 2. `structured_output_example.py` - 结构化输出示例
演示如何使用 Pydantic 模型从设备提取结构化数据：

- 🔋 获取电池信息（电量、充电状态）
- 📱 获取设备信息（型号、Android版本）
- 📬 获取通知摘要
- 📲 检查特定应用状态
- 📶 自定义数据提取（WiFi信息）

**运行方式：**
```bash
python examples/structured_output_example.py
```

---

### 3. `multi_device_example.py` - 多设备控制示例
演示如何同时控制多个 Android 设备：

- 🔄 在多个设备上执行相同任务
- 📋 在不同设备上执行不同任务
- ⏭️ 顺序工作流
- 🏥 批量设备健康检查

**运行方式：**
```bash
python examples/multi_device_example.py
```

**注意：** 此示例需要至少连接2个设备。

---

## 🚀 快速开始

### 前置要求

1. 已安装 DroidRun：
   ```bash
   pip install 'droidrun[google,anthropic,openai]'
   ```

2. 已设置 API 密钥：
   ```bash
   export GOOGLE_API_KEY=your-api-key
   # 或
   export OPENAI_API_KEY=your-api-key
   ```

3. 已连接 Android 设备并安装 Portal：
   ```bash
   droidrun setup
   droidrun ping
   ```

### 运行示例

```bash
# 进入项目目录
cd /Users/rejig/myproject/droidrun

# 运行基础示例
python examples/basic_example.py

# 运行结构化输出示例
python examples/structured_output_example.py

# 运行多设备控制示例
python examples/multi_device_example.py
```

---

## 💡 示例说明

### 基础示例 (basic_example.py)

这个示例适合初学者，展示了 DroidRun 的核心功能：

```python
from droidrun import DroidAgent
from droidrun.config_manager.config_manager import DroidrunConfig

config = DroidrunConfig()

agent = DroidAgent(
    goal="打开设置应用",
    config=config,
)

result = await agent.run()
print(f"任务完成: {result.success}")
```

### 结构化输出示例 (structured_output_example.py)

展示如何定义 Pydantic 模型并提取结构化数据：

```python
from pydantic import BaseModel, Field

class BatteryInfo(BaseModel):
    level: int = Field(description="电池电量百分比")
    is_charging: bool = Field(description="是否正在充电")

agent = DroidAgent(
    goal="检查电池状态",
    config=config,
    output_schema=BatteryInfo,
)

result = await agent.run()
battery: BatteryInfo = result.structured_output
print(f"电量: {battery.level}%")
```

### 多设备控制示例 (multi_device_example.py)

展示如何并行控制多个设备：

```python
from adbutils import adb

async def control_device(serial: str, task: str):
    device_config = DeviceConfig(serial=serial)
    config = DroidrunConfig(device=device_config)
    agent = DroidAgent(goal=task, config=config)
    return await agent.run()

# 并行执行
devices = adb.list()
tasks = [control_device(dev.serial, "打开设置") for dev in devices]
results = await asyncio.gather(*tasks)
```

---

## 🎓 学习路径

建议按以下顺序学习示例：

1. **basic_example.py** - 了解基本用法
2. **structured_output_example.py** - 学习如何提取数据
3. **multi_device_example.py** - 掌握多设备控制

---

## 🔧 自定义示例

你可以基于这些示例创建自己的自动化脚本：

### 示例：自动化登录流程

```python
import asyncio
from droidrun import DroidAgent
from droidrun.config_manager.config_manager import DroidrunConfig

async def auto_login():
    config = DroidrunConfig()
    
    agent = DroidAgent(
        goal="打开应用，点击登录，输入用户名test@example.com和密码123456，点击登录按钮",
        config=config,
        max_steps=20,
    )
    
    result = await agent.run()
    
    if result.success:
        print("✅ 登录成功")
    else:
        print(f"❌ 登录失败: {result.reason}")

asyncio.run(auto_login())
```

### 示例：定时任务

```python
import asyncio
import schedule
from droidrun import DroidAgent
from droidrun.config_manager.config_manager import DroidrunConfig

async def daily_task():
    """每天执行的任务"""
    config = DroidrunConfig()
    
    agent = DroidAgent(
        goal="打开日历，检查今天的日程",
        config=config,
    )
    
    result = await agent.run()
    print(f"任务完成: {result.reason}")

def schedule_task():
    """安排定时任务"""
    schedule.every().day.at("09:00").do(lambda: asyncio.run(daily_task()))
    
    while True:
        schedule.run_pending()
        time.sleep(60)

# 运行
schedule_task()
```

---

## 📚 更多资源

- [官方文档](https://docs.droidrun.ai)
- [完整使用指南](../使用指南.md)
- [SDK参考](https://docs.droidrun.ai/sdk/reference)
- [GitHub仓库](https://github.com/droidrun/droidrun)

---

## 🤝 贡献

如果你创建了有用的示例，欢迎提交 PR 分享给社区！

---

## ❓ 问题反馈

如果在运行示例时遇到问题：

1. 确保设备已正确连接：`adb devices`
2. 确保 Portal 正常运行：`droidrun ping`
3. 检查 API 密钥是否设置：`echo $GOOGLE_API_KEY`
4. 查看详细日志：在命令中添加 `--debug` 标志

如需更多帮助，请访问：
- [Discord 社区](https://discord.gg/ZZbKEZZkwK)
- [GitHub Issues](https://github.com/droidrun/droidrun/issues)

