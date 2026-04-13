"""
任务执行面板
"""

import customtkinter as ctk
from tkinter import BooleanVar, StringVar, messagebox
import threading
import asyncio
from core.task_runner import TaskRunner
from core.device_checker import DeviceChecker
from utils.task_history import TaskHistory
from utils.task_templates import TaskTemplates


class TaskPanel(ctk.CTkFrame):
    """任务执行面板"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.task_runner = TaskRunner()
        self.device_checker = DeviceChecker()
        self.task_history = TaskHistory()
        self.task_templates = TaskTemplates()
        
        # 任务控制
        self.task_running = False
        self.stop_requested = False
        self.current_loop = None
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        # 标题
        title_label = ctk.CTkLabel(
            self,
            text="⚡ 执行任务",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # 输入区域
        input_frame = ctk.CTkFrame(self)
        input_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)
        
        # 设备选择
        device_label = ctk.CTkLabel(input_frame, text="选择设备:")
        device_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.device_var = StringVar(value="自动检测")
        self.device_menu = ctk.CTkOptionMenu(
            input_frame,
            variable=self.device_var,
            values=["自动检测"]
        )
        self.device_menu.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        
        refresh_btn = ctk.CTkButton(
            input_frame,
            text="🔄",
            width=40,
            command=self.refresh_devices
        )
        refresh_btn.grid(row=0, column=2, padx=10, pady=5)
        
        # 任务输入
        task_label = ctk.CTkLabel(input_frame, text="任务描述:")
        task_label.grid(row=1, column=0, padx=10, pady=5, sticky="nw")
        
        # 使用多行文本框，更容易查看完整内容
        self.task_entry = ctk.CTkTextbox(
            input_frame,
            height=80,
            font=ctk.CTkFont(size=13)
        )
        self.task_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew", columnspan=2)
        
        # 添加占位符文本（通过初始插入灰色文本）
        placeholder_text = "输入任务，例如：打开设置并告诉我Android版本"
        self.task_entry.insert("1.0", placeholder_text)
        self.task_entry.configure(text_color="gray")
        
        # 占位符功能
        def on_focus_in(event):
            if self.task_entry.get("1.0", "end-1c") == placeholder_text:
                self.task_entry.delete("1.0", "end")
                self.task_entry.configure(text_color=("gray10", "#DCE4EE"))
        
        def on_focus_out(event):
            if not self.task_entry.get("1.0", "end-1c").strip():
                self.task_entry.insert("1.0", placeholder_text)
                self.task_entry.configure(text_color="gray")
        
        self.task_entry.bind("<FocusIn>", on_focus_in)
        self.task_entry.bind("<FocusOut>", on_focus_out)
        
        # 历史和模板按钮
        quick_access_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        quick_access_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
        quick_access_frame.grid_columnconfigure(1, weight=1)
        
        history_btn = ctk.CTkButton(
            quick_access_frame,
            text="📜 历史任务",
            width=120,
            command=self.show_history
        )
        history_btn.grid(row=0, column=0, padx=5)
        
        template_btn = ctk.CTkButton(
            quick_access_frame,
            text="📋 任务模板",
            width=120,
            command=self.show_templates
        )
        template_btn.grid(row=0, column=1, padx=5, sticky="w")
        
        # 选项
        self.vision_var = BooleanVar(value=False)
        vision_check = ctk.CTkCheckBox(
            input_frame,
            text="启用视觉功能",
            variable=self.vision_var
        )
        vision_check.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        
        self.reasoning_var = BooleanVar(value=False)
        reasoning_check = ctk.CTkCheckBox(
            input_frame,
            text="启用推理模式",
            variable=self.reasoning_var
        )
        reasoning_check.grid(row=3, column=1, padx=10, pady=5, sticky="w")
        
        # 执行和停止按钮框架
        button_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        button_frame.grid(row=4, column=0, columnspan=3, padx=10, pady=20, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=3)
        button_frame.grid_columnconfigure(1, weight=1)
        
        # 执行按钮
        self.run_button = ctk.CTkButton(
            button_frame,
            text="▶️ 执行任务",
            command=self.run_task,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50
        )
        self.run_button.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        
        # 停止按钮（使用柔和的红色）
        self.stop_button = ctk.CTkButton(
            button_frame,
            text="⏹️ 停止",
            command=self.stop_task,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            fg_color="#E57373",  # 柔和的红色
            hover_color="#EF5350",  # 悬停时稍深一点
            state="disabled"
        )
        self.stop_button.grid(row=0, column=1, sticky="ew")
        
        # 输出区域
        output_label = ctk.CTkLabel(
            self,
            text="执行日志:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        output_label.grid(row=2, column=0, padx=20, pady=(10, 5), sticky="w")
        
        self.output_textbox = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Courier", size=12)
        )
        self.output_textbox.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="nsew")
        
        # 初始化设备列表
        self.refresh_devices()
    
    def refresh_devices(self):
        """刷新设备列表"""
        def _refresh():
            devices = self.device_checker.list_devices()
            device_list = ["自动检测"] + [d['serial'] for d in devices]
            
            self.after(0, lambda: self.device_menu.configure(values=device_list))
            self.log(f"找到 {len(devices)} 个设备")
        
        threading.Thread(target=_refresh, daemon=True).start()
    
    def run_task(self):
        """运行任务"""
        # 从 Textbox 获取文本
        task = self.task_entry.get("1.0", "end-1c").strip()
        
        # 检查是否为空或仅为占位符
        placeholder_text = "输入任务，例如：打开设置并告诉我Android版本"
        if not task or task == placeholder_text:
            self.log("❌ 请输入任务描述", color="red")
            return
        
        device = None if self.device_var.get() == "自动检测" else self.device_var.get()
        
        # 设置状态
        self.task_running = True
        self.stop_requested = False
        
        # 更新按钮状态
        self.run_button.configure(state="disabled", text="⏳ 执行中...")
        self.stop_button.configure(state="normal")
        self.output_textbox.delete("1.0", "end")
        
        self.log(f"📝 任务: {task}")
        if device:
            self.log(f"📱 设备: {device}")
        self.log(f"👁️ 视觉功能: {'启用' if self.vision_var.get() else '关闭'}")
        self.log(f"🧠 推理模式: {'启用' if self.reasoning_var.get() else '关闭'}")
        self.log("-" * 50)
        
        # 在后台线程执行任务
        threading.Thread(
            target=self._do_run_task,
            args=(task, device),
            daemon=True
        ).start()
    
    def stop_task(self):
        """停止任务"""
        if self.task_running:
            self.stop_requested = True
            self.log("🛑 正在停止任务...")
            self.stop_button.configure(state="disabled")
            
            # 如果有运行中的事件循环，尝试停止
            if self.current_loop and self.current_loop.is_running():
                self.current_loop.call_soon_threadsafe(self.current_loop.stop)
    
    def _do_run_task(self, task, device):
        """执行实际的任务（后台线程）"""
        def log_callback(message):
            # 检查是否请求停止
            if self.stop_requested:
                self.log("🛑 检测到停止请求")
                return
            self.log(message)
        
        # 创建事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.current_loop = loop
        
        success = False
        result_reason = None
        stopped = False
        
        try:
            # 使用 asyncio.wait_for 添加超时和取消支持
            task_coroutine = self.task_runner.run_task(
                task,
                device_serial=device,
                enable_vision=self.vision_var.get(),
                enable_reasoning=self.reasoning_var.get(),
                callback=log_callback
            )
            
            # 定期检查停止请求
            async def run_with_stop_check():
                task_future = asyncio.ensure_future(task_coroutine)
                while not task_future.done():
                    if self.stop_requested:
                        task_future.cancel()
                        raise asyncio.CancelledError("任务被用户中断")
                    await asyncio.sleep(0.5)
                return await task_future
            
            result = loop.run_until_complete(run_with_stop_check())
            
            success = result['success']
            result_reason = result.get('reason', '')
            
            self.log("-" * 50)
            if result['success']:
                self.log("✅ 任务完成!", color="green")
                self.log(f"📊 执行步骤: {result['steps']}")
                self.log(f"💬 结果: {result['reason']}")
            else:
                self.log("❌ 任务失败", color="red")
                self.log(f"💬 原因: {result['reason']}")
        
        except asyncio.CancelledError:
            stopped = True
            self.log("-" * 50)
            self.log("🛑 任务已被停止", color="orange")
            result_reason = "任务被用户中断"
        
        except Exception as e:
            self.log(f"❌ 错误: {str(e)}", color="red")
            result_reason = str(e)
        
        finally:
            # 保存到历史记录（除非被中断）
            if not stopped:
                self.task_history.add_task(
                    task_description=task,
                    device_serial=device,
                    success=success,
                    result=result_reason
                )
            
            self.current_loop = None
            loop.close()
            
            # 重置状态
            self.task_running = False
            self.stop_requested = False
            
            # 更新按钮状态
            self.after(0, lambda: self.run_button.configure(
                state="normal",
                text="▶️ 执行任务"
            ))
            self.after(0, lambda: self.stop_button.configure(state="disabled"))
    
    def show_history(self):
        """显示历史任务"""
        history_window = ctk.CTkToplevel(self)
        history_window.title("📜 历史任务")
        history_window.geometry("700x500")
        
        # 标题
        title = ctk.CTkLabel(
            history_window,
            text="📜 历史任务",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(padx=20, pady=10)
        
        # 搜索框
        search_frame = ctk.CTkFrame(history_window)
        search_frame.pack(fill="x", padx=20, pady=10)
        
        search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="🔍 搜索任务..."
        )
        search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # 列表框架
        list_frame = ctk.CTkScrollableFrame(history_window)
        list_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        def update_list(keyword=""):
            # 清空列表
            for widget in list_frame.winfo_children():
                widget.destroy()
            
            # 获取任务（搜索或全部）
            tasks = (self.task_history.search_tasks(keyword) if keyword 
                    else self.task_history.get_recent_tasks(50))
            
            if not tasks:
                no_data = ctk.CTkLabel(
                    list_frame,
                    text="暂无历史记录" if not keyword else "未找到匹配的任务",
                    text_color="gray"
                )
                no_data.pack(pady=20)
                return
            
            # 显示任务
            for task in tasks:
                task_frame = ctk.CTkFrame(list_frame, cursor="hand2")
                task_frame.pack(fill="x", pady=5)
                
                # 使用 grid 布局确保按钮始终可见
                task_frame.grid_columnconfigure(0, weight=1)
                task_frame.grid_columnconfigure(1, weight=0)
                
                # 任务文本（不截断，使用自动换行）
                task_text = task['task']
                
                # 图标（成功/失败）
                icon = "✅" if task.get('last_success', False) else "❌"
                count = task.get('execution_count', 1)
                
                task_label = ctk.CTkLabel(
                    task_frame,
                    text=f"{icon} {task_text} (执行{count}次)",
                    anchor="w",
                    cursor="hand2",
                    wraplength=550,  # 设置自动换行宽度
                    justify="left"
                )
                task_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
                
                # 删除按钮（固定在右侧）
                del_btn = ctk.CTkButton(
                    task_frame,
                    text="🗑️",
                    width=40,
                    fg_color="#E57373",  # 柔和的红色
                    hover_color="#EF5350",
                    command=lambda t=task['task']: self.delete_history(t, update_list)
                )
                del_btn.grid(row=0, column=1, padx=5, pady=5, sticky="e")
                
                # 绑定点击事件到整个框架和标签（点击即应用任务）
                full_task = task['task']
                task_frame.bind("<Button-1>", lambda e, t=full_task: self.use_task(t, history_window))
                task_label.bind("<Button-1>", lambda e, t=full_task: self.use_task(t, history_window))
                
                # 添加悬停效果
                original_color = task_frame.cget("fg_color")
                task_frame.bind("<Enter>", lambda e, f=task_frame: f.configure(fg_color=("gray85", "gray25")))
                task_frame.bind("<Leave>", lambda e, f=task_frame, c=original_color: f.configure(fg_color=c))
        
        # 绑定搜索
        search_entry.bind("<KeyRelease>", lambda e: update_list(search_entry.get()))
        
        # 初始化列表
        update_list()
        
        # 关闭按钮
        close_btn = ctk.CTkButton(
            history_window,
            text="关闭",
            command=history_window.destroy
        )
        close_btn.pack(pady=10)
    
    def show_templates(self):
        """显示任务模板"""
        template_window = ctk.CTkToplevel(self)
        template_window.title("📋 任务模板")
        template_window.geometry("850x650")
        
        # 标题和新建按钮框架
        header_frame = ctk.CTkFrame(template_window, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=10)
        
        title = ctk.CTkLabel(
            header_frame,
            text="📋 任务模板",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(side="left")
        
        # 新建模板按钮（暂时禁用，后面会在 update_list 定义后启用）
        add_btn = ctk.CTkButton(
            header_frame,
            text="➕ 新建模板",
            width=120
        )
        add_btn.pack(side="right")
        
        # 提示信息
        hint_label = ctk.CTkLabel(
            template_window,
            text="💡 提示：🔒内置模板不可删除，✏️自定义模板可以编辑和删除",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        hint_label.pack(padx=20, pady=(0, 10))
        
        # 搜索和分类框架
        filter_frame = ctk.CTkFrame(template_window)
        filter_frame.pack(fill="x", padx=20, pady=10)
        
        # 搜索框
        search_entry = ctk.CTkEntry(
            filter_frame,
            placeholder_text="🔍 搜索模板..."
        )
        search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # 分类选择
        categories = ["全部"] + self.task_templates.get_categories()
        category_var = StringVar(value="全部")
        category_menu = ctk.CTkOptionMenu(
            filter_frame,
            variable=category_var,
            values=categories,
            width=150
        )
        category_menu.pack(side="right")
        
        # 列表框架
        list_frame = ctk.CTkScrollableFrame(template_window)
        list_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        def update_list(keyword="", category="全部"):
            # 清空列表
            for widget in list_frame.winfo_children():
                widget.destroy()
            
            # 获取模板
            if keyword:
                templates = self.task_templates.search_templates(keyword)
            elif category != "全部":
                templates = self.task_templates.get_templates_by_category(category)
            else:
                templates = self.task_templates.get_all_templates()
            
            if not templates:
                no_data = ctk.CTkLabel(
                    list_frame,
                    text="未找到匹配的模板",
                    text_color="gray"
                )
                no_data.pack(pady=20)
                return
            
            # 显示模板
            for template in templates:
                template_frame = ctk.CTkFrame(list_frame, cursor="hand2")
                template_frame.pack(fill="x", pady=5)
                
                # 使用 grid 布局确保按钮始终可见
                template_frame.grid_columnconfigure(0, weight=1)
                template_frame.grid_columnconfigure(1, weight=0)
                
                # 左侧信息
                info_frame = ctk.CTkFrame(template_frame, fg_color="transparent", cursor="hand2")
                info_frame.grid(row=0, column=0, padx=10, pady=10, sticky="w")
                
                # 名称和分类（使用 wraplength 限制宽度）
                # 添加标记：默认模板显示 [内置]，自定义模板显示 [自定义]
                is_default = template.get('is_default', False)
                badge = " 🔒内置" if is_default else " ✏️自定义"
                name_text = template['name'] + badge
                
                name_label = ctk.CTkLabel(
                    info_frame,
                    text=name_text,
                    font=ctk.CTkFont(size=14, weight="bold"),
                    anchor="w",
                    cursor="hand2",
                    wraplength=550,
                    justify="left"
                )
                name_label.pack(fill="x")
                
                # 描述
                if template.get('description'):
                    desc_label = ctk.CTkLabel(
                        info_frame,
                        text=template['description'],
                        text_color="gray",
                        anchor="w",
                        font=ctk.CTkFont(size=11),
                        cursor="hand2",
                        wraplength=550,
                        justify="left"
                    )
                    desc_label.pack(fill="x")
                
                # 示例（修改颜色为浅青色，更清晰）
                if template.get('example'):
                    example_label = ctk.CTkLabel(
                        info_frame,
                        text=f"示例: {template['example']}",
                        text_color="#4DD0E1",  # 浅青色，更清晰
                        anchor="w",
                        font=ctk.CTkFont(size=10),
                        cursor="hand2",
                        wraplength=550,
                        justify="left"
                    )
                    example_label.pack(fill="x")
                
                # 按钮框架（固定在右侧）
                btn_frame = ctk.CTkFrame(template_frame, fg_color="transparent")
                btn_frame.grid(row=0, column=1, padx=5, pady=5, sticky="e")
                
                # 编辑按钮（仅自定义模板）
                if not template.get('is_default', False):
                    def make_edit_callback(t):
                        def refresh():
                            update_list(search_entry.get(), category_var.get())
                        return lambda: self.show_template_editor(template_window, t, refresh_callback=refresh)
                    
                    edit_btn = ctk.CTkButton(
                        btn_frame,
                        text="✏️",
                        width=40,
                        fg_color="#FFA726",  # 柔和的橙色
                        hover_color="#FB8C00",
                        command=make_edit_callback(template)
                    )
                    edit_btn.pack(side="right", padx=2)
                    
                    # 删除按钮（仅自定义模板）
                    def make_delete_callback(name):
                        def callback():
                            self.delete_template(name)
                            update_list(search_entry.get(), category_var.get())
                        return callback
                    
                    del_btn = ctk.CTkButton(
                        btn_frame,
                        text="🗑️",
                        width=40,
                        fg_color="#E57373",  # 柔和的红色
                        hover_color="#EF5350",
                        command=make_delete_callback(template['name'])
                    )
                    del_btn.pack(side="right", padx=2)
                
                # 绑定点击事件到整个框架和信息区域（点击即应用任务）
                task_content = template['task']
                template_frame.bind("<Button-1>", lambda e, t=task_content: self.use_task(t, template_window))
                info_frame.bind("<Button-1>", lambda e, t=task_content: self.use_task(t, template_window))
                name_label.bind("<Button-1>", lambda e, t=task_content: self.use_task(t, template_window))
                if template.get('description'):
                    desc_label.bind("<Button-1>", lambda e, t=task_content: self.use_task(t, template_window))
                if template.get('example'):
                    example_label.bind("<Button-1>", lambda e, t=task_content: self.use_task(t, template_window))
                
                # 添加悬停效果
                original_color = template_frame.cget("fg_color")
                template_frame.bind("<Enter>", lambda e, f=template_frame: f.configure(fg_color=("gray85", "gray25")))
                template_frame.bind("<Leave>", lambda e, f=template_frame, c=original_color: f.configure(fg_color=c))
        
        # 配置新建模板按钮的回调（现在 update_list 已定义）
        def on_add_template():
            def refresh():
                update_list(search_entry.get(), category_var.get())
            self.show_template_editor(template_window, refresh_callback=refresh)
        add_btn.configure(command=on_add_template)
        
        # 绑定事件
        search_entry.bind("<KeyRelease>", lambda e: update_list(search_entry.get(), category_var.get()))
        category_var.trace_add("write", lambda *args: update_list(search_entry.get(), category_var.get()))
        
        # 初始化列表
        update_list()
        
        # 关闭按钮
        close_btn = ctk.CTkButton(
            template_window,
            text="关闭",
            command=template_window.destroy
        )
        close_btn.pack(pady=10)
    
    def use_task(self, task_text, window):
        """使用任务（填充到输入框）"""
        # 清除 Textbox 内容
        self.task_entry.delete("1.0", "end")
        # 插入新任务
        self.task_entry.insert("1.0", task_text)
        # 设置正常文本颜色
        self.task_entry.configure(text_color=("gray10", "#DCE4EE"))
        window.destroy()
    
    def delete_history(self, task_text, update_callback):
        """删除历史记录"""
        self.task_history.delete_task(task_text)
        update_callback()
    
    def show_template_editor(self, parent_window, template=None, refresh_callback=None):
        """显示模板编辑器"""
        editor_window = ctk.CTkToplevel(parent_window)
        editor_window.title("➕ 新建模板" if not template else "✏️ 编辑模板")
        editor_window.geometry("600x500")
        # 不使用 grab_set，避免卡死
        # editor_window.grab_set()  # 模态窗口
        
        # 标题
        title_text = "新建自定义模板" if not template else f"编辑模板: {template['name']}"
        title = ctk.CTkLabel(
            editor_window,
            text=title_text,
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.pack(padx=20, pady=20)
        
        # 表单框架
        form_frame = ctk.CTkFrame(editor_window)
        form_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # 模板名称
        name_label = ctk.CTkLabel(form_frame, text="模板名称:")
        name_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        name_entry = ctk.CTkEntry(form_frame, placeholder_text="例如: 📱 打开某应用")
        name_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        form_frame.grid_columnconfigure(1, weight=1)
        
        # 分类
        category_label = ctk.CTkLabel(form_frame, text="分类:")
        category_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        
        categories = ["自定义"] + [c for c in self.task_templates.get_categories() if c != "自定义"]
        category_var = StringVar(value="自定义")
        category_menu = ctk.CTkOptionMenu(
            form_frame,
            variable=category_var,
            values=categories
        )
        category_menu.grid(row=1, column=1, padx=10, pady=10, sticky="w")
        
        # 任务描述
        task_label = ctk.CTkLabel(form_frame, text="任务描述:")
        task_label.grid(row=2, column=0, padx=10, pady=10, sticky="nw")
        
        task_entry = ctk.CTkTextbox(form_frame, height=80)
        task_entry.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        
        # 描述
        desc_label = ctk.CTkLabel(form_frame, text="功能描述:")
        desc_label.grid(row=3, column=0, padx=10, pady=10, sticky="nw")
        
        desc_entry = ctk.CTkEntry(form_frame, placeholder_text="简要说明这个模板的功能")
        desc_entry.grid(row=3, column=1, padx=10, pady=10, sticky="ew")
        
        # 示例
        example_label = ctk.CTkLabel(form_frame, text="使用示例:")
        example_label.grid(row=4, column=0, padx=10, pady=10, sticky="nw")
        
        example_entry = ctk.CTkEntry(form_frame, placeholder_text="例如: 打开微信")
        example_entry.grid(row=4, column=1, padx=10, pady=10, sticky="ew")
        
        # 如果是编辑模式，填充现有数据
        if template:
            name_entry.insert(0, template['name'])
            category_var.set(template.get('category', '自定义'))
            task_entry.insert("1.0", template['task'])
            if template.get('description'):
                desc_entry.insert(0, template['description'])
            if template.get('example'):
                example_entry.insert(0, template['example'])
        
        # 按钮框架
        button_frame = ctk.CTkFrame(editor_window, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=20)
        
        def save_template():
            name = name_entry.get().strip()
            task = task_entry.get("1.0", "end").strip()
            category = category_var.get()
            description = desc_entry.get().strip()
            example = example_entry.get().strip()
            
            if not name or not task:
                messagebox.showerror("错误", "模板名称和任务描述不能为空！")
                return
            
            try:
                if template:
                    # 编辑现有模板
                    success = self.task_templates.update_template(
                        old_name=template['name'],
                        name=name,
                        task=task,
                        category=category,
                        description=description,
                        example=example
                    )
                else:
                    # 新建模板
                    success = self.task_templates.add_template(
                        name=name,
                        task=task,
                        category=category,
                        description=description,
                        example=example
                    )
                
                if success:
                    messagebox.showinfo("成功", "模板保存成功！")
                    editor_window.destroy()
                    # 刷新父窗口列表
                    if refresh_callback:
                        refresh_callback()
                else:
                    messagebox.showerror("错误", "模板名称已存在！")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {str(e)}")
        
        # 保存按钮
        save_btn = ctk.CTkButton(
            button_frame,
            text="💾 保存",
            command=save_template,
            width=120,
            height=40
        )
        save_btn.pack(side="left", padx=5)
        
        # 取消按钮
        cancel_btn = ctk.CTkButton(
            button_frame,
            text="❌ 取消",
            command=editor_window.destroy,
            width=120,
            height=40,
            fg_color="gray",
            hover_color="darkgray"
        )
        cancel_btn.pack(side="left", padx=5)
    
    def delete_template(self, template_name):
        """删除模板"""
        if messagebox.askyesno("确认删除", f"确定要删除模板 '{template_name}' 吗？\n此操作不可撤销！"):
            success = self.task_templates.delete_template(template_name)
            if success:
                messagebox.showinfo("成功", "模板已删除")
            else:
                messagebox.showerror("错误", "无法删除默认模板")
    
    def log(self, message, color=None):
        """添加日志（支持颜色）"""
        # 如果没有指定颜色，默认使用白色（执行中的日志）
        if color is None:
            color = "white"
        
        # 插入带颜色的文本
        start_index = self.output_textbox.index("end-1c")
        self.output_textbox.insert("end", message + "\n")
        end_index = self.output_textbox.index("end-1c")
        
        # 配置颜色标签
        tag_name = f"color_{color}"
        self.output_textbox.tag_config(tag_name, foreground=color)
        self.output_textbox.tag_add(tag_name, start_index, end_index)
        
        self.output_textbox.see("end")

