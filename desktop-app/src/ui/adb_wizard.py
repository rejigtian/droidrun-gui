"""
ADB 安装向导
检测 ADB 是否安装，如果未安装则引导用户安装或配置
"""

import customtkinter as ctk
import subprocess
import threading
import platform
import os
from pathlib import Path


class AdbWizard(ctk.CTkFrame):
    """ADB 安装向导"""
    
    def __init__(self, parent, on_complete=None):
        super().__init__(parent)
        self.on_complete = on_complete
        self.system = platform.system()
        
        # 创建内容框架
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=40, pady=40)
        
        # 显示检测页面
        self.show_detection_screen()
    
    def show_detection_screen(self):
        """显示 ADB 检测页面"""
        self._clear_content()
        
        # 标题
        title = ctk.CTkLabel(
            self.content_frame,
            text="🔍 环境检测",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        title.pack(pady=(0, 20))
        
        # 描述
        desc = ctk.CTkLabel(
            self.content_frame,
            text="正在检测 Android Debug Bridge (ADB)...\n这是与 Android 设备通信的必需工具",
            font=ctk.CTkFont(size=14),
            text_color="gray70"
        )
        desc.pack(pady=(0, 30))
        
        # 检测状态
        self.status_label = ctk.CTkLabel(
            self.content_frame,
            text="⏳ 检测中...",
            font=ctk.CTkFont(size=16)
        )
        self.status_label.pack(pady=20)
        
        # 在后台线程执行检测
        threading.Thread(target=self._do_detection, daemon=True).start()
    
    def _do_detection(self):
        """执行 ADB 检测"""
        import time
        time.sleep(1)  # 给用户一点视觉反馈
        
        # 尝试多种方式检测 ADB
        adb_path = self._find_adb()
        
        if adb_path:
            # 找到 ADB，测试是否可用
            if self._test_adb(adb_path):
                self.after(0, lambda: self._on_detection_success(adb_path))
            else:
                self.after(0, lambda: self._on_detection_failed("ADB 已找到但无法正常运行"))
        else:
            self.after(0, self._on_detection_failed)
    
    def _find_adb(self):
        """查找 ADB"""
        # 常见的 ADB 路径
        common_paths = []
        
        if self.system == "Darwin":  # macOS
            common_paths = [
                "/opt/homebrew/bin/adb",
                "/usr/local/bin/adb",
                str(Path.home() / "Library/Android/sdk/platform-tools/adb"),
                "/Users/{}/Library/Android/sdk/platform-tools/adb".format(os.getenv('USER', ''))
            ]
        elif self.system == "Windows":
            username = os.getenv('USERNAME', '')
            common_paths = [
                f"C:\\Users\\{username}\\AppData\\Local\\Android\\Sdk\\platform-tools\\adb.exe",
                "C:\\Android\\sdk\\platform-tools\\adb.exe",
                "C:\\platform-tools\\adb.exe"
            ]
        else:  # Linux
            common_paths = [
                "/usr/bin/adb",
                "/usr/local/bin/adb",
                str(Path.home() / "Android/Sdk/platform-tools/adb")
            ]
        
        # 检查常见路径
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        # 尝试使用 which/where 命令
        try:
            cmd = "where" if self.system == "Windows" else "which"
            result = subprocess.run(
                [cmd, "adb"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split('\n')[0]
        except:
            pass
        
        return None
    
    def _test_adb(self, adb_path):
        """测试 ADB 是否可用"""
        try:
            result = subprocess.run(
                [adb_path, "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False
    
    def _on_detection_success(self, adb_path):
        """检测成功"""
        # 检查控件是否仍然存在，并包装所有 UI 操作
        try:
            if not self.winfo_exists():
                print("⚠️ 窗口已销毁")
                return
            
            print(f"✅ ADB 检测成功: {adb_path}")
            
            self.status_label.configure(
                text=f"✅ ADB 已安装并可用\n路径: {adb_path}",
                text_color="green"
            )
            
            # 保存 ADB 路径到配置
            from utils.config import ConfigManager
            from utils.sdk_manager import get_sdk_manager
            
            config_manager = ConfigManager()
            sdk_manager = get_sdk_manager(config_manager)
            sdk_manager.set_tool_path('adb', adb_path)
            print("✅ ADB 路径已保存")
            
            # 显示继续按钮
            print("📝 创建继续按钮...")
            
            # 创建按钮容器
            btn_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
            btn_frame.pack(pady=30, fill="x", padx=20)
            
            # 继续按钮
            continue_btn = ctk.CTkButton(
                btn_frame,
                text="继续 →",
                command=self._complete,
                font=ctk.CTkFont(size=16, weight="bold"),
                height=50,
                fg_color="#4CAF50",
                hover_color="#45a049"
            )
            continue_btn.pack(side="left", expand=True, fill="x", padx=5)
            
            # 跳过按钮（备用）
            skip_btn = ctk.CTkButton(
                btn_frame,
                text="跳过",
                command=self._complete,
                font=ctk.CTkFont(size=14),
                height=50,
                fg_color="gray40",
                hover_color="gray50"
            )
            skip_btn.pack(side="right", padx=5)
            
            print("✅ 继续按钮已显示")
            
            # 强制刷新界面
            self.content_frame.update_idletasks()
            self.update_idletasks()
            
        except Exception as e:
            print(f"❌ 显示继续按钮失败: {e}")
            import traceback
            traceback.print_exc()
            # 即使失败也尝试自动继续
            try:
                self.after(3000, self._complete)  # 3秒后自动继续
            except:
                pass
    
    def _on_detection_failed(self, error=None):
        """检测失败，显示安装选项"""
        # 检查控件是否仍然存在，并包装所有 UI 操作
        try:
            if not self.winfo_exists():
                return
            self.show_install_options(error)
        except Exception as e:
            # 窗口已关闭，静默忽略
            pass
    
    def show_install_options(self, error=None):
        """显示安装选项"""
        self._clear_content()
        
        # 标题
        title = ctk.CTkLabel(
            self.content_frame,
            text="❌ 未找到 ADB",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color="#F44336"
        )
        title.pack(pady=(0, 10))
        
        # 错误信息（如果有）
        if error:
            error_label = ctk.CTkLabel(
                self.content_frame,
                text=f"原因: {error}",
                font=ctk.CTkFont(size=12),
                text_color="orange"
            )
            error_label.pack(pady=5)
        
        # 描述
        desc = ctk.CTkLabel(
            self.content_frame,
            text="ADB (Android Debug Bridge) 是与 Android 设备通信的必需工具\n请选择以下方式之一来安装或配置 ADB",
            font=ctk.CTkFont(size=14),
            text_color="gray70"
        )
        desc.pack(pady=(5, 30))
        
        # 选项按钮容器
        options_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        options_frame.pack(pady=20, fill="x")
        
        # 选项 1: 自动安装（推荐）
        auto_frame = ctk.CTkFrame(options_frame)
        auto_frame.pack(pady=10, padx=20, fill="x")
        
        auto_title = ctk.CTkLabel(
            auto_frame,
            text="🚀 自动安装（推荐）",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        auto_title.pack(pady=(15, 5))
        
        auto_desc = self._get_auto_install_desc()
        auto_desc_label = ctk.CTkLabel(
            auto_frame,
            text=auto_desc,
            font=ctk.CTkFont(size=12),
            text_color="gray60"
        )
        auto_desc_label.pack(pady=5)
        
        auto_btn = ctk.CTkButton(
            auto_frame,
            text="自动安装 ADB",
            command=self.start_auto_install,
            font=ctk.CTkFont(size=14),
            height=40,
            fg_color="#2196F3",
            hover_color="#1976D2"
        )
        auto_btn.pack(pady=15, padx=20, fill="x")
        
        # 选项 2: 手动配置路径
        manual_frame = ctk.CTkFrame(options_frame)
        manual_frame.pack(pady=10, padx=20, fill="x")
        
        manual_title = ctk.CTkLabel(
            manual_frame,
            text="⚙️ 手动配置路径",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        manual_title.pack(pady=(15, 5))
        
        manual_desc_label = ctk.CTkLabel(
            manual_frame,
            text="如果您已经安装了 ADB，可以手动指定路径",
            font=ctk.CTkFont(size=12),
            text_color="gray60"
        )
        manual_desc_label.pack(pady=5)
        
        manual_btn = ctk.CTkButton(
            manual_frame,
            text="手动配置路径",
            command=self.show_manual_config,
            font=ctk.CTkFont(size=14),
            height=40,
            fg_color="#FF9800",
            hover_color="#F57C00"
        )
        manual_btn.pack(pady=15, padx=20, fill="x")
        
        # 选项 3: 跳过（继续但功能受限）
        skip_btn = ctk.CTkButton(
            self.content_frame,
            text="跳过（稍后配置）",
            command=self._complete,
            font=ctk.CTkFont(size=12),
            height=30,
            fg_color="gray40",
            hover_color="gray50"
        )
        skip_btn.pack(pady=10)
    
    def _get_auto_install_desc(self):
        """获取自动安装描述"""
        if self.system == "Darwin":
            return "通过 Homebrew 安装 android-platform-tools\n需要: Homebrew 已安装"
        elif self.system == "Windows":
            return "下载 Android SDK Platform Tools 并配置环境变量\n需要: 管理员权限（可选）"
        else:
            return "通过系统包管理器安装 android-tools-adb\n需要: sudo 权限"
    
    def start_auto_install(self):
        """开始自动安装"""
        self._clear_content()
        
        # 标题
        title = ctk.CTkLabel(
            self.content_frame,
            text="🚀 正在安装 ADB",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        title.pack(pady=(0, 20))
        
        # 日志文本框
        self.log_textbox = ctk.CTkTextbox(
            self.content_frame,
            font=ctk.CTkFont(family="Courier", size=12),
            height=300
        )
        self.log_textbox.pack(padx=20, pady=20, fill="both", expand=True)
        
        # 进度条
        self.progress = ctk.CTkProgressBar(self.content_frame)
        self.progress.pack(padx=20, pady=10, fill="x")
        self.progress.set(0)
        
        # 在后台线程执行安装
        threading.Thread(target=self._do_auto_install, daemon=True).start()
    
    def _do_auto_install(self):
        """执行自动安装"""
        def log(message):
            self.log_textbox.insert("end", message + "\n")
            self.log_textbox.see("end")
        
        try:
            if self.system == "Darwin":
                success = self._install_macos(log)
            elif self.system == "Windows":
                success = self._install_windows(log)
            else:
                success = self._install_linux(log)
            
            self.progress.set(1.0)
            
            if success:
                self.after(0, self._on_install_success)
            else:
                self.after(0, self._on_install_failed)
        
        except Exception as e:
            self.after(0, lambda: self._on_install_failed(str(e)))
    
    def _install_macos(self, log):
        """macOS 安装"""
        log("📱 macOS 系统检测成功")
        log("正在检查 Homebrew...")
        
        # 检查 Homebrew
        try:
            result = subprocess.run(
                ["brew", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                log("❌ Homebrew 未安装")
                log("请先安装 Homebrew: https://brew.sh")
                return False
            
            log(f"✅ Homebrew 已安装: {result.stdout.strip()}")
        except:
            log("❌ 无法检测 Homebrew")
            return False
        
        self.progress.set(0.3)
        
        # 安装 android-platform-tools
        log("\n正在安装 android-platform-tools...")
        log("命令: brew install android-platform-tools")
        
        try:
            result = subprocess.run(
                ["brew", "install", "android-platform-tools"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            log(result.stdout)
            if result.stderr:
                log(result.stderr)
            
            if result.returncode != 0:
                log("\n❌ 安装失败")
                return False
            
            self.progress.set(0.8)
            
            # 验证安装
            log("\n正在验证安装...")
            adb_path = self._find_adb()
            if adb_path and self._test_adb(adb_path):
                log(f"✅ ADB 安装成功: {adb_path}")
                
                # 保存路径
                from utils.config import ConfigManager
                from utils.sdk_manager import get_sdk_manager
                config_manager = ConfigManager()
                sdk_manager = get_sdk_manager(config_manager)
                sdk_manager.set_tool_path('adb', adb_path)
                
                return True
            else:
                log("❌ 安装后验证失败")
                return False
        
        except subprocess.TimeoutExpired:
            log("❌ 安装超时")
            return False
        except Exception as e:
            log(f"❌ 安装错误: {e}")
            return False
    
    def _install_windows(self, log):
        """Windows 安装（提供下载链接）"""
        log("💻 Windows 系统检测成功")
        log("\n由于权限限制，请手动下载并安装 ADB:")
        log("\n1. 访问: https://developer.android.com/studio/releases/platform-tools")
        log("2. 下载 'SDK Platform-Tools for Windows'")
        log("3. 解压到 C:\\platform-tools")
        log("4. 将 C:\\platform-tools 添加到系统 PATH")
        log("\n📖 详细教程: https://www.xda-developers.com/install-adb-windows-macos-linux/")
        
        self.progress.set(1.0)
        return False  # 需要用户手动操作
    
    def _install_linux(self, log):
        """Linux 安装"""
        log("🐧 Linux 系统检测成功")
        
        # 检测发行版
        try:
            with open("/etc/os-release") as f:
                os_info = f.read()
            
            if "ubuntu" in os_info.lower() or "debian" in os_info.lower():
                cmd = ["sudo", "apt-get", "install", "-y", "android-tools-adb"]
                pkg = "android-tools-adb"
            elif "arch" in os_info.lower():
                cmd = ["sudo", "pacman", "-S", "--noconfirm", "android-tools"]
                pkg = "android-tools"
            elif "fedora" in os_info.lower():
                cmd = ["sudo", "dnf", "install", "-y", "android-tools"]
                pkg = "android-tools"
            else:
                log("❌ 未识别的 Linux 发行版")
                log("请手动安装 adb")
                return False
            
            log(f"正在安装 {pkg}...")
            log(f"命令: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            log(result.stdout)
            if result.stderr:
                log(result.stderr)
            
            if result.returncode == 0:
                log("✅ 安装成功")
                return True
            else:
                log("❌ 安装失败")
                return False
        
        except Exception as e:
            log(f"❌ 安装错误: {e}")
            return False
    
    def _on_install_success(self):
        """安装成功"""
        success_label = ctk.CTkLabel(
            self.content_frame,
            text="\n✅ ADB 安装成功！",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="green"
        )
        success_label.pack(pady=10)
        
        continue_btn = ctk.CTkButton(
            self.content_frame,
            text="继续 →",
            command=self._complete,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            fg_color="#4CAF50",
            hover_color="#45a049"
        )
        continue_btn.pack(pady=20)
    
    def _on_install_failed(self, error=None):
        """安装失败"""
        # 检查控件是否仍然存在，并包装所有 UI 操作
        try:
            if not self.winfo_exists():
                return
            
            fail_label = ctk.CTkLabel(
                self.content_frame,
                text="\n❌ 自动安装失败",
                font=ctk.CTkFont(size=18, weight="bold"),
                text_color="#F44336"
            )
            fail_label.pack(pady=10)
            
            if error:
                error_label = ctk.CTkLabel(
                    self.content_frame,
                    text=f"错误: {error}",
                    font=ctk.CTkFont(size=12),
                    text_color="orange"
                )
                error_label.pack(pady=5)
            
            # 显示替代选项
            manual_btn = ctk.CTkButton(
                self.content_frame,
                text="手动配置路径",
                command=self.show_manual_config,
                font=ctk.CTkFont(size=14),
                height=40,
                fg_color="#FF9800",
                hover_color="#F57C00"
            )
            manual_btn.pack(pady=10)
            
            skip_btn = ctk.CTkButton(
                self.content_frame,
                text="跳过（稍后配置）",
                command=self._complete,
                font=ctk.CTkFont(size=12),
                height=30,
                fg_color="gray40",
                hover_color="gray50"
            )
            skip_btn.pack(pady=5)
        except Exception as e:
            # 窗口已关闭，静默忽略
            pass
    
    def show_manual_config(self):
        """显示手动配置页面"""
        self._clear_content()
        
        # 标题
        title = ctk.CTkLabel(
            self.content_frame,
            text="⚙️ 手动配置 ADB 路径",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        title.pack(pady=(0, 20))
        
        # 描述
        desc = ctk.CTkLabel(
            self.content_frame,
            text="请输入 ADB 可执行文件的完整路径",
            font=ctk.CTkFont(size=14),
            text_color="gray70"
        )
        desc.pack(pady=(0, 20))
        
        # 路径输入
        path_frame = ctk.CTkFrame(self.content_frame)
        path_frame.pack(pady=20, padx=40, fill="x")
        
        self.path_entry = ctk.CTkEntry(
            path_frame,
            placeholder_text="/usr/local/bin/adb",
            font=ctk.CTkFont(size=14),
            height=40
        )
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(10, 5))
        
        browse_btn = ctk.CTkButton(
            path_frame,
            text="📁 浏览",
            command=self._browse_adb_path,
            width=100,
            height=40
        )
        browse_btn.pack(side="right", padx=(5, 10))
        
        # 验证按钮
        verify_btn = ctk.CTkButton(
            self.content_frame,
            text="✅ 验证并保存",
            command=self._verify_manual_path,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            fg_color="#4CAF50",
            hover_color="#45a049"
        )
        verify_btn.pack(pady=20)
        
        # 状态标签
        self.verify_status = ctk.CTkLabel(
            self.content_frame,
            text="",
            font=ctk.CTkFont(size=14)
        )
        self.verify_status.pack(pady=10)
        
        # 返回按钮
        back_btn = ctk.CTkButton(
            self.content_frame,
            text="← 返回",
            command=self.show_install_options,
            font=ctk.CTkFont(size=12),
            height=30,
            fg_color="gray40",
            hover_color="gray50"
        )
        back_btn.pack(pady=10)
    
    def _browse_adb_path(self):
        """浏览 ADB 路径"""
        from tkinter import filedialog
        
        filename = filedialog.askopenfilename(
            title="选择 ADB 可执行文件",
            filetypes=[("可执行文件", "*"), ("所有文件", "*.*")]
        )
        
        if filename:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, filename)
    
    def _verify_manual_path(self):
        """验证手动输入的路径"""
        path = self.path_entry.get().strip()
        
        if not path:
            self.verify_status.configure(
                text="❌ 请输入路径",
                text_color="red"
            )
            return
        
        # 展开路径
        path = os.path.expanduser(path)
        
        # 检查文件是否存在
        if not os.path.exists(path):
            self.verify_status.configure(
                text="❌ 文件不存在",
                text_color="red"
            )
            return
        
        # 测试 ADB
        if not self._test_adb(path):
            self.verify_status.configure(
                text="❌ 无法运行 ADB，请检查路径是否正确",
                text_color="red"
            )
            return
        
        # 保存路径
        from utils.config import ConfigManager
        from utils.sdk_manager import get_sdk_manager
        
        config_manager = ConfigManager()
        sdk_manager = get_sdk_manager(config_manager)
        sdk_manager.set_tool_path('adb', path)
        
        self.verify_status.configure(
            text="✅ ADB 配置成功！",
            text_color="green"
        )
        
        # 显示继续按钮
        continue_btn = ctk.CTkButton(
            self.content_frame,
            text="继续 →",
            command=self._complete,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            fg_color="#4CAF50",
            hover_color="#45a049"
        )
        continue_btn.pack(pady=20)
    
    def _complete(self):
        """完成向导"""
        if self.on_complete:
            self.on_complete()
    
    def _clear_content(self):
        """清空内容框架"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

