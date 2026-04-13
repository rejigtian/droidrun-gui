#!/bin/bash
# macOS 应用签名和公证脚本

APP_PATH="dist/SmartDroid.app"
BUNDLE_ID="com.smartdroid.app"

# 需要配置的变量（从环境变量或 Keychain 获取）
DEVELOPER_ID="${DEVELOPER_ID:-"Developer ID Application: Your Name (TEAM_ID)"}"
APPLE_ID="${APPLE_ID:-"your@email.com"}"
TEAM_ID="${TEAM_ID:-"YOUR_TEAM_ID"}"

echo "🔐 开始签名和公证..."

# 1. 签名所有可执行文件和库
echo "1️⃣ 签名动态库和可执行文件..."
find "$APP_PATH" \( -name "*.dylib" -o -name "*.so" \) -exec codesign --force --timestamp --options runtime --sign "$DEVELOPER_ID" {} \;

# 2. 签名 Python 框架
echo "2️⃣ 签名 Python 框架..."
find "$APP_PATH" -name "Python" -type f -exec codesign --force --timestamp --options runtime --sign "$DEVELOPER_ID" {} \;

# 3. 签名整个应用
echo "3️⃣ 签名应用包..."
codesign --force --deep --timestamp --options runtime --sign "$DEVELOPER_ID" --entitlements entitlements.plist "$APP_PATH"

# 4. 验证签名
echo "4️⃣ 验证签名..."
codesign --verify --deep --strict --verbose=2 "$APP_PATH"

# 5. 创建 ZIP 用于公证
echo "5️⃣ 创建公证用的 ZIP..."
ditto -c -k --keepParent "$APP_PATH" "SmartDroid.zip"

# 6. 上传到 Apple 公证
echo "6️⃣ 上传到 Apple 公证..."
xcrun notarytool submit SmartDroid.zip --apple-id "$APPLE_ID" --team-id "$TEAM_ID" --wait

# 7. 订书钉（Staple）公证票据
echo "7️⃣ 订书钉公证票据..."
xcrun stapler staple "$APP_PATH"

echo "✅ 签名和公证完成！"

