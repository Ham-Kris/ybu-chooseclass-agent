#!/bin/bash

# YBU 选课系统 Web 界面启动脚本 (Linux/macOS)

echo "🚀 启动 YBU 选课系统 Web 界面"
echo "=================================================="

# 检查Python版本
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未找到 Python3，请先安装 Python 3.8+"
    exit 1
fi

# 检查是否在虚拟环境中
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  建议在虚拟环境中运行，继续启动..."
fi

# 创建必要的目录
mkdir -p data
mkdir -p templates
mkdir -p static

# 检查并安装依赖
echo "📦 检查依赖..."
if ! python3 -c "import flask, flask_socketio" 2>/dev/null; then
    echo "📦 安装依赖中..."
    pip3 install -r requirements.txt
    echo "✅ 依赖安装完成"
else
    echo "✅ 依赖已就绪"
fi

# 设置环境变量
export FLASK_ENV=production
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

echo "📂 目录结构已就绪"
echo "🌐 启动Web服务器..."

# 读取环境变量配置
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

WEB_HOST=${WEB_HOST:-0.0.0.0}
WEB_PORT=${WEB_PORT:-5000}

echo "📱 访问地址：http://localhost:${WEB_PORT}"
echo "📱 局域网访问：http://$(hostname -I | awk '{print $1}'):${WEB_PORT}"
echo "🔧 主机地址：${WEB_HOST}"
echo "🔧 端口：${WEB_PORT}"
echo "🔧 支持多用户并发登录和抢课"
echo "=================================================="
echo "按 Ctrl+C 停止服务器"
echo ""

# 启动应用
python3 start_web.py 