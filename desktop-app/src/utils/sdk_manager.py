"""
SDK 路径管理器
自动检测和管理外部工具路径（adb, python, brew）
注意：DroidRun 已内置到应用中，无需配置路径
"""

import os
import subprocess
import platform
from pathlib import Path


class SDKManager:
    """SDK 路径管理器"""
    
    # 默认搜索路径
    DEFAULT_SEARCH_PATHS = {
        'adb': [
            '/usr/local/bin/adb',
            '/opt/homebrew/bin/adb',
            '~/Library/Android/sdk/platform-tools/adb',
            '/Users/{username}/Library/Android/sdk/platform-tools/adb',
            'C:\\Users\\{username}\\AppData\\Local\\Android\\Sdk\\platform-tools\\adb.exe',
            'C:\\Android\\sdk\\platform-tools\\adb.exe',
        ],
        # DroidRun 已内置到应用中，无需配置路径
        'python': [
            '/usr/local/bin/python3',
            '/opt/homebrew/bin/python3',
            '/usr/bin/python3',
            'C:\\Users\\{username}\\AppData\\Local\\Programs\\Python\\Python3*\\python.exe',
        ],
        'brew': [
            '/usr/local/bin/brew',
            '/opt/homebrew/bin/brew',
        ]
    }
    
    def __init__(self, config_manager):
        """
        初始化 SDK 管理器
        
        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager
        self.config = config_manager.config
        
        # 确保配置中有 sdk_paths 字段
        if 'sdk_paths' not in self.config:
            self.config['sdk_paths'] = {}
            self.config_manager.save(self.config)
    
    def get_tool_path(self, tool_name):
        """
        获取工具路径（优先使用用户配置，否则自动检测）
        
        Args:
            tool_name: 工具名称（adb, droidrun, python, brew）
            
        Returns:
            str: 工具的完整路径，如果未找到则返回工具名称本身
        """
        # 1. 优先使用用户配置的路径
        user_path = self.config.get('sdk_paths', {}).get(tool_name)
        if user_path and self._verify_path(user_path):
            return user_path
        
        # 2. 尝试自动检测
        detected_path = self.detect_tool_path(tool_name)
        if detected_path:
            # 自动保存检测到的路径
            self.save_tool_path(tool_name, detected_path)
            return detected_path
        
        # 3. 返回工具名称本身（依赖系统 PATH）
        return tool_name
    
    def detect_tool_path(self, tool_name):
        """
        自动检测工具路径
        
        Args:
            tool_name: 工具名称
            
        Returns:
            str: 检测到的路径，如果未找到则返回 None
        """
        # 方法1: 使用 which/where 命令
        path = self._detect_via_which(tool_name)
        if path:
            return path
        
        # 方法2: 搜索预定义路径
        path = self._search_default_paths(tool_name)
        if path:
            return path
        
        return None
    
    def _detect_via_which(self, tool_name):
        """
        使用 which/where 命令检测
        
        Args:
            tool_name: 工具名称
            
        Returns:
            str: 检测到的路径，如果未找到则返回 None
        """
        try:
            # macOS/Linux 使用 which，Windows 使用 where
            cmd = 'where' if platform.system() == 'Windows' else 'which'
            
            result = subprocess.run(
                [cmd, tool_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                path = result.stdout.strip().split('\n')[0]
                if self._verify_path(path):
                    return path
        
        except Exception as e:
            print(f"⚠️ which/where 命令失败: {e}")
        
        return None
    
    def _search_default_paths(self, tool_name):
        """
        在预定义路径中搜索工具
        
        Args:
            tool_name: 工具名称
            
        Returns:
            str: 找到的路径，如果未找到则返回 None
        """
        if tool_name not in self.DEFAULT_SEARCH_PATHS:
            return None
        
        username = os.getenv('USER') or os.getenv('USERNAME')
        
        for path_template in self.DEFAULT_SEARCH_PATHS[tool_name]:
            # 替换模板变量
            path = path_template.format(
                username=username,
                venv=os.getenv('VIRTUAL_ENV', '')
            )
            
            # 展开 ~ 和环境变量
            path = os.path.expanduser(path)
            path = os.path.expandvars(path)
            
            # 如果路径包含通配符（如 Python3*），使用 glob
            if '*' in path:
                from glob import glob
                matches = glob(path)
                if matches:
                    path = matches[0]
                else:
                    continue
            
            # 验证路径
            if self._verify_path(path):
                return path
        
        return None
    
    def _verify_path(self, path):
        """
        验证路径是否有效（文件存在且可执行）
        
        Args:
            path: 文件路径
            
        Returns:
            bool: 是否有效
        """
        if not path:
            return False
        
        path_obj = Path(path)
        
        # 检查文件是否存在
        if not path_obj.exists():
            return False
        
        # 检查是否为文件（不是目录）
        if not path_obj.is_file():
            return False
        
        # 检查是否可执行（Unix-like 系统）
        if platform.system() != 'Windows':
            if not os.access(path, os.X_OK):
                return False
        
        return True
    
    def save_tool_path(self, tool_name, path):
        """
        保存工具路径到配置
        
        Args:
            tool_name: 工具名称
            path: 工具路径
        """
        if 'sdk_paths' not in self.config:
            self.config['sdk_paths'] = {}
        
        self.config['sdk_paths'][tool_name] = path
        self.config_manager.save(self.config)
    
    def detect_all_tools(self):
        """
        检测所有工具的路径
        
        Returns:
            dict: 工具名称 -> 路径的字典
        """
        results = {}
        
        for tool_name in ['adb', 'python', 'brew']:  # DroidRun 已内置，无需检测
            path = self.detect_tool_path(tool_name)
            results[tool_name] = {
                'path': path,
                'found': path is not None,
                'user_configured': tool_name in self.config.get('sdk_paths', {})
            }
        
        return results
    
    def get_environment_info(self):
        """
        获取系统环境信息
        
        Returns:
            dict: 环境信息
        """
        return {
            'os': platform.system(),
            'os_version': platform.version(),
            'arch': platform.machine(),
            'python_version': platform.python_version(),
            'home': str(Path.home()),
            'user': os.getenv('USER') or os.getenv('USERNAME'),
            'path_dirs': os.getenv('PATH', '').split(os.pathsep)[:10]  # 只显示前10个
        }
    
    def verify_tool(self, tool_name, path=None):
        """
        验证工具是否可用
        
        Args:
            tool_name: 工具名称
            path: 工具路径（可选，不提供则使用 get_tool_path）
            
        Returns:
            dict: 验证结果 {'success': bool, 'message': str, 'version': str}
        """
        if not path:
            path = self.get_tool_path(tool_name)
        
        # 验证路径
        if not self._verify_path(path):
            return {
                'success': False,
                'message': f'路径无效或文件不存在: {path}',
                'version': None
            }
        
        # 尝试运行工具获取版本
        try:
            # 不同工具的版本命令
            version_cmd = {
                'adb': [path, 'version'],
                # DroidRun 已内置，无需验证
                'python': [path, '--version'],
                'brew': [path, '--version']
            }
            
            if tool_name not in version_cmd:
                return {
                    'success': True,
                    'message': '路径有效',
                    'version': 'Unknown'
                }
            
            result = subprocess.run(
                version_cmd[tool_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # 提取版本信息
                version = result.stdout.strip().split('\n')[0]
                
                return {
                    'success': True,
                    'message': '工具可用',
                    'version': version
                }
            else:
                return {
                    'success': False,
                    'message': f'工具无法运行: {result.stderr}',
                    'version': None
                }
        
        except Exception as e:
            return {
                'success': False,
                'message': f'验证失败: {str(e)}',
                'version': None
            }
    
    def reset_tool_path(self, tool_name):
        """
        重置工具路径（删除用户配置，恢复自动检测）
        
        Args:
            tool_name: 工具名称
        """
        if 'sdk_paths' in self.config and tool_name in self.config['sdk_paths']:
            del self.config['sdk_paths'][tool_name]
            self.config_manager.save(self.config)


# 全局单例
_sdk_manager = None


def get_sdk_manager(config_manager=None):
    """
    获取 SDK 管理器单例
    
    Args:
        config_manager: 配置管理器实例（首次调用时必须提供）
        
    Returns:
        SDKManager: SDK 管理器实例
    """
    global _sdk_manager
    
    if _sdk_manager is None:
        if config_manager is None:
            raise ValueError("首次调用必须提供 config_manager")
        _sdk_manager = SDKManager(config_manager)
    
    return _sdk_manager

