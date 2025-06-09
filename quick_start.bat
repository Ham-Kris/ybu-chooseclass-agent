@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
echo YBU 延边大学自动选课代理系统 - 快速启动

REM 激活虚拟环境（如果存在）
if exist "venv\Scripts\activate.bat" (
    echo 激活虚拟环境...
    call venv\Scripts\activate.bat
) else (
    echo 警告：未找到虚拟环境，请先运行 start_windows.bat 进行初始化
)

REM 如果提供了命令行参数，直接运行
if not "%1"=="" (
    echo 执行: python main.py %*
    python main.py %*
    pause
    exit /b 0
)

REM 显示快速命令菜单
echo.
echo ====================================
echo 🚀 快速启动菜单
echo ====================================
echo.
echo 请选择要执行的操作：
echo.
echo [1] 登录系统
echo [2] 自定义账号登录
echo [3] 查看课程列表
echo [4] 智能自动选课
echo [5] 模拟自动选课（测试）
echo [6] 查看系统状态
echo [7] 清理旧数据
echo [8] 进入完整交互模式
echo [0] 退出
echo.
set /p choice="请输入选项数字: "

if "!choice!"=="1" (
    python main.py login
) else if "!choice!"=="2" (
    set /p username="请输入学号: "
    set /p password="请输入密码: "
    python main.py login -u !username! -p "!password!"
) else if "!choice!"=="3" (
    python main.py list
) else if "!choice!"=="4" (
    python main.py auto-select-all
) else if "!choice!"=="5" (
    python main.py auto-select-all --dry-run
) else if "!choice!"=="6" (
    python main.py status
) else if "!choice!"=="7" (
    python main.py clean
) else if "!choice!"=="8" (
    call start_windows.bat
    exit /b 0
) else if "!choice!"=="0" (
    echo 感谢使用！
    exit /b 0
) else (
    echo 无效选项，请重新选择
    pause
    goto :EOF
)

echo.
echo 命令执行完毕
pause 