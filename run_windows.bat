@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
echo YBU 延边大学自动选课代理系统 - 简化启动脚本

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误：未找到 Python，请先安装 Python 3.8 或更高版本
    pause
    exit /b 1
)

REM 激活虚拟环境（如果存在）
if exist "venv\Scripts\activate.bat" (
    echo 激活虚拟环境...
    call venv\Scripts\activate.bat
)

echo.
echo ====================================
echo YBU 延边大学自动选课代理系统
echo ====================================
echo.
echo 常用命令：
echo 1. python main.py clean           # 清理旧数据
echo 2. python main.py login           # 首次登录
echo 3. python main.py login --clean   # 清理后登录
echo 4. python main.py list            # 查看课程列表
echo 5. python main.py auto-select-all # 智能自动选课
echo 6. python main.py status          # 查看系统状态
echo.

REM 如果提供了命令行参数，直接运行
if not "%1"=="" (
    echo 执行: python main.py %*
    python main.py %*
    goto :end
)

REM 如果没有参数，显示菜单
:menu
echo 请选择要执行的操作：
echo [1] 清理旧数据 (clean)
echo [2] 用户登录 (login)
echo [3] 清理后登录 (login --clean)
echo [4] 查看课程列表 (list)
echo [5] 智能自动选课 (auto-select-all)
echo [6] 查看系统状态 (status)
echo [7] 自定义命令
echo [0] 退出
echo.
set /p choice="请输入选项编号 (0-7): "

if "%choice%"=="1" (
    python main.py clean
    goto :menu
) else if "%choice%"=="2" (
    python main.py login
    goto :menu
) else if "%choice%"=="3" (
    python main.py login --clean
    goto :menu
) else if "%choice%"=="4" (
    python main.py list
    goto :menu
) else if "%choice%"=="5" (
    python main.py auto-select-all
    goto :menu
) else if "%choice%"=="6" (
    python main.py status
    goto :menu
) else if "%choice%"=="7" (
    set /p custom_cmd="请输入完整命令（不含 python main.py）: "
    if not "!custom_cmd!"=="" (
        python main.py !custom_cmd!
    )
    goto :menu
) else if "%choice%"=="0" (
    echo 退出程序
    goto :end
) else (
    echo 无效选项，请重新选择
    goto :menu
)

:end
pause 