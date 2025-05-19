import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

class TaskManager:
    def __init__(self):
        self.data_dir = Path.home() / ".droidrun-gui"
        self.data_dir.mkdir(exist_ok=True)
        self.templates_file = self.data_dir / "templates.json"
        self.history_file = self.data_dir / "history.json"
        self._load_data()
        
    def _load_data(self):
        # 加载任务模板
        if self.templates_file.exists():
            with open(self.templates_file, 'r', encoding='utf-8') as f:
                self.templates = json.load(f)
        else:
            self.templates = {
                "常用任务": [
                    {"name": "检查系统版本", "description": "打开设置应用并检查Android版本"},
                    {"name": "清理后台", "description": "打开最近任务列表并清理所有后台应用"},
                    {"name": "检查电池状态", "description": "打开设置应用并检查电池状态"}
                ]
            }
            self._save_templates()
            
        # 加载历史记录
        if self.history_file.exists():
            with open(self.history_file, 'r', encoding='utf-8') as f:
                self.history = json.load(f)
        else:
            self.history = []
            
    def _save_templates(self):
        with open(self.templates_file, 'w', encoding='utf-8') as f:
            json.dump(self.templates, f, ensure_ascii=False, indent=2)
            
    def _save_history(self):
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)
            
    def add_template(self, category: str, name: str, description: str):
        if category not in self.templates:
            self.templates[category] = []
        self.templates[category].append({
            "name": name,
            "description": description
        })
        self._save_templates()
        
    def remove_template(self, category: str, name: str):
        if category in self.templates:
            self.templates[category] = [t for t in self.templates[category] 
                                     if t["name"] != name]
            if not self.templates[category]:
                del self.templates[category]
            self._save_templates()
            
    def get_templates(self) -> Dict[str, List[Dict]]:
        return self.templates
        
    def add_history(self, task: str, model: str, device: str, success: bool, 
                   message: str, steps: int):
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "model": model,
            "device": device,
            "success": success,
            "message": message,
            "steps": steps
        })
        # 只保留最近100条记录
        if len(self.history) > 100:
            self.history = self.history[-100:]
        self._save_history()
        
    def get_history(self) -> List[Dict]:
        return self.history
        
    def clear_history(self):
        self.history = []
        self._save_history() 