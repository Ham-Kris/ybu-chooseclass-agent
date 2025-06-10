"""
DataManagerAgent - 数据管理代理
职责：解析 HTML/Table → pandas DataFrame；检测时间冲突；持久化 SQLite
接口：get_available(term), plan(schedule_rules)
"""

import pandas as pd
import sqlite3
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from rich.console import Console
from rich.table import Table
import os

console = Console()


class DataManagerAgent:
    def __init__(self, db_path: str = "ybu_courses.db"):
        """
        初始化数据管理代理
        
        Args:
            db_path: SQLite 数据库文件路径
        """
        self.db_path = db_path
        self.conn = None
        self._init_database()

    def _init_database(self):
        """初始化数据库"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self._create_tables()
            console.print("🗄️ 数据库已初始化", style="green")
        except Exception as e:
            console.print(f"❌ 数据库初始化失败：{e}", style="red")

    def _create_tables(self):
        """创建数据库表"""
        cursor = self.conn.cursor()
        
        # 课程表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS courses (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                details TEXT,
                url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 课程时间表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS course_schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id TEXT NOT NULL,
                day_of_week INTEGER NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                location TEXT,
                teacher TEXT,
                weeks TEXT,
                FOREIGN KEY (course_id) REFERENCES courses (id)
            )
        ''')
        
        # 选课记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS enrollment_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id TEXT NOT NULL,
                jx0404id TEXT,
                action TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (course_id) REFERENCES courses (id)
            )
        ''')
        
        # 课程可用性表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS course_availability (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id TEXT NOT NULL,
                remaining_slots INTEGER NOT NULL,
                total_slots INTEGER,
                jx0404id TEXT,
                checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (course_id) REFERENCES courses (id)
            )
        ''')
        
        self.conn.commit()

    def save_courses(self, courses_data: Dict[str, List[Dict]]) -> int:
        """
        保存课程数据到数据库
        
        Args:
            courses_data: 课程数据字典
            
        Returns:
            保存的课程数量
        """
        try:
            cursor = self.conn.cursor()
            total_saved = 0
            
            for course_type, courses in courses_data.items():
                if course_type == 'all':  # 跳过汇总列表，避免重复
                    continue
                    
                for course in courses:
                    # 构建详细信息字典
                    details = {
                        'code': course.get('code', ''),
                        'credits': course.get('credits', ''),
                        'category1': course.get('category1', ''),
                        'category2': course.get('category2', ''),
                        'grade': course.get('grade', ''),
                        'href': course.get('href', ''),
                        'is_retake': course.get('is_retake', False),
                        'link_text': course.get('link_text', '')
                    }
                    
                    # 插入或更新课程
                    cursor.execute('''
                        INSERT OR REPLACE INTO courses (id, name, type, details, url, updated_at)
                        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (
                        course['id'],
                        course['name'],
                        course.get('type', ''),
                        json.dumps(details),
                        course.get('url', '')
                    ))
                    total_saved += 1
            
            self.conn.commit()
            console.print(f"💾 已保存 {total_saved} 门课程到数据库", style="green")
            return total_saved
            
        except Exception as e:
            console.print(f"❌ 保存课程数据失败：{e}", style="red")
            return 0

    def get_available_courses(self, term: str = None, course_type: str = None) -> pd.DataFrame:
        """
        获取可用课程列表
        
        Args:
            term: 学期（暂未实现）
            course_type: 课程类型 ('professional', 'public', None for all)
            
        Returns:
            课程 DataFrame
        """
        try:
            # 课程类型映射
            type_mapping = {
                'professional': '必修',
                'public': '选修',
                'regular': '必修',
                'retake': '重修'
            }
            
            query = "SELECT * FROM courses"
            params = []
            
            if course_type and course_type in type_mapping:
                query += " WHERE type = ?"
                params.append(type_mapping[course_type])
            
            query += " ORDER BY type, name"
            
            df = pd.read_sql_query(query, self.conn, params=params)
            
            console.print(f"📚 查询到 {len(df)} 门课程", style="blue")
            return df
            
        except Exception as e:
            console.print(f"❌ 查询课程失败：{e}", style="red")
            return pd.DataFrame()

    def save_course_availability(self, course_id: str, availability_data: Dict[str, Any]):
        """
        保存课程可用性数据
        
        Args:
            course_id: 课程ID
            availability_data: 可用性数据
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO course_availability (course_id, remaining_slots, jx0404id)
                VALUES (?, ?, ?)
            ''', (
                course_id,
                availability_data.get('remaining', 0),
                availability_data.get('jx0404id', '')
            ))
            self.conn.commit()
            
        except Exception as e:
            console.print(f"❌ 保存课程可用性失败：{e}", style="red")

    def get_course_availability_history(self, course_id: str, days: int = 7) -> pd.DataFrame:
        """
        获取课程可用性历史
        
        Args:
            course_id: 课程ID
            days: 查询天数
            
        Returns:
            可用性历史 DataFrame
        """
        try:
            query = '''
                SELECT * FROM course_availability 
                WHERE course_id = ? AND checked_at >= datetime('now', '-{} days')
                ORDER BY checked_at DESC
            '''.format(days)
            
            df = pd.read_sql_query(query, self.conn, params=[course_id])
            return df
            
        except Exception as e:
            console.print(f"❌ 查询可用性历史失败：{e}", style="red")
            return pd.DataFrame()

    def parse_schedule_from_details(self, course_details: List[str]) -> List[Dict[str, Any]]:
        """
        从课程详情解析时间表
        
        Args:
            course_details: 课程详情列表
            
        Returns:
            时间表列表
        """
        schedules = []
        
        try:
            # 课程详情通常包含：[序号, 课程号, 课程名, 学分, 时间地点, 教师, 其他信息...]
            if len(course_details) < 5:
                return schedules
            
            time_location = course_details[4] if len(course_details) > 4 else ""
            teacher = course_details[5] if len(course_details) > 5 else ""
            
            # 解析时间地点信息（格式可能是：周一3-4节[教学楼101]）
            schedule_pattern = r'周([一二三四五六日])(\d+)-(\d+)节(?:\[([^\]]+)\])?'
            matches = re.findall(schedule_pattern, time_location)
            
            day_mapping = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '日': 7}
            
            for match in matches:
                day_chinese, start_period, end_period, location = match
                day_num = day_mapping.get(day_chinese, 0)
                
                if day_num > 0:
                    # 转换节次为时间（假设每节课45分钟，8:00开始）
                    start_time = self._period_to_time(int(start_period))
                    end_time = self._period_to_time(int(end_period) + 1)
                    
                    schedules.append({
                        'day_of_week': day_num,
                        'start_time': start_time,
                        'end_time': end_time,
                        'location': location or "",
                        'teacher': teacher
                    })
            
        except Exception as e:
            console.print(f"⚠️ 解析课程时间表失败：{e}", style="yellow")
        
        return schedules

    def _period_to_time(self, period: int) -> str:
        """
        将节次转换为时间
        
        Args:
            period: 节次（1-12）
            
        Returns:
            时间字符串 (HH:MM)
        """
        # 假设第1节课8:00开始，每节课45分钟，课间15分钟
        start_hour = 8
        if period <= 4:
            # 上午 8:00-11:30
            minutes = (period - 1) * 60  # 每节课+课间共60分钟
        elif period <= 8:
            # 下午 14:00-17:30
            start_hour = 14
            minutes = (period - 5) * 60
        else:
            # 晚上 19:00-21:30
            start_hour = 19
            minutes = (period - 9) * 60
        
        total_minutes = start_hour * 60 + minutes
        hour = total_minutes // 60
        minute = total_minutes % 60
        
        return f"{hour:02d}:{minute:02d}"

    def check_time_conflicts(self, course_schedules: List[Dict[str, Any]], 
                           existing_schedules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        检查时间冲突
        
        Args:
            course_schedules: 待检查的课程时间表
            existing_schedules: 已有的时间表
            
        Returns:
            冲突列表
        """
        conflicts = []
        
        for new_schedule in course_schedules:
            for existing_schedule in existing_schedules:
                if self._schedules_conflict(new_schedule, existing_schedule):
                    conflicts.append({
                        'new_course': new_schedule,
                        'existing_course': existing_schedule,
                        'conflict_type': 'time_overlap'
                    })
        
        return conflicts

    def _schedules_conflict(self, schedule1: Dict[str, Any], schedule2: Dict[str, Any]) -> bool:
        """
        检查两个时间表是否冲突
        
        Args:
            schedule1: 时间表1
            schedule2: 时间表2
            
        Returns:
            是否冲突
        """
        # 检查是否同一天
        if schedule1['day_of_week'] != schedule2['day_of_week']:
            return False
        
        # 转换时间为分钟数进行比较
        start1 = self._time_to_minutes(schedule1['start_time'])
        end1 = self._time_to_minutes(schedule1['end_time'])
        start2 = self._time_to_minutes(schedule2['start_time'])
        end2 = self._time_to_minutes(schedule2['end_time'])
        
        # 检查时间重叠
        return not (end1 <= start2 or end2 <= start1)

    def _time_to_minutes(self, time_str: str) -> int:
        """
        将时间字符串转换为分钟数
        
        Args:
            time_str: 时间字符串 (HH:MM)
            
        Returns:
            分钟数
        """
        try:
            hour, minute = map(int, time_str.split(':'))
            return hour * 60 + minute
        except:
            return 0

    def plan_course_selection(self, preference_rules: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        根据偏好规则规划选课
        
        Args:
            preference_rules: 偏好规则
            
        Returns:
            推荐的选课计划
        """
        try:
            # 获取所有可用课程
            all_courses = self.get_available_courses()
            
            if all_courses.empty:
                return []
            
            recommendations = []
            
            # 根据偏好筛选课程
            preferred_courses = self._filter_by_preferences(all_courses, preference_rules)
            
            for _, course in preferred_courses.iterrows():
                # 解析课程时间表
                details = json.loads(course['details']) if course['details'] else []
                schedules = self.parse_schedule_from_details(details)
                
                recommendation = {
                    'course_id': course['id'],
                    'course_name': course['name'],
                    'course_type': course['type'],
                    'schedules': schedules,
                    'priority': self._calculate_priority(course, preference_rules),
                    'conflicts': []  # 将在后续步骤中填充
                }
                
                recommendations.append(recommendation)
            
            # 按优先级排序
            recommendations.sort(key=lambda x: x['priority'], reverse=True)
            
            console.print(f"📋 生成了 {len(recommendations)} 个选课推荐", style="green")
            return recommendations
            
        except Exception as e:
            console.print(f"❌ 规划选课失败：{e}", style="red")
            return []

    def _filter_by_preferences(self, courses_df: pd.DataFrame, 
                              preferences: Dict[str, Any]) -> pd.DataFrame:
        """
        根据偏好筛选课程
        
        Args:
            courses_df: 课程 DataFrame
            preferences: 偏好设置
            
        Returns:
            筛选后的课程 DataFrame
        """
        filtered_df = courses_df.copy()
        
        # 按课程类型筛选
        if 'course_types' in preferences:
            filtered_df = filtered_df[filtered_df['type'].isin(preferences['course_types'])]
        
        # 按课程名称关键词筛选
        if 'keywords' in preferences:
            keywords = preferences['keywords']
            if keywords:
                pattern = '|'.join(keywords)
                filtered_df = filtered_df[filtered_df['name'].str.contains(pattern, na=False)]
        
        # 排除特定课程
        if 'exclude_keywords' in preferences:
            exclude_keywords = preferences['exclude_keywords']
            if exclude_keywords:
                pattern = '|'.join(exclude_keywords)
                filtered_df = filtered_df[~filtered_df['name'].str.contains(pattern, na=False)]
        
        return filtered_df

    def _calculate_priority(self, course: pd.Series, preferences: Dict[str, Any]) -> float:
        """
        计算课程优先级
        
        Args:
            course: 课程信息
            preferences: 偏好设置
            
        Returns:
            优先级分数
        """
        priority = 0.0
        
        # 基础分数
        priority += 1.0
        
        # 根据课程类型加分
        if 'priority_types' in preferences:
            priority_types = preferences['priority_types']
            if course['type'] in priority_types:
                priority += priority_types[course['type']]
        
        # 根据关键词加分
        if 'priority_keywords' in preferences:
            for keyword, score in preferences['priority_keywords'].items():
                if keyword in course['name']:
                    priority += score
        
        return priority

    def save_enrollment_record(self, course_id: str, jx0404id: str, 
                             action: str, status: str, message: str = ""):
        """
        保存选课记录
        
        Args:
            course_id: 课程ID
            jx0404id: 教学班ID
            action: 操作类型 ('enroll', 'drop')
            status: 状态 ('success', 'failed', 'pending')
            message: 消息
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO enrollment_records (course_id, jx0404id, action, status, message)
                VALUES (?, ?, ?, ?, ?)
            ''', (course_id, jx0404id, action, status, message))
            self.conn.commit()
            
        except Exception as e:
            console.print(f"❌ 保存选课记录失败：{e}", style="red")

    def get_enrollment_history(self, days: int = 30) -> pd.DataFrame:
        """
        获取选课历史
        
        Args:
            days: 查询天数
            
        Returns:
            选课历史 DataFrame
        """
        try:
            query = '''
                SELECT er.*, c.name as course_name, c.type as course_type
                FROM enrollment_records er
                LEFT JOIN courses c ON er.course_id = c.id
                WHERE er.timestamp >= datetime('now', '-{} days')
                ORDER BY er.timestamp DESC
            '''.format(days)
            
            df = pd.read_sql_query(query, self.conn)
            return df
            
        except Exception as e:
            console.print(f"❌ 查询选课历史失败：{e}", style="red")
            return pd.DataFrame()

    def display_courses_table(self, courses_df: pd.DataFrame):
        """
        以表格形式显示课程信息
        
        Args:
            courses_df: 课程 DataFrame
        """
        if courses_df.empty:
            console.print("📚 暂无课程数据", style="yellow")
            return
        
        table = Table(title=f"课程列表 ({len(courses_df)} 门)")
        table.add_column("序号", style="cyan", no_wrap=True)
        table.add_column("课程编号", style="magenta")
        table.add_column("课程名称", style="green")
        table.add_column("学分", style="blue")
        table.add_column("类型", style="yellow")
        table.add_column("一级体系", style="bright_black")
        table.add_column("是否重修", style="red")
        
        for idx, course in courses_df.iterrows():
            try:
                # 解析详细信息
                details = json.loads(course['details']) if course['details'] else {}
                
                table.add_row(
                    str(idx + 1),
                    details.get('code', '')[:15] + "..." if len(details.get('code', '')) > 15 else details.get('code', ''),
                    course['name'][:25] + "..." if len(course['name']) > 25 else course['name'],
                    details.get('credits', ''),
                    course['type'],
                    (details.get('category1', '') or '')[:12] + "..." if len(details.get('category1', '') or '') > 12 else (details.get('category1', '') or ''),
                    "✓" if details.get('is_retake', False) else ""
                )
            except Exception as e:
                # 如果解析失败，显示基本信息
                table.add_row(
                    str(idx + 1),
                    "",
                    course['name'][:25] + "..." if len(course['name']) > 25 else course['name'],
                    "",
                    course['type'],
                    "",
                    ""
                )
        
        console.print(table)

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            console.print("🗄️ 数据库连接已关闭", style="red") 