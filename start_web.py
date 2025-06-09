#!/usr/bin/env python3
"""
YBU 选课系统 Web 界面启动脚本
"""

import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def install_dependencies():
    """安装Web应用依赖"""
    print("📦 正在安装Web应用依赖...")
    
    # 安装基础依赖
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
    ])
    
    print("✅ 依赖安装完成")

def check_dependencies():
    """检查依赖是否已安装"""
    try:
        import flask
        import flask_socketio
        return True
    except ImportError:
        return False

def main():
    print("🚀 启动 YBU 选课系统 Web 界面")
    print("=" * 50)
    
    # 检查依赖
    if not check_dependencies():
        print("⚠️ 发现缺少依赖，正在自动安装...")
        try:
            install_dependencies()
        except Exception as e:
            print(f"❌ 依赖安装失败：{e}")
            print("请手动运行：pip install -r requirements.txt")
            return
    
    # 创建必要的目录
    os.makedirs('data', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    print("📂 目录结构已就绪")
    print("🌐 正在启动Web服务器...")
    
    # 从环境变量读取配置
    host = os.getenv('WEB_HOST', '0.0.0.0')
    port = os.getenv('WEB_PORT', '5000')
    
    print(f"📱 访问地址：http://localhost:{port}")
    print(f"📱 局域网访问：http://your-ip:{port}")
    print(f"🔧 主机地址：{host}")
    print(f"🔧 端口：{port}")
    print("🔧 支持多用户并发登录和抢课")
    print("=" * 50)
    
    # 启动应用
    try:
        from app import socketio, app
        
        # 从环境变量读取完整配置
        debug = os.getenv('WEB_DEBUG', 'false').lower() in ('true', '1', 'yes')
        port_int = int(port)
        
        socketio.run(app, host=host, port=port_int, debug=debug)
    except Exception as e:
        print(f"❌ 启动失败：{e}")
        print(f"请检查端口{port}是否被占用")

if __name__ == '__main__':
    main() 