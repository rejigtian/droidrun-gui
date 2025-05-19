#!/bin/bash
# 一键打包 droidrun CLI
cd "$(dirname "$0")"
source ../venv/bin/activate
CLI_PATH=$(python3 -c "import droidrun,os; print(os.path.join(os.path.dirname(droidrun.__file__), 'cli/main.py'))")
pyinstaller --noconfirm --onefile --name droidrun "$CLI_PATH" 