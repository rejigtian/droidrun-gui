"""
任务运行器 - 统一使用 Python API（import droidrun）
开发环境和打包环境行为完全一致
"""

import asyncio
import os
import sys
from pathlib import Path
from utils.config import ConfigManager


class TaskRunner:
    """任务运行器类"""

    def __init__(self):
        self.current_task = None

    async def run_task(self, task_description, device_serial=None,
                      enable_vision=False, enable_reasoning=False,
                      callback=None):
        """
        执行任务（统一使用 Python API）

        Args:
            task_description: 任务描述
            device_serial: 设备序列号
            enable_vision: 是否启用视觉功能
            enable_reasoning: 是否启用推理模式
            callback: 日志回调函数

        Returns:
            dict: 执行结果
        """
        try:
            # 导入 droidrun 0.5.8+
            try:
                from droidrun import DroidAgent
                from droidrun.config_manager import (
                    DroidConfig, AgentConfig, DeviceConfig, LLMProfile,
                    FastAgentConfig, ManagerConfig, ExecutorConfig,
                )
            except ImportError as e:
                if callback:
                    callback(f"❌ 无法导入 droidrun: {e}")
                return {
                    'success': False,
                    'reason': f'DroidRun 未安装: {e}',
                    'steps': 0
                }

            if callback:
                callback("正在准备执行环境...")

            # 加载桌面应用配置
            config_manager = ConfigManager()

            # 设置 API Keys 到环境变量（LLMProfile.api_key_source='auto' 会自动读取）
            google_key = config_manager.get('google_api_key', '')
            openai_key = config_manager.get('openai_api_key', '')
            anthropic_key = config_manager.get('anthropic_api_key', '')
            deepseek_key = config_manager.get('deepseek_api_key', '')
            zhipu_key = config_manager.get('zhipu_api_key', '')

            if google_key:
                os.environ['GOOGLE_API_KEY'] = google_key
            if openai_key:
                os.environ['OPENAI_API_KEY'] = openai_key
            if anthropic_key:
                os.environ['ANTHROPIC_API_KEY'] = anthropic_key
            if deepseek_key:
                os.environ['DEEPSEEK_API_KEY'] = deepseek_key
            if zhipu_key:
                os.environ['ZHIPUAI_API_KEY'] = zhipu_key

            # 读取提供商和模型配置
            default_provider = config_manager.get('default_provider', 'GoogleGenAI')
            gemini_model = config_manager.get('gemini_model', 'gemini-1.5-flash')
            zhipu_model = config_manager.get('zhipu_model', 'glm-4-plus')
            max_steps = config_manager.get('max_steps', 15)

            if callback:
                callback(f"正在初始化配置...")
                callback(f"📝 使用提供商: {default_provider}")

            # 将 UI 提供商名映射到 droidrun 模型名
            provider_model_map = {
                'GoogleGenAI': gemini_model,
                'OpenAI': 'gpt-4o',
                'Anthropic': 'claude-sonnet-4-6',
                'DeepSeek': 'deepseek-chat',
                'ZhipuAI': zhipu_model,
                'Ollama': 'llama3.2',
            }
            model_name = provider_model_map.get(default_provider, gemini_model)

            if callback:
                callback(f"🤖 模型: {model_name}")

            # 构建 LLMProfile（直接传 api_key 到 kwargs，避免依赖 droidrun 内置 env 解析）
            profile_kwargs = {}
            if default_provider == 'GoogleGenAI' and google_key:
                profile_kwargs['api_key'] = google_key
            elif default_provider == 'OpenAI' and openai_key:
                profile_kwargs['api_key'] = openai_key
            elif default_provider == 'Anthropic' and anthropic_key:
                profile_kwargs['api_key'] = anthropic_key
            elif default_provider == 'DeepSeek' and deepseek_key:
                profile_kwargs['api_key'] = deepseek_key
            elif default_provider == 'ZhipuAI' and zhipu_key:
                profile_kwargs['api_key'] = zhipu_key
            # Ollama 无需 API Key

            profile = LLMProfile(
                provider=default_provider,
                model=model_name,
                temperature=0.2,
                kwargs=profile_kwargs,
            )

            # 构建 DroidConfig（不再写 YAML 文件）
            agent_cfg = AgentConfig(
                max_steps=max_steps,
                reasoning=enable_reasoning,
                fast_agent=FastAgentConfig(vision=enable_vision),
                manager=ManagerConfig(vision=enable_vision),
                executor=ExecutorConfig(vision=enable_vision),
            )
            device_cfg = DeviceConfig(serial=device_serial) if device_serial else DeviceConfig()

            config = DroidConfig(
                agent=agent_cfg,
                device=device_cfg,
                llm_profiles={
                    'manager': profile,
                    'executor': profile,
                    'fast_agent': profile,
                    'app_opener': profile,
                    'structured_output': profile,
                },
            )

            if callback:
                is_frozen = getattr(sys, 'frozen', False)
                callback(f"🔍 环境: {'打包模式' if is_frozen else '开发模式'}")
                callback("正在创建 AI 代理...")

            agent = DroidAgent(
                goal=task_description,
                config=config,
            )

            if callback:
                callback("正在执行任务...")

            result = await agent.run()

            if callback:
                callback("任务执行完成")

            return {
                'success': result.success,
                'reason': result.reason,
                'steps': result.steps,
            }

        except Exception as e:
            if callback:
                callback(f"错误: {str(e)}")

            return {
                'success': False,
                'reason': str(e),
                'steps': 0
            }
