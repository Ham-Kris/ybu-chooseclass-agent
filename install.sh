#!/bin/bash

# YBU选课系统安装脚本

echo "🚀 开始安装YBU选课系统..."

# 检查Python版本
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
required_version="3.8"

if [[ $(echo "$python_version >= $required_version" | bc -l) -eq 1 ]]; then
    echo "✅ Python版本检查通过: $python_version"
else
    echo "❌ Python版本过低: $python_version (需要 >= $required_version)"
    exit 1
fi

# 安装基础依赖
echo "📦 安装依赖..."
pip3 install -r requirements.txt

# 安装Playwright浏览器
echo "🌐 安装Playwright浏览器..."
playwright install chromium

# 创建必要目录
echo "📁 创建必要目录..."
mkdir -p data
mkdir -p logs

echo "✅ 安装完成！"
echo ""
echo "🎯 使用方法："
echo "  Web界面: python3 start_web.py"
echo "  命令行:   python3 main.py login -u 学号 -p \"密码\""
echo ""
echo "�� 更多帮助请查看 README.md" 