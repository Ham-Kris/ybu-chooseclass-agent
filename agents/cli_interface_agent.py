"""
CLIInterfaceAgent - 命令行界面代理
职责：命令行入口；JSON-Line 日志；.env 持久化配置
命令：
python main.py login            # 首次登录 + Cookie 缓存
python main.py list --term 2025-2026-1
python main.py plan ./rules.yml # 解析偏好规则
python main.py grab CJ000123    # 立即抢课

交互：stdin & 彩色日志；--headful 选项可可视化
"""

import asyncio
import argparse
import json
import yaml
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from dotenv import load_dotenv, set_key
import logging

# 配置 JSON Lines 日志
def setup_json_logger():
    """设置 JSON Lines 格式的日志记录器"""
    logger = logging.getLogger('ybu_agent')
    logger.setLevel(logging.INFO)
    
    # 创建文件处理器
    file_handler = logging.FileHandler('ybu_agent.jsonl', encoding='utf-8')
    
    # 创建自定义格式器
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'level': record.levelname,
                'module': record.module,
                'message': record.getMessage(),
            }
            if hasattr(record, 'course_id'):
                log_entry['course_id'] = record.course_id
            if hasattr(record, 'action'):
                log_entry['action'] = record.action
            return json.dumps(log_entry, ensure_ascii=False)
    
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)
    
    return logger

console = Console()
logger = setup_json_logger()


class CLIInterfaceAgent:
    def __init__(self, env_file: str = ".env"):
        """
        初始化命令行界面代理
        
        Args:
            env_file: 环境配置文件路径
        """
        self.env_file = env_file
        self.config = {}
        self._load_env()
        
        # 代理实例（将由 main.py 注入）
        self.browser_agent = None
        self.captcha_solver = None
        self.data_manager = None
        self.scheduler = None

    def _load_env(self):
        """加载环境配置"""
        load_dotenv(self.env_file)
        
        self.config = {
            'username': os.getenv('YBU_USER', ''),
            'password': os.getenv('YBU_PASS', ''),
            'headless': os.getenv('HEADLESS', 'true').lower() == 'true',
            'ocr_engine': os.getenv('OCR_ENGINE', 'paddle'),
            'proxy': os.getenv('PROXY', ''),
        }

    def _save_env_var(self, key: str, value: str):
        """保存环境变量到 .env 文件"""
        set_key(self.env_file, key, value)
        console.print(f"✅ 已保存 {key} 到配置文件", style="green")

    def set_agents(self, browser_agent, captcha_solver, data_manager, scheduler):
        """
        设置代理实例
        
        Args:
            browser_agent: 浏览器代理
            captcha_solver: 验证码识别代理
            data_manager: 数据管理代理
            scheduler: 调度代理
        """
        self.browser_agent = browser_agent
        self.captcha_solver = captcha_solver
        self.data_manager = data_manager
        self.scheduler = scheduler

    def _setup_argument_parser(self) -> argparse.ArgumentParser:
        """设置参数解析器"""
        parser = argparse.ArgumentParser(
            description="YBU 延边大学自动选课代理系统",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="示例用法：\n"
                   "  python main.py login                    # 登录教务系统\n"
                   "  python main.py list --refresh          # 刷新并显示课程列表\n"
                   "  python main.py grab COURSE_ID          # 选择指定课程\n"
                   "  python main.py auto-select-all         # 自动选择所有可抢课程\n"
                   "  python main.py schedule --add ID       # 添加课程监控\n"
                   "  python main.py status                  # 查看系统状态"
        )
        
        subparsers = parser.add_subparsers(dest='command', help='可用命令')
        
        # 登录命令
        login_parser = subparsers.add_parser('login', help='登录教务系统')
        login_parser.add_argument('--headless', action='store_false', default=True, help='显示浏览器界面')
        login_parser.add_argument('--clean', action='store_true', help='清理旧的cookies和数据库文件后重新登录')
        
        # 列出课程命令
        list_parser = subparsers.add_parser('list', help='列出课程')
        list_parser.add_argument('--refresh', action='store_true', help='从服务器刷新课程数据')
        list_parser.add_argument('--type', choices=['all', 'regular', 'retake'], default='all', help='课程类型')
        list_parser.add_argument('--available-only', action='store_true', help='只显示有名额的课程')
        
        # 抢课命令
        grab_parser = subparsers.add_parser('grab', help='抢指定课程')
        grab_parser.add_argument('course_id', help='课程ID')
        grab_parser.add_argument('--headless', action='store_false', default=True, help='显示浏览器界面')
        
        # 测试选课命令
        test_select_parser = subparsers.add_parser('test-select', help='测试完整选课流程（仅测试，不实际选课）')
        test_select_parser.add_argument('course_id', help='课程ID')
        test_select_parser.add_argument('--headless', action='store_false', default=True, help='显示浏览器界面')
        
        # 自动选择所有可抢课程命令
        auto_select_parser = subparsers.add_parser('auto-select-all', help='自动选择所有可抢课程')
        auto_select_parser.add_argument('--dry-run', action='store_true', help='模拟运行，不实际选课')
        auto_select_parser.add_argument('--max-courses', type=int, default=5, help='最大选课数量（默认5门）')
        auto_select_parser.add_argument('--skip-retakes', action='store_true', help='跳过重修课程')
        auto_select_parser.add_argument('--delay', type=int, default=1, help='选课间隔时间（秒）')
        auto_select_parser.add_argument('--headless', action='store_false', default=True, help='显示浏览器界面')
        auto_select_parser.add_argument('--course-type', choices=['professional', 'public', 'all'], default='all', help='课程类型筛选')
        auto_select_parser.add_argument('--priority-keywords', nargs='+', help='优先选择包含关键词的课程')
        auto_select_parser.add_argument('--exclude-keywords', nargs='+', help='排除包含关键词的课程')
        auto_select_parser.add_argument('--min-slots', type=int, default=1, help='最少剩余名额要求')
        auto_select_parser.add_argument('--refresh-data', action='store_true', help='选课前先刷新课程数据')
        
        # 调度任务命令
        schedule_parser = subparsers.add_parser('schedule', help='管理调度任务')
        schedule_subparsers = schedule_parser.add_subparsers(dest='schedule_action', help='调度操作')
        
        add_parser = schedule_subparsers.add_parser('add', help='添加课程监控')
        add_parser.add_argument('course_id', help='课程ID')
        add_parser.add_argument('--interval', type=int, default=30, help='检查间隔（秒）')
        
        remove_parser = schedule_subparsers.add_parser('remove', help='移除课程监控')
        remove_parser.add_argument('course_id', help='课程ID')
        
        schedule_subparsers.add_parser('list', help='列出所有监控任务')
        schedule_subparsers.add_parser('start', help='启动调度器')
        schedule_subparsers.add_parser('stop', help='停止调度器')
        
        # 状态命令
        subparsers.add_parser('status', help='查看系统状态')
        
        # 清理命令
        clean_parser = subparsers.add_parser('clean', help='清理旧的cookies和数据库文件')
        clean_parser.add_argument('--all', action='store_true', help='清理所有数据文件（包括日志）')
        
        return parser

    async def run(self, args: List[str] = None) -> None:
        """运行CLI界面"""
        try:
            parser = self._setup_argument_parser()
            parsed_args = parser.parse_args(args)
            
            # 处理命令
            if parsed_args.command == 'login':
                await self._handle_login(parsed_args)
            elif parsed_args.command == 'list':
                await self._handle_list(parsed_args)
            elif parsed_args.command == 'grab':
                await self._handle_grab(parsed_args)
            elif parsed_args.command == 'auto-select-all':
                await self._handle_auto_select_all(parsed_args)
            elif parsed_args.command == 'schedule':
                await self._handle_schedule(parsed_args)
            elif parsed_args.command == 'status':
                await self._handle_status(parsed_args)
            elif parsed_args.command == 'scheduler':
                await self._handle_scheduler(parsed_args)
            elif parsed_args.command == 'test-select':
                await self._handle_test_select(parsed_args)
            elif parsed_args.command == 'clean':
                await self._handle_clean(parsed_args)
            else:
                await self._show_help()
                
        except KeyboardInterrupt:
            console.print("\n❌ 用户中断操作", style="red")
        except Exception as e:
            console.print(f"❌ 操作失败：{e}", style="red")
            logger.error(f"CLI operation failed: {e}", exc_info=True)

    async def _handle_login(self, args: argparse.Namespace):
        """处理登录命令"""
        console.print(Panel("🔐 登录延边大学教务系统", style="blue"))
        
        # 检查是否需要强制清理
        force_clean = getattr(args, 'clean', False)
        
        if force_clean:
            await self._clean_old_data()
        
        # 获取用户名和密码
        username = self.config.get('username')
        password = self.config.get('password')
        
        if not username:
            username = Prompt.ask("请输入学号")
            self._save_env_var('YBU_USER', username)
        
        if not password:
            password = Prompt.ask("请输入密码", password=True)
            if Confirm.ask("是否保存密码到配置文件？"):
                self._save_env_var('YBU_PASS', password)
        
        # 启动浏览器代理
        await self.browser_agent.start()
        
        try:
            # 首先检查已有的 cookies 是否有效
            if not force_clean and await self._check_existing_session():
                console.print("✅ 已有有效登录状态，无需重新登录", style="green")
                return
            
            # 如果 cookies 无效，清理旧数据并重新登录
            console.print("🧹 清理旧的登录状态...", style="yellow")
            await self._clean_old_data()
            
            # 重新启动浏览器以使用清理后的状态
            await self.browser_agent.stop()
            await self.browser_agent.start()
            
            # 获取验证码
            captcha_image = await self.browser_agent.get_captcha_image()
            captcha_code = ""
            
            if captcha_image:
                console.print("🖼️ 正在处理验证码...", style="blue")
                captcha_code = self.captcha_solver.solve_captcha(captcha_image, manual_fallback=True)
            
            # 尝试登录
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("正在登录...", total=None)
                success = await self.browser_agent.login(username, password, captcha_code)
            
            if success:
                console.print("✅ 登录成功！", style="green")
                logger.info("Login successful", extra={'action': 'login'})
            else:
                console.print("❌ 登录失败，建议使用 --clean 参数重试", style="red")
                console.print("💡 使用方法：python main.py login --clean", style="blue")
                logger.warning("Login failed", extra={'action': 'login'})
                
        except Exception as e:
            console.print(f"❌ 登录过程中出错：{e}", style="red")
            console.print("💡 建议使用 --clean 参数清理旧数据后重试", style="blue")
        finally:
            await self.browser_agent.stop()

    async def _check_existing_session(self) -> bool:
        """检查已有的登录会话是否有效"""
        try:
            # 尝试访问需要认证的页面
            test_url = f"{self.browser_agent.base_url}/jsxsd/framework/xsMain.jsp"
            response = await self.browser_agent.page.goto(test_url, wait_until="networkidle", timeout=10000)
            
            # 检查是否被重定向到登录页面
            current_url = self.browser_agent.page.url
            if "login" in current_url.lower() or response.status == 401:
                return False
            
            # 检查页面内容是否包含用户信息
            content = await self.browser_agent.page.content()
            if "退出系统" in content or "学生姓名" in content:
                return True
            
            return False
        except Exception:
            return False

    async def _clean_old_data(self):
        """清理旧的cookies和数据库文件"""
        import os
        
        files_to_clean = [
            "cookies.json",
            "ybu_courses.db",
            "courses.db"  # 可能的旧数据库文件名
        ]
        
        cleaned_files = []
        for file_path in files_to_clean:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    cleaned_files.append(file_path)
                except Exception as e:
                    console.print(f"⚠️ 无法删除文件 {file_path}: {e}", style="yellow")
        
        if cleaned_files:
            console.print(f"🧹 已清理文件：{', '.join(cleaned_files)}", style="blue")
        else:
            console.print("🧹 无需清理旧文件", style="blue")

    async def _handle_clean(self, args: argparse.Namespace):
        """处理清理命令"""
        console.print(Panel("🧹 清理系统数据", style="blue"))
        
        import os
        
        if args.all:
            # 清理所有数据文件
            files_to_clean = [
                "cookies.json",
                "ybu_courses.db", 
                "courses.db",
                "ybu_agent.jsonl",
                "temp_captcha.jpg",
                "processed_captcha.jpg",
                "debug_xklc_view.html",
                "debug_course_page.html"
            ]
        else:
            # 只清理登录相关文件
            files_to_clean = [
                "cookies.json",
                "ybu_courses.db",
                "courses.db"
            ]
        
        cleaned_files = []
        for file_path in files_to_clean:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    cleaned_files.append(file_path)
                except Exception as e:
                    console.print(f"⚠️ 无法删除文件 {file_path}: {e}", style="yellow")
        
        if cleaned_files:
            console.print(f"✅ 已清理文件：{', '.join(cleaned_files)}", style="green")
            console.print("💡 现在可以运行 'python main.py login' 重新登录", style="blue")
        else:
            console.print("🧹 无文件需要清理", style="yellow")

    async def _handle_list(self, args: argparse.Namespace):
        """处理课程列表命令"""
        console.print(Panel("📚 课程列表", style="blue"))
        
        if args.refresh or not self.data_manager.get_available_courses().shape[0]:
            # 刷新课程数据
            await self.browser_agent.start()
            try:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task("正在获取课程数据...", total=None)
                    courses_data = await self.browser_agent.fetch_courses()
                
                # 保存到数据库
                self.data_manager.save_courses(courses_data)
                
            finally:
                await self.browser_agent.stop()
        
        # 显示课程列表
        courses_df = self.data_manager.get_available_courses(
            course_type=args.type
        )
        
        if not courses_df.empty:
            self.data_manager.display_courses_table(courses_df)
        else:
            console.print("📚 暂无课程数据", style="yellow")
        
        logger.info(f"Listed {len(courses_df)} courses", 
                   extra={'action': 'list', 'course_type': args.type})

    async def _handle_plan(self, args: argparse.Namespace):
        """处理选课规划命令"""
        console.print(Panel("📋 选课规划", style="blue"))
        
        # 加载规则文件
        try:
            with open(args.rules_file, 'r', encoding='utf-8') as f:
                if args.rules_file.endswith('.yml') or args.rules_file.endswith('.yaml'):
                    rules = yaml.safe_load(f)
                else:
                    rules = json.load(f)
        except Exception as e:
            console.print(f"❌ 加载规则文件失败：{e}", style="red")
            return
        
        # 生成选课计划
        recommendations = self.data_manager.plan_course_selection(rules)
        
        if recommendations:
            table = Table(title="选课推荐")
            table.add_column("优先级", style="cyan")
            table.add_column("课程名称", style="green")
            table.add_column("课程类型", style="blue")
            table.add_column("课程ID", style="yellow")
            
            for rec in recommendations[:10]:  # 显示前10个推荐
                table.add_row(
                    f"{rec['priority']:.1f}",
                    rec['course_name'][:30] + "..." if len(rec['course_name']) > 30 else rec['course_name'],
                    rec['course_type'],
                    rec['course_id'][:15] + "..." if len(rec['course_id']) > 15 else rec['course_id']
                )
            
            console.print(table)
            
            # 询问是否设置自动选课
            if Confirm.ask("是否为推荐课程设置自动选课？"):
                course_ids = [rec['course_id'] for rec in recommendations[:5]]
                await self.scheduler.add_auto_enrollment_job(course_ids)
        else:
            console.print("📋 未找到符合条件的课程", style="yellow")
        
        logger.info(f"Generated {len(recommendations)} recommendations", 
                   extra={'action': 'plan'})

    async def _handle_grab(self, args: argparse.Namespace):
        """处理抢课命令"""
        console.print(Panel(f"🎯 抢课：{args.course_id}", style="blue"))
        
        # 启动浏览器
        await self.browser_agent.start()
        
        try:
            # 检查课程可用性
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("检查课程可用性...", total=None)
                
                # 需要确定课程类型，这里简化处理
                availability = await self.browser_agent.check_course_availability(
                    args.course_id, False  # 默认为普通选课
                )
            
            if not availability['available']:
                console.print("❌ 课程暂无名额", style="red")
                return
            
            console.print(f"✅ 课程有 {availability['total_remaining']} 个名额", style="green")
            
            # 验证码现在在 select_course 方法内部处理
            
            # 尝试选课
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("正在选课...", total=None)
                
                success = await self.browser_agent.select_course(
                    args.course_id,
                    False  # 默认为普通选课
                )
            
            if success:
                console.print("✅ 选课成功！", style="green")
                # 记录选课成功
                best_jx0404id = availability.get('best_class', {}).get('jx0404id', '') if availability.get('best_class') else ''
                self.data_manager.save_enrollment_record(
                    args.course_id, best_jx0404id, 'enroll', 'success'
                )
            else:
                console.print("❌ 选课失败", style="red")
                best_jx0404id = availability.get('best_class', {}).get('jx0404id', '') if availability.get('best_class') else ''
                self.data_manager.save_enrollment_record(
                    args.course_id, best_jx0404id, 'enroll', 'failed'
                )
                
        finally:
            await self.browser_agent.stop()
        
        logger.info(f"Grab attempt for course {args.course_id}", 
                   extra={'action': 'grab', 'course_id': args.course_id})

    async def _handle_auto_select_all(self, args: argparse.Namespace):
        """处理自动选择所有可抢课程命令"""
        console.print(Panel("🚀 自动选择所有可抢课程", style="blue"))
        
        # 启动浏览器
        await self.browser_agent.start()
        
        try:
            # 自动登录
            console.print("🔐 正在自动登录...", style="blue")
            username = self.config.get('username')
            password = self.config.get('password')
            
            if not username or not password:
                console.print("❌ 用户名或密码未配置，请先运行 login 命令", style="red")
                return
            
            # 获取验证码并登录
            captcha_image = await self.browser_agent.get_captcha_image()
            captcha_code = ""
            if captcha_image:
                captcha_code = self.captcha_solver.solve_captcha(captcha_image, manual_fallback=True)
            
            login_success = await self.browser_agent.login(username, password, captcha_code)
            if not login_success:
                console.print("❌ 自动登录失败", style="red")
                return
            
            console.print("✅ 登录成功", style="green")
            
            # 刷新课程数据（如果需要）
            if args.refresh_data:
                console.print("🔄 正在刷新课程数据...", style="blue")
                courses_data = await self.browser_agent.fetch_courses()
                self.data_manager.save_courses(courses_data)
            
            # 获取课程列表并应用筛选
            course_type = None if args.course_type == 'all' else args.course_type
            courses_df = self.data_manager.get_available_courses(course_type=course_type)
            
            if courses_df.empty:
                console.print("❌ 数据库中无课程数据，请先运行 list --refresh", style="red")
                return
            
            # 应用关键词筛选
            courses_df = self._apply_course_filters(courses_df, args)
            
            if courses_df.empty:
                console.print("❌ 筛选后无符合条件的课程", style="red")
                return
            
            # 按优先级排序课程
            courses_df = self._prioritize_courses(courses_df, args)
            
            # 统计信息
            total_courses = len(courses_df)
            attempted_courses = 0
            successful_courses = 0
            failed_courses = 0
            skipped_courses = 0
            
            console.print(f"📚 筛选后共找到 {total_courses} 门课程", style="blue")
            if args.max_courses > 0:
                console.print(f"🎯 最多选择 {args.max_courses} 门课程", style="blue")
            
            # 创建结果表格
            results_table = Table(title="自动选课结果")
            results_table.add_column("序号", style="cyan")
            results_table.add_column("课程名称", style="green")
            results_table.add_column("课程类型", style="blue")
            results_table.add_column("剩余名额", style="yellow")
            results_table.add_column("选课结果", style="magenta")
            
            # 遍历所有课程
            for idx, course in courses_df.iterrows():
                # 取消最大选课数量限制检查
                # if attempted_courses >= args.max_courses:
                #     console.print(f"⏹️ 已达到最大选课数量限制：{args.max_courses}", style="yellow")
                #     break
                
                # 解析课程详情
                try:
                    details = json.loads(course['details']) if course['details'] else {}
                    is_retake = details.get('is_retake', False)
                    
                    # 跳过重修课程（如果设置了跳过选项）
                    if args.skip_retakes and is_retake:
                        console.print(f"⏭️ 跳过重修课程：{course['name']}", style="dim")
                        skipped_courses += 1
                        results_table.add_row(
                            str(idx + 1),
                            course['name'][:25] + "..." if len(course['name']) > 25 else course['name'],
                            "重修" if is_retake else "普通",
                            "N/A",
                            "已跳过"
                        )
                        continue
                    
                    # 如果设置了最大课程数限制且不是模拟模式，则检查限制
                    if not args.dry_run and args.max_courses > 0 and successful_courses >= args.max_courses:
                        console.print(f"⏹️ 已成功选中 {args.max_courses} 门课程，达到设定目标", style="yellow")
                        break
                    
                    console.print(f"\n🔍 正在检查课程 {attempted_courses + 1}：{course['name']}", style="blue")
                    
                    # 检查课程可用性
                    availability = await self.browser_agent.check_course_availability(
                        course['id'], is_retake
                    )
                    
                    remaining = availability.get('total_remaining', 0)
                    
                    # 检查是否满足最少名额要求
                    if availability['available'] and remaining >= args.min_slots:
                        console.print(f"✅ 课程有名额：{remaining} 个", style="green")
                        
                        if args.dry_run:
                            console.print("🔄 模拟模式：跳过实际选课", style="yellow")
                            results_table.add_row(
                                str(idx + 1),
                                course['name'][:25] + "..." if len(course['name']) > 25 else course['name'],
                                "重修" if is_retake else "普通",
                                str(remaining),
                                "模拟成功"
                            )
                            successful_courses += 1
                        else:
                            # 实际选课
                            console.print("🎯 开始选课...", style="blue")
                            success = await self.browser_agent.select_course(course['id'], is_retake)
                            
                            if success:
                                console.print("🎉 选课成功！", style="green")
                                successful_courses += 1
                                result_text = "成功"
                                # 记录成功
                                best_jx0404id = availability.get('best_class', {}).get('jx0404id', '') if availability.get('best_class') else ''
                                self.data_manager.save_enrollment_record(
                                    course['id'], best_jx0404id, 'enroll', 'success'
                                )
                            else:
                                console.print("❌ 选课失败", style="red")
                                failed_courses += 1
                                result_text = "失败"
                                # 记录失败
                                best_jx0404id = availability.get('best_class', {}).get('jx0404id', '') if availability.get('best_class') else ''
                                self.data_manager.save_enrollment_record(
                                    course['id'], best_jx0404id, 'enroll', 'failed'
                                )
                            
                            results_table.add_row(
                                str(idx + 1),
                                course['name'][:25] + "..." if len(course['name']) > 25 else course['name'],
                                "重修" if is_retake else "普通",
                                str(remaining),
                                result_text
                            )
                            
                            # 选课间隔
                            if args.delay > 0:
                                console.print(f"⏳ 等待 {args.delay} 秒...", style="dim")
                                import time
                                time.sleep(args.delay)
                    else:
                        console.print("❌ 课程无名额", style="red")
                        results_table.add_row(
                            str(idx + 1),
                            course['name'][:25] + "..." if len(course['name']) > 25 else course['name'],
                            "重修" if is_retake else "普通",
                            "0",
                            "无名额"
                        )
                        skipped_courses += 1
                    
                    attempted_courses += 1
                    
                except Exception as e:
                    console.print(f"❌ 处理课程时出错：{e}", style="red")
                    failed_courses += 1
                    results_table.add_row(
                        str(idx + 1),
                        course['name'][:25] + "..." if len(course['name']) > 25 else course['name'],
                        "未知",
                        "N/A",
                        "错误"
                    )
                    continue
            
            # 显示结果
            console.print("\n" + "="*60, style="blue")
            console.print(results_table)
            
            # 显示统计信息
            summary_table = Table(title="选课统计")
            summary_table.add_column("项目", style="cyan")
            summary_table.add_column("数量", style="green")
            
            summary_table.add_row("总课程数", str(total_courses))
            summary_table.add_row("检查课程数", str(attempted_courses))
            summary_table.add_row("成功选课", str(successful_courses))
            summary_table.add_row("选课失败", str(failed_courses))
            summary_table.add_row("跳过课程", str(skipped_courses))
            
            console.print(summary_table)
            
            if successful_courses > 0:
                console.print(f"🎉 自动选课完成！成功选中 {successful_courses} 门课程", style="green")
            else:
                console.print("😔 未能成功选中任何课程", style="yellow")
            
        except Exception as e:
            console.print(f"❌ 自动选课过程中出错：{e}", style="red")
            import traceback
            traceback.print_exc()
            
        finally:
            await self.browser_agent.stop()
        
        logger.info(f"Auto select all completed: {successful_courses} successful, {failed_courses} failed", 
                   extra={'action': 'auto_select_all', 'successful': successful_courses, 'failed': failed_courses})

    async def _handle_status(self, args: argparse.Namespace):
        """处理状态查询命令"""
        console.print(Panel("📊 系统状态", style="blue"))
        
        # 显示配置信息
        config_table = Table(title="配置信息")
        config_table.add_column("配置项", style="cyan")
        config_table.add_column("值", style="green")
        
        config_table.add_row("用户名", self.config.get('username', '未设置'))
        config_table.add_row("密码", "已设置" if self.config.get('password') else "未设置")
        config_table.add_row("浏览器模式", "有头" if not self.config.get('headless') else "无头")
        config_table.add_row("OCR引擎", self.config.get('ocr_engine', 'paddle'))
        
        console.print(config_table)
        
        # 显示数据库信息
        courses_df = self.data_manager.get_available_courses()
        console.print(f"\n📚 数据库中共有 {len(courses_df)} 门课程")
        
        # 显示选课历史
        history_df = self.data_manager.get_enrollment_history(days=7)
        if not history_df.empty:
            console.print(f"📝 最近7天有 {len(history_df)} 条选课记录")
        
        # 显示调度器状态
        if self.scheduler:
            self.scheduler.display_jobs_status()

    async def _handle_scheduler(self, args: argparse.Namespace):
        """处理调度器命令"""
        if args.scheduler_action == 'start':
            await self.scheduler.start()
        elif args.scheduler_action == 'stop':
            await self.scheduler.stop()
        elif args.scheduler_action == 'status':
            self.scheduler.display_jobs_status()
        elif args.scheduler_action == 'auto':
            await self.scheduler.add_auto_enrollment_job(
                args.course_ids, 
                args.interval
            )

    async def _handle_test_select(self, args: argparse.Namespace):
        """处理测试选课命令"""
        console.print(Panel("🔍 测试选课流程", style="blue"))
        
        # 启动浏览器
        await self.browser_agent.start()
        
        try:
            console.print("⚠️ 跳过API检查，直接测试页面选课流程", style="yellow")
            
            # 直接测试选课流程
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("正在测试选课流程...", total=None)
                
                success = await self.browser_agent.select_course(
                    args.course_id,
                    False  # 默认为普通选课
                )
            
            if success:
                console.print("✅ 选课测试成功！", style="green")
                # 记录选课成功
                self.data_manager.save_enrollment_record(
                    args.course_id, '', 'test', 'success'
                )
            else:
                console.print("❌ 选课测试失败", style="red")
                self.data_manager.save_enrollment_record(
                    args.course_id, '', 'test', 'failed'
                )
                
        finally:
            await self.browser_agent.stop()
        
        logger.info(f"Test select completed: {success}", 
                   extra={'action': 'test_select', 'course_id': args.course_id})

    async def _show_help(self):
        """显示帮助信息"""
        help_text = """
🤖 YBU 延边大学自动选课代理系统

主要功能：
• 自动登录教务系统
• 智能验证码识别
• 课程数据抓取和管理
• 时间冲突检测
• 自动化选课和监控

快速开始：
1. python main.py clean              # 清理旧数据（如遇登录问题）
2. python main.py login              # 首次登录（出错时使用 --clean）
3. python main.py list --refresh     # 获取课程列表
4. python main.py grab COURSE_ID     # 立即抢课

自动化功能：
• python main.py auto-select-all     # 自动选择所有可抢课程
• python main.py auto-select-all --dry-run  # 模拟运行（测试）
• python main.py auto-select-all --skip-retakes  # 跳过重修课程
• python main.py auto-select-all --course-type professional  # 只选专业课
• python main.py auto-select-all --priority-keywords 计算机 数学  # 优先选择含关键词课程
• python main.py auto-select-all --exclude-keywords 体育 实验  # 排除含关键词课程
• python main.py auto-select-all --max-courses 3 --min-slots 5  # 最多选3门，至少5个名额

高级功能：
• python main.py plan rules.yml      # 智能选课规划
• python main.py scheduler start     # 启动自动化调度

详细帮助请使用：python main.py --help
        """
        console.print(Panel(help_text, title="帮助信息", style="blue"))

    def display_welcome(self):
        """显示欢迎信息"""
        welcome_text = """
🎓 延边大学自动选课代理系统

智能自动选课助手
支持自动登录、验证码识别、课程监控和智能选课

⚠️ 免责声明：仅供学习研究使用，请遵守学校相关规定
        """
        console.print(Panel(welcome_text, style="green", title="欢迎"))

    def _apply_course_filters(self, courses_df, args):
        """应用课程筛选条件"""
        filtered_df = courses_df.copy()
        
        # 排除关键词筛选
        if args.exclude_keywords:
            for keyword in args.exclude_keywords:
                filtered_df = filtered_df[~filtered_df['name'].str.contains(keyword, case=False, na=False)]
            console.print(f"🚫 排除包含关键词 {args.exclude_keywords} 的课程", style="yellow")
        
        console.print(f"📊 筛选后剩余 {len(filtered_df)} 门课程", style="blue")
        return filtered_df
    
    def _prioritize_courses(self, courses_df, args):
        """按优先级排序课程"""
        if courses_df.empty:
            return courses_df
        
        # 创建优先级分数列
        courses_df = courses_df.copy()
        courses_df['priority_score'] = 0.0
        
        # 优先关键词加分
        if args.priority_keywords:
            for keyword in args.priority_keywords:
                mask = courses_df['name'].str.contains(keyword, case=False, na=False)
                courses_df.loc[mask, 'priority_score'] += 10.0
            console.print(f"⭐ 优先选择包含关键词 {args.priority_keywords} 的课程", style="yellow")
        
        # 课程类型加分：专业课 > 公共课
        professional_mask = courses_df['type'] == 'professional'
        courses_df.loc[professional_mask, 'priority_score'] += 5.0
        
        # 按优先级分数排序
        courses_df = courses_df.sort_values('priority_score', ascending=False)
        
        return courses_df

    def close(self):
        """清理资源"""
        if self.data_manager:
            self.data_manager.close()
        
        logger.info("CLI interface closed", extra={'action': 'shutdown'}) 