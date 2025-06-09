# coding=utf-8
"""
核心功能模块
提供OCR识别、目标检测、滑块匹配等核心功能
"""

from .base import BaseEngine
from .ocr_engine import OCREngine
from .detection_engine import DetectionEngine
from .slide_engine import SlideEngine

__all__ = [
    'BaseEngine',
    'OCREngine',
    'DetectionEngine',
    'SlideEngine'
]
