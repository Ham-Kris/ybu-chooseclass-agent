#!/usr/bin/env python3
"""
Synthesizer Agent - 生成合成验证码图片用于训练
根据AGENTS.md规范实现
"""

import os
import random
import string
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from captcha.image import ImageCaptcha
import cv2

class CaptchaSynthesizer:
    def __init__(self, dataset_dir="dataset/train", n_samples=1000):
        self.dataset_dir = Path(dataset_dir)
        self.n_samples = n_samples
        self.charset = string.ascii_uppercase + string.digits  # A-Z, 0-9
        self.dataset_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建ImageCaptcha实例
        self.captcha_generator = ImageCaptcha(width=200, height=80)
        
    def apply_fisheye_distortion(self, image):
        """应用鱼眼失真效果"""
        img_array = np.array(image)
        height, width = img_array.shape[:2]
        
        # 创建鱼眼变换的映射
        center_x, center_y = width // 2, height // 2
        radius = min(center_x, center_y)
        
        # 创建目标坐标网格
        map_x = np.zeros((height, width), dtype=np.float32)
        map_y = np.zeros((height, width), dtype=np.float32)
        
        for y in range(height):
            for x in range(width):
                # 计算到中心的距离
                dx = x - center_x
                dy = y - center_y
                distance = np.sqrt(dx*dx + dy*dy)
                
                if distance < radius:
                    # 应用鱼眼失真
                    new_distance = distance * (1 + 0.3 * (distance / radius)**2)
                    if distance > 0:
                        map_x[y, x] = center_x + dx * new_distance / distance
                        map_y[y, x] = center_y + dy * new_distance / distance
                    else:
                        map_x[y, x] = x
                        map_y[y, x] = y
                else:
                    map_x[y, x] = x
                    map_y[y, x] = y
        
        # 应用重映射
        distorted = cv2.remap(img_array, map_x, map_y, cv2.INTER_LINEAR)
        return Image.fromarray(distorted)
    
    def add_red_vertical_line(self, image):
        """在图片中央添加红色垂直线"""
        draw = ImageDraw.Draw(image)
        width, height = image.size
        center_x = width // 2
        
        # 添加半透明的红色垂直线
        line_width = random.randint(2, 4)
        for i in range(-line_width//2, line_width//2 + 1):
            draw.line([(center_x + i, 0), (center_x + i, height)], 
                     fill=(255, 0, 0, 128), width=1)
        
        return image
    
    def add_noise_and_blur(self, image):
        """添加随机噪声和模糊效果"""
        # 添加高斯噪声
        img_array = np.array(image)
        noise = np.random.normal(0, 15, img_array.shape).astype(np.uint8)
        noisy_img = np.clip(img_array + noise, 0, 255).astype(np.uint8)
        
        # 转换回PIL图像
        image = Image.fromarray(noisy_img)
        
        # 随机应用轻微模糊
        if random.random() < 0.3:
            image = image.filter(ImageFilter.GaussianBlur(radius=0.5))
        
        return image
    
    def generate_captcha_label(self):
        """生成4位大写字母数字验证码标签"""
        return ''.join(random.choices(self.charset, k=4))
    
    def generate_single_captcha(self, label, save_id):
        """生成单个验证码图片"""
        # 使用captcha库生成基础图片
        image = self.captcha_generator.generate_image(label)
        
        # 应用鱼眼失真
        image = self.apply_fisheye_distortion(image)
        
        # 添加红色垂直线
        image = self.add_red_vertical_line(image)
        
        # 添加噪声和模糊
        image = self.add_noise_and_blur(image)
        
        # 保存图片
        filename = f"{label}_{save_id:04d}.png"
        filepath = self.dataset_dir / filename
        image.save(filepath)
        
        return filename, label
    
    def generate_dataset(self):
        """生成完整的验证码数据集"""
        print(f"开始生成 {self.n_samples} 个验证码图片...")
        
        labels_data = []
        
        for i in range(self.n_samples):
            # 生成随机标签
            label = self.generate_captcha_label()
            
            # 生成并保存验证码图片
            filename, true_label = self.generate_single_captcha(label, i)
            labels_data.append(f"{filename}\t{true_label}")
            
            # 进度显示
            if (i + 1) % 100 == 0:
                print(f"已生成 {i + 1}/{self.n_samples} 个验证码...")
        
        # 保存标签文件
        labels_file = self.dataset_dir / "labels.txt"
        with open(labels_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(labels_data))
        
        print(f"✅ 数据集生成完成！")
        print(f"📁 图片保存在: {self.dataset_dir}")
        print(f"📝 标签文件: {labels_file}")
        print(f"📊 总计生成: {self.n_samples} 个验证码图片")
        
        return len(labels_data)

def main():
    """主函数"""
    # 从环境变量读取配置
    n_samples = int(os.getenv('N_SAMPLES', 1000))
    dataset_dir = os.getenv('DATASET_DIR', 'dataset/train')
    
    print("🤖 Synthesizer Agent 启动")
    print(f"📋 目标生成数量: {n_samples}")
    print(f"📂 数据集目录: {dataset_dir}")
    
    # 创建合成器实例
    synthesizer = CaptchaSynthesizer(dataset_dir, n_samples)
    
    # 生成数据集
    total_generated = synthesizer.generate_dataset()
    
    print(f"\n🎉 任务完成！成功生成 {total_generated} 个验证码图片")

if __name__ == "__main__":
    main() 