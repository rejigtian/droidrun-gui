# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[('/Users/rejig/myproject/droidrun/desktop-app/venv/lib/python3.13/site-packages/droidrun/config', 'droidrun/config'), ('/Users/rejig/myproject/droidrun/desktop-app/venv/lib/python3.13/site-packages/tiktoken_ext', 'tiktoken_ext'), ('resources', 'resources')],
    hiddenimports=['customtkinter', 'tkinter', 'PIL', 'PIL._tkinter_finder', 'yaml', 'json', 'droidrun', 'droidrun.config_manager', 'droidrun.tools.android.portal_client', 'droidrun.portal', 'async_adbutils', 'llama_index', 'llama_index.core', 'llama_index.llms.google_genai', 'llama_index.llms.openai', 'llama_index.llms.anthropic', 'llama_index.llms.deepseek', 'llama_index.llms.ollama', 'llama_index.llms.zhipuai', 'requests', 'urllib3', 'urllib3.exceptions', 'certifi', 'httpx', 'httpx._transports.default', 'httpx._transports.asgi', 'uuid', 'subprocess', 'asyncio', 'threading', 'multiprocessing', 'socket', 'ssl', 'http', 'urllib', 'logging', 'pathlib', 'tempfile', 'shutil', 'zipfile', 'base64', 'hashlib', 'hmac', 'secrets', 'queue', 'collections', 'datetime', 'time', 're'],
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
