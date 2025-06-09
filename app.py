#!/usr/bin/env python3
"""
YBU 延边大学自动选课代理系统 - Web 界面
提供多用户登录、课程管理和并发抢课功能
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
# 不再需要密码哈希功能
import sqlite3
import asyncio
import time
import uuid
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from agents import (
    BrowserAgent,
    CaptchaSolverAgent,
    # DataManagerAgent,  # 暂时移除
    SchedulerAgent
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ybu_choose_classes_' + str(uuid.uuid4())
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# 全局变量
user_sessions = {}
active_users = {}
executor = ThreadPoolExecutor(max_workers=10)

# 不再需要UserManager，直接使用YBU凭据

class TaskManager:
    """任务管理器"""
    
    def __init__(self):
        self.db_path = "tasks.db"
        self.init_db()
    
    def init_db(self):
        """初始化任务数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS course_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                course_id TEXT NOT NULL,
                course_name TEXT NOT NULL,
                task_type TEXT DEFAULT 'grab',
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_task(self, user_id: str, course_id: str, course_name: str, task_type: str) -> int:
        """创建新任务"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO course_tasks (user_id, course_id, course_name, task_type, status) VALUES (?, ?, ?, ?, 'pending')",
            (user_id, course_id, course_name, task_type)
        )
        
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return task_id
    
    def update_task_status(self, task_id: int, status: str):
        """更新任务状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE course_tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, task_id)
        )
        
        conn.commit()
        conn.close()
    
    def get_user_tasks(self, user_id: str):
        """获取用户任务列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, course_id, course_name, task_type, status, created_at FROM course_tasks WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        
        tasks = []
        for row in cursor.fetchall():
            tasks.append({
                'id': row[0],
                'course_id': row[1],
                'course_name': row[2],
                'task_type': row[3],
                'status': row[4],
                'created_at': row[5]
            })
        
        conn.close()
        return tasks

task_manager = TaskManager()

def run_async_task(coro):
    """在新线程中运行异步任务"""
    def run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    return run

# 路由定义

@app.route('/')
def index():
    """主页"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """YBU直接登录"""
    if request.method == 'POST':
        data = request.json
        ybu_user = data.get('username')  # 前端发送的是YBU学号
        ybu_pass = data.get('password')  # 前端发送的是YBU密码
        
        if not ybu_user or not ybu_pass:
            return jsonify({
                'success': False,
                'message': 'YBU学号和密码不能为空'
            }), 400
        
        # 创建用户会话（使用YBU学号作为用户标识）
        user_id = ybu_user  # 直接使用YBU学号作为用户ID
        session['user_id'] = user_id
        session['username'] = ybu_user
        session['ybu_user'] = ybu_user
        session['ybu_pass'] = ybu_pass
        
        # 存储用户信息（使用用户ID作为键）
        active_users[user_id] = {
            'id': user_id,
            'username': ybu_user,
            'ybu_user': ybu_user,
            'ybu_pass': ybu_pass
        }
        
        # 延迟执行YBU登录任务，让前端先收到响应
        def ybu_login_task():
            """YBU登录任务"""
            try:
                # 创建用户数据目录
                user_data_dir = f"data/user_{user_id}"
                os.makedirs(user_data_dir, exist_ok=True)
                
                # 先保存基本会话信息
                user_sessions[user_id] = {
                    'ybu_user': ybu_user,
                    'ybu_pass': ybu_pass,
                    'last_activity': time.time(),
                    'status': 'connecting'
                }
                
                # 发送连接中状态
                socketio.emit('ybu_login_result', {
                    'success': False,  # 暂时设为False，表示还在连接中
                    'message': '正在初始化浏览器并连接YBU系统...'
                }, room=user_id)
                
                # 延迟执行实际的YBU登录
                def do_actual_login():
                    print(f"[{user_id}] 开始执行YBU登录任务")
                    async def ybu_login_async():
                        try:
                            print(f"[{user_id}] 初始化代理...")
                            
                            # 发送状态更新：正在初始化
                            socketio.emit('ybu_login_result', {
                                'success': False,
                                'message': '正在初始化浏览器代理...'
                            }, room=user_id)
                            
                            # 初始化代理
                            browser_agent = BrowserAgent(headless=True)
                            captcha_solver = CaptchaSolverAgent(mode='ai')
                            # 暂时跳过DataManagerAgent，专注于YBU登录测试
                            # data_manager = DataManagerAgent(db_path=f"{user_data_dir}/ybu_courses.db")
                            
                            # 更新会话信息
                            user_sessions[user_id].update({
                                'browser_agent': browser_agent,
                                'captcha_solver': captcha_solver,
                                # 'data_manager': data_manager,
                                'status': 'logging_in'
                            })
                            
                            print(f"[{user_id}] 启动浏览器...")
                            
                            # 发送状态更新：正在启动浏览器
                            socketio.emit('ybu_login_result', {
                                'success': False,
                                'message': '正在启动浏览器...'
                            }, room=user_id)
                            
                            await browser_agent.start()
                            
                            print(f"[{user_id}] 执行YBU登录...")
                            
                            # 发送状态更新：正在登录YBU
                            socketio.emit('ybu_login_result', {
                                'success': False,
                                'message': '正在登录YBU教务系统...'
                            }, room=user_id)
                            
                            # 执行YBU登录
                            # 首先尝试无验证码登录
                            login_success = await browser_agent.login(ybu_user, ybu_pass)
                            
                            # 如果无验证码登录失败，尝试使用验证码
                            if not login_success:
                                print(f"[{user_id}] 无验证码登录失败，尝试使用验证码...")
                                socketio.emit('ybu_login_result', {
                                    'success': False,
                                    'message': '获取验证码并重试登录...'
                                }, room=user_id)
                                
                                # 获取验证码图片
                                captcha_image = await browser_agent.get_captcha_image()
                                if captcha_image:
                                    # 使用AI识别验证码
                                    captcha_code = captcha_solver.solve_captcha(captcha_image, manual_fallback=False)
                                    if captcha_code:
                                        print(f"[{user_id}] 识别验证码: {captcha_code}")
                                        login_success = await browser_agent.login(ybu_user, ybu_pass, captcha_code)
                                    else:
                                        print(f"[{user_id}] 验证码识别失败")
                                else:
                                    print(f"[{user_id}] 获取验证码图片失败")
                            
                            if login_success:
                                print(f"[{user_id}] YBU登录成功")
                                user_sessions[user_id]['status'] = 'connected'
                                socketio.emit('ybu_login_result', {
                                    'success': True,
                                    'message': 'YBU系统登录成功，可以开始选课了'
                                }, room=user_id)
                            else:
                                print(f"[{user_id}] YBU登录失败")
                                # 如果YBU登录失败，清理会话
                                if user_id in user_sessions:
                                    del user_sessions[user_id]
                                socketio.emit('ybu_login_result', {
                                    'success': False,
                                    'message': 'YBU学号或密码错误，请重新登录'
                                }, room=user_id)
                            
                        except Exception as e:
                            import traceback
                            error_trace = traceback.format_exc()
                            print(f"[{user_id}] YBU登录异常: {str(e)}")
                            print(f"[{user_id}] 详细错误堆栈:\n{error_trace}")
                            # 登录出错，清理会话
                            if user_id in user_sessions:
                                del user_sessions[user_id]
                            socketio.emit('ybu_login_result', {
                                'success': False,
                                'message': f'登录过程中出错：{str(e)}'
                            }, room=user_id)
                    
                    # 在新的事件循环中运行
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(ybu_login_async())
                    finally:
                        loop.close()
                
                # 延迟1秒后执行实际登录
                threading.Timer(1.0, do_actual_login).start()
                
            except Exception as e:
                socketio.emit('ybu_login_result', {
                    'success': False,
                    'message': f'初始化失败：{str(e)}'
                }, room=user_id)
        
        # 在线程池中执行YBU登录任务
        executor.submit(ybu_login_task)
        
        return jsonify({
            'success': True,
            'message': '正在验证YBU凭据，请稍候...',
            'user': {
                'id': user_id,
                'username': ybu_user
            }
        })
    
    return render_template('login.html')



@app.route('/logout')
def logout():
    """用户登出"""
    user_id = session.get('user_id')
    if user_id and user_id in user_sessions:
        del user_sessions[user_id]
    
    if user_id and user_id in active_users:
        del active_users[user_id]
    
    session.clear()
    return redirect(url_for('login'))



@app.route('/api/courses')
def api_courses():
    """获取课程列表API"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    user_id = session['user_id']
    
    if user_id not in user_sessions:
        return jsonify({'success': False, 'message': '请先登录YBU系统'}), 400
    
    async def fetch_courses():
        """获取课程数据"""
        try:
            browser_agent = user_sessions[user_id]['browser_agent']
            courses_data = await browser_agent.fetch_courses()
            
            socketio.emit('courses_data', {
                'success': True,
                'message': '课程数据获取成功',
                'data': courses_data
            }, room=user_id)
            
        except Exception as e:
            socketio.emit('courses_data', {
                'success': False,
                'message': f'获取课程数据失败：{str(e)}',
                'data': None
            }, room=user_id)
    
    executor.submit(run_async_task(fetch_courses()))
    
    return jsonify({
        'success': True,
        'message': '正在获取课程数据，请稍候...'
    })

@app.route('/api/grab_course', methods=['POST'])
def api_grab_course():
    """抢课API"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    data = request.json
    course_id = data.get('course_id')
    course_name = data.get('course_name', f'课程_{course_id}')
    
    if not course_id:
        return jsonify({'success': False, 'message': '课程ID不能为空'}), 400
    
    user_id = session['user_id']
    
    if user_id not in user_sessions:
        return jsonify({'success': False, 'message': '请先登录YBU系统'}), 400
    
    # 创建任务记录
    task_id = task_manager.create_task(user_id, course_id, course_name, 'grab')
    
    async def grab_course():
        """执行抢课"""
        try:
            task_manager.update_task_status(task_id, 'running')
            
            browser_agent = user_sessions[user_id]['browser_agent']
            captcha_solver = user_sessions[user_id]['captcha_solver']
            
            # 检查课程可用性
            availability = await browser_agent.check_course_availability(course_id, False)
            
            if not availability['available']:
                task_manager.update_task_status(task_id, 'failed')
                socketio.emit('grab_course_result', {
                    'task_id': task_id,
                    'course_id': course_id,
                    'course_name': course_name,
                    'success': False,
                    'message': f"课程不可选：{availability.get('reason', '未知原因')}"
                }, room=user_id)
                return
            
            # 获取验证码并选课
            captcha_image = await browser_agent.get_captcha_image()
            if captcha_image:
                captcha_code = captcha_solver.solve_captcha(captcha_image, manual_fallback=False)
                
                if captcha_code:
                    success = await browser_agent.select_course(course_id, False)
                    
                    if success:
                        task_manager.update_task_status(task_id, 'success')
                        socketio.emit('grab_course_result', {
                            'task_id': task_id,
                            'course_id': course_id,
                            'course_name': course_name,
                            'success': True,
                            'message': f"课程 {course_name} 选课成功！"
                        }, room=user_id)
                    else:
                        task_manager.update_task_status(task_id, 'failed')
                        socketio.emit('grab_course_result', {
                            'task_id': task_id,
                            'course_id': course_id,
                            'course_name': course_name,
                            'success': False,
                            'message': "选课失败，可能是网络问题或课程已满"
                        }, room=user_id)
                else:
                    task_manager.update_task_status(task_id, 'failed')
                    socketio.emit('grab_course_result', {
                        'task_id': task_id,
                        'course_id': course_id,
                        'course_name': course_name,
                        'success': False,
                        'message': "验证码识别失败"
                    }, room=user_id)
            else:
                task_manager.update_task_status(task_id, 'failed')
                socketio.emit('grab_course_result', {
                    'task_id': task_id,
                    'course_id': course_id,
                    'course_name': course_name,
                    'success': False,
                    'message': "获取验证码失败"
                }, room=user_id)
                
        except Exception as e:
            task_manager.update_task_status(task_id, 'failed')
            socketio.emit('grab_course_result', {
                'task_id': task_id,
                'course_id': course_id,
                'course_name': course_name,
                'success': False,
                'message': f"抢课过程中出错：{str(e)}"
            }, room=user_id)
    
    executor.submit(run_async_task(grab_course()))
    
    return jsonify({
        'success': True,
        'message': f'已开始抢课任务：{course_name}',
        'task_id': task_id
    })

@app.route('/api/tasks')
def api_tasks():
    """获取用户任务列表API"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    user_id = session['user_id']
    tasks = task_manager.get_user_tasks(user_id)
    
    return jsonify({
        'success': True,
        'data': tasks
    })

# WebSocket事件处理

@socketio.on('connect')
def on_connect():
    """客户端连接"""
    print(f"WebSocket客户端连接: {request.sid}")
    if 'user_id' in session:
        user_id = session['user_id']
        join_room(user_id)
        print(f"用户 {user_id} 加入房间")
        emit('connected', {'message': f'用户 {user_id} 已连接'})
    else:
        print("WebSocket连接但用户未登录")
        emit('connected', {'message': '未登录用户连接'})

@socketio.on('disconnect')
def on_disconnect():
    """客户端断开连接"""
    print(f"WebSocket客户端断开连接: {request.sid}")
    if 'user_id' in session:
        user_id = session['user_id']
        leave_room(user_id)
        print(f"用户 {user_id} 离开房间")

@socketio.on('join_user_room')
def on_join_user_room(data):
    """用户手动加入房间"""
    if 'user_id' in session:
        user_id = session['user_id']
        join_room(user_id)
        print(f"用户 {user_id} 手动加入房间")
        emit('room_joined', {'message': f'已加入房间 {user_id}'})
        
        # 检查是否有pending的登录状态
        if user_id in user_sessions:
            status = user_sessions[user_id].get('status', 'unknown')
            if status == 'connected':
                emit('ybu_login_result', {
                    'success': True,
                    'message': 'YBU系统已连接，可以开始选课了'
                })
            elif status == 'connecting':
                emit('ybu_login_result', {
                    'success': False,
                    'message': '正在连接YBU系统，请稍候...'
                })
        return {'status': 'success'}

if __name__ == '__main__':
    # 从环境变量读取配置
    host = os.getenv('WEB_HOST', '0.0.0.0')
    port = int(os.getenv('WEB_PORT', '5000'))
    debug = os.getenv('WEB_DEBUG', 'false').lower() in ('true', '1', 'yes')
    
    print("🚀 启动 YBU 选课系统 Web 界面...")
    print(f"📱 访问地址：http://localhost:{port}")
    print(f"📱 局域网访问：http://{host}:{port}")
    print("👥 支持多用户并发登录和抢课")
    print(f"🔧 主机地址：{host}")
    print(f"🔧 端口：{port}")
    print(f"🔧 调试模式：{'开启' if debug else '关闭'}")
    
    # 创建必要的目录
    os.makedirs('data', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    socketio.run(app, host=host, port=port, debug=debug) 