# 📦 DroidRun Desktop 分发指南

## 📋 目录

1. [快速分发](#快速分发)
2. [创建 DMG 安装包](#创建-dmg-安装包-推荐)
3. [给用户的使用说明](#给用户的使用说明)
4. [Windows 打包](#windows-打包)
5. [版本管理](#版本管理)

---

## 🚀 快速分发

### macOS - ZIP 压缩包（最简单）

```bash
cd desktop-app

# 1. 清理并重新打包
python build.py

# 2. 修复 macOS 签名问题
./fix_macos_app.sh

# 3. 创建分发包
cd dist
zip -r "DroidRun-Desktop-macOS.zip" DroidRun-Desktop.app

# 4. 分发包位置
ls -lh DroidRun-Desktop-macOS.zip
```

**优点**：
- ✅ 快速简单
- ✅ 文件体积小（约 416 MB）
- ✅ 兼容所有 macOS 版本

**缺点**：
- ❌ 不够专业
- ❌ 用户需要手动解压

---

## 💿 创建 DMG 安装包（推荐）

### 方法1：使用 create-dmg（最专业）

#### 1. 安装工具
```bash
brew install create-dmg
```

#### 2. 创建安装背景（可选）
```bash
cd desktop-app/dist

# 创建 DMG 资源目录
mkdir -p dmg-resources

# 添加背景图片（可选，1000x600px）
# cp /path/to/background.png dmg-resources/background.png
```

#### 3. 生成 DMG
```bash
cd desktop-app

# 基础版本（无背景）
create-dmg \
  --volname "DroidRun Desktop" \
  --volicon "dist/DroidRun-Desktop.app/Contents/Resources/icon.icns" \
  --window-pos 200 120 \
  --window-size 800 450 \
  --icon-size 100 \
  --icon "DroidRun-Desktop.app" 200 190 \
  --hide-extension "DroidRun-Desktop.app" \
  --app-drop-link 600 190 \
  "dist/DroidRun-Desktop-macOS.dmg" \
  "dist/DroidRun-Desktop.app"
```

#### 4. 完整版（带背景和自定义布局）
```bash
create-dmg \
  --volname "DroidRun Desktop" \
  --volicon "dist/DroidRun-Desktop.app/Contents/Resources/icon.icns" \
  --background "dmg-resources/background.png" \
  --window-pos 200 120 \
  --window-size 800 450 \
  --icon-size 100 \
  --icon "DroidRun-Desktop.app" 200 190 \
  --hide-extension "DroidRun-Desktop.app" \
  --app-drop-link 600 190 \
  --text-size 12 \
  "dist/DroidRun-Desktop-macOS.dmg" \
  "dist/DroidRun-Desktop.app"
```

### 方法2：使用 hdiutil（系统内置）

```bash
cd desktop-app/dist

# 1. 创建临时 DMG 目录
mkdir -p dmg-temp
cp -R DroidRun-Desktop.app dmg-temp/

# 2. 创建 Applications 链接
ln -s /Applications dmg-temp/Applications

# 3. 生成 DMG
hdiutil create -volname "DroidRun Desktop" \
  -srcfolder dmg-temp \
  -ov -format UDZO \
  DroidRun-Desktop-macOS.dmg

# 4. 清理临时文件
rm -rf dmg-temp

echo "✅ DMG 已创建: dist/DroidRun-Desktop-macOS.dmg"
```

---

## 📖 给用户的使用说明

### 创建用户安装文档

```bash
cd desktop-app
cat > dist/安装说明.txt << 'EOF'
# DroidRun Desktop - 安装指南

## 📥 安装步骤

### macOS 用户

1. **打开 DMG/解压 ZIP**
   - 双击 DroidRun-Desktop-macOS.dmg
   - 或解压 DroidRun-Desktop-macOS.zip

2. **拖动应用到 Applications**
   - 将 DroidRun-Desktop.app 拖到 Applications 文件夹

3. **首次运行**
   - 打开 Applications 文件夹
   - 右键点击 DroidRun-Desktop.app
   - 选择"打开"（不要双击）
   - 点击"打开"确认

4. **可能遇到的问题**

   **问题1：无法打开，提示"已损坏"**
   解决方法：
   ```bash
   xattr -cr /Applications/DroidRun-Desktop.app
   ```

   **问题2：提示"无法验证开发者"**
   解决方法：
   - 系统设置 > 隐私与安全性
   - 点击"仍要打开"

5. **安装引导**
   - 首次启动会显示安装向导
   - 按照提示完成 DroidRun 环境安装
   - 配置 API Key（Google Gemini / 智谱AI）

## 🔧 系统要求

- **操作系统**: macOS 10.15 (Catalina) 或更高
- **Python**: 3.11+ (应用会自动处理)
- **ADB**: 通过 Homebrew 安装（应用会提示）
- **网络**: 需要访问 LLM API

## 📱 Android 设备准备

1. **启用开发者选项**
   - 设置 > 关于手机
   - 连续点击"版本号" 7次

2. **启用 USB 调试**
   - 设置 > 开发者选项
   - 开启"USB 调试"

3. **连接设备**
   - USB 连接电脑
   - 允许 USB 调试授权

## 💡 获取 API Key

### Google Gemini（推荐，免费）
- 访问: https://ai.google.dev/
- 注册并创建 API Key
- 推荐模型: gemini-2.0-flash-exp

### 智谱AI（国内推荐）
- 访问: https://open.bigmodel.cn/
- 注册并创建 API Key
- 推荐模型: glm-4-plus

## 🆘 支持

- 项目主页: https://github.com/username/droidrun
- 文档: https://docs.droidrun.ai
- 问题反馈: https://github.com/username/droidrun/issues

EOF

echo "✅ 用户安装文档已创建"
```

### 创建 README 文件

```bash
cd desktop-app/dist
cat > README.md << 'EOF'
# 🤖 DroidRun Desktop

**AI 驱动的 Android 自动化桌面应用**

## ✨ 特性

- 🎯 **自然语言控制**: 用中文描述任务，AI 自动执行
- 📱 **设备管理**: 自动检测连接的 Android 设备
- 🤖 **多 LLM 支持**: Google Gemini、智谱AI、DeepSeek、Ollama
- 📝 **任务历史**: 保存并快速重用常用任务
- 📋 **任务模板**: 内置常用任务，一键执行
- ⏹️ **任务中断**: 随时停止正在执行的任务

## 🚀 快速开始

1. **安装应用**（参考 `安装说明.txt`）
2. **配置 API Key**（设置页面）
3. **连接设备**（设备管理页面）
4. **执行任务**（任务执行页面）

## 📦 文件说明

- `DroidRun-Desktop.app` - 应用程序
- `安装说明.txt` - 详细安装步骤
- `README.md` - 本文件

## 🆘 常见问题

**Q: 无法打开应用？**
A: 参考 `安装说明.txt` 中的"可能遇到的问题"

**Q: 检测不到设备？**
A: 确保 USB 调试已启用，尝试重新插拔设备

**Q: 任务执行失败？**
A: 检查 API Key 是否正确，确保网络通畅

EOF

echo "✅ README 已创建"
```

---

## 🪟 Windows 打包

### 1. 在 Windows 环境打包

```bash
# 安装依赖
pip install -r requirements.txt
pip install pyinstaller

# 运行打包脚本
python build.py
```

### 2. 创建安装程序（使用 Inno Setup）

#### 安装 Inno Setup
- 下载: https://jrsoftware.org/isdl.php
- 安装后创建 `installer.iss`

```ini
; DroidRun Desktop 安装脚本
[Setup]
AppName=DroidRun Desktop
AppVersion=1.0.0
DefaultDirName={autopf}\DroidRun Desktop
DefaultGroupName=DroidRun Desktop
OutputDir=dist
OutputBaseFilename=DroidRun-Desktop-Setup
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\DroidRun-Desktop\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\DroidRun Desktop"; Filename: "{app}\DroidRun-Desktop.exe"
Name: "{commondesktop}\DroidRun Desktop"; Filename: "{app}\DroidRun-Desktop.exe"

[Run]
Filename: "{app}\DroidRun-Desktop.exe"; Description: "启动 DroidRun Desktop"; Flags: postinstall nowait skipifsilent
```

#### 编译安装程序
```bash
# 使用 Inno Setup Compiler 编译 installer.iss
# 或使用命令行
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

---

## 📊 版本管理

### 创建版本号
```bash
cd desktop-app

# 编辑版本信息
cat > VERSION << 'EOF'
VERSION=1.0.0
BUILD_DATE=$(date +%Y%m%d)
GIT_COMMIT=$(git rev-parse --short HEAD)
EOF
```

### 自动化打包脚本

```bash
cd desktop-app
cat > build_release.sh << 'EOF'
#!/bin/bash

# 读取版本号
source VERSION

echo "🚀 开始构建 DroidRun Desktop v$VERSION"

# 1. 清理旧构建
echo "🧹 清理旧文件..."
python build.py

# 2. 修复签名
echo "🔐 修复 macOS 签名..."
./fix_macos_app.sh

# 3. 创建 ZIP
echo "📦 创建 ZIP 压缩包..."
cd dist
zip -r "DroidRun-Desktop-${VERSION}-macOS.zip" DroidRun-Desktop.app

# 4. 创建 DMG
echo "💿 创建 DMG 安装包..."
if command -v create-dmg &> /dev/null; then
    create-dmg \
      --volname "DroidRun Desktop v$VERSION" \
      --window-pos 200 120 \
      --window-size 800 450 \
      --icon-size 100 \
      --icon "DroidRun-Desktop.app" 200 190 \
      --hide-extension "DroidRun-Desktop.app" \
      --app-drop-link 600 190 \
      "DroidRun-Desktop-${VERSION}-macOS.dmg" \
      "DroidRun-Desktop.app"
else
    echo "⚠️  create-dmg 未安装，跳过 DMG 创建"
    echo "   安装: brew install create-dmg"
fi

# 5. 生成校验和
echo "🔍 生成校验和..."
shasum -a 256 DroidRun-Desktop-${VERSION}-macOS.* > checksums.txt

# 6. 创建发布说明
cat > RELEASE_NOTES.txt << 'RELEASE'
# DroidRun Desktop v${VERSION}

发布日期: $(date +%Y-%m-%d)
构建号: ${GIT_COMMIT}

## 📦 下载

- DMG 安装包: DroidRun-Desktop-${VERSION}-macOS.dmg
- ZIP 压缩包: DroidRun-Desktop-${VERSION}-macOS.zip

## ✨ 新特性

- 🎯 自然语言 Android 自动化
- 📱 智能设备管理
- 🤖 多 LLM 支持
- 📝 任务历史和模板

## 📋 系统要求

- macOS 10.15+
- Python 3.11+（自动安装）
- ADB（自动安装）

## 🔐 安全校验

SHA-256 校验和见 checksums.txt

RELEASE

cd ..

echo ""
echo "✅ 构建完成！"
echo ""
echo "📦 分发文件:"
ls -lh dist/DroidRun-Desktop-${VERSION}-*
echo ""
echo "📝 下一步:"
echo "  1. 测试应用: open dist/DroidRun-Desktop.app"
echo "  2. 上传到发布平台（GitHub Releases）"
echo "  3. 更新文档链接"
EOF

chmod +x build_release.sh
echo "✅ 自动化打包脚本已创建"
```

---

## 📤 发布流程

### 1. GitHub Releases

```bash
# 1. 创建 Git Tag
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0

# 2. 上传到 GitHub Releases
# - 访问: https://github.com/username/droidrun/releases/new
# - 选择 Tag: v1.0.0
# - 上传文件:
#   - DroidRun-Desktop-1.0.0-macOS.dmg
#   - DroidRun-Desktop-1.0.0-macOS.zip
#   - checksums.txt
# - 粘贴 RELEASE_NOTES.txt 内容
```

### 2. 其他分发平台

- **网盘**: 百度网盘、阿里云盘
- **CDN**: AWS S3、Cloudflare R2
- **自建服务器**: Nginx 静态文件服务

---

## 🔍 测试清单

分发前务必测试：

```bash
# macOS 测试清单
□ 在全新 Mac 上测试安装
□ 测试首次运行安装向导
□ 测试设备连接和检测
□ 测试任务执行（至少 3 个任务）
□ 测试历史记录和模板
□ 测试任务中断功能
□ 测试设置页面保存/加载
□ 测试应用崩溃恢复
```

---

## 📚 相关文档

- `README.md` - 项目主文档
- `快速开始.md` - 新用户指南
- `build.py` - 打包脚本
- `fix_macos_app.sh` - macOS 签名修复

---

## 💡 常见问题

### Q: 如何减小分发包体积？

A: 当前约 416 MB，主要来自科学计算库。可以在 `build.py` 中移除不需要的库。

### Q: 如何添加代码签名？

A: 需要 Apple Developer 账号（$99/年）：

```bash
# 签名命令
codesign --force --deep --sign "Developer ID Application: YOUR NAME" \
  dist/DroidRun-Desktop.app

# 公证（Notarization）
xcrun notarytool submit dist/DroidRun-Desktop.dmg \
  --apple-id "your@email.com" \
  --password "app-specific-password" \
  --team-id "TEAM_ID"
```

### Q: 如何创建自动更新？

A: 推荐使用 [Sparkle](https://sparkle-project.org/) 框架。

---

**🎉 现在你可以把应用分享给全世界了！**

