"""
DroidRun 安装器
"""

import subprocess
import sys
import platform
import os
import json


class DroidRunInstaller:
    """DroidRun 安装器类"""
    
    def __init__(self):
        """初始化"""
        # 缓存文件路径
        self.cache_file = os.path.expanduser("~/.droidrun_desktop_cache.json")
    
    def _load_cache(self):
        """加载缓存"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
    
    def _save_cache(self, data):
        """保存缓存"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(data, f)
        except Exception:
            pass
    
    def check_python(self):
        """检查 Python 版本"""
        version = sys.version_info
        return version.major == 3 and version.minor >= 11
    
    def check_adb(self):
        """检查 ADB 是否安装"""
        adb_cmd = self._find_command('adb')
        try:
            result = subprocess.run(
                [adb_cmd, 'version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def _is_frozen(self):
        """检测是否在打包环境中运行"""
        return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')
    
    def _find_command(self, command):
        """
        查找系统命令的完整路径
        
        Args:
            command: 命令名称（如 'brew', 'pip3', 'python3'）
            
        Returns:
            str: 命令的完整路径，如果找不到则返回原命令名
        """
        # 常见命令的可能路径
        common_paths = {
            'brew': ['/opt/homebrew/bin/brew', '/usr/local/bin/brew'],
            'pip3': ['/opt/homebrew/bin/pip3', '/usr/local/bin/pip3', '/usr/bin/pip3'],
            'python3': ['/opt/homebrew/bin/python3', '/usr/local/bin/python3', '/usr/bin/python3'],
            'pipx': ['/opt/homebrew/bin/pipx', '/usr/local/bin/pipx', os.path.expanduser('~/.local/bin/pipx')],
            'droidrun': ['/opt/homebrew/bin/droidrun', '/usr/local/bin/droidrun', os.path.expanduser('~/.local/bin/droidrun')],
            'adb': ['/opt/homebrew/bin/adb', '/usr/local/bin/adb', os.path.expanduser('~/Library/Android/sdk/platform-tools/adb')],
        }
        
        # 如果在开发环境中，直接返回命令名（系统会自动查找）
        if not self._is_frozen():
            return command
        
        # 在打包环境中，尝试找到完整路径
        if command in common_paths:
            for path in common_paths[command]:
                if os.path.exists(path):
                    return path
        
        # 尝试使用 which 查找（作为后备）
        try:
            result = subprocess.run(
                ['which', command],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass
        
        # 找不到就返回原命令名
        return command
    
    def check_droidrun(self, force=False):
        """
        检查 DroidRun 是否可用

        打包环境下 droidrun 已内置，直接返回 True。
        开发环境下通过 import 检测。

        Args:
            force: 是否强制重新检测（忽略缓存）

        Returns:
            bool: 是否已安装
        """
        # 打包环境：droidrun 已被 PyInstaller 打包进 app，无需检测
        if self._is_frozen():
            return True

        # 开发环境：通过 import 检测
        if not force:
            cache = self._load_cache()
            if cache.get('droidrun_installed') == True:
                try:
                    import droidrun
                    return True
                except ImportError:
                    pass  # 缓存过期，继续完整检测

        try:
            import droidrun
            self._save_cache({'droidrun_installed': True})
            return True
        except ImportError:
            self._save_cache({'droidrun_installed': False})
            return False
    
    def install_droidrun(self, method='pipx', callback=None):
        """
        安装 DroidRun
        
        Args:
            method: 安装方法 ('pipx' 或 'pip')
            callback: 日志回调函数
            
        Returns:
            (success, message): 成功标志和消息
        """
        try:
            if method == 'pipx':
                commands = self._get_pipx_commands()
            else:  # pip
                commands = self._get_pip_commands()
            
            for i, cmd in enumerate(commands):
                if callback:
                    callback(f"执行: {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5分钟超时
                )
                
                if callback:
                    if result.stdout:
                        callback(result.stdout)
                    if result.stderr:
                        callback(result.stderr)
                
                # 特殊处理：如果是 brew unlink 失败，继续执行
                if 'brew unlink' in ' '.join(cmd) and result.returncode != 0:
                    if callback:
                        callback("⚠️ brew unlink 失败（可能 pipx 未安装），继续...")
                    continue
                
                # 如果是 pipx 方法的 brew install 失败，尝试降级到 pip
                if method == 'pipx' and 'brew install' in ' '.join(cmd) and result.returncode != 0:
                    if callback:
                        callback("⚠️ brew install 失败，自动切换到 pip 方法...")
                    # 递归调用，使用 pip 方法
                    return self.install_droidrun('pip', callback)
                
                if result.returncode != 0:
                    return False, f"命令失败: {' '.join(cmd)}\n{result.stderr}"
            
            # 安装成功，更新缓存
            self._save_cache({'droidrun_installed': True})
            return True, "安装成功"
        
        except subprocess.TimeoutExpired:
            return False, "安装超时"
        except Exception as e:
            return False, f"安装错误: {str(e)}"
    
    def _get_pipx_commands(self):
        """获取 pipx 安装命令"""
        system = platform.system()
        
        commands = []
        
        # 查找命令的完整路径
        brew_cmd = self._find_command('brew')
        pipx_cmd = self._find_command('pipx')
        python_cmd = self._find_command('python3')
        
        # 检查 pipx 是否已安装
        try:
            subprocess.run([pipx_cmd, '--version'], capture_output=True, check=True, timeout=5)
            has_pipx = True
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            has_pipx = False
        
        if not has_pipx:
            if system == 'Darwin':  # macOS
                # 检查 brew 是否可用
                if os.path.exists(brew_cmd) or brew_cmd == 'brew':
                    # 尝试修复可能的 link 问题
                    commands.append([brew_cmd, 'unlink', 'pipx'])
                    commands.append([brew_cmd, 'install', 'pipx'])
                else:
                    # brew 不可用，使用 pip 安装 pipx
                    # 检测是否为 Homebrew Python
                    is_homebrew = (
                        '/opt/homebrew/' in python_cmd or 
                        '/usr/local/Cellar/' in python_cmd or 
                        'Homebrew' in python_cmd
                    )
                    if is_homebrew:
                        commands.append([python_cmd, '-m', 'pip', 'install', '--break-system-packages', 'pipx'])
                    else:
                        commands.append([python_cmd, '-m', 'pip', 'install', '--user', 'pipx'])
            else:  # Windows 或其他
                commands.append([python_cmd, '-m', 'pip', 'install', '--user', 'pipx'])
            
            commands.append([pipx_cmd, 'ensurepath'])
        
        # 安装 DroidRun（包含主要的 LLM 提供商）
        commands.append([
            pipx_cmd, 'install',
            'droidrun[google,anthropic,openai,deepseek,ollama]'
        ])
        
        # 安装智谱AI支持（需要单独安装）
        commands.append([
            pipx_cmd, 'inject', 'droidrun', 'llama-index-llms-zhipuai'
        ])
        
        return commands
    
    def _get_pip_commands(self):
        """获取 pip 安装命令"""
        # 使用系统的 Python（打包环境中使用 python3）
        python_cmd = self._find_command('python3')
        
        # 检测是否在虚拟环境中
        in_venv = (
            hasattr(sys, 'real_prefix') or  # virtualenv
            (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)  # venv
        )
        
        commands = []
        
        # 检测是否为 Homebrew Python（会遇到 PEP 668 限制）
        is_homebrew_python = False
        try:
            # 方法1: 检查 python_cmd 路径是否包含 Homebrew 特征
            if '/opt/homebrew/' in python_cmd or '/usr/local/Cellar/' in python_cmd or 'Homebrew' in python_cmd:
                is_homebrew_python = True
            else:
                # 方法2: 检查实际的 Python 可执行文件路径
                result = subprocess.run(
                    [python_cmd, '-c', 'import sys; print(sys.executable)'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                executable_path = result.stdout.strip().lower()
                if 'cellar' in executable_path or 'homebrew' in executable_path or '/opt/homebrew/' in executable_path:
                    is_homebrew_python = True
        except:
            # 如果检测失败，假设是 Homebrew（安全的默认值，因为 --break-system-packages 在非 Homebrew 上也能工作）
            if '/opt/homebrew/' in python_cmd or 'brew' in python_cmd.lower():
                is_homebrew_python = True
        
        # 安装 DroidRun（包含主要的 LLM 提供商）
        if in_venv:
            # 虚拟环境中，直接安装
            commands.append([
                python_cmd, '-m', 'pip', 'install',
                'droidrun[google,anthropic,openai,deepseek,ollama]'
            ])
            commands.append([
                python_cmd, '-m', 'pip', 'install',
                'llama-index-llms-zhipuai'
            ])
        elif is_homebrew_python:
            # Homebrew Python 3.11+，使用 --break-system-packages
            # 注意：虽然不推荐，但这是唯一的方法（除了 pipx）
            commands.append([
                python_cmd, '-m', 'pip', 'install', '--break-system-packages',
                'droidrun[google,anthropic,openai,deepseek,ollama]'
            ])
            commands.append([
                python_cmd, '-m', 'pip', 'install', '--break-system-packages',
                'llama-index-llms-zhipuai'
            ])
        else:
            # 其他 Python，使用 --user
            commands.append([
                python_cmd, '-m', 'pip', 'install', '--user',
                'droidrun[google,anthropic,openai,deepseek,ollama]'
            ])
            commands.append([
                python_cmd, '-m', 'pip', 'install', '--user',
                'llama-index-llms-zhipuai'
            ])
        
        return commands

