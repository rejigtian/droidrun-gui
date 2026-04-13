#!/bin/bash

# Gradle Kotlin Multiplatform 插件冲突快速修复脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${BLUE}  Gradle 插件冲突修复工具${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo ""

# 检查是否在项目根目录
if [ ! -f "settings.gradle" ] && [ ! -f "settings.gradle.kts" ]; then
    echo -e "${RED}❌ 错误: 未找到 settings.gradle 或 settings.gradle.kts${NC}"
    echo "请在项目根目录运行此脚本"
    exit 1
fi

echo -e "${YELLOW}🔍 正在诊断问题...${NC}"
echo ""

# 查找所有包含 kotlin.multiplatform 的文件
echo -e "${BLUE}[1/5] 查找插件声明位置...${NC}"
CONFLICTS=$(grep -r "kotlin.multiplatform" . --include="*.gradle" --include="*.gradle.kts" 2>/dev/null | grep -v ".gradle/caches" | wc -l | tr -d ' ')

if [ "$CONFLICTS" -gt 0 ]; then
    echo -e "${YELLOW}   找到 $CONFLICTS 处插件声明${NC}"
    echo ""
    echo -e "${BLUE}   插件声明位置：${NC}"
    grep -r "kotlin.multiplatform" . --include="*.gradle" --include="*.gradle.kts" 2>/dev/null | grep -v ".gradle/caches" | while read -r line; do
        echo -e "   ${YELLOW}$line${NC}"
    done
else
    echo -e "${GREEN}   ✅ 未找到插件声明${NC}"
fi

echo ""

# 查找版本声明
echo -e "${BLUE}[2/5] 查找版本声明...${NC}"
VERSIONS=$(grep -r "version.*2.2.0\|version.*'2.2.0'\|version.*\"2.2.0\"" . --include="*.gradle" --include="*.gradle.kts" 2>/dev/null | grep -v ".gradle/caches" | wc -l | tr -d ' ')

if [ "$VERSIONS" -gt 0 ]; then
    echo -e "${YELLOW}   找到 $VERSIONS 处版本声明${NC}"
    echo ""
    echo -e "${BLUE}   版本声明位置：${NC}"
    grep -r "version.*2.2.0\|version.*'2.2.0'\|version.*\"2.2.0\"" . --include="*.gradle" --include="*.gradle.kts" 2>/dev/null | grep -v ".gradle/caches" | while read -r line; do
        echo -e "   ${YELLOW}$line${NC}"
    done
else
    echo -e "${GREEN}   ✅ 未找到版本声明${NC}"
fi

echo ""

# 检查 settings.gradle
echo -e "${BLUE}[3/5] 检查 settings.gradle 配置...${NC}"
if [ -f "settings.gradle" ]; then
    if grep -q "pluginManagement" settings.gradle; then
        echo -e "${GREEN}   ✅ settings.gradle 包含 pluginManagement${NC}"
    else
        echo -e "${YELLOW}   ⚠️  settings.gradle 缺少 pluginManagement 块${NC}"
    fi
elif [ -f "settings.gradle.kts" ]; then
    if grep -q "pluginManagement" settings.gradle.kts; then
        echo -e "${GREEN}   ✅ settings.gradle.kts 包含 pluginManagement${NC}"
    else
        echo -e "${YELLOW}   ⚠️  settings.gradle.kts 缺少 pluginManagement 块${NC}"
    fi
fi

echo ""

# 提供修复建议
echo -e "${BLUE}[4/5] 修复建议${NC}"
echo ""
echo -e "${YELLOW}建议操作：${NC}"
echo "1. 确保插件版本只在 settings.gradle(.kts) 的 pluginManagement 中声明"
echo "2. 在所有 build.gradle(.kts) 中只使用插件ID，不指定版本"
echo "3. 清理 Gradle 缓存"
echo ""

# 询问是否执行清理
read -p "是否执行清理操作？(y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}[5/5] 执行清理操作...${NC}"
    echo ""
    
    # 停止 Gradle 守护进程
    if command -v ./gradlew &> /dev/null; then
        echo -e "${YELLOW}   停止 Gradle 守护进程...${NC}"
        ./gradlew --stop 2>/dev/null || true
        echo -e "${GREEN}   ✅ 已停止${NC}"
    fi
    
    # 清理项目构建缓存
    if [ -d ".gradle" ]; then
        echo -e "${YELLOW}   清理项目 .gradle 目录...${NC}"
        rm -rf .gradle
        echo -e "${GREEN}   ✅ 已清理${NC}"
    fi
    
    # 清理构建目录
    if [ -d "build" ]; then
        echo -e "${YELLOW}   清理 build 目录...${NC}"
        rm -rf build
        echo -e "${GREEN}   ✅ 已清理${NC}"
    fi
    
    # 清理所有子模块的构建目录
    find . -type d -name "build" -not -path "*/.gradle/*" -exec rm -rf {} + 2>/dev/null || true
    
    echo ""
    echo -e "${GREEN}✅ 清理完成！${NC}"
    echo ""
    echo -e "${BLUE}下一步：${NC}"
    echo "1. 检查并修复 settings.gradle(.kts) 配置"
    echo "2. 检查并修复所有 build.gradle(.kts) 配置"
    echo "3. 运行: ./gradlew clean"
    echo "4. 在 IDE 中同步项目"
else
    echo -e "${YELLOW}跳过清理操作${NC}"
fi

echo ""
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${GREEN}诊断完成！${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}📖 详细解决方案请查看：${NC}"
echo "   docs/guides/gradle-kotlin-multiplatform-plugin-fix.md"
echo ""

