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

REM 如果提供了命令行参数，直接运行后退出
if not "%1"=="" (
    echo 执行: python main.py %*
    python main.py %*
    pause
    exit /b 0
)

REM 进入交互式命令循环
:main_loop
echo.
echo ====================================
echo 🚀 YBU 自动选课系统 - 交互式控制台
echo ====================================
echo.
echo 常用命令：
echo   1. login              - 登录系统
echo   2. login -u 学号 -p "密码"  - 自定义账号登录  
echo   3. list               - 查看课程列表
echo   4. auto-select-all    - 智能自动选课
echo   5. status             - 查看系统状态
echo   6. clean              - 清理旧数据
echo   7. help               - 查看所有命令
echo   8. exit               - 退出程序
echo.
set /p command="请输入命令（不含 python main.py）: "

REM 处理退出命令
if /i "!command!"=="exit" (
    echo 感谢使用 YBU 自动选课系统！
    pause
    exit /b 0
)

REM 处理帮助命令
if /i "!command!"=="help" (
    echo.
    echo 📖 完整命令列表：
    echo.
    echo 🔐 登录相关：
    echo   login                    - 从配置文件登录
    echo   login -u 学号 -p "密码"    - 自定义账号登录（推荐）
    echo   login --clean            - 清理后登录
    echo.
    echo 📚 课程管理：  
    echo   list                     - 查看课程列表
    echo   list --refresh           - 刷新课程数据
    echo   list --type professional - 只看专业课程
    echo.
    echo 🎯 自动选课：
    echo   auto-select-all          - 智能自动选课
    echo   auto-select-all --dry-run - 模拟运行测试
    echo   auto-select-all --max-courses 3 --course-type professional
    echo.
    echo 🛠️ 系统管理：
    echo   status                   - 查看系统状态
    echo   clean                    - 清理旧数据
    echo   clean --all              - 清理所有数据
    echo.
    echo 更多详细用法请查看 README.md
    echo.
    goto main_loop
)

REM 处理空命令
if "!command!"=="" (
    echo 请输入有效命令，输入 help 查看帮助，输入 exit 退出
    goto main_loop
)

REM 执行命令
echo.
echo ⚡ 执行: python main.py !command!
echo.
python main.py !command!

REM 显示执行结果并询问是否继续
echo.
echo ====================================
echo 命令执行完毕
echo ====================================
echo.
set /p continue="按回车继续操作，输入 exit 退出: "
if /i "!continue!"=="exit" (
    echo 感谢使用 YBU 自动选课系统！
    pause
    exit /b 0
)

REM 回到主循环
goto main_loop 