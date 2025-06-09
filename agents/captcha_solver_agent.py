"""
CaptchaSolverAgent - 验证码识别代理
职责：接收验证码图，对其进行预处理并输出文本

预处理流程：
二值化处理

模型选型：
基础方案：图像预处理 + 手动输入
AI方案：DdddOcr 自动识别（已集成）
备选方案：手动输入

输出：{ "code": "7a9cB" }
"""


import cv2
import numpy as np
import base64
import io
import sys
import os
from PIL import Image
from typing import Dict, Optional, Any
from rich.console import Console

console = Console()

# 动态导入ddddocr模块
def _import_ddddocr():
    """动态导入ddddocr模块"""
    try:
        import importlib.util
        # 添加ddddocr模块路径
        ddddocr_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'vision_model', 'ddddocr')
        if ddddocr_path not in sys.path:
            sys.path.insert(0, ddddocr_path)
        
        # 使用importlib动态导入
        spec = importlib.util.find_spec('ddddocr')
        if spec is None:
            raise ImportError("找不到ddddocr模块")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.DdddOcr, True
    except Exception as e:
        console.print(f"⚠️ DdddOcr模块导入失败：{e}", style="yellow")
        return None, False

DdddOcr, DDDDOCR_AVAILABLE = _import_ddddocr()


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
            if DDDDOCR_AVAILABLE:
                try:
                    # 初始化DdddOcr模型
                    self.model = DdddOcr(show_ad=False)
                    console.print("🔍 DdddOcr识别模型已初始化", style="green")
                except Exception as e:
                    console.print(f"❌ DdddOcr模型初始化失败：{e}，回退到手动模式", style="red")
                    self.mode = "manual"
                    self.model = None
            else:
                console.print("⚠️ DdddOcr模块不可用，回退到手动模式", style="yellow")
                self.mode = "manual"
                self.model = None
        elif self.mode == "manual":
            # 手动输入模式，不需要初始化任何模型
            self.model = None
        else:
            console.print("⚠️ 未知识别模式，使用手动输入", style="yellow")
            self.mode = "manual"
            self.model = None

    def preprocess_image(self, image_data: bytes) -> bytes:
        """
        预处理验证码图片 - 使用OpenCV OTSU二值化
        
        Args:
            image_data: 图片字节数据
            
        Returns:
            预处理后的图片字节数据
        """
        try:
            # 将字节数据转换为numpy数组
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # 1. 转换为灰度图
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # 2. OTSU自适应二值化
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # 3. 转换回字节数据
            _, buffer = cv2.imencode('.png', binary)
            processed_bytes = buffer.tobytes()
            
            console.print("🖼️ 图片预处理完成（灰度+OTSU二值化）", style="blue")
            return processed_bytes
            
        except Exception as e:
            console.print(f"❌ 图片预处理失败：{e}", style="red")
            return None



    def recognize_text(self, image_data: bytes) -> Dict[str, Any]:
        """
        识别验证码文本
        
        Args:
            image_data: 验证码图片字节数据
            
        Returns:
            识别结果字典 {"code": "认识的文本", "confidence": 置信度}
        """
        try:
            # 使用 DdddOcr 模型识别
            if self.mode == "ai" and self.model is not None:
                try:
                    # 预处理图片（灰度+对比度增强）
                    processed_bytes = self.preprocess_image(image_data)
                    if processed_bytes is None:
                        return {"code": "", "confidence": 0.0, "error": "预处理失败"}
                    
                    # 先尝试预处理后的图像
                    try:
                        result_processed = self.model.classification(processed_bytes)
                        console.print(f"🤖 DdddOcr识别结果（预处理图像）：{result_processed}", style="green")
                        
                        if result_processed and len(result_processed.strip()) > 0:
                            return {"code": result_processed.strip(), "confidence": 0.95}
                    except Exception as e1:
                        console.print(f"⚠️ 预处理图像识别失败：{e1}", style="yellow")
                    
                    # 如果预处理失败，再尝试原始图像
                    try:
                        result_original = self.model.classification(image_data)
                        console.print(f"🤖 DdddOcr识别结果（原始图像）：{result_original}", style="green")
                        
                        if result_original and len(result_original.strip()) > 0:
                            return {"code": result_original.strip(), "confidence": 0.8}
                    except Exception as e2:
                        console.print(f"⚠️ 原始图像识别失败：{e2}", style="yellow")
                    
                    # 如果两种方法都失败，返回需要手动输入
                    console.print("⚠️ DdddOcr自动识别失败，需要手动输入", style="yellow")
                    return {"code": "", "confidence": 0.0, "manual_input_required": True}
                    
                except Exception as e:
                    console.print(f"❌ DdddOcr模型推理失败：{e}", style="red")
                    return {"code": "", "confidence": 0.0, "error": str(e)}
            
            # 如果 AI 模型不可用，返回需要手动输入的结果
            console.print("⚠️ 自动识别不可用，需要手动输入", style="yellow")
            return {"code": "", "confidence": 0.0, "manual_input_required": True}
            
        except Exception as e:
            console.print(f"❌ 验证码识别失败：{e}", style="red")
            return {"code": "", "confidence": 0.0, "error": str(e)}

    def save_processed_image(self, image_data: bytes, save_path: str = "processed_captcha.png"):
        """
        保存预处理后的图片用于调试
        
        Args:
            image_data: 原始图片数据
            save_path: 保存路径
        """
        try:
            processed_bytes = self.preprocess_image(image_data)
            if processed_bytes is not None:
                with open(save_path, 'wb') as f:
                    f.write(processed_bytes)
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