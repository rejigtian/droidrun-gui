"""
任务历史记录管理
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict


class TaskHistory:
    """任务历史记录管理类"""
    
    def __init__(self):
        # 历史文件路径
        self.history_dir = Path.home() / '.droidrun-desktop'
        self.history_file = self.history_dir / 'task_history.json'
        
        # 确保目录存在
        self.history_dir.mkdir(exist_ok=True)
        
        # 加载历史记录
        self.history = self._load_history()
    
    def _load_history(self) -> List[Dict]:
        """加载历史记录"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return []
        return []
    
    def _save_history(self):
        """保存历史记录"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存历史记录失败: {e}")
            return False
    
    def add_task(self, task_description: str, device_serial: str = None, 
                 success: bool = True, result: str = None):
        """
        添加任务到历史记录
        
        Args:
            task_description: 任务描述
            device_serial: 设备序列号
            success: 是否成功
            result: 执行结果
        """
        # 检查是否已存在相同任务（避免重复）
        for item in self.history:
            if item.get('task') == task_description:
                # 更新最后执行时间和次数
                item['last_executed'] = datetime.now().isoformat()
                item['execution_count'] = item.get('execution_count', 1) + 1
                item['last_success'] = success
                if device_serial:
                    item['device'] = device_serial
                self._save_history()
                return
        
        # 新建记录
        task_record = {
            'task': task_description,
            'device': device_serial,
            'created_at': datetime.now().isoformat(),
            'last_executed': datetime.now().isoformat(),
            'execution_count': 1,
            'last_success': success,
            'result': result
        }
        
        # 添加到开头（最新的在前面）
        self.history.insert(0, task_record)
        
        # 限制历史记录数量（保留最近100条）
        if len(self.history) > 100:
            self.history = self.history[:100]
        
        self._save_history()
    
    def get_recent_tasks(self, limit: int = 20) -> List[Dict]:
        """
        获取最近的任务记录
        
        Args:
            limit: 返回的最大数量
            
        Returns:
            任务记录列表
        """
        return self.history[:limit]
    
    def get_frequent_tasks(self, limit: int = 10) -> List[Dict]:
        """
        获取最常用的任务
        
        Args:
            limit: 返回的最大数量
            
        Returns:
            按执行次数排序的任务列表
        """
        sorted_tasks = sorted(
            self.history, 
            key=lambda x: x.get('execution_count', 1), 
            reverse=True
        )
        return sorted_tasks[:limit]
    
    def search_tasks(self, keyword: str) -> List[Dict]:
        """
        搜索任务
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            匹配的任务列表
        """
        if not keyword:
            return []
        
        keyword = keyword.lower()
        results = []
        
        for task in self.history:
            if keyword in task.get('task', '').lower():
                results.append(task)
        
        return results
    
    def delete_task(self, task_description: str) -> bool:
        """
        删除指定任务
        
        Args:
            task_description: 任务描述
            
        Returns:
            是否删除成功
        """
        for i, task in enumerate(self.history):
            if task.get('task') == task_description:
                self.history.pop(i)
                return self._save_history()
        return False
    
    def clear_history(self) -> bool:
        """清空所有历史记录"""
        self.history = []
        return self._save_history()
    
    def get_task_count(self) -> int:
        """获取历史记录总数"""
        return len(self.history)

