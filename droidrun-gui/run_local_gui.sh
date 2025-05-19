#!/bin/bash
# 一键本地运行 DroidRun GUI
cd "$(dirname "$0")"
source ../venv/bin/activate
PYTHONPATH=. python3 droidrun_gui/gui_main.py 