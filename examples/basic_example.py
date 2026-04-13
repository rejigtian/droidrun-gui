"""
DroidRun 基础示例
演示如何使用 DroidRun 控制 Android 设备
"""

import asyncio
from droidrun import DroidAgent
from droidrun.config_manager.config_manager import DroidrunConfig


async def example_1_simple_task():
    """示例1: 执行简单任务"""
    print("=" * 50)
    print("示例1: 执行简单任务")
    print("=" * 50)
    
    config = DroidrunConfig()
    
    agent = DroidAgent(
        goal="打开设置应用",
        config=config,
    )
    
    result = await agent.run()
    
    print(f"✅ 任务完成: {result.success}")
    print(f"📝 原因: {result.reason}")
    print(f"🔢 执行步骤数: {result.steps}")
    print()


async def example_2_with_vision():
    """示例2: 使用视觉功能（发送截图给LLM）"""
    print("=" * 50)
    print("示例2: 使用视觉功能")
    print("=" * 50)
    
    config = DroidrunConfig()
    # 启用视觉功能
    config.enable_vision = True
    
    agent = DroidAgent(
        goal="告诉我当前屏幕上显示的是什么",
        config=config,
    )
    
    result = await agent.run()
    
    print(f"✅ 任务完成: {result.success}")
    print(f"📝 LLM 的回答: {result.reason}")
    print()


async def example_3_multi_step():
    """示例3: 复杂的多步骤任务"""
    print("=" * 50)
    print("示例3: 复杂的多步骤任务")
    print("=" * 50)
    
    config = DroidrunConfig()
    
    agent = DroidAgent(
        goal="打开设置，找到关于手机，告诉我Android版本号",
        config=config,
        max_steps=20,  # 增加最大步骤数
    )
    
    result = await agent.run()
    
    print(f"✅ 任务完成: {result.success}")
    print(f"📝 结果: {result.reason}")
    print(f"🔢 执行步骤数: {result.steps}")
    print()


async def example_4_specific_device():
    """示例4: 控制特定设备"""
    print("=" * 50)
    print("示例4: 控制特定设备")
    print("=" * 50)
    
    from droidrun.config_manager.config_manager import DeviceConfig
    from adbutils import adb
    
    # 列出所有设备
    devices = adb.list()
    print(f"📱 发现 {len(devices)} 个设备:")
    for dev in devices:
        print(f"  - {dev.serial}")
    
    if not devices:
        print("❌ 未找到设备，请确保设备已连接")
        return
    
    # 使用第一个设备
    device_config = DeviceConfig(
        serial=devices[0].serial,
        use_tcp=False  # 使用内容提供程序模式
    )
    
    config = DroidrunConfig(device=device_config)
    
    agent = DroidAgent(
        goal="打开设置",
        config=config,
    )
    
    result = await agent.run()
    
    print(f"✅ 任务完成: {result.success}")
    print()


async def example_5_with_reasoning():
    """示例5: 使用推理模式（Manager-Executor工作流）"""
    print("=" * 50)
    print("示例5: 使用推理模式")
    print("=" * 50)
    
    config = DroidrunConfig()
    # 启用推理模式 - 适合复杂任务
    config.enable_reasoning = True
    
    agent = DroidAgent(
        goal="找到系统设置中的电池选项，并告诉我当前电池百分比",
        config=config,
        max_steps=25,
    )
    
    result = await agent.run()
    
    print(f"✅ 任务完成: {result.success}")
    print(f"📝 结果: {result.reason}")
    print(f"🔢 执行步骤数: {result.steps}")
    print()


async def main():
    """运行所有示例"""
    print("\n🚀 DroidRun 示例程序\n")
    
    # 选择要运行的示例
    print("请选择要运行的示例:")
    print("1. 简单任务")
    print("2. 使用视觉功能")
    print("3. 复杂的多步骤任务")
    print("4. 控制特定设备")
    print("5. 使用推理模式")
    print("6. 运行所有示例")
    
    choice = input("\n请输入选项 (1-6): ").strip()
    
    print()
    
    if choice == "1":
        await example_1_simple_task()
    elif choice == "2":
        await example_2_with_vision()
    elif choice == "3":
        await example_3_multi_step()
    elif choice == "4":
        await example_4_specific_device()
    elif choice == "5":
        await example_5_with_reasoning()
    elif choice == "6":
        await example_1_simple_task()
        await example_2_with_vision()
        await example_3_multi_step()
        await example_4_specific_device()
        await example_5_with_reasoning()
    else:
        print("❌ 无效选项")
        return
    
    print("=" * 50)
    print("✨ 所有示例完成！")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())

