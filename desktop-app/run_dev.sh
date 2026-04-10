#!/bin/bash
# DroidRun Desktop 开发环境启动脚本
# 使用此脚本运行的效果与打包版本完全一致

cd "$(dirname "$0")"

echo "🚀 启动 DroidRun Desktop (开发模式)"
echo ""
echo "注意: 此模式与打包版本行为完全一致"
echo "      直接通过 Python API (droidrun>=0.5.8) 调用"
echo ""

# 激活虚拟环境
if [ ! -d "venv" ]; then
    echo "⚠️  虚拟环境不存在，创建中..."
    python3 -m venv venv
fi

source venv/bin/activate
echo "✅ 虚拟环境已激活"

# 同步依赖（升级时自动更新，pip 会跳过已是最新的包）
echo "🔄 同步依赖..."
pip install -r requirements.txt -q
echo "✅ 依赖已就绪"

echo ""
echo "▶️  启动应用..."
echo ""

# 设置 PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# 运行应用
python src/main.py

