# coding=utf-8
"""
工具函数模块
提供图像处理、异常处理、输入验证等工具函数
"""

from .image_io import base64_to_image, get_img_base64, png_rgba_black_preprocess
from .exceptions import DDDDOCRError, ModelLoadError, ImageProcessError
from .validators import validate_image_input, validate_model_config

__all__ = [
    'base64_to_image',
    'get_img_base64', 
    'png_rgba_black_preprocess',
    'DDDDOCRError',
    'ModelLoadError',
    'ImageProcessError',
    'validate_image_input',
    'validate_model_config'
]
