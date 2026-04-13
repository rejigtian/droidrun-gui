#!/bin/bash
# SmartDroid 一键权限修复脚本
# 双击运行此脚本自动修复应用权限

clear
echo "╔════════════════════════════════════════╗"
echo "║      SmartDroid 权限修复工具           ║"
echo "╚════════════════════════════════════════╝"
echo ""

# 查找应用位置
APP_NAME="SmartDroid.app"
APP_PATH=""

# 检查常见位置
if [ -d "/Applications/$APP_NAME" ]; then
    APP_PATH="/Applications/$APP_NAME"
elif [ -d "$(dirname "$0")/$APP_NAME" ]; then
    APP_PATH="$(dirname "$0")/$APP_NAME"
else
    echo "❌ 找不到 $APP_NAME"
    echo ""
    echo "请将此脚本放在与 $APP_NAME 相同的文件夹中"
    echo "或确保应用已安装到 /Applications 文件夹"
    echo ""
    read -p "按回车键退出..." 
    exit 1
fi

echo "✅ 找到应用: $APP_PATH"
echo ""
echo "正在修复权限，可能需要输入管理员密码..."
echo ""

# 移除隔离属性
sudo xattr -cr "$APP_PATH" 2>/dev/null && echo "✅ 已移除隔离属性"

# 移除签名
codesign --remove-signature "$APP_PATH" 2>/dev/null && echo "✅ 已移除签名限制"

# 重新签名（ad-hoc）
codesign --force --deep --sign - "$APP_PATH" 2>/dev/null && echo "✅ 已重新签名"

echo ""
echo "╔════════════════════════════════════════╗"
echo "║      ✅  修复完成！                     ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo "现在可以直接双击运行 SmartDroid 了！"
echo ""
read -p "按回车键退出..." 

