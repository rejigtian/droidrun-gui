import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QPushButton, QLabel, QTextEdit, QComboBox, 
                            QMessageBox, QProgressBar, QTabWidget, QHBoxLayout,
                            QListWidget, QListWidgetItem, QDialog, QLineEdit,
                            QFormLayout, QGroupBox, QSplitter, QSpinBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QFont
import subprocess
import json
from pathlib import Path
from .task_executor import TaskExecutor, PORTAL_APK_PATH, DROIDRUN_CLI_PATH
from .task_manager import TaskManager
from .device_manager import DeviceManager
from .apikey_manager import APIKeyManager

class AddTemplateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加任务模板")
        self.setModal(True)
        
        layout = QFormLayout(self)
        
        self.category_input = QLineEdit()
        self.name_input = QLineEdit()
        self.description_input = QTextEdit()
        
        layout.addRow("分类:", self.category_input)
        layout.addRow("名称:", self.name_input)
        layout.addRow("描述:", self.description_input)
        
        buttons = QHBoxLayout()
        save_button = QPushButton("保存")
        cancel_button = QPushButton("取消")
        
        save_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        
        buttons.addWidget(save_button)
        buttons.addWidget(cancel_button)
        layout.addRow(buttons)

class DeviceThread(QThread):
    update_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(list)

    def run(self):
        try:
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
            devices = []
            for line in result.stdout.split('\n')[1:]:
                if line.strip() and 'device' in line:
                    devices.append(line.split('\t')[0])
            self.finished_signal.emit(devices)
        except Exception as e:
            self.update_signal.emit(f"Error: {str(e)}")

class InstallAdbKeyboardThread(QThread):
    result_signal = pyqtSignal(str, bool)  # (msg, success)
    def __init__(self, device_id, apk_path):
        super().__init__()
        self.device_id = device_id
        self.apk_path = apk_path
    def run(self):
        import subprocess
        result1 = subprocess.run(['adb', '-s', self.device_id, 'install', '-r', self.apk_path], capture_output=True, text=True)
        install_output = result1.stdout + result1.stderr
        if "Success" in install_output:
            subprocess.run(['adb', '-s', self.device_id, 'shell', 'am', 'start', '-a', 'android.settings.INPUT_METHOD_SETTINGS'])
            msg = f"安装ADBKeyboard结果：{install_output}\n[引导] 已自动打开输入法设置界面，请在手机上手动启用ADBKeyboard输入法，然后再点击切换按钮。"
            self.result_signal.emit(msg, True)
        else:
            msg = f"[失败] 安装ADBKeyboard失败：{install_output}\n请检查APK路径和设备连接。"
            self.result_signal.emit(msg, False)

class PortalSetupThread(QThread):
    result_signal = pyqtSignal(str)
    def __init__(self, device_manager, devices):
        super().__init__()
        self.device_manager = device_manager
        self.devices = devices
    def run(self):
        import os, subprocess
        from .task_executor import PORTAL_APK_PATH, DROIDRUN_CLI_PATH
        env_initialized = False
        for device_id in self.devices:
            flag_file = os.path.expanduser(f"~/.droidrun-gui/portal_{device_id}.flag")
            if not os.path.exists(flag_file):
                setup_cmd = [DROIDRUN_CLI_PATH, "setup", f"--path={PORTAL_APK_PATH}", "--device", device_id]
                try:
                    result = subprocess.run(setup_cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        with open(flag_file, "w") as f:
                            f.write("ok")
                        env_initialized = True
                except Exception as e:
                    self.result_signal.emit(f"[自动安装Portal异常] {device_id}: {e}")
        if env_initialized:
            self.result_signal.emit("[环境已初始化] Portal APK 已自动安装到所有设备。")

class DroidRunGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DroidRun GUI")
        self.setMinimumSize(1000, 800)
        
        # 初始化管理器
        self.task_manager = TaskManager()
        self.device_manager = DeviceManager()
        self.task_executor = TaskExecutor()
        self.apikey_manager = APIKeyManager()
        
        # 连接信号
        self.task_executor.progress_signal.connect(self.update_progress)
        self.task_executor.output_signal.connect(self.update_output)
        self.task_executor.finished_signal.connect(self.task_finished)
        self.device_manager.device_connected.connect(self.on_device_connected)
        self.device_manager.device_disconnected.connect(self.on_device_disconnected)
        
        # 创建主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 主任务页面
        self.main_tab = QWidget()
        self.tab_widget.addTab(self.main_tab, "主任务")
        self.setup_main_tab()
        
        # 设备管理页面
        self.device_tab = QWidget()
        self.tab_widget.addTab(self.device_tab, "设备管理")
        self.setup_device_tab()
        
        # 任务模板页面
        self.template_tab = QWidget()
        self.tab_widget.addTab(self.template_tab, "任务模板")
        self.setup_template_tab()
        
        # 历史记录页面
        self.history_tab = QWidget()
        self.tab_widget.addTab(self.history_tab, "历史记录")
        self.setup_history_tab()
        
        # API密钥管理页面
        self.apikey_tab = QWidget()
        self.tab_widget.addTab(self.apikey_tab, "API密钥管理")
        self.setup_apikey_tab()
        
        # 设置定时器定期刷新设备状态
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_devices)
        self.refresh_timer.start(5000)  # 每5秒刷新一次
        
        self._setup_done_devices = set()
        self.device_combo.currentIndexChanged.connect(self.on_device_selected)
        
    def setup_main_tab(self):
        layout = QVBoxLayout(self.main_tab)
        
        # 设备选择部分
        device_group = QGroupBox("设备选择")
        device_layout = QVBoxLayout(device_group)
        
        self.device_combo = QComboBox()
        self.refresh_button = QPushButton("刷新设备列表")
        self.refresh_button.clicked.connect(self.refresh_devices)
        
        device_layout.addWidget(self.device_combo)
        device_layout.addWidget(self.refresh_button)
        
        # 任务输入部分
        task_group = QGroupBox("任务输入")
        task_layout = QVBoxLayout(task_group)
        
        # 新增模板选择下拉框
        self.template_combo = QComboBox()
        self.template_combo.addItem("选择任务模板（可选）")
        self.template_combo.currentIndexChanged.connect(self.select_main_tab_template)
        task_layout.addWidget(self.template_combo)
        
        self.task_input = QTextEdit()
        self.task_input.setPlaceholderText("例如：打开设置应用并检查Android版本")
        
        # 新增历史任务下拉框
        self.history_task_combo = QComboBox()
        self.history_task_combo.addItem("选择历史任务（可选）")
        self.history_task_combo.currentIndexChanged.connect(self.select_history_task)
        task_layout.addWidget(self.history_task_combo)
        
        # 新增steps步数输入框
        steps_layout = QHBoxLayout()
        self.steps_label = QLabel("最大步数:")
        self.steps_spin = QSpinBox()
        self.steps_spin.setMinimum(1)
        self.steps_spin.setMaximum(100)
        self.steps_spin.setValue(15)
        steps_layout.addWidget(self.steps_label)
        steps_layout.addWidget(self.steps_spin)
        steps_layout.addStretch()
        task_layout.addLayout(steps_layout)
        
        # 模型选择部分
        model_layout = QHBoxLayout()
        self.model_label = QLabel("选择AI模型:")
        self.model_combo = QComboBox()
        self.model_combo.addItems(["OpenAI GPT-4", "Anthropic Claude", "Google Gemini"])
        model_layout.addWidget(self.model_label)
        model_layout.addWidget(self.model_combo)
        
        # 执行按钮
        self.execute_button = QPushButton("执行任务")
        self.execute_button.clicked.connect(self.execute_task)
        # 新增中断按钮
        self.interrupt_button = QPushButton("中断任务")
        self.interrupt_button.clicked.connect(self.interrupt_task)
        self.interrupt_button.setEnabled(False)
        
        task_layout.addWidget(self.task_input)
        task_layout.addLayout(model_layout)
        task_layout.addWidget(self.execute_button)
        task_layout.addWidget(self.interrupt_button)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        # 输出区域
        output_group = QGroupBox("执行结果")
        output_layout = QVBoxLayout(output_group)
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        output_layout.addWidget(self.output_text)
        
        # 添加所有部件到布局
        layout.addWidget(device_group)
        layout.addWidget(task_group)
        layout.addWidget(self.progress_bar)
        layout.addWidget(output_group)
        
        # 初始化历史任务下拉框
        self.load_history_tasks()
        
    def setup_device_tab(self):
        layout = QVBoxLayout(self.device_tab)
        
        # 设备列表
        self.device_list = QListWidget()
        layout.addWidget(self.device_list)
        
        # 设备信息
        info_group = QGroupBox("设备信息")
        info_layout = QFormLayout(info_group)
        self.device_info_label = QLabel("请选择设备")
        info_layout.addRow("设备信息:", self.device_info_label)
        
        # 设备操作按钮
        buttons_layout = QHBoxLayout()
        self.connect_button = QPushButton("连接设备")
        self.disconnect_button = QPushButton("断开连接")
        self.connect_button.clicked.connect(self.show_connect_dialog)
        self.disconnect_button.clicked.connect(self.disconnect_device)
        buttons_layout.addWidget(self.connect_button)
        buttons_layout.addWidget(self.disconnect_button)
        
        # 新增：安装并切换ADBKeyboard输入法按钮
        self.install_adbkeyboard_button = QPushButton("安装并切换ADBKeyboard输入法")
        self.install_adbkeyboard_button.clicked.connect(self.install_and_switch_adbkeyboard)
        buttons_layout.addWidget(self.install_adbkeyboard_button)
        
        layout.addWidget(info_group)
        layout.addLayout(buttons_layout)
        
    def setup_template_tab(self):
        layout = QVBoxLayout(self.template_tab)
        
        # 模板列表
        self.template_list = QListWidget()
        self.template_list.itemClicked.connect(self.use_template)
        layout.addWidget(self.template_list)
        
        # 模板操作按钮
        buttons_layout = QHBoxLayout()
        add_button = QPushButton("添加模板")
        remove_button = QPushButton("删除模板")
        edit_button = QPushButton("编辑模板")
        add_button.clicked.connect(self.show_add_template_dialog)
        remove_button.clicked.connect(self.remove_template)
        edit_button.clicked.connect(self.edit_template)
        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(edit_button)
        buttons_layout.addWidget(remove_button)
        
        layout.addLayout(buttons_layout)
        
        # 加载模板
        self.load_templates()
        
    def setup_history_tab(self):
        layout = QVBoxLayout(self.history_tab)
        
        # 历史记录列表
        self.history_list = QListWidget()
        layout.addWidget(self.history_list)
        
        # 历史记录操作按钮
        buttons_layout = QHBoxLayout()
        clear_button = QPushButton("清除历史")
        clear_button.clicked.connect(self.clear_history)
        buttons_layout.addWidget(clear_button)
        
        layout.addLayout(buttons_layout)
        
        # 加载历史记录
        self.load_history()
        
    def setup_apikey_tab(self):
        layout = QFormLayout(self.apikey_tab)
        self.key_inputs = {}
        for provider in ["OPENAI", "ANTHROPIC", "GEMINI"]:
            line = QLineEdit()
            line.setText(self.apikey_manager.get_key(provider) or "")
            layout.addRow(f"{provider} API KEY:", line)
            self.key_inputs[provider] = line
        save_btn = QPushButton("保存API密钥")
        save_btn.clicked.connect(self.save_apikeys)
        layout.addRow(save_btn)
        
    def save_apikeys(self):
        for provider, line in self.key_inputs.items():
            self.apikey_manager.set_key(provider, line.text().strip())
        QMessageBox.information(self, "提示", "API密钥已保存！")
        
    def refresh_devices(self):
        current_device = self.device_combo.currentText()
        devices = self.device_manager.get_connected_devices()
        self.device_combo.clear()
        if devices:
            self.device_combo.addItems(devices)
            # 恢复用户选择
            if current_device in devices:
                self.device_combo.setCurrentText(current_device)
        else:
            self.device_combo.addItem("未检测到设备")
        # 更新设备列表
        self.device_list.clear()
        for device_id in devices:
            info = self.device_manager.get_device_info(device_id)
            if info:
                item = QListWidgetItem(f"{info['name']} ({info['model']})")
                item.setData(Qt.ItemDataRole.UserRole, device_id)
                self.device_list.addItem(item)
                
    def on_device_connected(self, device_id):
        self.refresh_devices()
        
    def on_device_disconnected(self, device_id):
        self.refresh_devices()
        
    def show_connect_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("连接设备")
        layout = QFormLayout(dialog)
        
        ip_input = QLineEdit()
        layout.addRow("IP地址:", ip_input)
        
        buttons = QHBoxLayout()
        connect_button = QPushButton("连接")
        cancel_button = QPushButton("取消")
        
        connect_button.clicked.connect(lambda: self.connect_device(ip_input.text(), dialog))
        cancel_button.clicked.connect(dialog.reject)
        
        buttons.addWidget(connect_button)
        buttons.addWidget(cancel_button)
        layout.addRow(buttons)
        
        dialog.exec()
        
    def connect_device(self, ip_address, dialog):
        if self.device_manager.connect_device(ip_address):
            dialog.accept()
            self.refresh_devices()
        else:
            QMessageBox.warning(self, "错误", "连接设备失败")
            
    def disconnect_device(self):
        current_item = self.device_list.currentItem()
        if current_item:
            device_id = current_item.data(Qt.ItemDataRole.UserRole)
            if self.device_manager.disconnect_device(device_id):
                self.refresh_devices()
            else:
                QMessageBox.warning(self, "错误", "断开设备连接失败")
                
    def show_add_template_dialog(self):
        dialog = AddTemplateDialog(self)
        if dialog.exec():
            self.task_manager.add_template(
                dialog.category_input.text(),
                dialog.name_input.text(),
                dialog.description_input.toPlainText()
            )
            self.load_templates()
            
    def remove_template(self):
        current_item = self.template_list.currentItem()
        if current_item:
            category, name = current_item.data(Qt.ItemDataRole.UserRole)
            self.task_manager.remove_template(category, name)
            self.load_templates()
            
    def load_templates(self):
        self.template_list.clear()
        self.template_combo.blockSignals(True)
        self.template_combo.clear()
        self.template_combo.addItem("选择任务模板（可选）")
        templates = self.task_manager.get_templates()
        for category, tasks in templates.items():
            for task in tasks:
                item = QListWidgetItem(f"{category} - {task['name']}")
                item.setData(Qt.ItemDataRole.UserRole, (category, task['name']))
                self.template_list.addItem(item)
                # 同步添加到主任务下拉框
                self.template_combo.addItem(f"{category} - {task['name']}", (category, task['name']))
        self.template_combo.blockSignals(False)
        
    def load_history(self):
        self.history_list.clear()
        history = self.task_manager.get_history()
        for entry in reversed(history):
            item = QListWidgetItem(
                f"{entry['timestamp']} - {entry['task']} "
                f"({'成功' if entry['success'] else '失败'})"
            )
            self.history_list.addItem(item)
            
    def clear_history(self):
        self.task_manager.clear_history()
        self.load_history()
        
    def execute_task(self):
        if self.device_combo.currentText() == "未检测到设备":
            QMessageBox.warning(self, "警告", "请先连接设备")
            return
            
        task = self.task_input.toPlainText()
        if not task:
            QMessageBox.warning(self, "警告", "请输入任务描述")
            return
            
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.output_text.clear()
        self.execute_button.setEnabled(False)
        self.interrupt_button.setEnabled(True)
        
        # 设置环境变量，确保底层droidrun用选中的设备
        os.environ["DROIDRUN_DEVICE_SERIAL"] = self.device_combo.currentText()
        
        # 读取步数
        steps = self.steps_spin.value()
        
        # 开始执行任务
        self.task_executor.start_task(
            task,
            self.model_combo.currentText(),
            self.device_combo.currentText(),
            steps
        )
        
    def update_progress(self, value):
        self.progress_bar.setValue(value)
        
    def update_output(self, message):
        self.output_text.append(message)
        
    def task_finished(self, success, message, steps):
        self.execute_button.setEnabled(True)
        self.interrupt_button.setEnabled(False)
        if not success:
            QMessageBox.warning(self, "任务执行失败", message)
            
        # 添加到历史记录
        self.task_manager.add_history(
            self.task_input.toPlainText(),
            self.model_combo.currentText(),
            self.device_combo.currentText(),
            success,
            message,
            steps
        )
        self.load_history()
        self.load_history_tasks()
        
    def use_template(self, item):
        # 获取模板内容并填充到任务输入框
        category, name = item.data(Qt.ItemDataRole.UserRole)
        templates = self.task_manager.get_templates()
        for t in templates.get(category, []):
            if t["name"] == name:
                self.task_input.setPlainText(t["description"])
                break
        
    def select_main_tab_template(self, idx):
        if idx <= 0:
            return
        data = self.template_combo.itemData(idx)
        if not data:
            return
        category, name = data
        templates = self.task_manager.get_templates()
        for t in templates.get(category, []):
            if t["name"] == name:
                self.task_input.setPlainText(t["description"])
                break
        
    def edit_template(self):
        current_item = self.template_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择要编辑的模板")
            return
        category, name = current_item.data(Qt.ItemDataRole.UserRole)
        templates = self.task_manager.get_templates()
        for t in templates.get(category, []):
            if t["name"] == name:
                dialog = AddTemplateDialog(self)
                dialog.category_input.setText(category)
                dialog.name_input.setText(name)
                dialog.description_input.setPlainText(t["description"])
                dialog.category_input.setReadOnly(True)
                dialog.name_input.setReadOnly(True)
                if dialog.exec():
                    t["description"] = dialog.description_input.toPlainText()
                    self.task_manager._save_templates()
                    self.load_templates()
                break
        
    def on_device_selected(self, idx):
        device_id = self.device_combo.currentText()
        if not device_id or device_id == "未检测到设备":
            return
        if device_id in self._setup_done_devices:
            return
        from .task_executor import PORTAL_APK_PATH, DROIDRUN_CLI_PATH
        import subprocess
        setup_cmd = [DROIDRUN_CLI_PATH, "setup", f"--path={PORTAL_APK_PATH}", "--device", device_id]
        try:
            result = subprocess.run(setup_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                flag_file = os.path.expanduser(f"~/.droidrun-gui/portal_{device_id}.flag")
                with open(flag_file, "w") as f:
                    f.write("ok")
                self.output_text.append(f"[环境已初始化] Portal APK 已安装到设备 {device_id}。")
            else:
                self.output_text.append(f"[Portal安装失败] {device_id}: {result.stdout}\n{result.stderr}")
        except Exception as e:
            self.output_text.append(f"[Portal安装异常] {device_id}: {e}")
        self._setup_done_devices.add(device_id)
        
    def load_history_tasks(self):
        self.history_task_combo.blockSignals(True)
        self.history_task_combo.clear()
        self.history_task_combo.addItem("选择历史任务（可选）")
        history = self.task_manager.get_history()
        seen = set()
        for entry in reversed(history):
            task = entry['task']
            if task and task not in seen:
                self.history_task_combo.addItem(task)
                seen.add(task)
        self.history_task_combo.blockSignals(False)

    def select_history_task(self, idx):
        if idx <= 0:
            return
        task = self.history_task_combo.currentText()
        if task:
            self.task_input.setPlainText(task)
        
    def install_and_switch_adbkeyboard(self):
        device_id = self.device_combo.currentText()
        if not device_id or device_id == "未检测到设备":
            QMessageBox.warning(self, "提示", "请先选择设备")
            return
        import sys, os
        if hasattr(sys, '_MEIPASS'):
            apk_path = os.path.join(sys._MEIPASS, 'resources', 'ADBKeyboard.apk')
        else:
            apk_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "resources", "ADBKeyboard.apk"))
        self.adbkeyboard_thread = InstallAdbKeyboardThread(device_id, apk_path)
        self.adbkeyboard_thread.result_signal.connect(self.on_adbkeyboard_install_result)
        self.adbkeyboard_thread.start()

    def on_adbkeyboard_install_result(self, msg, success):
        self.output_text.append(msg)
        if success:
            QMessageBox.information(self, "ADBKeyboard", "ADBKeyboard安装成功，已自动打开输入法设置界面，请在手机上手动启用ADBKeyboard输入法，然后再点击切换按钮。")
        else:
            QMessageBox.warning(self, "ADBKeyboard", "ADBKeyboard安装失败，请检查APK路径和设备连接。")

    def interrupt_task(self):
        if hasattr(self.task_executor, 'worker') and self.task_executor.worker.isRunning():
            self.task_executor.worker.stop()
            self.task_executor.worker.terminate()
            self.output_text.append("[中断] 已请求中断当前任务。")
            self.interrupt_button.setEnabled(False)
            self.execute_button.setEnabled(True)
        else:
            self.output_text.append("[中断] 当前无正在运行的任务。")

def main():
    device_manager = DeviceManager()
    devices = device_manager.get_connected_devices()
    app = QApplication(sys.argv)
    window = DroidRunGUI()
    window.show()
    # 启动 Portal 安装线程
    def portal_result(msg):
        window.output_text.append(msg)
    portal_thread = PortalSetupThread(device_manager, devices)
    portal_thread.result_signal.connect(portal_result)
    portal_thread.start()
    sys.exit(app.exec()) 