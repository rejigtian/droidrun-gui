"""
设备管理面板
"""

import customtkinter as ctk
import threading
from core.device_checker import DeviceChecker


class DeviceManagerPanel(ctk.CTkScrollableFrame):
    """设备管理面板"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.device_checker = DeviceChecker()
        self.grid_columnconfigure(0, weight=1)
        
        # 标题栏
        title_frame = ctk.CTkFrame(self)
        title_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        title_frame.grid_columnconfigure(0, weight=1)
        
        title_label = ctk.CTkLabel(
            title_frame,
            text="📱 设备管理",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")
        
        refresh_button = ctk.CTkButton(
            title_frame,
            text="🔄 刷新设备",
            command=self.refresh_devices
        )
        refresh_button.grid(row=0, column=1, padx=20, pady=10)
        
        # 设备列表容器
        self.device_list_frame = ctk.CTkFrame(self)
        self.device_list_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.device_list_frame.grid_columnconfigure(0, weight=1)
        
        # 初始加载设备
        self.refresh_devices()
        self._bind_trackpad()

    def _bind_trackpad(self):
        canvas = self._parent_canvas

        def _scroll(event):
            canvas.yview_scroll(int(-1 * event.delta), "units")

        self.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _scroll))
        self.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

    def refresh_devices(self):
        """刷新设备列表"""
        # 显示加载动画
        self.show_loading()
        
        # 在后台线程获取设备
        threading.Thread(target=self._load_devices, daemon=True).start()
    
    def show_loading(self):
        """显示加载状态"""
        for widget in self.device_list_frame.winfo_children():
            widget.destroy()
        
        loading_label = ctk.CTkLabel(
            self.device_list_frame,
            text="正在扫描设备...",
            font=ctk.CTkFont(size=14)
        )
        loading_label.pack(padx=20, pady=40)
    
    def _load_devices(self):
        """加载设备列表（后台线程）"""
        devices = self.device_checker.list_devices()
        
        # 在主线程更新 UI
        self.after(0, lambda: self._display_devices(devices))
    
    def _display_devices(self, devices):
        """显示设备列表"""
        # 清空当前列表
        for widget in self.device_list_frame.winfo_children():
            widget.destroy()
        
        if not devices:
            # 没有设备
            no_device_label = ctk.CTkLabel(
                self.device_list_frame,
                text="未找到连接的设备\n\n请确保：\n• 设备已连接\n• 已启用 USB 调试\n• 已授权此计算机",
                font=ctk.CTkFont(size=14),
                justify="center"
            )
            no_device_label.pack(padx=20, pady=40)
            return
        
        # 显示每个设备
        for i, device in enumerate(devices):
            device_card = DeviceCard(
                self.device_list_frame,
                device=device,
                device_checker=self.device_checker
            )
            device_card.pack(padx=10, pady=10, fill="x")


class DeviceCard(ctk.CTkFrame):
    """设备卡片组件"""
    
    def __init__(self, parent, device, device_checker):
        super().__init__(parent)
        
        self.device = device
        self.device_checker = device_checker
        
        self.grid_columnconfigure(1, weight=1)
        
        # 设备图标
        icon_label = ctk.CTkLabel(
            self,
            text="📱",
            font=ctk.CTkFont(size=40)
        )
        icon_label.grid(row=0, column=0, rowspan=3, padx=20, pady=20)
        
        # 设备信息
        model = device.get('model', 'Unknown')
        model_label = ctk.CTkLabel(
            self,
            text=model,
            font=ctk.CTkFont(size=18, weight="bold")
        )
        model_label.grid(row=0, column=1, padx=10, pady=(20, 5), sticky="w")
        
        serial_label = ctk.CTkLabel(
            self,
            text=f"序列号: {device['serial']}",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        serial_label.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        
        # Portal 状态
        self.portal_status_label = ctk.CTkLabel(
            self,
            text="检查中...",
            font=ctk.CTkFont(size=12)
        )
        self.portal_status_label.grid(row=2, column=1, padx=10, pady=(5, 20), sticky="w")
        
        # 操作按钮
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=0, column=2, rowspan=3, padx=20, pady=20)
        
        self.portal_button = ctk.CTkButton(
            button_frame,
            text="安装 Portal",
            command=self.install_portal,
            width=120
        )
        self.portal_button.pack(pady=5)
        
        test_button = ctk.CTkButton(
            button_frame,
            text="测试连接",
            command=self.test_connection,
            width=120
        )
        test_button.pack(pady=5)
        
        # 检查 Portal 状态
        self.check_portal_status()
    
    def check_portal_status(self):
        """检查 Portal 状态"""
        def _check():
            has_portal = self.device_checker.check_portal(self.device['serial'])
            
            if has_portal:
                status_text = "✅ Portal 已安装"
                status_color = "green"
                button_text = "重新安装"
            else:
                status_text = "❌ Portal 未安装"
                status_color = "red"
                button_text = "安装 Portal"
            
            # 安全地更新UI（lambda内部捕获错误，避免widget已销毁的问题）
            def update_status():
                try:
                    self.portal_status_label.configure(text=status_text, text_color=status_color)
                except Exception:
                    pass  # Widget已销毁，静默忽略
            
            def update_button():
                try:
                    self.portal_button.configure(text=button_text)
                except Exception:
                    pass  # Widget已销毁，静默忽略
            
            self.after(0, update_status)
            self.after(0, update_button)
        
        threading.Thread(target=_check, daemon=True).start()
    
    def install_portal(self):
        """安装 Portal"""
        self.portal_button.configure(state="disabled", text="安装中...")
        
        def _install():
            success, message = self.device_checker.install_portal(self.device['serial'])
            
            if success:
                needs_a11y = "请在手机" in message
                status_text = "⚠️ 需手动开启无障碍服务" if needs_a11y else "✅ Portal 已安装并启用"
                status_color = "orange" if needs_a11y else "green"
                def update_success(t=status_text, c=status_color):
                    try:
                        self.portal_status_label.configure(text=t, text_color=c)
                    except Exception:
                        pass  # Widget已销毁
                self.after(0, update_success)
                if needs_a11y:
                    import tkinter.messagebox as mb
                    self.after(200, lambda: mb.showinfo(
                        "需手动操作",
                        "Portal APK 已成功安装到设备。\n\n"
                        "请在手机上：\n"
                        "「设置 → 辅助功能（无障碍）→ 已下载的应用」\n"
                        "找到 DroidRun Portal 并开启。\n\n"
                        "开启后点击「测试连接」验证。"
                    ))
            else:
                def update_error():
                    try:
                        self.portal_status_label.configure(
                            text=f"❌ 安装失败: {message}",
                            text_color="red"
                        )
                    except Exception:
                        pass  # Widget已销毁
                self.after(0, update_error)
            
            def update_button_final():
                try:
                    self.portal_button.configure(
                        state="normal",
                        text="重新安装"
                    )
                except Exception:
                    pass  # Widget已销毁
            self.after(0, update_button_final)
        
        threading.Thread(target=_install, daemon=True).start()
    
    def test_connection(self):
        """测试连接"""
        try:
            self.portal_status_label.configure(text="测试中...", text_color="gray")
        except Exception:
            return  # Widget已销毁，直接返回
        
        def _test():
            has_portal = self.device_checker.check_portal(self.device['serial'])
            
            if has_portal:
                message = "✅ 连接正常"
                color = "green"
            else:
                message = "❌ 连接失败"
                color = "red"
            
            def update_test_result():
                try:
                    self.portal_status_label.configure(text=message, text_color=color)
                except Exception:
                    pass  # Widget已销毁
            self.after(0, update_test_result)
        
        threading.Thread(target=_test, daemon=True).start()

