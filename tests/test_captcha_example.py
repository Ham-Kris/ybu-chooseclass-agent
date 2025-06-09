#!/usr/bin/env python3
"""
验证码识别测试脚本
测试 example_captcha-jaejp.jpg 图片的识别效果
"""

import sys
import os
from rich.console import Console

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.captcha_solver_agent import CaptchaSolverAgent

console = Console()

def test_captcha_recognition():
    """测试验证码识别功能"""
    
    # 测试图片路径 - 从tests目录向上一级找到图片
    image_path = os.path.join(os.path.dirname(__file__), "..", "example_captcha-jaejp.jpg")
    
    if not os.path.exists(image_path):
        console.print(f"❌ 找不到图片文件：{image_path}", style="red")
        return
    
    console.print(f"🖼️ 开始测试验证码图片：{image_path}", style="blue")
    
    # 读取图片数据
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    console.print(f"📊 图片大小：{len(image_data)} 字节", style="cyan")
    
    # 测试手动模式
    console.print("\n🔧 测试手动模式...", style="yellow")
    agent_manual = CaptchaSolverAgent(mode="manual")
    
    # 测试图片预处理
    console.print("🖼️ 测试图片预处理...", style="blue")
    processed_data = agent_manual.preprocess_image(image_data)
    
    if processed_data:
        console.print(f"✅ 预处理成功，处理后大小：{len(processed_data)} 字节", style="green")
        
        # 保存预处理后的图片
        processed_path = "processed_captcha-jaejp.jpg"
        with open(processed_path, 'wb') as f:
            f.write(processed_data)
        console.print(f"💾 预处理后的图片已保存到：{processed_path}", style="green")
    else:
        console.print("❌ 图片预处理失败", style="red")
        return
    
    # 测试文本识别
    console.print("\n🤖 测试文本识别...", style="blue")
    result = agent_manual.recognize_text(image_data)
    
    console.print(f"📝 识别结果：{result}", style="cyan")
    
    # 测试AI模式（如果可用）
    console.print("\n🧠 尝试AI模式...", style="yellow")
    agent_ai = CaptchaSolverAgent(mode="ai")
    
    if agent_ai.mode == "ai" and agent_ai.model is not None:
        console.print("✅ AI模式可用，进行AI识别...", style="green")
        ai_result = agent_ai.recognize_text(image_data)
        console.print(f"🤖 AI识别结果：{ai_result}", style="cyan")
        
        if ai_result.get("code"):
            console.print(f"🎯 AI识别的验证码：{ai_result['code']}", style="green bold")
            console.print(f"📊 置信度：{ai_result.get('confidence', 0)}", style="blue")
    else:
        console.print("⚠️ AI模式不可用，已回退到手动模式", style="yellow")
    
    # 测试完整的solve_captcha方法（不允许手动输入）
    console.print("\n🔍 测试完整识别流程（自动模式）...", style="blue")
    final_result = agent_ai.solve_captcha(image_data, manual_fallback=False)
    
    if final_result:
        console.print(f"🎉 最终识别结果：{final_result}", style="green bold")
    else:
        console.print("❌ 自动识别失败", style="red")

if __name__ == "__main__":
    console.print("🚀 验证码识别测试开始", style="green bold")
    console.print("=" * 50, style="blue")
    
    try:
        test_captcha_recognition()
    except Exception as e:
        console.print(f"❌ 测试过程中发生错误：{e}", style="red")
        import traceback
        console.print(traceback.format_exc(), style="red dim")
    
    console.print("=" * 50, style="blue")
    console.print("✅ 测试完成", style="green bold") 