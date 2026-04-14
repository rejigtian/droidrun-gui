#!/bin/bash

# DroidRun 快速启动脚本
# 帮助用户快速设置和运行 DroidRun

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# 打印横幅
print_banner() {
    echo -e "${GREEN}"
    echo "╔═══════════════════════════════════════╗"
    echo "║                                       ║"
    echo "║        DroidRun 快速启动工具         ║"
    echo "║                                       ║"
    echo "╚═══════════════════════════════════════╝"
    echo -e "${NC}"
}

# 检查 Python 版本
check_python() {
    print_info "检查 Python 版本..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | awk '{print $2}')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
        
        if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
            print_success "Python $PYTHON_VERSION (符合要求 >= 3.11)"
        else
            print_error "Python 版本过低: $PYTHON_VERSION (需要 >= 3.11)"
            exit 1
        fi
    else
        print_error "未找到 Python 3，请先安装 Python 3.11+"
        exit 1
    fi
}

# 检查 ADB
check_adb() {
    print_info "检查 ADB 工具..."
    
    if command -v adb &> /dev/null; then
        ADB_VERSION=$(adb version | head -n 1)
        print_success "ADB 已安装: $ADB_VERSION"
    else
        print_warning "ADB 未安装"
        echo ""
        echo "请安装 ADB:"
        echo "  macOS:   brew install android-platform-tools"
        echo "  Linux:   sudo apt install adb"
        echo "  Windows: 访问 https://developer.android.com/studio/releases/platform-tools"
        echo ""
        read -p "按 Enter 继续，或 Ctrl+C 取消..."
    fi
}

# 检查设备连接
check_devices() {
    print_info "检查设备连接..."
    
    DEVICE_COUNT=$(adb devices | grep -v "List" | grep "device$" | wc -l | tr -d ' ')
    
    if [ "$DEVICE_COUNT" -eq 0 ]; then
        print_warning "未找到连接的设备"
        echo ""
        echo "请确保："
        echo "  1. 设备已通过 USB 连接"
        echo "  2. 已启用 USB 调试"
        echo "  3. 已在设备上授权此计算机"
        echo ""
        read -p "按 Enter 继续，或 Ctrl+C 取消..."
    else
        print_success "找到 $DEVICE_COUNT 个设备"
        adb devices | grep -v "List" | grep "device$" | awk '{print "  - " $1}'
    fi
}

# 检查 DroidRun 安装
check_droidrun() {
    print_info "检查 DroidRun 安装..."
    
    if command -v droidrun &> /dev/null; then
        print_success "DroidRun 已安装"
    else
        print_warning "DroidRun 未安装"
        echo ""
        echo "推荐的安装方式："
        echo "  1. 使用 pipx (推荐 - 适合 CLI 工具)"
        echo "  2. 使用 pip3 --user (用户级安装)"
        echo "  3. 使用虚拟环境"
        echo ""
        read -p "请选择安装方式 (1-3): " install_method
        
        case $install_method in
            1)
                print_info "使用 pipx 安装..."
                if ! command -v pipx &> /dev/null; then
                    print_warning "pipx 未安装，正在安装 pipx..."
                    brew install pipx
                    pipx ensurepath
                fi
                pipx install 'droidrun[google,anthropic,openai,deepseek,ollama]'
                print_success "DroidRun 安装完成"
                print_info "请重启终端或运行: source ~/.zshrc"
                ;;
            2)
                print_info "使用 pip3 --user 安装..."
                pip3 install --user 'droidrun[google,anthropic,openai,deepseek,ollama]'
                print_success "DroidRun 安装完成"
                print_info "如果命令不可用，请确保 ~/.local/bin 在 PATH 中"
                ;;
            3)
                print_info "创建虚拟环境并安装..."
                python3 -m venv ~/droidrun_env
                source ~/droidrun_env/bin/activate
                pip install 'droidrun[google,anthropic,openai,deepseek,ollama]'
                print_success "DroidRun 已安装到虚拟环境"
                print_warning "使用前需要激活虚拟环境: source ~/droidrun_env/bin/activate"
                ;;
            *)
                print_error "无效选项"
                exit 1
                ;;
        esac
    fi
}

# 检查 Portal
check_portal() {
    print_info "检查 Portal 应用..."
    
    DEVICE_COUNT=$(adb devices | grep -v "List" | grep "device$" | wc -l | tr -d ' ')
    
    if [ "$DEVICE_COUNT" -eq 0 ]; then
        print_warning "没有连接的设备，跳过 Portal 检查"
        return
    fi
    
    if droidrun ping &> /dev/null; then
        print_success "Portal 运行正常"
    else
        print_warning "Portal 未安装或未启用"
        echo ""
        read -p "是否现在安装 Portal? (y/n): " setup_choice
        
        if [ "$setup_choice" = "y" ] || [ "$setup_choice" = "Y" ]; then
            print_info "安装 Portal..."
            droidrun setup
            print_success "Portal 安装完成"
        else
            print_warning "Portal 未安装，某些功能可能无法使用"
        fi
    fi
}

# 检查 API 密钥
check_api_keys() {
    print_info "检查 API 密钥..."
    
    HAS_KEY=false
    
    if [ ! -z "$GOOGLE_API_KEY" ]; then
        print_success "Google API Key 已设置"
        HAS_KEY=true
    fi
    
    if [ ! -z "$OPENAI_API_KEY" ]; then
        print_success "OpenAI API Key 已设置"
        HAS_KEY=true
    fi
    
    if [ ! -z "$ANTHROPIC_API_KEY" ]; then
        print_success "Anthropic API Key 已设置"
        HAS_KEY=true
    fi
    
    if [ "$HAS_KEY" = false ]; then
        print_warning "未设置 API 密钥"
        echo ""
        echo "请设置至少一个 LLM 提供商的 API 密钥："
        echo "  export GOOGLE_API_KEY=your-key"
        echo "  export OPENAI_API_KEY=your-key"
        echo "  export ANTHROPIC_API_KEY=your-key"
        echo ""
        read -p "按 Enter 继续..."
    fi
}

# 运行测试任务
run_test() {
    print_info "运行测试任务..."
    echo ""
    
    print_info "执行任务: 打开设置"
    echo ""
    
    if droidrun "打开设置" --steps 10; then
        echo ""
        print_success "测试任务成功！"
    else
        echo ""
        print_error "测试任务失败"
    fi
}

# 显示菜单
show_menu() {
    echo ""
    echo "请选择操作："
    echo "  1. 运行测试任务 (打开设置)"
    echo "  2. 运行基础示例"
    echo "  3. 运行结构化输出示例"
    echo "  4. 运行多设备控制示例"
    echo "  5. 自定义任务"
    echo "  6. 查看文档"
    echo "  7. 退出"
    echo ""
    read -p "请输入选项 (1-7): " menu_choice
    
    case $menu_choice in
        1)
            run_test
            ;;
        2)
            print_info "运行基础示例..."
            python3 examples/basic_example.py
            ;;
        3)
            print_info "运行结构化输出示例..."
            python3 examples/structured_output_example.py
            ;;
        4)
            print_info "运行多设备控制示例..."
            python3 examples/multi_device_example.py
            ;;
        5)
            echo ""
            read -p "请输入任务描述: " custom_task
            print_info "执行任务: $custom_task"
            droidrun "$custom_task"
            ;;
        6)
            print_info "打开文档..."
            if [ -f "使用指南.md" ]; then
                cat 使用指南.md
            else
                print_error "找不到使用指南.md"
            fi
            ;;
        7)
            print_info "退出"
            exit 0
            ;;
        *)
            print_error "无效选项"
            ;;
    esac
    
    echo ""
    read -p "按 Enter 返回菜单..."
    show_menu
}

# 主函数
main() {
    print_banner
    
    echo "正在进行系统检查..."
    echo ""
    
    check_python
    check_adb
    check_devices
    check_droidrun
    check_portal
    check_api_keys
    
    echo ""
    print_success "所有检查完成！"
    
    show_menu
}

# 运行主函数
main

