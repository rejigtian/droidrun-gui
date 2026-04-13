"""
主窗口
"""

import customtkinter as ctk
from tkinter import StringVar
from ui.task_panel import TaskPanel
from ui.device_manager import DeviceManagerPanel
from ui.settings import SettingsPanel
from ui.adb_wizard import AdbWizard
import subprocess
import os
import sys
from pathlib import Path
from PIL import Image, ImageTk


class MainWindow(ctk.CTk):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        
        # 窗口配置
        self.title("SmartDroid")
        self.geometry("1000x700")
        
        # 设置应用图标
        self._set_app_icon()
        
        # DroidRun 已内置到应用中，无需额外安装
        # 但需要检测 ADB 是否安装
        if not self._check_adb():
            self.show_adb_wizard()
        else:
            self.setup_ui()
    
    def _set_app_icon(self):
        """设置应用图标"""
        try:
            # 获取图标路径（支持开发和打包模式）
            if getattr(sys, 'frozen', False):
                # 打包模式：从 _internal/resources/ 或 Resources/ 读取
                base_path = Path(sys._MEIPASS)
            else:
                # 开发模式：从项目根目录读取
                base_path = Path(__file__).parent.parent.parent
            
            icon_path = base_path / 'resources' / 'icons' / 'app_icon.png'
            
            if icon_path.exists():
                # 加载图标
                icon_image = Image.open(str(icon_path))
                # 转换为 PhotoImage（Tkinter 需要）
                icon_photo = ImageTk.PhotoImage(icon_image)
                # 设置窗口图标
                self.iconphoto(True, icon_photo)
                # 保持引用，防止被垃圾回收
                self._icon_photo = icon_photo
            else:
                print(f"⚠️  图标文件不存在: {icon_path}")
        except Exception as e:
            print(f"⚠️  设置图标失败: {e}")
    
    def _check_adb(self):
        """检查 ADB 是否安装"""
        try:
            # 尝试运行 adb version
            result = subprocess.run(
                ['adb', 'version'],
                capture_output=True,
                text=True,
                timeout=3
            )
            return result.returncode == 0
        except:
            return False
    
    def show_adb_wizard(self):
        """显示 ADB 安装向导"""
        # 清空窗口
        for widget in self.winfo_children():
            widget.destroy()
        
        # 显示 ADB 向导
        wizard = AdbWizard(self, on_complete=self.setup_ui)
        wizard.pack(fill="both", expand=True)
    
    def setup_ui(self):
        """设置主界面"""
        # 清空窗口
        for widget in self.winfo_children():
            widget.destroy()
        
        # 配置网格布局
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # 创建侧边栏
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)
        
        # Logo 和标题
        self.logo_label = ctk.CTkLabel(
            self.sidebar,
            text="SmartDroid",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # 侧边栏按钮
        self.home_button = ctk.CTkButton(
            self.sidebar,
            text="🏠 首页",
            command=self.show_home,
            font=ctk.CTkFont(size=14)
        )
        self.home_button.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        self.device_button = ctk.CTkButton(
            self.sidebar,
            text="📱 设备管理",
            command=self.show_devices,
            font=ctk.CTkFont(size=14)
        )
        self.device_button.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        self.task_button = ctk.CTkButton(
            self.sidebar,
            text="⚡ 执行任务",
            command=self.show_tasks,
            font=ctk.CTkFont(size=14)
        )
        self.task_button.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        
        self.settings_button = ctk.CTkButton(
            self.sidebar,
            text="⚙️ 设置",
            command=self.show_settings,
            font=ctk.CTkFont(size=14)
        )
        self.settings_button.grid(row=4, column=0, padx=20, pady=10, sticky="ew")
        
        # 外观模式切换
        self.appearance_label = ctk.CTkLabel(
            self.sidebar,
            text="外观模式:",
            anchor="w"
        )
        self.appearance_label.grid(row=5, column=0, padx=20, pady=(20, 0))
        
        self.appearance_switch = ctk.CTkSwitch(
            self.sidebar,
            text="深色模式",
            command=self.toggle_appearance,
            onvalue="dark",
            offvalue="light"
        )
        self.appearance_switch.grid(row=6, column=0, padx=20, pady=10, sticky="s")
        self.appearance_switch.select()
        
        # 创建主内容区域
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        
        # 初始化面板实例（保持实例，避免重复创建）
        self.task_panel = None
        self.device_panel = None
        self.settings_panel = None
        self.home_panel = None
        self.current_panel = None
        
        # 默认显示任务面板
        self.show_tasks()
    
    def hide_current_panel(self):
        """隐藏当前面板（而不是销毁）"""
        if self.current_panel:
            self.current_panel.grid_forget()
    
    def show_home(self):
        """显示首页"""
        self.hide_current_panel()
        
        # 如果首页面板不存在，创建它
        if self.home_panel is None:
            self.home_panel = ctk.CTkFrame(self.main_frame)
            self.home_panel.grid_columnconfigure(0, weight=1)
            
            # 欢迎标题
            welcome_label = ctk.CTkLabel(
                self.home_panel,
                text="欢迎使用 SmartDroid",
                font=ctk.CTkFont(size=28, weight="bold")
            )
            welcome_label.grid(row=0, column=0, padx=20, pady=(40, 20))
            
            # 说明文字
            info_text = """
            DroidRun 是一个强大的 Android 设备自动化框架
            
            通过这个桌面应用，你可以：
            
            • 管理多个 Android 设备
            • 使用自然语言执行任务
            • 查看任务执行历史
            • 配置 LLM 提供商
            
            点击左侧菜单开始使用！
            """
            
            info_label = ctk.CTkLabel(
                self.home_panel,
                text=info_text,
                font=ctk.CTkFont(size=14),
                justify="left"
            )
            info_label.grid(row=1, column=0, padx=40, pady=20)
            
            # 快速开始按钮
            quick_start_btn = ctk.CTkButton(
                self.home_panel,
                text="⚡ 快速开始",
                command=self.show_tasks,
                font=ctk.CTkFont(size=16, weight="bold"),
                height=50,
                width=200
            )
            quick_start_btn.grid(row=2, column=0, pady=40)
        
        # 显示首页面板
        self.home_panel.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.current_panel = self.home_panel
    
    def show_devices(self):
        """显示设备管理"""
        self.hide_current_panel()
        
        # 如果设备面板不存在，创建它
        if self.device_panel is None:
            self.device_panel = DeviceManagerPanel(self.main_frame)
        
        # 显示设备面板
        self.device_panel.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.current_panel = self.device_panel
    
    def show_tasks(self):
        """显示任务面板"""
        self.hide_current_panel()
        
        # 如果任务面板不存在，创建它
        if self.task_panel is None:
            self.task_panel = TaskPanel(self.main_frame)
        
        # 显示任务面板
        self.task_panel.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.current_panel = self.task_panel
    
    def show_settings(self):
        """显示设置"""
        self.hide_current_panel()
        
        # 如果设置面板不存在，创建它
        if self.settings_panel is None:
            self.settings_panel = SettingsPanel(self.main_frame)
        
        # 显示设置面板
        self.settings_panel.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.current_panel = self.settings_panel
    
    def toggle_appearance(self):
        """切换外观模式"""
        if self.appearance_switch.get() == "dark":
            ctk.set_appearance_mode("dark")
        else:
            ctk.set_appearance_mode("light")

