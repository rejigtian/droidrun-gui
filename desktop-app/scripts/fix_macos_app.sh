#!/bin/bash

# macOS 应用签名修复脚本
# 用于移除 Homebrew Python 的问题签名

set -e

APP_PATH="dist/SmartDroid.app"

echo "🔐 修复 macOS 应用签名..."

if [ ! -d "$APP_PATH" ]; then
    echo "❌ 错误: 找不到应用 $APP_PATH"
    exit 1
fi

echo "1️⃣ 移除扩展属性..."
xattr -cr "$APP_PATH" 2>/dev/null || true

echo "2️⃣ 移除现有签名..."
codesign --remove-signature "$APP_PATH" 2>/dev/null || true

# 尝试找到 Python 框架并移除其签名
echo "3️⃣ 移除 Python 框架签名..."
find "$APP_PATH" -name "Python" -type f 2>/dev/null | while read -r python_bin; do
    codesign --remove-signature "$python_bin" 2>/dev/null || true
done

# 移除所有 .dylib 和 .so 文件的签名
echo "4️⃣ 移除动态库签名..."
find "$APP_PATH" \( -name "*.dylib" -o -name "*.so" \) -type f 2>/dev/null | while read -r lib; do
    codesign --remove-signature "$lib" 2>/dev/null || true
done

echo "5️⃣ 重新签名（ad-hoc）..."
codesign --force --deep --sign - "$APP_PATH" 2>/dev/null || true

echo "✅ 签名修复完成"
echo ""
echo "💡 如果仍无法运行，请执行:"
echo "   sudo xattr -d com.apple.quarantine $APP_PATH"

