"""
DroidRun 多设备控制示例
演示如何同时控制多个 Android 设备
"""

import asyncio
from typing import List
from adbutils import adb
from droidrun import DroidAgent
from droidrun.config_manager.config_manager import DroidrunConfig, DeviceConfig


async def control_single_device(serial: str, task: str) -> dict:
    """
    控制单个设备
    
    Args:
        serial: 设备序列号
        task: 要执行的任务
        
    Returns:
        包含结果的字典
    """
    print(f"📱 [{serial}] 开始任务: {task}")
    
    device_config = DeviceConfig(serial=serial)
    config = DroidrunConfig(device=device_config)
    
    agent = DroidAgent(
        goal=task,
        config=config,
        max_steps=15,
    )
    
    result = await agent.run()
    
    status = "✅ 成功" if result.success else "❌ 失败"
    print(f"{status} [{serial}] {result.reason}")
    
    return {
        "serial": serial,
        "task": task,
        "success": result.success,
        "reason": result.reason,
        "steps": result.steps,
    }


async def example_1_same_task_multiple_devices():
    """示例1: 在多个设备上执行相同任务"""
    print("=" * 50)
    print("示例1: 在多个设备上执行相同任务")
    print("=" * 50)
    
    devices = adb.list()
    
    if len(devices) < 2:
        print("⚠️ 需要至少2个连接的设备")
        print(f"   当前连接设备数: {len(devices)}")
        return
    
    print(f"📱 发现 {len(devices)} 个设备")
    for dev in devices:
        print(f"   - {dev.serial}")
    print()
    
    # 在所有设备上执行相同任务
    task = "打开设置"
    
    print(f"🚀 在所有设备上执行任务: {task}\n")
    
    # 并行执行
    tasks = [
        control_single_device(dev.serial, task)
        for dev in devices
    ]
    
    results = await asyncio.gather(*tasks)
    
    # 统计结果
    success_count = sum(1 for r in results if r["success"])
    print(f"\n📊 统计: {success_count}/{len(results)} 个设备成功完成任务")
    print()


async def example_2_different_tasks():
    """示例2: 在不同设备上执行不同任务"""
    print("=" * 50)
    print("示例2: 在不同设备上执行不同任务")
    print("=" * 50)
    
    devices = adb.list()
    
    if len(devices) < 2:
        print("⚠️ 需要至少2个连接的设备")
        print(f"   当前连接设备数: {len(devices)}")
        return
    
    print(f"📱 发现 {len(devices)} 个设备")
    
    # 为不同设备分配不同任务
    device_tasks = [
        (devices[0].serial, "打开设置并告诉我Android版本"),
        (devices[1].serial, "检查电池电量"),
    ]
    
    # 如果有更多设备，添加更多任务
    if len(devices) > 2:
        device_tasks.append((devices[2].serial, "打开日历"))
    
    print("\n📋 任务分配:")
    for serial, task in device_tasks:
        print(f"   [{serial}] -> {task}")
    print()
    
    # 并行执行
    tasks = [
        control_single_device(serial, task)
        for serial, task in device_tasks
    ]
    
    results = await asyncio.gather(*tasks)
    
    # 显示详细结果
    print("\n📊 执行结果:")
    for result in results:
        status = "✅" if result["success"] else "❌"
        print(f"{status} [{result['serial']}] {result['reason']} (步骤: {result['steps']})")
    print()


async def example_3_sequential_workflow():
    """示例3: 顺序工作流（先在设备1操作，再在设备2操作）"""
    print("=" * 50)
    print("示例3: 顺序工作流")
    print("=" * 50)
    
    devices = adb.list()
    
    if len(devices) < 2:
        print("⚠️ 需要至少2个连接的设备")
        print(f"   当前连接设备数: {len(devices)}")
        return
    
    device1 = devices[0].serial
    device2 = devices[1].serial
    
    print(f"📱 设备1: {device1}")
    print(f"📱 设备2: {device2}\n")
    
    # 步骤1: 在设备1上获取信息
    print("步骤1: 在设备1上打开设置...")
    result1 = await control_single_device(device1, "打开设置")
    
    if not result1["success"]:
        print("❌ 设备1任务失败，工作流终止")
        return
    
    # 步骤2: 在设备2上执行相关操作
    print("\n步骤2: 在设备2上打开设置...")
    result2 = await control_single_device(device2, "打开设置")
    
    if result2["success"]:
        print("\n✅ 工作流完成！")
    else:
        print("\n⚠️ 设备2任务失败")
    print()


async def example_4_device_health_check():
    """示例4: 批量设备健康检查"""
    print("=" * 50)
    print("示例4: 批量设备健康检查")
    print("=" * 50)
    
    devices = adb.list()
    
    if not devices:
        print("❌ 未找到设备")
        return
    
    print(f"📱 开始检查 {len(devices)} 个设备\n")
    
    # 对每个设备执行健康检查
    from pydantic import BaseModel, Field
    
    class DeviceHealth(BaseModel):
        """设备健康信息"""
        battery_level: int = Field(description="电池电量百分比")
        storage_available: str = Field(description="可用存储空间，大致估算")
        is_connected_to_wifi: bool = Field(description="是否连接WiFi")
    
    async def check_device_health(serial: str):
        """检查单个设备健康状况"""
        print(f"🔍 检查设备: {serial}")
        
        device_config = DeviceConfig(serial=serial)
        config = DroidrunConfig(device=device_config)
        config.enable_vision = True
        
        agent = DroidAgent(
            goal="检查设备状态：电池电量、可用存储空间、WiFi连接状态",
            config=config,
            output_schema=DeviceHealth,
            max_steps=20,
        )
        
        result = await agent.run()
        
        return {
            "serial": serial,
            "success": result.success,
            "health": result.structured_output if result.success else None,
        }
    
    # 并行检查所有设备
    tasks = [check_device_health(dev.serial) for dev in devices]
    results = await asyncio.gather(*tasks)
    
    # 显示报告
    print("\n" + "=" * 50)
    print("📊 设备健康报告")
    print("=" * 50)
    
    for result in results:
        print(f"\n设备: {result['serial']}")
        if result["success"] and result["health"]:
            health: DeviceHealth = result["health"]
            
            # 电池状态
            battery_emoji = "🔋" if health.battery_level > 50 else "🪫"
            print(f"  {battery_emoji} 电池: {health.battery_level}%")
            
            # WiFi状态
            wifi_emoji = "📶" if health.is_connected_to_wifi else "📵"
            print(f"  {wifi_emoji} WiFi: {'已连接' if health.is_connected_to_wifi else '未连接'}")
            
            # 存储空间
            print(f"  💾 存储: {health.storage_available}")
        else:
            print("  ❌ 检查失败")
    
    print()


async def main():
    """运行示例"""
    print("\n🚀 DroidRun 多设备控制示例\n")
    
    # 首先列出所有设备
    devices = adb.list()
    print(f"📱 发现 {len(devices)} 个连接的设备:")
    
    if not devices:
        print("❌ 未找到设备，请确保设备已连接")
        return
    
    for i, dev in enumerate(devices, 1):
        print(f"  {i}. {dev.serial}")
    print()
    
    print("请选择要运行的示例:")
    print("1. 在多个设备上执行相同任务")
    print("2. 在不同设备上执行不同任务")
    print("3. 顺序工作流")
    print("4. 批量设备健康检查")
    
    choice = input("\n请输入选项 (1-4): ").strip()
    
    print()
    
    if choice == "1":
        await example_1_same_task_multiple_devices()
    elif choice == "2":
        await example_2_different_tasks()
    elif choice == "3":
        await example_3_sequential_workflow()
    elif choice == "4":
        await example_4_device_health_check()
    else:
        print("❌ 无效选项")
        return
    
    print("=" * 50)
    print("✨ 示例完成！")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())

