"""
SchedulerAgent - 调度代理
职责：基于 cron 规则定时触发 UX 指令；清晨 06:00 检查新课
库：APScheduler；支持动态 RRULE
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from rich.console import Console
import json
import os

console = Console()


class SchedulerAgent:
    def __init__(self, config_file: str = "scheduler_config.json"):
        """
        初始化调度代理
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.scheduler = AsyncIOScheduler(
            jobstores={'default': MemoryJobStore()},
            timezone='Asia/Shanghai'
        )
        self.jobs = {}
        self.callbacks = {}
        self.is_running = False
        
        # 加载配置
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载调度配置"""
        default_config = {
            "monitoring": {
                "enabled": True,
                "interval_minutes": 5,
                "course_check_hour": 6,
                "course_check_minute": 0
            },
            "auto_enrollment": {
                "enabled": False,
                "retry_interval_minutes": 2,
                "max_retries": 30
            },
            "notifications": {
                "enabled": True,
                "methods": ["console"]
            }
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    # 合并配置
                    default_config.update(user_config)
        except Exception as e:
            console.print(f"⚠️ 加载配置文件失败，使用默认配置：{e}", style="yellow")
        
        return default_config

    def _save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            console.print(f"❌ 保存配置文件失败：{e}", style="red")

    def register_callback(self, event_type: str, callback: Callable):
        """
        注册回调函数
        
        Args:
            event_type: 事件类型 ('course_check', 'auto_enroll', 'notification')
            callback: 回调函数
        """
        self.callbacks[event_type] = callback
        console.print(f"📋 已注册 {event_type} 回调", style="blue")

    async def start(self):
        """启动调度器"""
        if self.is_running:
            console.print("⚠️ 调度器已在运行", style="yellow")
            return
        
        try:
            self.scheduler.start()
            self.is_running = True
            
            # 添加默认任务
            await self._setup_default_jobs()
            
            console.print("⏰ 调度器已启动", style="green")
            
        except Exception as e:
            console.print(f"❌ 启动调度器失败：{e}", style="red")

    async def stop(self):
        """停止调度器"""
        if not self.is_running:
            return
        
        try:
            self.scheduler.shutdown()
            self.is_running = False
            console.print("⏰ 调度器已停止", style="red")
        except Exception as e:
            console.print(f"❌ 停止调度器失败：{e}", style="red")

    async def _setup_default_jobs(self):
        """设置默认任务"""
        # 课程监控任务
        if self.config.get("monitoring", {}).get("enabled", True):
            await self.add_monitoring_job()
        
        # 每日课程检查任务
        await self.add_daily_course_check()

    async def add_monitoring_job(self, interval_minutes: int = None):
        """
        添加课程监控任务
        
        Args:
            interval_minutes: 监控间隔（分钟），默认从配置读取
        """
        if interval_minutes is None:
            interval_minutes = self.config.get("monitoring", {}).get("interval_minutes", 5)
        
        job_id = "course_monitoring"
        
        # 移除已存在的任务
        if job_id in self.jobs:
            self.scheduler.remove_job(job_id)
        
        # 添加新任务
        job = self.scheduler.add_job(
            self._monitor_courses,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id=job_id,
            name="课程监控",
            max_instances=1
        )
        
        self.jobs[job_id] = job
        console.print(f"⏰ 已添加课程监控任务，间隔 {interval_minutes} 分钟", style="green")

    async def add_daily_course_check(self):
        """添加每日课程检查任务"""
        monitoring_config = self.config.get("monitoring", {})
        hour = monitoring_config.get("course_check_hour", 6)
        minute = monitoring_config.get("course_check_minute", 0)
        
        job_id = "daily_course_check"
        
        # 移除已存在的任务
        if job_id in self.jobs:
            self.scheduler.remove_job(job_id)
        
        # 添加新任务
        job = self.scheduler.add_job(
            self._daily_course_check,
            trigger=CronTrigger(hour=hour, minute=minute),
            id=job_id,
            name="每日课程检查",
            max_instances=1
        )
        
        self.jobs[job_id] = job
        console.print(f"⏰ 已添加每日课程检查任务，时间 {hour:02d}:{minute:02d}", style="green")

    async def add_auto_enrollment_job(self, course_ids: List[str], 
                                    retry_interval_minutes: int = None):
        """
        添加自动选课任务
        
        Args:
            course_ids: 课程ID列表
            retry_interval_minutes: 重试间隔（分钟）
        """
        if not self.config.get("auto_enrollment", {}).get("enabled", False):
            console.print("⚠️ 自动选课功能未启用", style="yellow")
            return
        
        if retry_interval_minutes is None:
            retry_interval_minutes = self.config.get("auto_enrollment", {}).get("retry_interval_minutes", 2)
        
        for course_id in course_ids:
            job_id = f"auto_enroll_{course_id}"
            
            # 移除已存在的任务
            if job_id in self.jobs:
                self.scheduler.remove_job(job_id)
            
            # 添加新任务
            job = self.scheduler.add_job(
                self._auto_enroll_course,
                trigger=IntervalTrigger(minutes=retry_interval_minutes),
                id=job_id,
                name=f"自动选课-{course_id}",
                args=[course_id],
                max_instances=1
            )
            
            self.jobs[job_id] = job
            console.print(f"⏰ 已添加自动选课任务：{course_id}，间隔 {retry_interval_minutes} 分钟", style="green")

    async def add_custom_job(self, job_id: str, callback: Callable, 
                           trigger_type: str = "cron", **trigger_kwargs):
        """
        添加自定义任务
        
        Args:
            job_id: 任务ID
            callback: 回调函数
            trigger_type: 触发器类型 ('cron' 或 'interval')
            **trigger_kwargs: 触发器参数
        """
        try:
            # 移除已存在的任务
            if job_id in self.jobs:
                self.scheduler.remove_job(job_id)
            
            # 选择触发器
            if trigger_type == "cron":
                trigger = CronTrigger(**trigger_kwargs)
            elif trigger_type == "interval":
                trigger = IntervalTrigger(**trigger_kwargs)
            else:
                raise ValueError(f"不支持的触发器类型：{trigger_type}")
            
            # 添加任务
            job = self.scheduler.add_job(
                callback,
                trigger=trigger,
                id=job_id,
                name=f"自定义任务-{job_id}",
                max_instances=1
            )
            
            self.jobs[job_id] = job
            console.print(f"⏰ 已添加自定义任务：{job_id}", style="green")
            
        except Exception as e:
            console.print(f"❌ 添加自定义任务失败：{e}", style="red")

    async def remove_job(self, job_id: str):
        """
        移除任务
        
        Args:
            job_id: 任务ID
        """
        try:
            if job_id in self.jobs:
                self.scheduler.remove_job(job_id)
                del self.jobs[job_id]
                console.print(f"⏰ 已移除任务：{job_id}", style="yellow")
            else:
                console.print(f"⚠️ 任务不存在：{job_id}", style="yellow")
        except Exception as e:
            console.print(f"❌ 移除任务失败：{e}", style="red")

    async def _monitor_courses(self):
        """监控课程可用性"""
        try:
            if "course_check" in self.callbacks:
                await self.callbacks["course_check"]()
            else:
                console.print("⚠️ 未注册课程检查回调", style="yellow")
        except Exception as e:
            console.print(f"❌ 课程监控任务执行失败：{e}", style="red")

    async def _daily_course_check(self):
        """每日课程检查"""
        try:
            console.print("🌅 开始执行每日课程检查", style="blue")
            
            if "course_check" in self.callbacks:
                await self.callbacks["course_check"]()
            
            # 发送通知
            await self._send_notification("每日课程检查完成", "info")
            
        except Exception as e:
            console.print(f"❌ 每日课程检查失败：{e}", style="red")
            await self._send_notification(f"每日课程检查失败：{e}", "error")

    async def _auto_enroll_course(self, course_id: str):
        """自动选课"""
        try:
            console.print(f"🤖 尝试自动选课：{course_id}", style="blue")
            
            if "auto_enroll" in self.callbacks:
                success = await self.callbacks["auto_enroll"](course_id)
                
                if success:
                    # 选课成功，移除任务
                    await self.remove_job(f"auto_enroll_{course_id}")
                    await self._send_notification(f"自动选课成功：{course_id}", "success")
                    
            else:
                console.print("⚠️ 未注册自动选课回调", style="yellow")
                
        except Exception as e:
            console.print(f"❌ 自动选课失败：{e}", style="red")

    async def _send_notification(self, message: str, level: str = "info"):
        """
        发送通知
        
        Args:
            message: 通知消息
            level: 通知级别 ('info', 'warning', 'error', 'success')
        """
        if not self.config.get("notifications", {}).get("enabled", True):
            return
        
        try:
            # 控制台通知
            if "console" in self.config.get("notifications", {}).get("methods", ["console"]):
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                if level == "info":
                    console.print(f"[{timestamp}] ℹ️ {message}", style="blue")
                elif level == "warning":
                    console.print(f"[{timestamp}] ⚠️ {message}", style="yellow")
                elif level == "error":
                    console.print(f"[{timestamp}] ❌ {message}", style="red")
                elif level == "success":
                    console.print(f"[{timestamp}] ✅ {message}", style="green")
            
            # 如果注册了通知回调，也调用它
            if "notification" in self.callbacks:
                await self.callbacks["notification"](message, level)
                
        except Exception as e:
            console.print(f"❌ 发送通知失败：{e}", style="red")

    def get_jobs_status(self) -> Dict[str, Any]:
        """
        获取任务状态
        
        Returns:
            任务状态字典
        """
        status = {
            "scheduler_running": self.is_running,
            "total_jobs": len(self.jobs),
            "jobs": []
        }
        
        for job_id, job in self.jobs.items():
            job_info = {
                "id": job_id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            }
            status["jobs"].append(job_info)
        
        return status

    def display_jobs_status(self):
        """显示任务状态"""
        from rich.table import Table
        
        status = self.get_jobs_status()
        
        table = Table(title=f"调度器状态 - {'运行中' if status['scheduler_running'] else '已停止'}")
        table.add_column("任务ID", style="cyan")
        table.add_column("任务名称", style="green")
        table.add_column("下次运行", style="yellow")
        table.add_column("触发器", style="blue")
        
        for job in status["jobs"]:
            next_run = job["next_run"][:19] if job["next_run"] else "未计划"
            table.add_row(
                job["id"],
                job["name"],
                next_run,
                job["trigger"][:50] + "..." if len(job["trigger"]) > 50 else job["trigger"]
            )
        
        console.print(table)

    async def pause_job(self, job_id: str):
        """暂停任务"""
        try:
            if job_id in self.jobs:
                self.scheduler.pause_job(job_id)
                console.print(f"⏸️ 已暂停任务：{job_id}", style="yellow")
            else:
                console.print(f"⚠️ 任务不存在：{job_id}", style="yellow")
        except Exception as e:
            console.print(f"❌ 暂停任务失败：{e}", style="red")

    async def resume_job(self, job_id: str):
        """恢复任务"""
        try:
            if job_id in self.jobs:
                self.scheduler.resume_job(job_id)
                console.print(f"▶️ 已恢复任务：{job_id}", style="green")
            else:
                console.print(f"⚠️ 任务不存在：{job_id}", style="yellow")
        except Exception as e:
            console.print(f"❌ 恢复任务失败：{e}", style="red")

    def update_config(self, new_config: Dict[str, Any]):
        """
        更新配置
        
        Args:
            new_config: 新配置
        """
        self.config.update(new_config)
        self._save_config()
        console.print("⚙️ 配置已更新", style="green") 