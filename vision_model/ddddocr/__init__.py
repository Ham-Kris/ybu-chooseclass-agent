# coding=utf-8
"""
DDDDOCR - 带带弟弟OCR通用验证码识别
重构版本 - 模块化架构

主要功能：
- OCR文字识别
- 目标检测
- 滑块匹配
- 颜色过滤
- HTTP API服务
- MCP协议支持

使用示例：
    import ddddocr
    
    # OCR识别
    ocr = ddddocr.DdddOcr()
    result = ocr.classification(image)
    
    # 颜色过滤OCR
    result = ocr.classification(image, color_filter_colors=['red', 'blue'])
    
    # 目标检测
    det = ddddocr.DdddOcr(det=True)
    bboxes = det.detection(image)
    
    # 滑块匹配
    slide = ddddocr.DdddOcr(det=False, ocr=False)
    result = slide.slide_match(target, background)
"""

import warnings
warnings.filterwarnings('ignore')

# 版本信息
__version__ = "1.6.0"
__author__ = "sml2h3"
__email__ = "sml2h3@gmail.com"
__url__ = "https://github.com/sml2h3/ddddocr"

# 导入核心功能类
from .compat.legacy import DdddOcr
from .preprocessing.color_filter import ColorFilter

# 导入工具函数（保持向后兼容）
from .utils.image_io import base64_to_image, get_img_base64, png_rgba_black_preprocess
from .utils.exceptions import DDDDOCRError, ModelLoadError, ImageProcessError, TypeError

# 导入新的模块化组件（供高级用户使用）
from .core import OCREngine, DetectionEngine, SlideEngine
from .preprocessing import ImageProcessor
from .models import ModelLoader, CharsetManager

# 公共接口
__all__ = [
    # 主要类（向后兼容）
    'DdddOcr',
    'ColorFilter',
    
    # 工具函数（向后兼容）
    'base64_to_image',
    'get_img_base64', 
    'png_rgba_black_preprocess',
    
    # 异常类
    'DDDDOCRError',
    'ModelLoadError',
    'ImageProcessError',
    'TypeError',
    
    # 新的模块化组件
    'OCREngine',
    'DetectionEngine', 
    'SlideEngine',
    'ImageProcessor',
    'ModelLoader',
    'CharsetManager',
    
    # 版本信息
    '__version__',
    '__author__',
    '__email__',
    '__url__'
]

# 设置ONNX运行时日志级别
try:
    import onnxruntime
    onnxruntime.set_default_logger_severity(3)
except ImportError:
    pass

# 兼容性处理：确保PIL有ANTIALIAS属性
try:
    from PIL import Image
    if not hasattr(Image, 'ANTIALIAS'):
        setattr(Image, 'ANTIALIAS', Image.LANCZOS)
except ImportError:
    pass
