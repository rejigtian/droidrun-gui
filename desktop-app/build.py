# -*- coding: utf-8 -*-
"""
构建脚本 - 打包桌面应用

支持平台：
- macOS: 生成 .app 和 .dmg
- Windows: 生成 .exe 和安装包
- Linux: 生成可执行文件

使用方法：
    python build.py
"""

import os
import platform
import subprocess
import sys
import shutil
from pathlib import Path


def check_requirements():
    """检查打包所需工具"""
    print("🔍 检查打包环境...")
    
    # 检查 pyinstaller
    try:
        subprocess.run(['pyinstaller', '--version'], capture_output=True, check=True)
        print("✅ PyInstaller 已安装")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ PyInstaller 未安装")
        print("   安装命令: pip install pyinstaller")
        return False
    
    return True


def clean_build():
    """清理之前的构建文件"""
    print("🧹 清理旧的构建文件...")
    
    dirs_to_clean = ['build', 'dist', '__pycache__']
    files_to_clean = ['*.spec']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            try:
                # 尝试删除目录
                shutil.rmtree(dir_name)
                print(f"   已删除: {dir_name}/")
            except OSError as e:
                # 如果删除失败（目录被占用），给出提示并继续
                print(f"   ⚠️  无法删除 {dir_name}/: {e}")
                print(f"   💡 提示: 请关闭正在运行的应用或手动删除该目录")
                print(f"   可以运行: pkill -f SmartDroid && rm -rf {dir_name}")
                # 不退出，继续尝试清理其他文件
    
    for pattern in files_to_clean:
        for file in Path('.').glob(pattern):
            try:
                file.unlink()
                print(f"   已删除: {file}")
            except OSError:
                print(f"   ⚠️  无法删除: {file}")


def build():
    """构建可执行文件"""
    system = platform.system()
    
    print(f"\n🚀 正在为 {system} 系统构建...")
    
    # 基础命令
    command = [
        'pyinstaller',
        '--name=SmartDroid',
        '--windowed',  # GUI应用，不显示控制台
        '--onedir',    # 打包成目录（macOS 推荐，避免签名问题）
        '--noconfirm', # 覆盖已有文件
        '--exclude-module=pkg_resources',  # 禁用 pkg_resources（避免 jaraco 依赖问题）
    ]
    
    # 隐藏导入（包含所有依赖，确保打包前后行为一致）
    hidden_imports = [
        # UI 相关
        'customtkinter',
        'tkinter',
        'PIL',
        'PIL._tkinter_finder',
        'yaml',
        'json',
        # DroidRun 核心 0.5.8+（打包进应用，保持一致性）
        'droidrun',
        'droidrun.config_manager',
        'droidrun.tools.android.portal_client',
        'droidrun.portal',
        # ADB（0.5.8 迁移到 async_adbutils，不再使用 adbutils）
        'async_adbutils',
        # LiteLLM（0.5.8 使用 litellm 统一 LLM 接口）
        'litellm',
        'litellm.utils',
        'litellm.main',
        # HTTP 客户端
        'httpx',
        'httpx._transports.default',
        'httpx._transports.asgi',
        # 标准库
        'uuid',
        'subprocess',
        'asyncio',
        'threading',
        'multiprocessing',
        'socket',
        'ssl',
        'http',
        'urllib',
        'logging',
        'pathlib',
        'tempfile',
        'shutil',
        'zipfile',
        'base64',
        'hashlib',
        'hmac',
        'secrets',
        'queue',
        'collections',
        'datetime',
        'time',
        're',
    ]
    
    for module in hidden_imports:
        command.append(f'--hidden-import={module}')
    
    # 排除不需要的大型模块（减小包体积）
    # 注意：不能排除 numpy、scipy 等，因为 DroidRun 依赖它们
    exclude_modules = [
        # 大型机器学习库（DroidRun 不直接使用）
        'torch',
        'tensorflow',
        # 开发工具
        'IPython',
        'jupyter',
        'pytest',
    ]
    
    for module in exclude_modules:
        command.append(f'--exclude-module={module}')
    
    # 添加 DroidRun 数据文件（配置、prompts）
    import site
    site_packages = site.getsitepackages()[0]
    droidrun_config = f"{site_packages}/droidrun/config"
    
    if os.path.exists(droidrun_config):
        if system == 'Windows':
            command.append(f'--add-data={droidrun_config};droidrun/config')
        else:
            command.append(f'--add-data={droidrun_config}:droidrun/config')
        print(f"📁 添加 DroidRun 配置文件: {droidrun_config}")
    
    # 添加 tiktoken 数据文件（tokenizer 编码）
    tiktoken_data = f"{site_packages}/tiktoken_ext"
    if os.path.exists(tiktoken_data):
        if system == 'Windows':
            command.append(f'--add-data={tiktoken_data};tiktoken_ext')
        else:
            command.append(f'--add-data={tiktoken_data}:tiktoken_ext')
        print(f"📁 添加 tiktoken 数据文件: {tiktoken_data}")
    
    # 添加应用资源文件（图标等）
    resources_dir = "resources"
    if os.path.exists(resources_dir):
        if system == 'Windows':
            command.append(f'--add-data={resources_dir};resources')
        else:
            command.append(f'--add-data={resources_dir}:resources')
        print(f"🎨 添加应用资源文件: {resources_dir}")
    
    # 如果有图标文件，设置为应用图标
    icon_path = "resources/icons/app_icon.png"
    if os.path.exists(icon_path):
        # macOS 需要 .icns，Windows 需要 .ico
        # PyInstaller 可以从 PNG 自动转换（需要 Pillow）
        if system == 'Darwin':
            # macOS 使用 PNG（PyInstaller 会自动转换为 .icns）
            command.append(f'--icon={icon_path}')
        elif system == 'Windows':
            # Windows 需要 .ico 文件
            ico_path = "resources/icons/app_icon.ico"
            if os.path.exists(ico_path):
                command.append(f'--icon={ico_path}')
            else:
                print("⚠️  Windows .ico 图标未找到，将不设置图标")
        print(f"🖼️  设置应用图标: {icon_path}")
    
    # 系统特定配置
    if system == 'Darwin':  # macOS
        print("📱 配置 macOS 打包...")
        command.extend([
            '--osx-bundle-identifier=com.smartdroid.app',
            # 不使用 codesign-identity，让 PyInstaller 不签名
            # 用户可以稍后手动签名或移除签名验证
        ])
    elif system == 'Windows':
        print("🪟 配置 Windows 打包...")
        # Windows 特定选项
        pass
    elif system == 'Linux':
        print("🐧 配置 Linux 打包...")
        # Linux 特定选项
        pass
    
    # 主程序文件
    command.append('src/main.py')
    
    print(f"\n📝 执行命令:")
    print(f"   {' '.join(command)}")
    
    # 执行构建
    try:
        print("\n⏳ 开始构建（这可能需要几分钟）...\n")
        result = subprocess.run(command, check=True)
        
        print("\n" + "="*60)
        print("✅ 构建成功!")
        print("="*60)
        
        # 显示输出位置
        if system == 'Darwin':
            print(f"\n📦 应用位置: dist/SmartDroid.app/")
            # Homebrew Python 打出来的包带有冲突签名，自动清理
            print("\n🔧 移除签名限制...")
            subprocess.run(['xattr', '-cr', 'dist/SmartDroid.app'], check=False)
            subprocess.run(['codesign', '--remove-signature', 'dist/SmartDroid.app'], check=False)
            print("✅ 签名已清理，可直接双击运行")
            print("\n🚀 运行应用:")
            print("   open dist/SmartDroid.app")
            print("\n💡 创建 DMG 安装包:")
            print("   1. 安装工具: brew install create-dmg")
            print('   2. 创建 DMG: create-dmg \\')
            print('        --volname "SmartDroid" \\')
            print('        --window-pos 200 120 \\')
            print('        --window-size 800 400 \\')
            print('        --icon-size 100 \\')
            print('        --icon "SmartDroid.app" 200 190 \\')
            print('        --hide-extension "SmartDroid.app" \\')
            print('        --app-drop-link 600 185 \\')
            print('        "SmartDroid-Installer.dmg" \\')
            print('        "dist/"')
        elif system == 'Windows':
            print(f"\n📦 程序位置: dist\\SmartDroid.exe")
            print("\n💡 创建安装包:")
            print("   使用 Inno Setup 或 NSIS 创建 Windows 安装程序")
            print("   教程: https://pyinstaller.org/en/stable/usage.html")
        else:
            print(f"\n📦 程序位置: dist/SmartDroid")
            print("\n💡 分发说明:")
            print("   可以直接分发 dist/SmartDroid 文件")
        
        print("\n📋 使用说明:")
        print("   1. 用户需要先安装 ADB (Android Debug Bridge)")
        print("   2. 用户需要在设置中配置 LLM API Key")
        print("   3. Android 设备需要开启 USB 调试")
        
        return True
    
    except subprocess.CalledProcessError as e:
        print("\n" + "="*60)
        print("❌ 构建失败")
        print("="*60)
        print(f"\n错误: {e}")
        print("\n💡 常见问题:")
        print("   1. 确保已安装所有依赖: pip install -r requirements.txt")
        print("   2. 确保已安装 pyinstaller: pip install pyinstaller")
        print("   3. 检查 Python 版本 (推荐 3.9-3.11)")
        return False


if __name__ == '__main__':
    print("="*60)
    print("🎯 SmartDroid 打包工具")
    print("="*60)
    
    # 检查环境
    if not check_requirements():
        sys.exit(1)
    
    # 清理旧文件
    clean_build()
    
    # 执行构建
    success = build()
    
    if success:
        print("\n🎉 打包完成！")
        sys.exit(0)
    else:
        sys.exit(1)

