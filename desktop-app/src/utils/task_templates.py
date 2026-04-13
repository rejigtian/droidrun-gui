"""
任务模板管理
"""

import json
from pathlib import Path
from typing import List, Dict


class TaskTemplates:
    """任务模板管理类"""
    
    def __init__(self):
        # 模板文件路径
        self.templates_dir = Path.home() / '.droidrun-desktop'
        self.templates_file = self.templates_dir / 'task_templates.json'
        
        # 确保目录存在
        self.templates_dir.mkdir(exist_ok=True)
        
        # 加载模板
        self.templates = self._load_templates()
        
        # 初始化默认模板
        if not self.templates:
            self._init_default_templates()
    
    def _load_templates(self) -> List[Dict]:
        """加载模板"""
        if self.templates_file.exists():
            try:
                with open(self.templates_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return []
        return []
    
    def _save_templates(self):
        """保存模板"""
        try:
            with open(self.templates_file, 'w', encoding='utf-8') as f:
                json.dump(self.templates, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存模板失败: {e}")
            return False
    
    def _init_default_templates(self):
        """初始化默认模板"""
        default_templates = [
            {
                'name': '📱 打开应用',
                'category': '基础操作',
                'task': '打开',
                'description': '打开指定应用',
                'example': '打开微信',
                'is_default': True
            },
            {
                'name': '💬 发送消息',
                'category': '社交',
                'task': '在微信中给发送消息：',
                'description': '通过微信发送消息',
                'example': '在微信中给张三发送消息：明天见',
                'is_default': True
            },
            {
                'name': '📧 发送邮件',
                'category': '办公',
                'task': '发送邮件给，标题：，内容：',
                'description': '发送电子邮件',
                'example': '发送邮件给test@example.com，标题：会议通知，内容：明天下午3点开会',
                'is_default': True
            },
            {
                'name': '🔍 搜索',
                'category': '基础操作',
                'task': '在浏览器中搜索',
                'description': '使用浏览器搜索内容',
                'example': '在浏览器中搜索人工智能',
                'is_default': True
            },
            {
                'name': '📸 截图',
                'category': '基础操作',
                'task': '截图并保存',
                'description': '截取当前屏幕',
                'example': '截图并保存',
                'is_default': True
            },
            {
                'name': '⚙️ 打开设置',
                'category': '系统',
                'task': '打开设置',
                'description': '打开系统设置',
                'example': '打开设置',
                'is_default': True
            },
            {
                'name': '🔊 调整音量',
                'category': '系统',
                'task': '将音量调整到',
                'description': '调整系统音量',
                'example': '将音量调整到50%',
                'is_default': True
            },
            {
                'name': '📲 安装应用',
                'category': '应用管理',
                'task': '打开应用商店搜索并安装',
                'description': '从应用商店安装应用',
                'example': '打开应用商店搜索并安装抖音',
                'is_default': True
            },
            {
                'name': '🎵 播放音乐',
                'category': '娱乐',
                'task': '打开音乐应用播放',
                'description': '播放指定音乐',
                'example': '打开音乐应用播放周杰伦的歌',
                'is_default': True
            },
            {
                'name': '📹 拍照',
                'category': '娱乐',
                'task': '打开相机拍照',
                'description': '使用相机拍照',
                'example': '打开相机拍照',
                'is_default': True
            }
        ]
        
        self.templates = default_templates
        self._save_templates()
    
    def get_all_templates(self) -> List[Dict]:
        """获取所有模板"""
        return self.templates
    
    def get_templates_by_category(self, category: str) -> List[Dict]:
        """
        按分类获取模板
        
        Args:
            category: 分类名称
            
        Returns:
            该分类下的模板列表
        """
        return [t for t in self.templates if t.get('category') == category]
    
    def get_categories(self) -> List[str]:
        """获取所有分类"""
        categories = set()
        for template in self.templates:
            if 'category' in template:
                categories.add(template['category'])
        return sorted(list(categories))
    
    def add_template(self, name: str, task: str, category: str = '自定义', 
                     description: str = '', example: str = '') -> bool:
        """
        添加新模板
        
        Args:
            name: 模板名称
            task: 任务描述
            category: 分类
            description: 描述
            example: 示例
            
        Returns:
            是否添加成功
        """
        # 检查是否已存在同名模板
        for template in self.templates:
            if template.get('name') == name:
                return False
        
        new_template = {
            'name': name,
            'category': category,
            'task': task,
            'description': description,
            'example': example,
            'is_default': False
        }
        
        self.templates.append(new_template)
        return self._save_templates()
    
    def update_template(self, old_name: str, name: str = None, task: str = None, 
                       category: str = None, description: str = None, 
                       example: str = None) -> bool:
        """
        更新模板
        
        Args:
            old_name: 原模板名称
            name: 新名称
            task: 新任务描述
            category: 新分类
            description: 新描述
            example: 新示例
            
        Returns:
            是否更新成功
        """
        for template in self.templates:
            if template.get('name') == old_name:
                if name is not None:
                    template['name'] = name
                if task is not None:
                    template['task'] = task
                if category is not None:
                    template['category'] = category
                if description is not None:
                    template['description'] = description
                if example is not None:
                    template['example'] = example
                
                return self._save_templates()
        
        return False
    
    def delete_template(self, name: str) -> bool:
        """
        删除模板
        
        Args:
            name: 模板名称
            
        Returns:
            是否删除成功
        """
        for i, template in enumerate(self.templates):
            if template.get('name') == name:
                # 不允许删除默认模板
                if template.get('is_default', False):
                    return False
                
                self.templates.pop(i)
                return self._save_templates()
        
        return False
    
    def search_templates(self, keyword: str) -> List[Dict]:
        """
        搜索模板
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            匹配的模板列表
        """
        if not keyword:
            return self.templates
        
        keyword = keyword.lower()
        results = []
        
        for template in self.templates:
            if (keyword in template.get('name', '').lower() or
                keyword in template.get('task', '').lower() or
                keyword in template.get('description', '').lower() or
                keyword in template.get('category', '').lower()):
                results.append(template)
        
        return results
    
    def get_template_count(self) -> int:
        """获取模板总数"""
        return len(self.templates)

