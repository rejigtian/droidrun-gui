#!/bin/bash
# SmartDroid 启动脚本

cd "$(dirname "$0")"
source venv/bin/activate
python src/main.py

