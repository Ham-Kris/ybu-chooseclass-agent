#!/usr/bin/env python3
"""
分析延边大学教务系统验证码特征
"""

import cv2
import numpy as np
from PIL import Image

def analyze_captcha(image_path):
    """分析验证码图片特征"""
    print(f"🔍 分析验证码: {image_path}")
    
    # 读取图片
    image = cv2.imread(image_path)
    if image is None:
        print(f"❌ 无法读取图片: {image_path}")
        return
    
    # 基本信息
    height, width, channels = image.shape
    print(f"📏 图片尺寸: {width} x {height}")
    print(f"🎨 颜色通道: {channels}")
    
    # 转换为RGB (PIL格式)
    pil_image = Image.open(image_path)
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # 转为灰度图
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 颜色分析
    print("\n🎨 颜色分析:")
    unique_colors = np.unique(rgb_image.reshape(-1, 3), axis=0)
    print(f"唯一颜色数量: {len(unique_colors)}")
    print("主要颜色 (RGB):")
    for i, color in enumerate(unique_colors[:10]):  # 显示前10种颜色
        print(f"  {i+1}. {color}")
    
    # 亮度分析
    print("\n💡 亮度分析:")
    brightness = np.mean(gray)
    print(f"平均亮度: {brightness:.2f}")
    print(f"最暗像素: {np.min(gray)}")
    print(f"最亮像素: {np.max(gray)}")
    
    # 阈值处理分析
    print("\n🔲 阈值处理分析:")
    
    # OTSU阈值
    _, otsu_thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    otsu_value = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[0]
    print(f"OTSU阈值: {otsu_value:.2f}")
    
    # 自适应阈值
    adaptive_thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    
    # 字符区域分析 (连通组件)
    print("\n📝 字符区域分析:")
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # 查找轮廓
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 过滤合理大小的轮廓 (可能的字符)
    char_contours = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = cv2.contourArea(contour)
        
        # 过滤条件：面积和宽高比合理
        if area > 50 and w > 5 and h > 10 and w < width/2 and h < height:
            char_contours.append((x, y, w, h, area))
    
    print(f"潜在字符数量: {len(char_contours)}")
    if char_contours:
        print("字符边界框:")
        for i, (x, y, w, h, area) in enumerate(sorted(char_contours, key=lambda c: c[0])):
            print(f"  字符{i+1}: x={x}, y={y}, w={w}, h={h}, area={area}")
    
    # 保存分析结果图片
    analysis_image = rgb_image.copy()
    
    # 在原图上标记字符边界框
    for x, y, w, h, _ in char_contours:
        cv2.rectangle(analysis_image, (x, y), (x+w, y+h), (255, 0, 0), 2)
    
    # 保存处理后的图片
    cv2.imwrite('captcha_analysis.png', cv2.cvtColor(analysis_image, cv2.COLOR_RGB2BGR))
    cv2.imwrite('captcha_gray.png', gray)
    cv2.imwrite('captcha_binary.png', binary)
    cv2.imwrite('captcha_otsu.png', otsu_thresh)
    cv2.imwrite('captcha_adaptive.png', adaptive_thresh)
    
    print(f"\n💾 分析结果已保存:")
    print(f"  - captcha_analysis.png (标记字符边界)")
    print(f"  - captcha_gray.png (灰度图)")
    print(f"  - captcha_binary.png (二值化)")
    print(f"  - captcha_otsu.png (OTSU阈值)")
    print(f"  - captcha_adaptive.png (自适应阈值)")

def main():
    # 分析项目中的验证码样例
    captcha_files = ['temp_captcha.jpg', 'sample_captcha.png']
    
    for captcha_file in captcha_files:
        try:
            analyze_captcha(captcha_file)
            print("=" * 60)
        except Exception as e:
            print(f"❌ 分析 {captcha_file} 失败: {e}")

if __name__ == "__main__":
    main() 