@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
echo YBU 延边大学自动选课代理系统 - Windows 启动脚本

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误：未找到 Python，请先安装 Python 3.8 或更高版本
    pause
    exit /b 1
)

REM 检查Python版本并应用修复
echo 检查 Python 版本和异步兼容性...
python -c "import sys; print(f'Python 版本: {sys.version}'); import platform; print(f'操作系统: {platform.system()} {platform.release()}')"

REM 检查是否有虚拟环境
if not exist "venv" (
    echo 创建虚拟环境...
    python -m venv venv
)

REM 激活虚拟环境
echo 激活虚拟环境...
call venv\Scripts\activate.bat

REM 升级pip
echo 升级 pip...
python -m pip install --upgrade pip

REM 安装Windows专用依赖
echo 安装 Windows 专用依赖...
pip install colorama pywin32

REM 安装依赖
echo 安装依赖包...
pip install -r requirements.txt

REM 安装 Playwright 浏览器
echo 安装 Playwright 浏览器...
playwright install chromium

REM 测试异步兼容性修复
echo 测试异步兼容性修复...
python fix_windows_async.py

REM 检查配置文件
if not exist ".env" (
    echo 复制配置文件...
    copy env.example .env
    echo 请编辑 .env 文件填写您的学号和密码
    notepad .env
)

echo.
echo ====================================
echo 安装完成！已应用 Windows 异步兼容性修复
echo.
echo 🔧 针对您遇到的错误已进行专门优化：
echo   - 禁用了异步资源警告
echo   - 修复了管道传输错误 
echo   - 设置了正确的事件循环策略
echo.
echo 使用方法：
echo   python main.py clean           # 清理旧数据
echo   python main.py login           # 首次登录
echo   python main.py login --clean   # 清理后登录
echo   python main.py list            # 查看课程列表  
echo   python main.py auto-select-all # 智能自动选课
echo.
echo 更多命令请参考 README.md
echo ====================================
echo.

REM 如果提供了命令行参数，直接运行
if "%1"=="" (
    echo 请输入要执行的命令（不含 python main.py）：
    echo 示例: login, list, auto-select-all
    echo 留空直接按回车将退出脚本
    set /p command="命令: "
    if not "!command!"=="" (
        echo 执行: python main.py !command!
        python main.py !command!
    ) else (
        echo 未输入命令，退出脚本
    )
) else (
    echo 执行: python main.py %*
    python main.py %*
)

pause 