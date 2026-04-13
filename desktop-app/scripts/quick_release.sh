#!/bin/bash

# SmartDroid - 一键打包发布脚本
# 使用方法: ./quick_release.sh [版本号]
# 例如: ./quick_release.sh 1.0.0

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 版本号（默认或从参数获取）
VERSION="${1:-1.0.0}"
BUILD_DATE=$(date +%Y%m%d)

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   SmartDroid 一键打包发布工具      ║${NC}"
echo -e "${BLUE}║   版本: v${VERSION}                       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

# 检查是否在正确的目录
if [ ! -f "build.py" ]; then
    echo -e "${RED}❌ 错误: 请在 desktop-app 目录下运行此脚本${NC}"
    exit 1
fi

# 激活虚拟环境（如果存在）
if [ -d "venv" ]; then
    echo "🔧 激活虚拟环境..."
    source venv/bin/activate
fi

# 步骤 0: 关闭可能正在运行的应用（避免文件占用）
echo -e "${YELLOW}🛑 检查并关闭正在运行的应用...${NC}"
if pgrep -f "SmartDroid" > /dev/null; then
    echo "   发现正在运行的应用，正在关闭..."
    pkill -f "SmartDroid" 2>/dev/null || true
    sleep 2  # 等待进程完全退出
    echo -e "${GREEN}   ✅ 应用已关闭${NC}"
else
    echo "   ✅ 没有正在运行的应用"
fi
echo ""

# 步骤 1: 清理并构建
echo -e "${YELLOW}📦 步骤 1/5: 构建应用...${NC}"
python build.py

if [ ! -d "dist/SmartDroid.app" ]; then
    echo -e "${RED}❌ 构建失败${NC}"
    exit 1
fi
echo -e "${GREEN}✅ 构建完成${NC}"
echo ""

# 步骤 2: 修复 macOS 签名
echo -e "${YELLOW}🔐 步骤 2/5: 修复 macOS 签名...${NC}"
if [ -f "fix_macos_app.sh" ]; then
    ./fix_macos_app.sh
    echo -e "${GREEN}✅ 签名修复完成${NC}"
else
    echo -e "${YELLOW}⚠️  fix_macos_app.sh 不存在，跳过签名修复${NC}"
fi
echo ""

# 步骤 3: 创建 ZIP 压缩包
echo -e "${YELLOW}📦 步骤 3/5: 创建 ZIP 压缩包...${NC}"
cd dist
rm -f SmartDroid-*.zip 2>/dev/null || true
zip -r "SmartDroid-${VERSION}-macOS.zip" SmartDroid.app > /dev/null
ZIP_SIZE=$(ls -lh SmartDroid-${VERSION}-macOS.zip | awk '{print $5}')
echo -e "${GREEN}✅ ZIP 创建完成 (${ZIP_SIZE})${NC}"
cd ..
echo ""

# 步骤 4: 创建 DMG（可选）
echo -e "${YELLOW}💿 步骤 4/5: 创建 DMG 安装包...${NC}"
if command -v create-dmg &> /dev/null; then
    # 复制修复脚本到 dist 目录
    if [ -f "修复权限.command" ]; then
        cp "修复权限.command" dist/
        chmod +x dist/修复权限.command
        echo -e "${GREEN}✅ 已添加一键修复脚本${NC}"
    fi
    
    cd dist
    rm -f SmartDroid-*.dmg 2>/dev/null || true
    
    # 创建临时目录用于 DMG 内容
    DMG_TEMP="dmg_temp"
    rm -rf "$DMG_TEMP"
    mkdir -p "$DMG_TEMP"
    
    # 复制应用和修复脚本
    cp -R SmartDroid.app "$DMG_TEMP/"
    if [ -f "修复权限.command" ]; then
        cp "修复权限.command" "$DMG_TEMP/"
    fi
    
    create-dmg \
      --volname "SmartDroid v${VERSION}" \
      --window-pos 200 120 \
      --window-size 800 450 \
      --icon-size 100 \
      --icon "SmartDroid.app" 200 190 \
      --hide-extension "SmartDroid.app" \
      --app-drop-link 600 190 \
      "SmartDroid-${VERSION}-macOS.dmg" \
      "$DMG_TEMP" > /dev/null 2>&1 || true
    
    # 清理临时目录
    rm -rf "$DMG_TEMP"
    
    if [ -f "SmartDroid-${VERSION}-macOS.dmg" ]; then
        DMG_SIZE=$(ls -lh SmartDroid-${VERSION}-macOS.dmg | awk '{print $5}')
        echo -e "${GREEN}✅ DMG 创建完成 (${DMG_SIZE})${NC}"
    else
        echo -e "${YELLOW}⚠️  DMG 创建失败，仅提供 ZIP 版本${NC}"
    fi
    cd ..
else
    echo -e "${YELLOW}⚠️  create-dmg 未安装，跳过 DMG 创建${NC}"
    echo -e "   ${BLUE}安装命令: brew install create-dmg${NC}"
fi
echo ""

# 步骤 5: 生成文档和校验和
echo -e "${YELLOW}📝 步骤 5/5: 生成文档和校验和...${NC}"
cd dist

# 生成校验和
shasum -a 256 SmartDroid-${VERSION}-macOS.* > checksums.txt 2>/dev/null || true
echo -e "${GREEN}✅ 校验和已生成${NC}"

# 创建用户安装文档
cat > 安装说明.txt << 'EOF'
# SmartDroid - 安装指南

## 📥 安装步骤

### macOS 用户

1. **解压文件**
   - 双击 SmartDroid-macOS.dmg（或解压 .zip）

2. **安装应用**
   - 将 SmartDroid.app 拖到 Applications 文件夹

3. **⭐️ 首次运行前必须执行（推荐）**
   
   **方法1：一键修复（最简单）**
   - 双击 DMG 中的 "修复权限.command" 脚本
   - 输入管理员密码
   - 等待修复完成
   - 然后就可以正常打开 SmartDroid 了！
   
   **方法2：右键打开**
   - 右键点击 SmartDroid.app
   - 选择"打开"（不要双击）
   - 点击"打开"确认

4. **可能遇到的问题**

   **问题1：双击无法打开，提示"已损坏"或"无法验证开发者"**
   
   ✅ 最简单的解决方法：
   双击 DMG 中的 "修复权限.command" 脚本
   
   ✅ 或者在终端执行：
   ```bash
   sudo xattr -cr /Applications/SmartDroid.app
   ```
   
   然后再打开应用。

   **问题2：提示"无法验证开发者"**
   
   ✅ 解决方法：
   - 系统设置 > 隐私与安全性
   - 找到并点击"仍要打开"
   
   或者运行 DMG 中的 "修复权限.command" 脚本

5. **开始使用**
   - 首次启动会显示安装向导
   - 按照提示完成 DroidRun 环境配置
   - 连接 Android 设备并开始自动化！

## 🔧 系统要求

- macOS 10.15 (Catalina) 或更高
- 至少 1GB 可用存储空间
- 网络连接（用于下载依赖和访问 LLM API）

## 💡 获取 API Key

### Google Gemini（推荐，免费）
- 访问: https://ai.google.dev/
- 注册并创建 API Key
- 推荐模型: gemini-2.0-flash-exp（每日免费配额充足）

### 智谱AI（国内推荐）
- 访问: https://open.bigmodel.cn/
- 注册并创建 API Key
- 推荐模型: glm-4-plus

## 🆘 获取帮助

- 项目主页: https://github.com/username/droidrun
- 详细文档: 见应用内帮助
- 问题反馈: https://github.com/username/droidrun/issues
EOF

# 创建发布说明
cat > RELEASE_NOTES.txt << RELEASE
# SmartDroid v${VERSION}

发布日期: $(date +%Y-%m-%d)
构建号: ${BUILD_DATE}

## ✨ 主要特性

🎯 **智能自动化**
- 使用自然语言描述任务，AI 自动执行
- 支持复杂的多步骤操作

📱 **设备管理**
- 自动检测连接的 Android 设备
- 实时显示设备状态和 Portal 应用状态

🤖 **多 LLM 支持**
- Google Gemini（推荐，免费）
- 智谱AI（国内优化）
- DeepSeek、Ollama 等

📝 **任务管理**
- 任务历史记录，快速重用
- 内置任务模板，一键执行
- 支持自定义模板

⏹️ **任务控制**
- 实时查看执行日志
- 随时中断正在执行的任务

## 📦 下载文件

- DMG 安装包: SmartDroid-${VERSION}-macOS.dmg (推荐)
- ZIP 压缩包: SmartDroid-${VERSION}-macOS.zip (备选)

## 📋 系统要求

- macOS 10.15 (Catalina) 或更高版本
- Python 3.11+（应用会自动处理）
- ADB（应用会提示安装）

## 🔐 安全校验

SHA-256 校验和见 checksums.txt 文件

## 📖 安装说明

详见 安装说明.txt 文件

## 🐛 已知问题

- 首次运行需要手动"右键 > 打开"以绕过 macOS 安全检查
- 部分 Mac 可能需要手动移除扩展属性（见安装说明）

## 🙏 致谢

感谢所有贡献者和用户的支持！
RELEASE

cd ..

# 显示最终结果
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           🎉 打包完成！                   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📦 分发文件位置:${NC} dist/"
echo ""
echo -e "${BLUE}📄 文件列表:${NC}"
cd dist
ls -lh SmartDroid-${VERSION}-* 安装说明.txt RELEASE_NOTES.txt checksums.txt 2>/dev/null | awk '{printf "   - %-50s %8s\n", $9, $5}'
cd ..
echo ""
echo -e "${BLUE}📝 下一步操作:${NC}"
echo -e "   1️⃣  测试应用:"
echo -e "      ${YELLOW}open dist/SmartDroid.app${NC}"
echo ""
echo -e "   2️⃣  验证安装文档:"
echo -e "      ${YELLOW}cat dist/安装说明.txt${NC}"
echo ""
echo -e "   3️⃣  查看发布说明:"
echo -e "      ${YELLOW}cat dist/RELEASE_NOTES.txt${NC}"
echo ""
echo -e "   4️⃣  上传到 GitHub Releases:"
echo -e "      - 创建 Tag: ${YELLOW}git tag -a v${VERSION} -m \"Release v${VERSION}\"${NC}"
echo -e "      - 推送 Tag: ${YELLOW}git push origin v${VERSION}${NC}"
echo -e "      - 访问: ${YELLOW}https://github.com/username/droidrun/releases/new${NC}"
echo -e "      - 上传 dist/ 目录中的所有文件"
echo ""
echo -e "   5️⃣  分享给用户:"
echo -e "      - 百度网盘/阿里云盘"
echo -e "      - 或直接发送 ZIP/DMG 文件"
echo ""
echo -e "${GREEN}✨ 祝发布顺利！${NC}"

