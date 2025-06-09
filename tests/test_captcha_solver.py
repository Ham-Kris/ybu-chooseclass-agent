"""
验证码识别代理测试
"""

import pytest
import numpy as np
from PIL import Image
import io
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.captcha_solver_agent import CaptchaSolverAgent


class TestCaptchaSolverAgent:
    
    def setup_method(self):
        """测试前准备"""
        self.agent = CaptchaSolverAgent(engine="paddle")
    
    def test_init(self):
        """测试初始化"""
        assert self.agent.engine == "paddle"
        assert self.agent.model_path is None
    
    def test_preprocess_image(self):
        """测试图片预处理"""
        # 创建测试图片
        test_image = Image.new('RGB', (100, 40), color='white')
        img_bytes = io.BytesIO()
        test_image.save(img_bytes, format='PNG')
        img_data = img_bytes.getvalue()
        
        # 测试预处理
        processed = self.agent.preprocess_image(img_data)
        
        assert processed is not None
        assert isinstance(processed, np.ndarray)
    
    def test_recognize_text_without_ocr(self):
        """测试在没有OCR引擎时的文本识别"""
        # 创建没有OCR的代理
        agent_no_ocr = CaptchaSolverAgent(engine="none")
        
        # 创建测试图片
        test_image = Image.new('RGB', (100, 40), color='white')
        img_bytes = io.BytesIO()
        test_image.save(img_bytes, format='PNG')
        img_data = img_bytes.getvalue()
        
        result = agent_no_ocr.recognize_text(img_data)
        
        assert isinstance(result, dict)
        assert 'code' in result
        assert 'confidence' in result
    
    def test_solve_captcha_fallback(self):
        """测试验证码解决的回退机制"""
        # 创建测试图片
        test_image = Image.new('RGB', (100, 40), color='white')
        img_bytes = io.BytesIO()
        test_image.save(img_bytes, format='PNG')
        img_data = img_bytes.getvalue()
        
        # 测试不允许手动输入的情况
        result = self.agent.solve_captcha(img_data, manual_fallback=False)
        
        # 应该返回空字符串或自动识别结果
        assert isinstance(result, str)


if __name__ == "__main__":
    pytest.main([__file__]) 