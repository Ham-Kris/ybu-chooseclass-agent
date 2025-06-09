#!/usr/bin/env python3
"""
选课功能测试脚本
用于验证完整的选课流程
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents import BrowserAgent

async def test_course_selection():
    """测试选课功能"""
    browser_agent = BrowserAgent(headless=False)  # 使用有头模式便于观察
    
    try:
        await browser_agent.start()
        print("✅ 浏览器已启动")
        
        # 测试课程ID（从列表中选择一个普通选课课程）
        test_course_id = "5F7D647FED934753A93A1C84CAC4F531"  # 习近平新时代中国特色社会主义思想概论
        
        print(f"🎯 开始测试选课，课程ID：{test_course_id}")
        
        # 检查课程可用性
        print("📋 检查课程可用性...")
        availability = await browser_agent.check_course_availability(test_course_id, False)
        
        if availability['available']:
            print(f"✅ 课程可用，总剩余：{availability['total_remaining']}")
            print(f"📚 可用教学班数量：{len(availability['classes'])}")
            
            # 显示教学班信息
            for i, class_info in enumerate(availability['classes']):
                print(f"  班级 {i+1}: ID={class_info['jx0404id']}, 剩余={class_info['remaining']}")
            
            # 进行选课测试（注意：这会实际尝试选课！）
            confirm = input("⚠️ 确实要尝试选课吗？(y/n): ")
            if confirm.lower() == 'y':
                print("🚀 开始选课...")
                success = await browser_agent.select_course(test_course_id, False)
                
                if success:
                    print("🎉 选课成功！")
                else:
                    print("❌ 选课失败")
            else:
                print("🚫 用户取消选课")
        else:
            print("❌ 课程暂无可用名额")
        
    except Exception as e:
        print(f"❌ 测试过程中出错：{e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser_agent.stop()
        print("✅ 浏览器已关闭")

if __name__ == "__main__":
    print("🧪 延边大学选课功能测试")
    print("=" * 50)
    asyncio.run(test_course_selection()) 