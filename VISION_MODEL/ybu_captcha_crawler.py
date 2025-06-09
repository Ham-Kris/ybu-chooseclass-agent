#!/usr/bin/env python3
"""
YBU Captcha Crawler - 延边大学教务系统验证码爬取器
获取真实验证码样例用于分析和训练
"""

import os
import requests
import time
import random
from pathlib import Path
from PIL import Image
import io

class YBUCaptchaCrawler:
    def __init__(self, save_dir="dataset/real", max_samples=100):
        self.save_dir = Path(save_dir)
        self.max_samples = max_samples
        self.save_dir.mkdir(parents=True, exist_ok=True)
        
        # 延边大学教务系统验证码URL
        self.captcha_url = "https://jwxt.ybu.edu.cn/jsxsd/sys/kaptcha/handleRequestInternal?82"
        
        # 请求头 (模拟浏览器)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://jwxt.ybu.edu.cn/',
            'Sec-Fetch-Dest': 'image',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'same-origin'
        }
        
        # 创建会话
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def get_single_captcha(self):
        """获取单个验证码图片"""
        try:
            # 添加随机参数避免缓存
            url = f"{self.captcha_url}&t={int(time.time() * 1000)}&r={random.randint(1000, 9999)}"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            if response.status_code == 200 and len(response.content) > 0:
                # 验证是否为有效图片
                try:
                    image = Image.open(io.BytesIO(response.content))
                    return response.content, image.size
                except Exception:
                    print("❌ 无效的图片数据")
                    return None, None
            else:
                print(f"❌ 请求失败，状态码: {response.status_code}")
                return None, None
                
        except Exception as e:
            print(f"❌ 获取验证码失败: {e}")
            return None, None
    
    def crawl_captchas(self):
        """批量获取验证码样例"""
        print(f"🕷️ 开始爬取延边大学教务系统验证码...")
        print(f"🎯 目标URL: {self.captcha_url}")
        print(f"📁 保存目录: {self.save_dir}")
        print(f"📊 目标数量: {self.max_samples}")
        print("⚠️ 请确保网络连接正常且学校系统可访问")
        
        success_count = 0
        sizes = set()
        
        for i in range(self.max_samples):
            print(f"📸 获取第 {i+1}/{self.max_samples} 个验证码...", end=" ")
            
            captcha_data, size = self.get_single_captcha()
            
            if captcha_data:
                # 保存验证码图片
                filename = f"real_captcha_{i+1:04d}.png"
                filepath = self.save_dir / filename
                
                with open(filepath, 'wb') as f:
                    f.write(captcha_data)
                
                success_count += 1
                sizes.add(size)
                print(f"✅ 成功 (尺寸: {size})")
                
                # 保存最后一个样例作为分析用
                if i == 0:
                    sample_path = self.save_dir / "sample_captcha.png"
                    with open(sample_path, 'wb') as f:
                        f.write(captcha_data)
                    print(f"💾 样例已保存到: {sample_path}")
            else:
                print("❌ 失败")
            
            # 请求间隔 (遵守服务器压力限制)
            if i < self.max_samples - 1:
                delay = random.uniform(1.0, 3.0)  # 1-3秒随机间隔
                time.sleep(delay)
        
        print(f"\n🎉 爬取完成！")
        print(f"✅ 成功获取: {success_count}/{self.max_samples} 个验证码")
        print(f"📏 发现的尺寸: {list(sizes)}")
        
        if success_count > 0:
            print(f"📂 验证码已保存到: {self.save_dir}")
            
            # 创建标签文件模板 (需要手动标记)
            labels_file = self.save_dir / "real_labels.txt"
            with open(labels_file, 'w', encoding='utf-8') as f:
                f.write("# 真实验证码标签文件\n")
                f.write("# 格式: filename\tlabel\n")
                f.write("# 请手动识别每个验证码并填写对应标签\n\n")
                
                for i in range(1, success_count + 1):
                    filename = f"real_captcha_{i:04d}.png"
                    f.write(f"{filename}\t# 请填写识别结果\n")
            
            print(f"📝 标签模板已创建: {labels_file}")
            print("💡 请手动识别验证码并完善标签文件")
        
        return success_count

def main():
    """主函数"""
    max_samples = int(os.getenv('MAX_SAMPLES', 50))  # 默认获取50个样例
    save_dir = os.getenv('SAVE_DIR', 'dataset/real')
    
    print("🕷️ YBU Captcha Crawler 启动")
    print("🏫 延边大学教务系统验证码爬取器")
    print(f"📋 目标获取数量: {max_samples}")
    print(f"📂 保存目录: {save_dir}")
    
    crawler = YBUCaptchaCrawler(save_dir, max_samples)
    
    try:
        total_crawled = crawler.crawl_captchas()
        
        if total_crawled > 0:
            print(f"\n🎊 任务完成！成功获取 {total_crawled} 个真实验证码")
            print("📋 接下来你可以:")
            print("1. 查看生成的验证码样例分析真实特征")
            print("2. 手动标记验证码内容")
            print("3. 基于真实样例优化合成验证码生成器")
        else:
            print("\n❌ 未能获取任何验证码，请检查:")
            print("1. 网络连接是否正常")
            print("2. 延边大学教务系统是否可访问")
            print("3. 验证码URL是否有变化")
    
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断操作")
    except Exception as e:
        print(f"\n❌ 程序执行失败: {e}")

if __name__ == "__main__":
    main() 