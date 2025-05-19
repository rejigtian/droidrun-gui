# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['droidrun_gui/gui_main.py'],
    pathex=[],
    binaries=[('dist/droidrun', 'resources')],
    datas=[('resources/droidrun-portal-v0.1.1.apk', 'resources')],
    hiddenimports=['droidrun', 'droidrun.agent.react_agent', 'droidrun.agent.llm_reasoning', 'droidrun.tools.actions', 'droidrun.tools.device', 'droidrun.adb.device', 'droidrun.adb.manager', 'droidrun.adb.wrapper'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='gui_main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
