"""
设置面板
"""

import customtkinter as ctk
from tkinter import StringVar, filedialog, messagebox
import os
import platform
from utils.config import ConfigManager
from utils.sdk_manager import get_sdk_manager


class SettingsPanel(ctk.CTkScrollableFrame):
    """设置面板"""
    
    def __init__(self, parent):
        # 创建可滚动Frame，增加滚动条宽度，优化触摸板用户体验
        super().__init__(
            parent,
            scrollbar_button_color="#4CAF50",  # 绿色滚动条，更醒目
            scrollbar_button_hover_color="#45a049",
            fg_color="transparent"
        )
        
        # Tkinter 在 macOS 上不支持触摸板滚动手势（底层限制）
        # 建议：使用右侧滚动条或外接鼠标
        
        self.config = ConfigManager()
        self.grid_columnconfigure(0, weight=1)
        
        # 初始化 SDK 管理器
        try:
            self.sdk_manager = get_sdk_manager(self.config)
        except:
            self.sdk_manager = get_sdk_manager(self.config)
        
        # 存储 SDK 路径的 Entry 控件
        self.sdk_entries = {}
        self.sdk_status_labels = {}
        
        # 标题
        title_label = ctk.CTkLabel(
            self,
            text="⚙️ 设置",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        # LLM 提供商设置
        llm_frame = ctk.CTkFrame(self)
        llm_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        llm_frame.grid_columnconfigure(1, weight=1)
        
        llm_title = ctk.CTkLabel(
            llm_frame,
            text="LLM 提供商",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        llm_title.grid(row=0, column=0, columnspan=2, padx=20, pady=10, sticky="w")
        
        # Google API Key
        google_label = ctk.CTkLabel(llm_frame, text="Google API Key:")
        google_label.grid(row=1, column=0, padx=20, pady=10, sticky="w")
        
        self.google_entry = ctk.CTkEntry(llm_frame, show="*", placeholder_text="输入 API Key")
        self.google_entry.grid(row=1, column=1, padx=20, pady=10, sticky="ew")
        
        # OpenAI API Key
        openai_label = ctk.CTkLabel(llm_frame, text="OpenAI API Key:")
        openai_label.grid(row=2, column=0, padx=20, pady=10, sticky="w")
        
        self.openai_entry = ctk.CTkEntry(llm_frame, show="*", placeholder_text="输入 API Key")
        self.openai_entry.grid(row=2, column=1, padx=20, pady=10, sticky="ew")
        
        # Anthropic API Key
        anthropic_label = ctk.CTkLabel(llm_frame, text="Anthropic API Key:")
        anthropic_label.grid(row=3, column=0, padx=20, pady=10, sticky="w")
        
        self.anthropic_entry = ctk.CTkEntry(llm_frame, show="*", placeholder_text="输入 API Key")
        self.anthropic_entry.grid(row=3, column=1, padx=20, pady=10, sticky="ew")
        
        # DeepSeek API Key
        deepseek_label = ctk.CTkLabel(llm_frame, text="DeepSeek API Key:")
        deepseek_label.grid(row=4, column=0, padx=20, pady=10, sticky="w")
        
        self.deepseek_entry = ctk.CTkEntry(llm_frame, show="*", placeholder_text="输入 API Key (几乎免费)")
        self.deepseek_entry.grid(row=4, column=1, padx=20, pady=10, sticky="ew")
        
        # ZhipuAI API Key
        zhipu_label = ctk.CTkLabel(llm_frame, text="智谱 AI API Key:")
        zhipu_label.grid(row=5, column=0, padx=20, pady=10, sticky="w")
        
        self.zhipu_entry = ctk.CTkEntry(llm_frame, show="*", placeholder_text="输入 API Key (国内访问快)")
        self.zhipu_entry.grid(row=5, column=1, padx=20, pady=10, sticky="ew")
        
        # 分隔线
        separator = ctk.CTkLabel(llm_frame, text="———— 或使用免费的本地模型 ————", text_color="gray")
        separator.grid(row=6, column=0, columnspan=2, padx=20, pady=10)
        
        # Ollama 说明
        ollama_info = ctk.CTkLabel(
            llm_frame, 
            text="💡 Ollama: 完全免费的本地 AI (无需 API Key)\n   安装: brew install ollama && ollama pull llama3.2:3b",
            justify="left",
            text_color="green"
        )
        ollama_info.grid(row=7, column=0, columnspan=2, padx=20, pady=10, sticky="w")
        
        # 默认提供商选择
        provider_label = ctk.CTkLabel(llm_frame, text="默认提供商:")
        provider_label.grid(row=8, column=0, padx=20, pady=10, sticky="w")
        
        self.provider_var = StringVar(value="GoogleGenAI")
        provider_menu = ctk.CTkOptionMenu(
            llm_frame,
            variable=self.provider_var,
            values=["Ollama (免费推荐)", "智谱AI (国内快)", "DeepSeek (便宜)", "GoogleGenAI", "OpenAI", "Anthropic"]
        )
        provider_menu.grid(row=8, column=1, padx=20, pady=10, sticky="w")
        
        # Gemini 模型选择
        model_label = ctk.CTkLabel(llm_frame, text="Gemini 模型:")
        model_label.grid(row=9, column=0, padx=20, pady=10, sticky="w")

        self.gemini_model_var = StringVar(value="gemini-1.5-flash")
        model_menu = ctk.CTkOptionMenu(
            llm_frame,
            variable=self.gemini_model_var,
            values=[
                "gemini-1.5-flash (推荐)",
                "gemini-1.5-flash-8b (更快)",
                "gemini-2.0-flash-exp (实验版)",
                "gemini-1.5-pro (效果好但限制多)"
            ]
        )
        model_menu.grid(row=9, column=1, padx=20, pady=10, sticky="w")

        # OpenAI 模型选择
        openai_model_label = ctk.CTkLabel(llm_frame, text="OpenAI 模型:")
        openai_model_label.grid(row=10, column=0, padx=20, pady=10, sticky="w")

        self.openai_model_var = StringVar(value="gpt-4o")
        openai_model_menu = ctk.CTkOptionMenu(
            llm_frame,
            variable=self.openai_model_var,
            values=[
                "gpt-4o (推荐)",
                "gpt-4o-mini (快速便宜)",
                "gpt-4-turbo (强推理)",
                "o1-mini (推理专用)",
            ]
        )
        openai_model_menu.grid(row=10, column=1, padx=20, pady=10, sticky="w")

        # Anthropic 模型选择
        anthropic_model_label = ctk.CTkLabel(llm_frame, text="Anthropic 模型:")
        anthropic_model_label.grid(row=11, column=0, padx=20, pady=10, sticky="w")

        self.anthropic_model_var = StringVar(value="claude-sonnet-4-6")
        anthropic_model_menu = ctk.CTkOptionMenu(
            llm_frame,
            variable=self.anthropic_model_var,
            values=[
                "claude-sonnet-4-6 (推荐)",
                "claude-haiku-4-5-20251001 (快速便宜)",
                "claude-opus-4-6 (最强)",
            ]
        )
        anthropic_model_menu.grid(row=11, column=1, padx=20, pady=10, sticky="w")

        # 智谱AI 模型选择
        zhipu_model_label = ctk.CTkLabel(llm_frame, text="智谱AI 模型:")
        zhipu_model_label.grid(row=12, column=0, padx=20, pady=10, sticky="w")

        self.zhipu_model_var = StringVar(value="glm-4-plus")
        zhipu_model_menu = ctk.CTkOptionMenu(
            llm_frame,
            variable=self.zhipu_model_var,
            values=[
                "glm-4-plus (推荐)",
                "glm-4-flash (快速)",
                "glm-4-flashx (超快)",
                "glm-4-air (经济)"
            ]
        )
        zhipu_model_menu.grid(row=12, column=1, padx=20, pady=10, sticky="w")

        # 提示信息
        tip_label = ctk.CTkLabel(
            llm_frame,
            text="💡 推荐：Ollama(免费) / 智谱AI(国内快) / gemini-1.5-flash(国外快)",
            text_color="orange",
            font=ctk.CTkFont(size=11)
        )
        tip_label.grid(row=13, column=0, columnspan=2, padx=20, pady=5, sticky="w")
        
        # 应用设置
        app_frame = ctk.CTkFrame(self)
        app_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        app_frame.grid_columnconfigure(1, weight=1)
        
        app_title = ctk.CTkLabel(
            app_frame,
            text="应用设置",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        app_title.grid(row=0, column=0, columnspan=2, padx=20, pady=10, sticky="w")
        
        # 最大步骤数
        steps_label = ctk.CTkLabel(app_frame, text="默认最大步骤数:")
        steps_label.grid(row=1, column=0, padx=20, pady=10, sticky="w")
        
        self.steps_var = StringVar(value="15")
        steps_entry = ctk.CTkEntry(app_frame, textvariable=self.steps_var, width=100)
        steps_entry.grid(row=1, column=1, padx=20, pady=10, sticky="w")
        
        # SDK 路径设置
        sdk_frame = ctk.CTkFrame(self)
        sdk_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        sdk_frame.grid_columnconfigure(1, weight=1)
        
        sdk_title = ctk.CTkLabel(
            sdk_frame,
            text="SDK 路径设置",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        sdk_title.grid(row=0, column=0, columnspan=3, padx=20, pady=10, sticky="w")
        
        sdk_tip = ctk.CTkLabel(
            sdk_frame,
            text="💡 应用会自动检测工具路径，也可以手动指定以避免路径问题",
            text_color="gray60",
            font=ctk.CTkFont(size=11)
        )
        sdk_tip.grid(row=1, column=0, columnspan=3, padx=20, pady=5, sticky="w")
        
        # ADB 路径
        self._create_sdk_path_row(sdk_frame, 2, "ADB 路径:", "adb")
        
        # Python 路径
        self._create_sdk_path_row(sdk_frame, 3, "Python 路径:", "python")
        
        # Python 提示（只读，用于调试）
        python_tip = ctk.CTkLabel(
            sdk_frame,
            text="ℹ️ Python 已内置，此路径仅用于调试和验证",
            text_color="#9E9E9E",
            font=ctk.CTkFont(size=10, slant="italic")
        )
        python_tip.grid(row=4, column=0, columnspan=3, padx=40, pady=(0, 10), sticky="w")
        
        # Homebrew 路径 (仅 macOS)
        if platform.system() == 'Darwin':
            self._create_sdk_path_row(sdk_frame, 5, "Homebrew 路径:", "brew")
            next_row = 6
        else:
            next_row = 5
        
        # 提示：DroidRun 已内置
        droidrun_tip = ctk.CTkLabel(
            sdk_frame,
            text="💡 DroidRun 已内置到应用中，无需配置路径",
            text_color="#4DD0E1",
            font=ctk.CTkFont(size=12)
        )
        droidrun_tip.grid(row=next_row, column=0, columnspan=3, padx=20, pady=(10, 5), sticky="w")
        
        # 自动检测所有工具
        detect_button = ctk.CTkButton(
            sdk_frame,
            text="🔍 自动检测所有路径",
            command=self.detect_all_paths,
            font=ctk.CTkFont(size=14),
            height=40,
            fg_color="#2196F3",
            hover_color="#1976D2"
        )
        detect_button.grid(row=next_row+1, column=0, columnspan=3, padx=20, pady=15, sticky="ew")
        
        # 保存按钮
        save_button = ctk.CTkButton(
            self,
            text="💾 保存设置",
            command=self.save_settings,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50
        )
        save_button.grid(row=4, column=0, padx=20, pady=30, sticky="ew")
        
        # 状态标签
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.grid(row=5, column=0, padx=20, pady=10)
        
        # 加载当前设置
        self.load_settings()
        
        # 添加上下滚动箭头（用于触摸板用户）
        self.after(100, self._add_scroll_arrows)
    
    def load_settings(self):
        """加载当前设置"""
        # 从配置文件加载（优先）或从环境变量加载
        google_key = self.config.get('google_api_key') or os.getenv('GOOGLE_API_KEY', '')
        openai_key = self.config.get('openai_api_key') or os.getenv('OPENAI_API_KEY', '')
        anthropic_key = self.config.get('anthropic_api_key') or os.getenv('ANTHROPIC_API_KEY', '')
        deepseek_key = self.config.get('deepseek_api_key') or os.getenv('DEEPSEEK_API_KEY', '')
        zhipu_key = self.config.get('zhipu_api_key') or os.getenv('ZHIPUAI_API_KEY', '')
        
        if google_key:
            self.google_entry.insert(0, google_key)
        if openai_key:
            self.openai_entry.insert(0, openai_key)
        if anthropic_key:
            self.anthropic_entry.insert(0, anthropic_key)
        if deepseek_key:
            self.deepseek_entry.insert(0, deepseek_key)
        if zhipu_key:
            self.zhipu_entry.insert(0, zhipu_key)
        
        # 加载默认提供商
        default_provider = self.config.get('default_provider', 'GoogleGenAI')
        provider_display_map = {
            "Ollama": "Ollama (免费推荐)",
            "ZhipuAI": "智谱AI (国内快)",
            "DeepSeek": "DeepSeek (便宜)",
            "GoogleGenAI": "GoogleGenAI",
            "OpenAI": "OpenAI",
            "Anthropic": "Anthropic"
        }
        self.provider_var.set(provider_display_map.get(default_provider, default_provider))
        
        # 加载 Gemini 模型
        gemini_model = self.config.get('gemini_model', 'gemini-1.5-flash')
        model_display_map = {
            "gemini-1.5-flash": "gemini-1.5-flash (推荐)",
            "gemini-1.5-flash-8b": "gemini-1.5-flash-8b (更快)",
            "gemini-2.0-flash-exp": "gemini-2.0-flash-exp (实验版)",
            "gemini-1.5-pro": "gemini-1.5-pro (效果好但限制多)"
        }
        self.gemini_model_var.set(model_display_map.get(gemini_model, "gemini-1.5-flash (推荐)"))

        # 加载 OpenAI 模型
        openai_model = self.config.get('openai_model', 'gpt-4o')
        openai_model_display_map = {
            "gpt-4o": "gpt-4o (推荐)",
            "gpt-4o-mini": "gpt-4o-mini (快速便宜)",
            "gpt-4-turbo": "gpt-4-turbo (强推理)",
            "o1-mini": "o1-mini (推理专用)",
        }
        self.openai_model_var.set(openai_model_display_map.get(openai_model, "gpt-4o (推荐)"))

        # 加载 Anthropic 模型
        anthropic_model = self.config.get('anthropic_model', 'claude-sonnet-4-6')
        anthropic_model_display_map = {
            "claude-sonnet-4-6": "claude-sonnet-4-6 (推荐)",
            "claude-haiku-4-5-20251001": "claude-haiku-4-5-20251001 (快速便宜)",
            "claude-opus-4-6": "claude-opus-4-6 (最强)",
        }
        self.anthropic_model_var.set(anthropic_model_display_map.get(anthropic_model, "claude-sonnet-4-6 (推荐)"))

        # 加载智谱AI模型
        zhipu_model = self.config.get('zhipu_model', 'glm-4-plus')
        zhipu_model_display_map = {
            "glm-4-plus": "glm-4-plus (推荐)",
            "glm-4-flash": "glm-4-flash (快速)",
            "glm-4-flashx": "glm-4-flashx (超快)",
            "glm-4-air": "glm-4-air (经济)"
        }
        self.zhipu_model_var.set(zhipu_model_display_map.get(zhipu_model, "glm-4-plus (推荐)"))
        
        # 加载 SDK 路径
        sdk_paths = self.config.get('sdk_paths', {})
        for tool_name, entry in self.sdk_entries.items():
            path = sdk_paths.get(tool_name, '')
            if path:
                entry.insert(0, path)
                # 自动验证路径
                self.after(100, lambda t=tool_name: self._verify_path(t))
    
    def _add_scroll_arrows(self):
        """
        添加上下滚动箭头按钮
        鼠标悬停时自动滚动，离开时停止
        """
        # 滚动状态
        self._scrolling_up = False
        self._scrolling_down = False
        self._scroll_job = None
        
        # 创建箭头容器（固定在右侧中间位置）
        # 顶部箭头
        top_arrow_frame = ctk.CTkFrame(self.winfo_toplevel(), fg_color="transparent", height=50)
        top_arrow_frame.place(relx=0.96, rely=0.15, anchor="center")
        
        up_arrow = ctk.CTkButton(
            top_arrow_frame,
            text="▲",
            width=40,
            height=40,
            font=ctk.CTkFont(size=20, weight="bold"),
            fg_color="#4CAF50",
            hover_color="#45a049",
            corner_radius=20,
            text_color="white"
        )
        up_arrow.pack()
        
        # 底部箭头
        bottom_arrow_frame = ctk.CTkFrame(self.winfo_toplevel(), fg_color="transparent", height=50)
        bottom_arrow_frame.place(relx=0.96, rely=0.85, anchor="center")
        
        down_arrow = ctk.CTkButton(
            bottom_arrow_frame,
            text="▼",
            width=40,
            height=40,
            font=ctk.CTkFont(size=20, weight="bold"),
            fg_color="#4CAF50",
            hover_color="#45a049",
            corner_radius=20,
            text_color="white"
        )
        down_arrow.pack()
        
        # 悬停滚动逻辑
        def start_scroll_up(event=None):
            self._scrolling_up = True
            self._auto_scroll_up()
        
        def stop_scroll_up(event=None):
            self._scrolling_up = False
            if self._scroll_job:
                self.after_cancel(self._scroll_job)
                self._scroll_job = None
        
        def start_scroll_down(event=None):
            self._scrolling_down = True
            self._auto_scroll_down()
        
        def stop_scroll_down(event=None):
            self._scrolling_down = False
            if self._scroll_job:
                self.after_cancel(self._scroll_job)
                self._scroll_job = None
        
        # 绑定悬停事件
        up_arrow.bind("<Enter>", start_scroll_up)
        up_arrow.bind("<Leave>", stop_scroll_up)
        down_arrow.bind("<Enter>", start_scroll_down)
        down_arrow.bind("<Leave>", stop_scroll_down)
        
        # 保存引用，防止被垃圾回收
        self._up_arrow = up_arrow
        self._down_arrow = down_arrow
        self._top_arrow_frame = top_arrow_frame
        self._bottom_arrow_frame = bottom_arrow_frame
    
    def _auto_scroll_up(self):
        """自动向上滚动"""
        if self._scrolling_up:
            self._parent_canvas.yview_scroll(-3, "units")
            self._scroll_job = self.after(50, self._auto_scroll_up)  # 每50ms滚动一次
    
    def _auto_scroll_down(self):
        """自动向下滚动"""
        if self._scrolling_down:
            self._parent_canvas.yview_scroll(3, "units")
            self._scroll_job = self.after(50, self._auto_scroll_down)  # 每50ms滚动一次
    
    def save_settings(self):
        """保存设置"""
        # 保存 API Keys 到配置文件（而不是环境变量）
        provider_map = {
            "Ollama (免费推荐)": "Ollama",
            "智谱AI (国内快)": "ZhipuAI",
            "DeepSeek (便宜)": "DeepSeek",
            "GoogleGenAI": "GoogleGenAI",
            "OpenAI": "OpenAI",
            "Anthropic": "Anthropic"
        }
        
        # 解析 Gemini 模型
        gemini_model_map = {
            "gemini-1.5-flash (推荐)": "gemini-1.5-flash",
            "gemini-1.5-flash-8b (更快)": "gemini-1.5-flash-8b",
            "gemini-2.0-flash-exp (实验版)": "gemini-2.0-flash-exp",
            "gemini-1.5-pro (效果好但限制多)": "gemini-1.5-pro"
        }

        # 解析 OpenAI 模型
        openai_model_map = {
            "gpt-4o (推荐)": "gpt-4o",
            "gpt-4o-mini (快速便宜)": "gpt-4o-mini",
            "gpt-4-turbo (强推理)": "gpt-4-turbo",
            "o1-mini (推理专用)": "o1-mini",
        }

        # 解析 Anthropic 模型
        anthropic_model_map = {
            "claude-sonnet-4-6 (推荐)": "claude-sonnet-4-6",
            "claude-haiku-4-5-20251001 (快速便宜)": "claude-haiku-4-5-20251001",
            "claude-opus-4-6 (最强)": "claude-opus-4-6",
        }

        # 解析智谱AI模型
        zhipu_model_map = {
            "glm-4-plus (推荐)": "glm-4-plus",
            "glm-4-flash (快速)": "glm-4-flash",
            "glm-4-flashx (超快)": "glm-4-flashx",
            "glm-4-air (经济)": "glm-4-air"
        }

        config = {
            'google_api_key': self.google_entry.get(),
            'openai_api_key': self.openai_entry.get(),
            'anthropic_api_key': self.anthropic_entry.get(),
            'deepseek_api_key': self.deepseek_entry.get(),
            'zhipu_api_key': self.zhipu_entry.get(),
            'default_provider': provider_map.get(self.provider_var.get(), self.provider_var.get()),
            'gemini_model': gemini_model_map.get(self.gemini_model_var.get(), "gemini-1.5-flash"),
            'openai_model': openai_model_map.get(self.openai_model_var.get(), "gpt-4o"),
            'anthropic_model': anthropic_model_map.get(self.anthropic_model_var.get(), "claude-sonnet-4-6"),
            'zhipu_model': zhipu_model_map.get(self.zhipu_model_var.get(), "glm-4-plus"),
            'max_steps': int(self.steps_var.get()) if self.steps_var.get().isdigit() else 15,
            'sdk_paths': {}
        }
        
        # 保存 SDK 路径
        for tool_name, entry in self.sdk_entries.items():
            path = entry.get().strip()
            if path:
                config['sdk_paths'][tool_name] = path
        
        self.config.save(config)
        
        self.status_label.configure(
            text="✅ 设置已保存",
            text_color="green"
        )
        
        # 3秒后清除状态
        self.after(3000, lambda: self.status_label.configure(text=""))
    
    def _create_sdk_path_row(self, parent, row, label_text, tool_name):
        """
        创建 SDK 路径配置行
        
        Args:
            parent: 父容器
            row: 行号
            label_text: 标签文本
            tool_name: 工具名称
        """
        # 标签
        label = ctk.CTkLabel(parent, text=label_text)
        label.grid(row=row, column=0, padx=20, pady=8, sticky="w")
        
        # 路径输入框
        entry = ctk.CTkEntry(parent, placeholder_text="自动检测或手动输入路径")
        entry.grid(row=row, column=1, padx=10, pady=8, sticky="ew")
        self.sdk_entries[tool_name] = entry
        
        # 状态标签
        status_label = ctk.CTkLabel(parent, text="", font=ctk.CTkFont(size=10))
        status_label.grid(row=row+10, column=1, padx=10, pady=2, sticky="w")
        self.sdk_status_labels[tool_name] = status_label
        
        # 按钮容器
        button_frame = ctk.CTkFrame(parent, fg_color="transparent")
        button_frame.grid(row=row, column=2, padx=10, pady=8, sticky="e")
        
        # 浏览按钮
        browse_btn = ctk.CTkButton(
            button_frame,
            text="📁",
            width=40,
            height=28,
            command=lambda: self._browse_path(tool_name)
        )
        browse_btn.pack(side="left", padx=2)
        
        # 检测按钮
        detect_btn = ctk.CTkButton(
            button_frame,
            text="🔍",
            width=40,
            height=28,
            fg_color="#4CAF50",
            hover_color="#45a049",
            command=lambda: self._detect_single_path(tool_name)
        )
        detect_btn.pack(side="left", padx=2)
        
        # 验证按钮
        verify_btn = ctk.CTkButton(
            button_frame,
            text="✓",
            width=40,
            height=28,
            fg_color="#2196F3",
            hover_color="#1976D2",
            command=lambda: self._verify_path(tool_name)
        )
        verify_btn.pack(side="left", padx=2)
        
        # 安装按钮（ADB 和 Homebrew）
        if tool_name in ['adb', 'brew']:
            install_btn = ctk.CTkButton(
                button_frame,
                text="📦",
                width=40,
                height=28,
                fg_color="#9C27B0",
                hover_color="#7B1FA2",
                command=lambda: self._install_tool(tool_name)
            )
            install_btn.pack(side="left", padx=2)
        
        # 重置按钮
        reset_btn = ctk.CTkButton(
            button_frame,
            text="↺",
            width=40,
            height=28,
            fg_color="#FF9800",
            hover_color="#F57C00",
            command=lambda: self._reset_path(tool_name)
        )
        reset_btn.pack(side="left", padx=2)
    
    def _browse_path(self, tool_name):
        """浏览文件选择路径"""
        filename = filedialog.askopenfilename(
            title=f"选择 {tool_name} 路径",
            filetypes=[("可执行文件", "*"), ("所有文件", "*.*")]
        )
        if filename:
            self.sdk_entries[tool_name].delete(0, "end")
            self.sdk_entries[tool_name].insert(0, filename)
            self._verify_path(tool_name)
    
    def _detect_single_path(self, tool_name):
        """检测单个工具的路径"""
        self.sdk_status_labels[tool_name].configure(text="🔍 检测中...", text_color="gray")
        self.update()
        
        path = self.sdk_manager.detect_tool_path(tool_name)
        if path:
            self.sdk_entries[tool_name].delete(0, "end")
            self.sdk_entries[tool_name].insert(0, path)
            self.sdk_status_labels[tool_name].configure(text=f"✅ 已找到", text_color="green")
            # 自动验证
            self.after(500, lambda: self._verify_path(tool_name))
        else:
            self.sdk_status_labels[tool_name].configure(text="❌ 未找到", text_color="red")
    
    def _verify_path(self, tool_name):
        """验证工具路径"""
        path = self.sdk_entries[tool_name].get().strip()
        if not path:
            self.sdk_status_labels[tool_name].configure(text="", text_color="gray")
            return
        
        self.sdk_status_labels[tool_name].configure(text="🔍 验证中...", text_color="gray")
        self.update()
        
        result = self.sdk_manager.verify_tool(tool_name, path)
        if result['success']:
            version_text = f" ({result['version']})" if result['version'] else ""
            self.sdk_status_labels[tool_name].configure(
                text=f"✅ {result['message']}{version_text}",
                text_color="green"
            )
        else:
            self.sdk_status_labels[tool_name].configure(
                text=f"❌ {result['message']}",
                text_color="red"
            )
    
    def _reset_path(self, tool_name):
        """重置工具路径"""
        self.sdk_entries[tool_name].delete(0, "end")
        self.sdk_status_labels[tool_name].configure(text="", text_color="gray")
        self.sdk_manager.reset_tool_path(tool_name)
    
    def _install_tool(self, tool_name):
        """安装工具"""
        if tool_name == 'adb':
            self._install_adb()
        elif tool_name == 'brew':
            self._install_homebrew()
        else:
            # 其他工具暂不支持自动安装
            from tkinter import messagebox
            messagebox.showinfo(
                "提示",
                f"{tool_name} 暂不支持自动安装\n请手动下载并配置路径"
            )
    
    def _install_adb(self):
        """显示 ADB 安装对话框"""
        # 创建新窗口
        install_window = ctk.CTkToplevel(self)
        install_window.title("安装 ADB")
        install_window.geometry("800x600")
        
        # 导入 ADB 向导
        from ui.adb_wizard import AdbWizard
        
        def on_complete():
            """安装完成后的回调"""
            # 重新检测 ADB 路径
            self._detect_single_path('adb')
            install_window.destroy()
        
        # 显示 ADB 向导（跳过检测，直接显示安装选项）
        wizard = AdbWizard(install_window, on_complete=on_complete)
        wizard.pack(fill="both", expand=True)
        
        # 直接显示安装选项（而不是检测页面）
        wizard.show_install_options()
    
    def _install_homebrew(self):
        """安装 Homebrew（仅 macOS）"""
        import platform
        import subprocess
        import threading
        from tkinter import messagebox
        
        # 检查是否为 macOS
        if platform.system() != 'Darwin':
            messagebox.showinfo(
                "提示",
                "Homebrew 仅适用于 macOS\n其他系统请手动配置工具路径"
            )
            return
        
        # 确认安装
        result = messagebox.askyesno(
            "安装 Homebrew",
            "Homebrew 是 macOS 的包管理器，可以帮助安装其他工具（如 ADB）\n\n"
            "安装需要:\n"
            "• 网络连接\n"
            "• 管理员密码\n"
            "• 约 5-10 分钟\n\n"
            "是否继续？"
        )
        
        if not result:
            return
        
        # 创建安装窗口
        install_window = ctk.CTkToplevel(self)
        install_window.title("安装 Homebrew")
        install_window.geometry("700x500")
        
        # 标题
        title_label = ctk.CTkLabel(
            install_window,
            text="🍺 正在安装 Homebrew",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=20)
        
        # 输出框
        output_text = ctk.CTkTextbox(
            install_window,
            width=650,
            height=350,
            font=ctk.CTkFont(family="Courier", size=12)
        )
        output_text.pack(pady=10, padx=20)
        
        # 关闭按钮（初始禁用）
        close_btn = ctk.CTkButton(
            install_window,
            text="关闭",
            width=200,
            state="disabled",
            command=install_window.destroy
        )
        close_btn.pack(pady=10)
        
        def run_install():
            """在后台线程运行安装"""
            def safe_update_ui(callback):
                """安全地更新 UI（检查窗口是否存在）"""
                try:
                    if install_window.winfo_exists():
                        callback()
                except:
                    pass
            
            try:
                # Homebrew 官方安装脚本
                install_cmd = '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
                
                safe_update_ui(lambda: output_text.insert("end", "📥 正在下载 Homebrew 安装脚本...\n\n"))
                safe_update_ui(lambda: output_text.insert("end", "⚠️ 安装过程中可能需要输入管理员密码\n\n"))
                safe_update_ui(lambda: output_text.see("end"))
                
                # 运行安装命令
                process = subprocess.Popen(
                    install_cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                
                # 实时显示输出
                for line in process.stdout:
                    safe_update_ui(lambda l=line: output_text.insert("end", l))
                    safe_update_ui(lambda: output_text.see("end"))
                
                process.wait()
                
                if process.returncode == 0:
                    safe_update_ui(lambda: output_text.insert("end", "\n\n✅ Homebrew 安装成功！\n", "success"))
                    safe_update_ui(lambda: output_text.tag_config("success", foreground="#4CAF50"))
                    
                    # 重新检测路径
                    try:
                        if self.winfo_exists():
                            self.after(500, lambda: self._detect_single_path('brew') if self.winfo_exists() else None)
                    except:
                        pass
                else:
                    safe_update_ui(lambda: output_text.insert("end", f"\n\n❌ 安装失败（退出码: {process.returncode}）\n", "error"))
                    safe_update_ui(lambda: output_text.tag_config("error", foreground="#F44336"))
                
            except Exception as e:
                safe_update_ui(lambda: output_text.insert("end", f"\n\n❌ 安装错误: {str(e)}\n", "error"))
                safe_update_ui(lambda: output_text.tag_config("error", foreground="#F44336"))
            
            finally:
                # 启用关闭按钮
                safe_update_ui(lambda: close_btn.configure(state="normal"))
        
        # 在后台线程启动安装
        install_thread = threading.Thread(target=run_install, daemon=True)
        install_thread.start()
    
    def detect_all_paths(self):
        """检测所有工具的路径"""
        self.status_label.configure(text="🔍 正在检测所有工具...", text_color="blue")
        self.update()
        
        results = self.sdk_manager.detect_all_tools()
        
        found_count = 0
        for tool_name, info in results.items():
            if tool_name in self.sdk_entries:
                if info['found']:
                    self.sdk_entries[tool_name].delete(0, "end")
                    self.sdk_entries[tool_name].insert(0, info['path'])
                    self.sdk_status_labels[tool_name].configure(text="✅ 已找到", text_color="green")
                    found_count += 1
                    # 验证
                    self.after(100, lambda t=tool_name: self._verify_path(t))
                else:
                    self.sdk_status_labels[tool_name].configure(text="❌ 未找到", text_color="red")
        
        total = len([k for k in results.keys() if k in self.sdk_entries])
        self.status_label.configure(
            text=f"✅ 检测完成: 找到 {found_count}/{total} 个工具",
            text_color="green"
        )
        self.after(5000, lambda: self.status_label.configure(text=""))
    