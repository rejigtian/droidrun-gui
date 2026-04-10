# -*- mode: python ; coding: utf-8 -*-
import site
import os

# 动态解析 site-packages 路径（跨开发者环境通用）
_site_packages = site.getsitepackages()[0]
_droidrun_config = os.path.join(_site_packages, 'droidrun', 'config')
_tiktoken_ext = os.path.join(_site_packages, 'tiktoken_ext')

# 按需添加 datas（路径不存在时跳过，避免构建报错）
_datas = [('resources', 'resources')]
if os.path.exists(_droidrun_config):
    _datas.append((_droidrun_config, 'droidrun/config'))
if os.path.exists(_tiktoken_ext):
    _datas.append((_tiktoken_ext, 'tiktoken_ext'))


a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=_datas,
    hiddenimports=[
        'customtkinter', 'tkinter', 'PIL', 'PIL._tkinter_finder', 'yaml', 'json',
        # DroidRun 0.5.8+
        'droidrun', 'droidrun.config_manager',
        'droidrun.tools.android.portal_client', 'droidrun.portal',
        # ADB (0.5.8 迁移到 async_adbutils)
        'async_adbutils',
        # LiteLLM
        'litellm', 'litellm.utils', 'litellm.main',
        # HTTP
        'httpx', 'httpx._transports.default', 'httpx._transports.asgi',
        # 标准库
        'uuid', 'subprocess', 'asyncio', 'threading', 'multiprocessing',
        'socket', 'ssl', 'http', 'urllib', 'logging', 'pathlib',
        'tempfile', 'shutil', 'zipfile', 'base64', 'hashlib', 'hmac',
        'secrets', 'queue', 'collections', 'datetime', 'time', 're',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pkg_resources', 'torch', 'tensorflow', 'IPython', 'jupyter', 'pytest'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SmartDroid',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['resources/icons/app_icon.png'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SmartDroid',
)
app = BUNDLE(
    coll,
    name='SmartDroid.app',
    icon='resources/icons/app_icon.png',
    bundle_identifier='com.smartdroid.app',
)
