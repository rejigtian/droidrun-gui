"""
DroidRun 结构化输出示例
演示如何使用 Pydantic 模型从设备提取结构化数据
"""

import asyncio
from pydantic import BaseModel, Field
from droidrun import DroidAgent
from droidrun.config_manager.config_manager import DroidrunConfig


class BatteryInfo(BaseModel):
    """电池信息模型"""
    level: int = Field(description="电池电量百分比 (0-100)")
    is_charging: bool = Field(description="是否正在充电")
    charging_mode: str = Field(description="充电模式，如'USB'、'AC'、'无线充电'等，如果未充电则为'未充电'")


class AppInfo(BaseModel):
    """应用信息模型"""
    name: str = Field(description="应用名称")
    is_open: bool = Field(description="应用是否当前打开")
    has_notifications: bool = Field(description="是否有未读通知")


class DeviceInfo(BaseModel):
    """设备信息模型"""
    android_version: str = Field(description="Android版本号")
    device_model: str = Field(description="设备型号")
    security_patch: str = Field(description="安全补丁日期")


class NotificationSummary(BaseModel):
    """通知摘要模型"""
    total_count: int = Field(description="总通知数量")
    app_names: list[str] = Field(description="有通知的应用名称列表")
    has_important: bool = Field(description="是否有重要通知")


async def example_1_battery_info():
    """示例1: 获取电池信息"""
    print("=" * 50)
    print("示例1: 获取电池信息（结构化输出）")
    print("=" * 50)
    
    config = DroidrunConfig()
    config.enable_vision = True
    
    agent = DroidAgent(
        goal="打开设置，进入电池选项，查看电池状态",
        config=config,
        output_schema=BatteryInfo,
    )
    
    result = await agent.run()
    
    if result.success and result.structured_output:
        battery: BatteryInfo = result.structured_output
        print(f"🔋 电池电量: {battery.level}%")
        print(f"⚡ 充电状态: {'充电中' if battery.is_charging else '未充电'}")
        print(f"🔌 充电模式: {battery.charging_mode}")
    else:
        print(f"❌ 任务失败: {result.reason}")
    
    print()


async def example_2_device_info():
    """示例2: 获取设备信息"""
    print("=" * 50)
    print("示例2: 获取设备信息（结构化输出）")
    print("=" * 50)
    
    config = DroidrunConfig()
    config.enable_vision = True
    
    agent = DroidAgent(
        goal="打开设置，进入关于手机，查看Android版本、设备型号和安全补丁信息",
        config=config,
        output_schema=DeviceInfo,
        max_steps=20,
    )
    
    result = await agent.run()
    
    if result.success and result.structured_output:
        device: DeviceInfo = result.structured_output
        print(f"📱 设备型号: {device.device_model}")
        print(f"🤖 Android版本: {device.android_version}")
        print(f"🛡️ 安全补丁: {device.security_patch}")
    else:
        print(f"❌ 任务失败: {result.reason}")
    
    print()


async def example_3_notification_summary():
    """示例3: 获取通知摘要"""
    print("=" * 50)
    print("示例3: 获取通知摘要（结构化输出）")
    print("=" * 50)
    
    config = DroidrunConfig()
    config.enable_vision = True
    
    agent = DroidAgent(
        goal="打开通知面板，统计有多少通知，来自哪些应用",
        config=config,
        output_schema=NotificationSummary,
    )
    
    result = await agent.run()
    
    if result.success and result.structured_output:
        notifications: NotificationSummary = result.structured_output
        print(f"📬 通知总数: {notifications.total_count}")
        print(f"📱 应用列表: {', '.join(notifications.app_names)}")
        print(f"⚠️ 有重要通知: {'是' if notifications.has_important else '否'}")
    else:
        print(f"❌ 任务失败: {result.reason}")
    
    print()


async def example_4_check_app():
    """示例4: 检查特定应用状态"""
    print("=" * 50)
    print("示例4: 检查应用状态（结构化输出）")
    print("=" * 50)
    
    app_name = input("请输入要检查的应用名称（如：WhatsApp）: ").strip()
    
    config = DroidrunConfig()
    config.enable_vision = True
    
    agent = DroidAgent(
        goal=f"检查{app_name}应用是否打开，是否有未读通知",
        config=config,
        output_schema=AppInfo,
    )
    
    result = await agent.run()
    
    if result.success and result.structured_output:
        app: AppInfo = result.structured_output
        print(f"📱 应用名称: {app.name}")
        print(f"▶️ 运行状态: {'打开' if app.is_open else '未打开'}")
        print(f"🔔 通知状态: {'有未读通知' if app.has_notifications else '无未读通知'}")
    else:
        print(f"❌ 任务失败: {result.reason}")
    
    print()


async def example_5_custom_extraction():
    """示例5: 自定义数据提取"""
    print("=" * 50)
    print("示例5: 自定义数据提取")
    print("=" * 50)
    
    # 动态定义模型
    class WifiInfo(BaseModel):
        """WiFi信息模型"""
        is_connected: bool = Field(description="是否连接到WiFi")
        network_name: str = Field(description="WiFi网络名称，如果未连接则为'未连接'")
        signal_strength: str = Field(description="信号强度（强/中/弱），如果未连接则为'无'")
    
    config = DroidrunConfig()
    config.enable_vision = True
    
    agent = DroidAgent(
        goal="打开WiFi设置，查看当前WiFi连接状态和信号强度",
        config=config,
        output_schema=WifiInfo,
        max_steps=15,
    )
    
    result = await agent.run()
    
    if result.success and result.structured_output:
        wifi: WifiInfo = result.structured_output
        print(f"📶 连接状态: {'已连接' if wifi.is_connected else '未连接'}")
        print(f"🌐 网络名称: {wifi.network_name}")
        print(f"📊 信号强度: {wifi.signal_strength}")
    else:
        print(f"❌ 任务失败: {result.reason}")
    
    print()


async def main():
    """运行所有示例"""
    print("\n🚀 DroidRun 结构化输出示例\n")
    
    print("这些示例展示如何使用 Pydantic 模型从设备提取结构化数据")
    print("=" * 50)
    print()
    
    print("请选择要运行的示例:")
    print("1. 获取电池信息")
    print("2. 获取设备信息")
    print("3. 获取通知摘要")
    print("4. 检查特定应用状态")
    print("5. 自定义数据提取（WiFi信息）")
    print("6. 运行所有示例")
    
    choice = input("\n请输入选项 (1-6): ").strip()
    
    print()
    
    if choice == "1":
        await example_1_battery_info()
    elif choice == "2":
        await example_2_device_info()
    elif choice == "3":
        await example_3_notification_summary()
    elif choice == "4":
        await example_4_check_app()
    elif choice == "5":
        await example_5_custom_extraction()
    elif choice == "6":
        await example_1_battery_info()
        await example_2_device_info()
        await example_3_notification_summary()
        # 跳过需要用户输入的示例4
        await example_5_custom_extraction()
    else:
        print("❌ 无效选项")
        return
    
    print("=" * 50)
    print("✨ 所有示例完成！")
    print("=" * 50)
    print("\n💡 提示: 结构化输出让您能以编程方式处理从设备提取的数据")
    print("   您可以将这些数据保存到数据库、生成报告或触发其他自动化任务")


if __name__ == "__main__":
    asyncio.run(main())

