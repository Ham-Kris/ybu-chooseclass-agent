"""
CaptchaSolverAgent - 验证码识别代理
职责：接收验证码图，对其进行预处理并输出文本

预处理流程：
灰度化 → 高斯模糊 → 自适应阈值
腐蚀/膨胀去噪 → 投影分割 → 字符标准化 (28×28)

模型选型：
基础方案：图像预处理 + 手动输入
AI方案：CRNN (ResNet18 + BiLSTM + CTC) 自动识别（开发中）

输出：{ "code": "7a9B" }
"""

import cv2
import numpy as np
import base64
import io
from PIL import Image
from typing import Dict, Optional, Any
from rich.console import Console

console = Console()


class CaptchaSolverAgent:
    def __init__(self, mode: str = "manual", model_path: str = None):
        """
        初始化验证码识别代理
        
        Args:
            mode: 识别模式 ('manual', 'ai')
            model_path: AI模型路径（用于ai模式）
        """
        self.mode = mode
        self.model_path = model_path
        self.model = None
        self._init_model()

    def _init_model(self):
        """初始化识别模型"""
        if self.mode == "ai":
            if self.model_path:
                try:
                    # 这里将加载训练好的CRNN模型
                    console.print("🔍 AI识别模型已初始化", style="green")
                    # TODO: 实现模型加载逻辑
                    # self.model = torch.load(self.model_path)
                except Exception as e:
                    console.print(f"❌ AI模型加载失败：{e}，回退到手动模式", style="red")
                    self.mode = "manual"
                    self.model = None
            else:
                console.print("⚠️ AI模式需要指定模型路径，回退到手动模式", style="yellow")
                self.mode = "manual"
        elif self.mode == "manual":
            # 手动输入模式，不需要初始化任何模型
            self.model = None
        else:
            console.print("⚠️ 未知识别模式，使用手动输入", style="yellow")
            self.mode = "manual"

    def preprocess_image(self, image_data: bytes) -> np.ndarray:
        """
        预处理验证码图片
        
        Args:
            image_data: 图片字节数据
            
        Returns:
            预处理后的图片数组
        """
        try:
            # 将字节数据转换为图片
            image = Image.open(io.BytesIO(image_data))
            img_array = np.array(image)
            
            # 如果是 RGBA，转换为 RGB
            if img_array.shape[2] == 4:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
            
            # 转为 BGR 格式（OpenCV 标准）
            img = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            # 1. 转灰度
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # 2. 中值滤波（降噪）
            blurred = cv2.medianBlur(gray, 3)
            
            # 3. 阈值处理（字符前景提取）
            _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            # 4. 干扰线去除
            cleaned = self._remove_interference(img, thresh)
            
            # 5. 形态学操作去噪
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)
            
            console.print("🖼️ 图片预处理完成", style="blue")
            return cleaned
            
        except Exception as e:
            console.print(f"❌ 图片预处理失败：{e}", style="red")
            return None

    def _remove_interference(self, original_img: np.ndarray, thresh_img: np.ndarray) -> np.ndarray:
        """
        去除红色竖线和网格干扰
        
        Args:
            original_img: 原始彩色图片
            thresh_img: 二值化图片
            
        Returns:
            去除干扰后的图片
        """
        try:
            # 转换到 HSV 颜色空间
            hsv = cv2.cvtColor(original_img, cv2.COLOR_BGR2HSV)
            
            # 红色范围掩膜（注意红色在HSV中有两个区段）
            lower_red1 = np.array([0, 70, 50])
            upper_red1 = np.array([10, 255, 255])
            lower_red2 = np.array([170, 70, 50])
            upper_red2 = np.array([180, 255, 255])
            mask_red = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(hsv, lower_red2, upper_red2)
            
            # 蓝色范围掩膜（网格线）
            lower_blue = np.array([100, 80, 50])
            upper_blue = np.array([140, 255, 255])
            mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
            
            # 合并干扰掩膜
            mask_interference = cv2.bitwise_or(mask_red, mask_blue)
            
            # 使用 inpainting 去除干扰
            img_inpainted = cv2.inpaint(original_img, mask_interference, 3, cv2.INPAINT_TELEA)
            
            # 重新灰度化和二值化
            gray_clean = cv2.cvtColor(img_inpainted, cv2.COLOR_BGR2GRAY)
            _, clean_thresh = cv2.threshold(gray_clean, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            return clean_thresh
            
        except Exception as e:
            console.print(f"⚠️ 干扰去除失败，使用原始二值化图：{e}", style="yellow")
            return thresh_img

    def recognize_text(self, image_data: bytes) -> Dict[str, Any]:
        """
        识别验证码文本
        
        Args:
            image_data: 验证码图片字节数据
            
        Returns:
            识别结果字典 {"code": "认识的文本", "confidence": 置信度}
        """
        try:
            # 预处理图片
            processed_img = self.preprocess_image(image_data)
            if processed_img is None:
                return {"code": "", "confidence": 0.0, "error": "预处理失败"}

            # 使用 AI 模型识别
            if self.mode == "ai" and self.model is not None:
                try:
                    # TODO: 实现AI模型推理逻辑
                    # 这里将调用训练好的CRNN模型进行推理
                    # predicted_text = self.model.predict(processed_img)
                    
                    console.print("🤖 AI模型识别功能开发中...", style="yellow")
                    return {"code": "", "confidence": 0.0, "manual_input_required": True}
                    
                except Exception as e:
                    console.print(f"❌ AI模型推理失败：{e}", style="red")
                    return {"code": "", "confidence": 0.0, "error": str(e)}
            
            # 如果 AI 模型不可用，返回需要手动输入的结果
            console.print("⚠️ 自动识别失败，需要手动输入", style="yellow")
            return {"code": "", "confidence": 0.0, "manual_input_required": True}
            
        except Exception as e:
            console.print(f"❌ 验证码识别失败：{e}", style="red")
            return {"code": "", "confidence": 0.0, "error": str(e)}

    def save_processed_image(self, image_data: bytes, save_path: str = "processed_captcha.jpg"):
        """
        保存预处理后的图片用于调试
        
        Args:
            image_data: 原始图片数据
            save_path: 保存路径
        """
        try:
            processed_img = self.preprocess_image(image_data)
            if processed_img is not None:
                cv2.imwrite(save_path, processed_img)
                console.print(f"💾 预处理图片已保存到：{save_path}", style="blue")
        except Exception as e:
            console.print(f"❌ 保存预处理图片失败：{e}", style="red")

    def get_manual_input(self, image_data: bytes) -> str:
        """
        显示验证码图片并获取手动输入
        
        Args:
            image_data: 验证码图片数据
            
        Returns:
            手动输入的验证码
        """
        try:
            # 保存图片到临时文件
            temp_path = "temp_captcha.jpg"
            with open(temp_path, 'wb') as f:
                f.write(image_data)
            
            # 显示图片（如果在支持的环境中）
            try:
                import platform
                if platform.system() == "Darwin":  # macOS
                    import subprocess
                    subprocess.run(["open", temp_path], check=False)
                elif platform.system() == "Windows":
                    import os
                    os.startfile(temp_path)
                elif platform.system() == "Linux":
                    import subprocess
                    subprocess.run(["xdg-open", temp_path], check=False)
                else:
                    # 尝试使用PIL显示
                    image = Image.open(io.BytesIO(image_data))
                    image.show()
                console.print("🖼️ 验证码图片已显示", style="blue")
            except Exception as show_error:
                console.print(f"🖼️ 验证码图片已保存到：{temp_path}，请手动查看", style="blue")
                console.print(f"显示图片失败：{show_error}", style="yellow")
            
            # 强制刷新输出缓冲区
            import sys
            sys.stdout.flush()
            
            # 获取用户输入，使用更明确的提示
            console.print("⌨️ 请查看验证码图片并输入验证码内容", style="cyan")
            try:
                captcha_input = input("请输入验证码：").strip()
                if captcha_input:
                    console.print(f"✅ 已接收验证码输入：{captcha_input}", style="green")
                    return captcha_input
                else:
                    console.print("⚠️ 验证码输入为空", style="yellow")
                    return ""
            except (EOFError, KeyboardInterrupt):
                console.print("❌ 用户取消输入", style="red")
                return ""
            
        except Exception as e:
            console.print(f"❌ 获取手动输入失败：{e}", style="red")
            return ""

    def solve_captcha(self, image_data: bytes, manual_fallback: bool = True) -> str:
        """
        解决验证码（主入口方法）
        
        Args:
            image_data: 验证码图片数据
            manual_fallback: 是否允许手动输入作为回退方案
            
        Returns:
            验证码文本
        """
        # 首先尝试自动识别
        result = self.recognize_text(image_data)
        
        if result.get("code") and result.get("confidence", 0) > 0.5:
            return result["code"]
        
        # 如果自动识别失败且允许手动输入
        if manual_fallback:
            console.print("🤖 自动识别失败，切换到手动输入模式", style="yellow")
            return self.get_manual_input(image_data)
        
        console.print("❌ 验证码识别失败", style="red")
        return "" 