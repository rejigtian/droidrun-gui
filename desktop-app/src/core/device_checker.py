"""
设备检查器
"""

import asyncio
import subprocess
import sys
import os
import traceback
from utils.config import ConfigManager
from utils.sdk_manager import get_sdk_manager

# 使用 droidrun 0.5.8+ API
try:
    from async_adbutils import adb as async_adb
    from droidrun.tools.android.portal_client import PortalClient
    from droidrun.portal import download_portal_apk, enable_portal_accessibility
    HAS_DROIDRUN = True
except ImportError:
    HAS_DROIDRUN = False


class DeviceChecker:
    """设备检查器类"""

    def __init__(self):
        """初始化设备检查器"""
        self.config_manager = ConfigManager()
        try:
            self.sdk_manager = get_sdk_manager(self.config_manager)
        except:
            self.sdk_manager = get_sdk_manager(self.config_manager)

    def list_devices(self):
        """
        列出所有连接的设备

        Returns:
            list: 设备列表
        """
        # 使用 adb 命令（最可靠，无需额外库）
        return self._list_devices_via_adb()

    def _list_devices_via_adb(self):
        """
        使用 adb 命令获取设备列表

        Returns:
            list: 设备列表
        """
        try:
            adb_path = self.sdk_manager.get_tool_path('adb')
            result = subprocess.run(
                [adb_path, 'devices', '-l'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return []

            devices = []
            lines = result.stdout.strip().split('\n')[1:]  # 跳过第一行 "List of devices"

            for line in lines:
                line = line.strip()
                if not line or 'offline' in line or 'unauthorized' in line:
                    continue

                parts = line.split()
                if len(parts) >= 2:
                    serial = parts[0]
                    state = parts[1] if len(parts) > 1 else 'device'

                    # 尝试获取设备型号
                    model = 'Unknown'
                    try:
                        model_result = subprocess.run(
                            [adb_path, '-s', serial, 'shell', 'getprop', 'ro.product.model'],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        if model_result.returncode == 0:
                            model = model_result.stdout.strip()
                    except:
                        pass

                    devices.append({
                        'serial': serial,
                        'state': state,
                        'model': model
                    })

            return devices

        except Exception as e:
            print(f"❌ adb 命令失败: {e}", file=sys.stderr)
            return []

    def check_portal(self, serial):
        """
        检查设备上是否安装了 Portal

        Args:
            serial: 设备序列号

        Returns:
            bool: 是否安装并运行
        """
        if not HAS_DROIDRUN:
            print("❌ DroidRun API 未导入", file=sys.stderr)
            return False

        async def _check():
            device = await async_adb.device(serial=serial)
            portal_client = PortalClient(device, prefer_tcp=True)
            result = await portal_client.ping()
            print(f"🔍 Portal ping 结果: {result}", file=sys.stderr)
            status = result.get('status', '')
            if status == 'success':
                print(f"✅ Portal 连接成功 ({result.get('method', 'unknown')})", file=sys.stderr)
                return True
            else:
                print(f"❌ Portal 状态: {status}", file=sys.stderr)
                return False

        try:
            return asyncio.run(_check())
        except Exception as e:
            error_detail = traceback.format_exc()
            print(f"❌ 检查 Portal 失败: {e}", file=sys.stderr)
            print(f"详细错误:\n{error_detail}", file=sys.stderr)
            return False

    def install_portal(self, serial):
        """
        安装 Portal 到指定设备

        Args:
            serial: 设备序列号

        Returns:
            (success, message): 成功标志和消息
        """
        if not HAS_DROIDRUN:
            return False, "DroidRun API 未导入"

        async def _install():
            device = await async_adb.device(serial=serial)

            with download_portal_apk(debug=False) as apk_path:
                if not apk_path or not os.path.exists(apk_path):
                    return False, "APK 文件下载失败"

                try:
                    await device.install(apk_path, uninstall=True, flags=["-g"], silent=True)
                except Exception as e:
                    return False, f"APK 安装失败: {str(e)}"

                try:
                    await enable_portal_accessibility(device)
                    return True, "Portal 安装并启用成功"
                except Exception:
                    return True, "Portal 安装成功，请在设备上手动启用辅助功能"

        try:
            return asyncio.run(_install())
        except Exception as e:
            error_detail = traceback.format_exc()
            print(f"❌ Portal 安装错误: {error_detail}", file=sys.stderr)
            return False, f"安装错误: {str(e)}"
