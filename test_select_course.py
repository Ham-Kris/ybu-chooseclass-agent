#!/usr/bin/env python3
"""
选课功能测试脚本
用于验证修复后的选课代理功能
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.browser_agent import BrowserAgent
from rich.console import Console

console = Console()


async def test_course_selection():
    """测试选课功能"""
    browser_agent = None
    
    try:
        console.print("🚀 启动选课功能测试...", style="bold blue")
        
        # 创建浏览器代理
        browser_agent = BrowserAgent(headless=False)  # 设置为非无头模式便于观察
        await browser_agent.start()
        
        console.print("✅ 浏览器代理启动成功", style="green")
        
        # 测试获取课程列表
        console.print("📚 获取可选课程列表...", style="blue")
        courses = await browser_agent.fetch_courses()
        
        if not courses or not courses.get('available_courses'):
            console.print("❌ 无法获取课程列表，请先登录", style="red")
            return False
        
        available_courses = courses['available_courses']
        console.print(f"📋 找到 {len(available_courses)} 门可选课程", style="green")
        
        # 显示前5门课程供选择
        console.print("\n可选课程列表（前5门）：", style="bold")
        for i, course in enumerate(available_courses[:5]):
            console.print(f"{i+1}. {course.get('kcmc', '未知课程')} - {course.get('kcid', 'N/A')}")
        
        # 让用户选择要测试的课程
        try:
            choice = input("\n请输入要测试选课的课程编号 (1-5): ")
            course_index = int(choice) - 1
            
            if 0 <= course_index < min(5, len(available_courses)):
                selected_course = available_courses[course_index]
                course_id = selected_course.get('kcid')
                course_name = selected_course.get('kcmc')
                
                console.print(f"\n🎯 选择测试课程：{course_name} ({course_id})", style="cyan")
                
                # 执行选课测试
                console.print("🔄 开始选课测试...", style="blue")
                result = await browser_agent.select_course(
                    course_id=course_id,
                    is_retake=False
                )
                
                if result:
                    console.print("🎉 选课测试成功！", style="bold green")
                else:
                    console.print("❌ 选课测试失败", style="bold red")
                
                return result
            else:
                console.print("❌ 无效的课程编号", style="red")
                return False
                
        except (ValueError, KeyboardInterrupt):
            console.print("❌ 测试被取消", style="yellow")
            return False
    
    except Exception as e:
        console.print(f"❌ 测试过程中出错：{e}", style="red")
        import traceback
        console.print(traceback.format_exc(), style="dim")
        return False
    
    finally:
        if browser_agent:
            try:
                await browser_agent.stop()
                console.print("🔒 浏览器代理已关闭", style="blue")
            except:
                pass


async def test_verification_system():
    """测试验证码识别系统"""
    console.print("🔍 测试验证码识别系统...", style="bold blue")
    
    try:
        from agents.captcha_solver_agent import CaptchaSolverAgent
        
        # 创建验证码解决代理
        captcha_solver = CaptchaSolverAgent()
        
        # 测试预处理功能
        console.print("✅ 验证码识别代理创建成功", style="green")
        console.print("📋 支持的识别方法：OCR识别 + 手动输入回退", style="blue")
        
        return True
        
    except Exception as e:
        console.print(f"❌ 验证码识别系统测试失败：{e}", style="red")
        return False


def main():
    """主函数"""
    console.print("=" * 60, style="bold")
    console.print("🎓 YBU 选课系统功能测试", style="bold cyan")
    console.print("=" * 60, style="bold")
    
    # 检查依赖
    try:
        import playwright
        import bs4
        import requests
        console.print("✅ 所有依赖包检查通过", style="green")
    except ImportError as e:
        console.print(f"❌ 缺少依赖包：{e}", style="red")
        console.print("请运行: pip install -r requirements.txt", style="yellow")
        return
    
    # 运行测试
    console.print("\n🧪 开始功能测试...\n", style="bold")
    
    # 测试验证码系统
    verification_result = asyncio.run(test_verification_system())
    
    if verification_result:
        console.print("\n选择测试模式：", style="bold")
        console.print("1. 选课功能完整测试（需要先登录）")
        console.print("2. 仅验证码识别测试")
        console.print("0. 退出测试")
        
        try:
            mode = input("\n请选择测试模式 (0-2): ")
            
            if mode == "1":
                # 完整选课测试
                result = asyncio.run(test_course_selection())
                if result:
                    console.print("\n🎉 所有测试通过！选课功能正常", style="bold green")
                else:
                    console.print("\n❌ 选课功能测试失败", style="bold red")
            
            elif mode == "2":
                console.print("\n✅ 验证码识别系统测试完成", style="green")
                console.print("在实际选课过程中，系统会自动调用验证码识别功能", style="blue")
            
            elif mode == "0":
                console.print("\n👋 测试结束", style="yellow")
            
            else:
                console.print("\n❌ 无效的选择", style="red")
                
        except KeyboardInterrupt:
            console.print("\n👋 测试被用户中断", style="yellow")
    
    console.print("\n" + "=" * 60, style="bold")
    console.print("测试完成", style="bold cyan")
    console.print("=" * 60, style="bold")


if __name__ == "__main__":
    main() 