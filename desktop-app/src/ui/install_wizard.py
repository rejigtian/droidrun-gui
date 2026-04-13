"""
安装向导
"""

import sys
import platform
import customtkinter as ctk
import threading
from core.installer import DroidRunInstaller


class InstallWizard(ctk.CTkFrame):
    """安装向导类"""
    
    def __init__(self, parent, on_complete=None):
        super().__init__(parent)
        
        self.on_complete = on_complete
        self.installer = DroidRunInstaller()
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # 标题
        self.title_label = ctk.CTkLabel(
            self,
            text="欢迎使用 DroidRun Desktop",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        self.title_label.grid(row=0, column=0, padx=40, pady=(60, 20))
        
        # 内容区域
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=100, pady=20)
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        self.show_welcome_screen()
    
    def clear_content(self):
        """清空内容区域"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def _is_frozen(self):
        return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

    def show_welcome_screen(self):
        """显示欢迎屏幕"""
        self.clear_content()

        if self._is_frozen():
            welcome_text = (
                "DroidRun Desktop 需要以下环境：\n\n"
                "• ADB (Android Debug Bridge)\n\n"
                "点击「开始检查」来检测你的系统环境"
            )
        else:
            welcome_text = (
                "DroidRun Desktop 需要以下环境：\n\n"
                "• Python 3.11+\n"
                "• ADB (Android Debug Bridge)\n"
                "• DroidRun 库\n\n"
                "点击「开始检查」来检测你的系统环境"
            )

        welcome_label = ctk.CTkLabel(
            self.content_frame,
            text=welcome_text,
            font=ctk.CTkFont(size=16),
            justify="left"
        )
        welcome_label.pack(padx=40, pady=(40, 20))
        
        # 按钮容器
        button_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        button_frame.pack(pady=40)
        
        # 开始按钮
        start_button = ctk.CTkButton(
            button_frame,
            text="开始检查",
            command=self.check_environment,
            font=ctk.CTkFont(size=16),
            height=50,
            width=200
        )
        start_button.grid(row=0, column=0, padx=10)
        
        # 跳过按钮
        skip_button = ctk.CTkButton(
            button_frame,
            text="已安装，跳过检测",
            command=self._skip_and_complete,
            font=ctk.CTkFont(size=16),
            height=50,
            width=200,
            fg_color="gray40",
            hover_color="gray30"
        )
        skip_button.grid(row=0, column=1, padx=10)
    
    def check_environment(self):
        """检查环境"""
        self.clear_content()
        
        # 检查标题
        check_label = ctk.CTkLabel(
            self.content_frame,
            text="正在检查系统环境...",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        check_label.pack(padx=40, pady=(40, 20))
        
        # 检查结果区域
        self.result_frame = ctk.CTkFrame(self.content_frame)
        self.result_frame.pack(padx=40, pady=20, fill="both", expand=True)
        
        # 进度条
        self.progress = ctk.CTkProgressBar(self.content_frame)
        self.progress.pack(padx=40, pady=20, fill="x")
        self.progress.set(0)
        
        # 在后台线程执行检查
        threading.Thread(target=self._do_check, daemon=True).start()
    
    def _do_check(self):
        """执行实际的检查（后台线程）"""
        results = {}

        if self._is_frozen():
            # 打包模式：droidrun 已内置，只检查 ADB
            self.progress.set(0.5)
            results['python'] = True
            results['adb'] = self.installer.check_adb()
            self._show_check_result("Android Debug Bridge (ADB)", results['adb'])
            results['droidrun'] = True  # 已内置，无需检查
        else:
            # 开发模式：完整检查
            self.progress.set(0.2)
            results['python'] = self.installer.check_python()
            self._show_check_result("Python 3.11+", results['python'])

            self.progress.set(0.5)
            results['adb'] = self.installer.check_adb()
            self._show_check_result("Android Debug Bridge (ADB)", results['adb'])

            self.progress.set(0.8)
            results['droidrun'] = self.installer.check_droidrun()
            self._show_check_result("DroidRun 库", results['droidrun'])

        self.progress.set(1.0)

        # 根据检查结果决定下一步
        self.after(1000, lambda: self._handle_check_results(results))
    
    def _show_check_result(self, item, success):
        """显示检查结果"""
        status = "✅ 已安装" if success else "❌ 未安装"
        color = "green" if success else "red"
        
        result_label = ctk.CTkLabel(
            self.result_frame,
            text=f"{item}: {status}",
            font=ctk.CTkFont(size=14),
            text_color=color
        )
        result_label.pack(padx=20, pady=10, anchor="w")
    
    def _handle_check_results(self, results):
        """处理检查结果"""
        if not results['adb']:
            self.show_adb_install_screen()
        elif not results['droidrun']:
            self.show_install_screen(results)
        else:
            self.show_complete_screen()
    
    def show_adb_install_screen(self):
        """显示 ADB 安装指引"""
        self.clear_content()

        title_label = ctk.CTkLabel(
            self.content_frame,
            text="需要安装 ADB",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="orange"
        )
        title_label.pack(padx=40, pady=(40, 10))

        system = platform.system()
        if system == 'Darwin':
            instructions = (
                "ADB (Android Debug Bridge) 未检测到。\n\n"
                "安装方法（选其一）：\n\n"
                "方法一（推荐）：Homebrew\n"
                "  brew install android-platform-tools\n\n"
                "方法二：Android Studio\n"
                "  安装 Android Studio 后，adb 位于：\n"
                "  ~/Library/Android/sdk/platform-tools/adb\n\n"
                "安装完成后点击「重新检测」。"
            )
        elif system == 'Windows':
            instructions = (
                "ADB (Android Debug Bridge) 未检测到。\n\n"
                "安装方法：\n\n"
                "方法一：下载 Platform Tools\n"
                "  https://developer.android.com/tools/releases/platform-tools\n"
                "  解压后将文件夹路径添加到系统 PATH\n\n"
                "方法二：Android Studio\n"
                "  安装 Android Studio 后 adb 会自动配置\n\n"
                "安装完成后点击「重新检测」。"
            )
        else:
            instructions = (
                "ADB (Android Debug Bridge) 未检测到。\n\n"
                "安装方法：\n\n"
                "  sudo apt install adb          # Debian/Ubuntu\n"
                "  sudo pacman -S android-tools  # Arch\n\n"
                "安装完成后点击「重新检测」。"
            )

        inst_label = ctk.CTkLabel(
            self.content_frame,
            text=instructions,
            font=ctk.CTkFont(family="Courier", size=13),
            justify="left"
        )
        inst_label.pack(padx=40, pady=20, anchor="w")

        btn_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        btn_frame.pack(pady=30)

        retry_button = ctk.CTkButton(
            btn_frame,
            text="重新检测",
            command=self.check_environment,
            font=ctk.CTkFont(size=15),
            height=44,
            width=160
        )
        retry_button.grid(row=0, column=0, padx=10)

        skip_button = ctk.CTkButton(
            btn_frame,
            text="稍后安装，先跳过",
            command=self._skip_and_complete,
            font=ctk.CTkFont(size=15),
            height=44,
            width=180,
            fg_color="gray40",
            hover_color="gray30"
        )
        skip_button.grid(row=0, column=1, padx=10)

    def show_install_screen(self, check_results):
        """显示安装屏幕"""
        self.clear_content()
        
        # 标题
        install_label = ctk.CTkLabel(
            self.content_frame,
            text="安装 DroidRun",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        install_label.pack(padx=40, pady=(40, 20))
        
        # 提示信息
        if not check_results.get('python'):
            info_text = "❌ Python 3.11+ 未安装\n请先安装 Python 3.11 或更高版本"
            color = "red"
        elif not check_results.get('adb'):
            info_text = "⚠️ ADB 未安装\n建议先安装 ADB，或稍后手动安装"
            color = "orange"
        else:
            info_text = "准备安装 DroidRun\n选择安装方式："
            color = "white"
        
        info_label = ctk.CTkLabel(
            self.content_frame,
            text=info_text,
            font=ctk.CTkFont(size=14),
            text_color=color
        )
        info_label.pack(padx=40, pady=20)
        
        if check_results.get('python'):
            # 安装方式选择
            self.install_method = ctk.StringVar(value="pipx")
            
            pipx_radio = ctk.CTkRadioButton(
                self.content_frame,
                text="pipx (推荐)",
                variable=self.install_method,
                value="pipx"
            )
            pipx_radio.pack(padx=60, pady=10, anchor="w")
            
            pip_radio = ctk.CTkRadioButton(
                self.content_frame,
                text="pip3 --user",
                variable=self.install_method,
                value="pip"
            )
            pip_radio.pack(padx=60, pady=10, anchor="w")
            
            # 安装按钮
            install_button = ctk.CTkButton(
                self.content_frame,
                text="开始安装",
                command=self.start_install,
                font=ctk.CTkFont(size=16),
                height=50,
                width=200
            )
            install_button.pack(pady=40)
        else:
            # Python 未安装，显示安装指南
            guide_text = """
            请先安装 Python 3.11+:
            
            macOS: brew install python@3.11
            Windows: 访问 python.org 下载安装
            
            安装完成后重新运行此程序
            """
            
            guide_label = ctk.CTkLabel(
                self.content_frame,
                text=guide_text,
                font=ctk.CTkFont(size=12),
                justify="left"
            )
            guide_label.pack(padx=40, pady=20)
    
    def start_install(self):
        """开始安装"""
        self.clear_content()
        
        # 安装进度标题
        progress_label = ctk.CTkLabel(
            self.content_frame,
            text="正在安装 DroidRun...",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        progress_label.pack(padx=40, pady=(40, 20))
        
        # 日志显示区域
        self.log_textbox = ctk.CTkTextbox(
            self.content_frame,
            font=ctk.CTkFont(family="Courier", size=12)
        )
        self.log_textbox.pack(padx=40, pady=20, fill="both", expand=True)
        
        # 进度条
        self.install_progress = ctk.CTkProgressBar(self.content_frame)
        self.install_progress.pack(padx=40, pady=20, fill="x")
        self.install_progress.set(0)
        
        # 在后台线程执行安装
        method = self.install_method.get()
        threading.Thread(
            target=self._do_install,
            args=(method,),
            daemon=True
        ).start()
    
    def _do_install(self, method):
        """执行实际的安装"""
        def log_callback(message):
            self.log_textbox.insert("end", message + "\n")
            self.log_textbox.see("end")
        
        success, message = self.installer.install_droidrun(method, log_callback)
        
        self.install_progress.set(1.0)
        
        if success:
            self.after(1000, self.show_complete_screen)
        else:
            self.after(1000, lambda: self.show_error_screen(message))
    
    def show_complete_screen(self):
        """显示完成屏幕"""
        self.clear_content()
        
        # 成功图标和文字
        success_label = ctk.CTkLabel(
            self.content_frame,
            text="✅ 安装完成！",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="green"
        )
        success_label.pack(padx=40, pady=(80, 40))
        
        info_label = ctk.CTkLabel(
            self.content_frame,
            text="DroidRun Desktop 已准备就绪",
            font=ctk.CTkFont(size=16)
        )
        info_label.pack(padx=40, pady=20)
        
        # 开始使用按钮
        start_button = ctk.CTkButton(
            self.content_frame,
            text="开始使用",
            command=self._complete,
            font=ctk.CTkFont(size=16),
            height=50,
            width=200
        )
        start_button.pack(pady=40)
    
    def show_error_screen(self, error_message):
        """显示错误屏幕"""
        self.clear_content()
        
        error_label = ctk.CTkLabel(
            self.content_frame,
            text="❌ 安装失败",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="red"
        )
        error_label.pack(padx=40, pady=(80, 40))
        
        error_text = ctk.CTkTextbox(
            self.content_frame,
            font=ctk.CTkFont(family="Courier", size=12)
        )
        error_text.pack(padx=40, pady=20, fill="both", expand=True)
        error_text.insert("1.0", error_message)
        
        # 重试按钮
        retry_button = ctk.CTkButton(
            self.content_frame,
            text="重试",
            command=self.check_environment,
            font=ctk.CTkFont(size=16),
            height=50,
            width=200
        )
        retry_button.pack(pady=40)
    
    def _skip_and_complete(self):
        """跳过检测并完成"""
        # 标记为已安装（保存到缓存）
        self.installer._save_cache({'droidrun_installed': True})
        
        # 显示跳过提示
        self.clear_content()
        
        skip_label = ctk.CTkLabel(
            self.content_frame,
            text="✅ 已跳过检测\n\n正在启动应用...",
            font=ctk.CTkFont(size=20),
            text_color="green"
        )
        skip_label.pack(pady=100)
        
        # 延迟进入主界面
        self.after(500, self._complete)
    
    def _complete(self):
        """安装完成"""
        if self.on_complete:
            self.on_complete()

