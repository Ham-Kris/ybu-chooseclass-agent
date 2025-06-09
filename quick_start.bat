@echo off
chcp 65001 >nul
echo YBU 延边大学自动选课代理系统 - 快速启动

REM 激活虚拟环境（如果存在）
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

echo.
echo ====================================
echo 选择要执行的操作：
echo ====================================
echo [1] 清理旧数据
echo [2] 用户登录
echo [3] 清理后登录  
echo [4] 查看课程列表
echo [5] 智能自动选课
echo [6] 查看系统状态
echo [0] 直接输入命令
echo ====================================
echo.

set /p choice="请输入选项编号: "

if "%choice%"=="1" python main.py clean
if "%choice%"=="2" python main.py login
if "%choice%"=="3" python main.py login --clean
if "%choice%"=="4" python main.py list
if "%choice%"=="5" python main.py auto-select-all
if "%choice%"=="6" python main.py status
if "%choice%"=="0" goto custom_command

goto end

:custom_command
echo.
echo 请直接输入 main.py 后面的命令部分
echo 例如: login -u 学号 -p "密码"
echo 例如: auto-select-all --dry-run
set /p cmd="命令: "
python main.py %cmd%

:end
echo.
pause 