@echo off
REM DroidRun 快速启动脚本 (Windows)
REM 帮助用户快速设置和运行 DroidRun

setlocal enabledelayedexpansion

:banner
echo.
echo ╔═══════════════════════════════════════╗
echo ║                                       ║
echo ║        DroidRun 快速启动工具         ║
echo ║                                       ║
echo ╚═══════════════════════════════════════╝
echo.

:check_python
echo [INFO] 检查 Python 版本...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未找到 Python，请先安装 Python 3.11+
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [SUCCESS] Python %PYTHON_VERSION% 已安装
echo.

:check_adb
echo [INFO] 检查 ADB 工具...
adb version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] ADB 未安装
    echo.
    echo 请安装 ADB:
    echo   访问 https://developer.android.com/studio/releases/platform-tools
    echo.
    pause
) else (
    echo [SUCCESS] ADB 已安装
    echo.
)

:check_devices
echo [INFO] 检查设备连接...
adb devices 2>nul | find "device" | find /v "List" >nul
if errorlevel 1 (
    echo [WARNING] 未找到连接的设备
    echo.
    echo 请确保：
    echo   1. 设备已通过 USB 连接
    echo   2. 已启用 USB 调试
    echo   3. 已在设备上授权此计算机
    echo.
    pause
) else (
    echo [SUCCESS] 找到连接的设备
    adb devices | find "device" | find /v "List"
    echo.
)

:check_droidrun
echo [INFO] 检查 DroidRun 安装...
droidrun --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] DroidRun 未安装
    echo.
    set /p install_choice="是否现在安装 DroidRun? (y/n): "
    if /i "!install_choice!"=="y" (
        echo [INFO] 安装 DroidRun...
        pip install "droidrun[google,anthropic,openai,deepseek,ollama]"
        echo [SUCCESS] DroidRun 安装完成
    ) else (
        echo [ERROR] DroidRun 未安装，无法继续
        pause
        exit /b 1
    )
) else (
    echo [SUCCESS] DroidRun 已安装
)
echo.

:check_portal
echo [INFO] 检查 Portal 应用...
droidrun ping >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Portal 未安装或未启用
    echo.
    set /p setup_choice="是否现在安装 Portal? (y/n): "
    if /i "!setup_choice!"=="y" (
        echo [INFO] 安装 Portal...
        droidrun setup
        echo [SUCCESS] Portal 安装完成
    ) else (
        echo [WARNING] Portal 未安装，某些功能可能无法使用
    )
) else (
    echo [SUCCESS] Portal 运行正常
)
echo.

:check_api_keys
echo [INFO] 检查 API 密钥...
set HAS_KEY=0

if defined GOOGLE_API_KEY (
    echo [SUCCESS] Google API Key 已设置
    set HAS_KEY=1
)

if defined OPENAI_API_KEY (
    echo [SUCCESS] OpenAI API Key 已设置
    set HAS_KEY=1
)

if defined ANTHROPIC_API_KEY (
    echo [SUCCESS] Anthropic API Key 已设置
    set HAS_KEY=1
)

if !HAS_KEY!==0 (
    echo [WARNING] 未设置 API 密钥
    echo.
    echo 请设置至少一个 LLM 提供商的 API 密钥：
    echo   set GOOGLE_API_KEY=your-key
    echo   set OPENAI_API_KEY=your-key
    echo   set ANTHROPIC_API_KEY=your-key
    echo.
    pause
)
echo.

:menu
echo [SUCCESS] 所有检查完成！
echo.
echo 请选择操作：
echo   1. 运行测试任务 (打开设置)
echo   2. 运行基础示例
echo   3. 运行结构化输出示例
echo   4. 运行多设备控制示例
echo   5. 自定义任务
echo   6. 退出
echo.
set /p menu_choice="请输入选项 (1-6): "

if "%menu_choice%"=="1" goto test_task
if "%menu_choice%"=="2" goto basic_example
if "%menu_choice%"=="3" goto structured_example
if "%menu_choice%"=="4" goto multi_device_example
if "%menu_choice%"=="5" goto custom_task
if "%menu_choice%"=="6" goto exit
echo [ERROR] 无效选项
pause
goto menu

:test_task
echo.
echo [INFO] 运行测试任务...
echo [INFO] 执行任务: 打开设置
echo.
droidrun "打开设置" --steps 10
echo.
pause
goto menu

:basic_example
echo.
echo [INFO] 运行基础示例...
python examples\basic_example.py
echo.
pause
goto menu

:structured_example
echo.
echo [INFO] 运行结构化输出示例...
python examples\structured_output_example.py
echo.
pause
goto menu

:multi_device_example
echo.
echo [INFO] 运行多设备控制示例...
python examples\multi_device_example.py
echo.
pause
goto menu

:custom_task
echo.
set /p custom_task="请输入任务描述: "
echo [INFO] 执行任务: !custom_task!
droidrun "!custom_task!"
echo.
pause
goto menu

:exit
echo [INFO] 退出
exit /b 0

