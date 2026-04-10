"""
配置管理器
"""

import json
import os
from pathlib import Path


class ConfigManager:
    """配置管理器类"""
    
    def __init__(self):
        # 配置文件路径
        self.config_dir = Path.home() / '.droidrun-desktop'
        self.config_file = self.config_dir / 'config.json'
        
        # 确保配置目录存在
        self.config_dir.mkdir(exist_ok=True)
        
        # 加载配置
        self.config = self.load()
    
    def load(self):
        """加载配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return self._default_config()
        else:
            return self._default_config()
    
    def save(self, config):
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            self.config = config
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False
    
    def get(self, key, default=None):
        """获取配置项"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """设置配置项"""
        self.config[key] = value
        return self.save(self.config)
    
    def _default_config(self):
        """默认配置"""
        return {
            'google_api_key': '',
            'openai_api_key': '',
            'anthropic_api_key': '',
            'deepseek_api_key': '',
            'zhipu_api_key': '',
            'default_provider': 'GoogleGenAI',
            'gemini_model': 'gemini-1.5-flash',
            'openai_model': 'gpt-4o',
            'anthropic_model': 'claude-sonnet-4-6',
            'zhipu_model': 'glm-4-plus',
            'max_steps': 15,
            'appearance_mode': 'dark'
        }

