#!/bin/bash
# 一键打包 DroidRun GUI 为独立可执行文件
cd "$(dirname "$0")"
source ../venv/bin/activate
# 先打包droidrun CLI
./build_droidrun_cli.sh
pyinstaller --noconfirm --onefile --windowed --console \
  --add-data "resources/droidrun-portal-v0.1.1.apk:resources" \
  --add-binary "dist/droidrun:resources" \
  --hidden-import droidrun \
  --hidden-import droidrun.agent.react_agent \
  --hidden-import droidrun.agent.llm_reasoning \
  --hidden-import droidrun.tools.actions \
  --hidden-import droidrun.tools.device \
  --hidden-import droidrun.adb.device \
  --hidden-import droidrun.adb.manager \
  --hidden-import droidrun.adb.wrapper \
  droidrun_gui/gui_main.py 