import asyncio
import os
import subprocess
import sys
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from .apikey_manager import APIKeyManager

def get_portal_apk_path():
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, 'resources', 'droidrun-portal-v0.1.1.apk')
    else:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "resources", "droidrun-portal-v0.1.1.apk"))
PORTAL_APK_PATH = get_portal_apk_path()

def get_droidrun_cli_path():
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, 'resources', 'droidrun')
    else:
        return "droidrun"
DROIDRUN_CLI_PATH = get_droidrun_cli_path()

class TaskWorker(QThread):
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str, int)
    def __init__(self, cmd, env, device_id):
        super().__init__()
        self.cmd = cmd
        self.env = env
        self.device_id = device_id
        self.process = None
    def run(self):
        # 检查并安装portal apk
        portal_flag_file = os.path.expanduser(f"~/.droidrun-gui/portal_{self.device_id}.flag")
        if not os.path.exists(portal_flag_file):
            setup_cmd = [
                DROIDRUN_CLI_PATH, "setup",
                f"--path={PORTAL_APK_PATH}",
                f"--device", self.device_id
            ]
            self.output_signal.emit(f"首次在该设备上运行，自动安装Portal APK: {' '.join(setup_cmd)}")
            try:
                result = subprocess.run(setup_cmd, capture_output=True, text=True, env=self.env)
                output = result.stdout + "\n" + result.stderr
                self.output_signal.emit(output)
                if result.returncode == 0:
                    with open(portal_flag_file, "w") as f:
                        f.write("ok")
                else:
                    self.finished_signal.emit(False, "Portal APK 安装失败", 0)
                    return
            except Exception as e:
                self.output_signal.emit(f"Portal 安装错误: {str(e)}")
                self.finished_signal.emit(False, str(e), 0)
                return
        self.output_signal.emit(f"执行命令: {' '.join(self.cmd)}")
        try:
            if self.cmd[0] == "droidrun":
                self.cmd[0] = DROIDRUN_CLI_PATH
            self.process = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=self.env)
            stdout, stderr = self.process.communicate()
            output = stdout + "\n" + stderr
            self.output_signal.emit(output)
            success = self.process.returncode == 0
            self.finished_signal.emit(success, "CLI执行完成", 0)
        except Exception as e:
            self.output_signal.emit(f"错误: {str(e)}")
            self.finished_signal.emit(False, str(e), 0)
    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.output_signal.emit("[中断] 已终止子进程。")

class TaskExecutor(QObject):
    progress_signal = pyqtSignal(int)
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str, int)
    
    def __init__(self):
        super().__init__()
        self.current_task = None
        self.apikey_manager = APIKeyManager()
        
    def get_llm_provider(self, model_name):
        if "OpenAI" in model_name:
            return "openai", "gpt-4"
        elif "Anthropic" in model_name:
            return "anthropic", "claude-3-sonnet-20240229"
        else:
            return "gemini", "gemini-2.0-flash"

    def start_task(self, task_description, model_name, device_id, steps=15):
        provider, model = self.get_llm_provider(model_name)
        api_key = self.apikey_manager.get_key(provider)
        env = os.environ.copy()
        if api_key:
            env[f"{provider.upper()}_API_KEY"] = api_key
        cmd = [
            "droidrun",
            task_description,
            "--device", device_id,
            "--provider", provider,
            "--model", model,
            "--steps", str(steps)
        ]
        self.worker = TaskWorker(cmd, env, device_id)
        self.worker.output_signal.connect(self.output_signal.emit)
        self.worker.finished_signal.connect(self.finished_signal.emit)
        self.worker.start() 