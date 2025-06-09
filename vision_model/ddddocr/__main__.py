# coding=utf-8
"""
ddddocr命令行入口点
支持通过 python -m ddddocr api 启动HTTP服务
"""

import sys
import argparse
import json
from pathlib import Path


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="DDDDOCR 带带弟弟OCR通用验证码识别工具",
        prog="python -m ddddocr"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # API服务命令
    api_parser = subparsers.add_parser("api", help="启动HTTP API服务")
    api_parser.add_argument("--host", default="0.0.0.0", help="服务器主机地址 (默认: 0.0.0.0)")
    api_parser.add_argument("--port", type=int, default=8000, help="服务器端口 (默认: 8000)")
    api_parser.add_argument("--workers", type=int, default=1, help="工作进程数 (默认: 1)")
    api_parser.add_argument("--reload", action="store_true", help="启用自动重载 (开发模式)")
    api_parser.add_argument("--config", help="配置文件路径 (JSON格式)")
    api_parser.add_argument("--log-level", default="info", 
                           choices=["critical", "error", "warning", "info", "debug", "trace"],
                           help="日志级别 (默认: info)")
    
    # 颜色过滤器信息命令
    color_parser = subparsers.add_parser("colors", help="显示可用的颜色过滤器预设")
    
    # 版本信息命令
    version_parser = subparsers.add_parser("version", help="显示版本信息")
    
    # 示例命令
    example_parser = subparsers.add_parser("example", help="显示使用示例")
    
    args = parser.parse_args()
    
    if args.command == "api":
        start_api_server(args)
    elif args.command == "colors":
        show_color_presets()
    elif args.command == "version":
        show_version()
    elif args.command == "example":
        show_examples()
    else:
        parser.print_help()


def start_api_server(args):
    """启动API服务器"""
    try:
        from .api import run_server
        
        # 加载配置文件
        config = {}
        if args.config:
            config_path = Path(args.config)
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                print(f"已加载配置文件: {config_path}")
            else:
                print(f"警告: 配置文件不存在: {config_path}")
        
        # 合并命令行参数和配置文件
        server_config = {
            "host": config.get("host", args.host),
            "port": config.get("port", args.port),
            "workers": config.get("workers", args.workers),
            "reload": config.get("reload", args.reload),
            "log_level": config.get("log_level", args.log_level)
        }
        
        print("=" * 60)
        print("DDDDOCR API 服务启动中...")
        print("=" * 60)
        print(f"主机地址: {server_config['host']}")
        print(f"端口: {server_config['port']}")
        print(f"工作进程: {server_config['workers']}")
        print(f"自动重载: {server_config['reload']}")
        print(f"日志级别: {server_config['log_level']}")
        print("=" * 60)
        
        # 启动服务器
        run_server(**server_config)
        
    except ImportError as e:
        print(f"错误: 缺少API服务依赖，请安装: pip install fastapi uvicorn")
        print(f"详细错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"启动API服务失败: {e}")
        sys.exit(1)


def show_color_presets():
    """显示颜色过滤器预设"""
    try:
        from . import ColorFilter
        
        print("DDDDOCR 颜色过滤器预设")
        print("=" * 40)
        
        colors = ColorFilter.get_available_colors()
        for i, color in enumerate(colors, 1):
            ranges = ColorFilter.COLOR_PRESETS[color]
            print(f"{i:2d}. {color:8s} - HSV范围: {ranges}")
        
        print("\n使用示例:")
        print("  # 使用预设颜色")
        print("  ocr.classification(image, color_filter_colors=['red', 'blue'])")
        print("  # 使用自定义HSV范围")
        print("  ocr.classification(image, color_filter_custom_ranges=[((0,50,50), (10,255,255))])")
        
    except ImportError as e:
        print(f"错误: 无法导入颜色过滤器: {e}")


def show_version():
    """显示版本信息"""
    try:
        import ddddocr
        print("DDDDOCR 版本信息")
        print("=" * 30)
        print(f"版本: 1.6.0")
        print(f"作者: sml2h3")
        print(f"项目地址: https://github.com/sml2h3/ddddocr")
        print(f"文档地址: https://github.com/sml2h3/ddddocr/blob/master/README.md")
        
    except Exception as e:
        print(f"获取版本信息失败: {e}")


def show_examples():
    """显示使用示例"""
    examples = """
DDDDOCR 使用示例
===============

1. 基础OCR识别:
   import ddddocr
   ocr = ddddocr.DdddOcr()
   with open('captcha.jpg', 'rb') as f:
       image = f.read()
   result = ocr.classification(image)
   print(result)

2. 颜色过滤OCR识别:
   import ddddocr
   ocr = ddddocr.DdddOcr()
   with open('captcha.jpg', 'rb') as f:
       image = f.read()
   # 只保留红色和蓝色文字
   result = ocr.classification(image, color_filter_colors=['red', 'blue'])
   print(result)

3. 目标检测:
   import ddddocr
   det = ddddocr.DdddOcr(det=True)
   with open('image.jpg', 'rb') as f:
       image = f.read()
   bboxes = det.detection(image)
   print(bboxes)

4. 滑块匹配:
   import ddddocr
   slide = ddddocr.DdddOcr(det=False, ocr=False)
   with open('target.png', 'rb') as f:
       target = f.read()
   with open('background.png', 'rb') as f:
       background = f.read()
   result = slide.slide_match(target, background)
   print(result)

5. 启动API服务:
   python -m ddddocr api --host 0.0.0.0 --port 8000

6. 查看可用颜色:
   python -m ddddocr colors

API服务使用示例:
===============

1. 初始化服务:
   POST http://localhost:8000/initialize
   {
       "ocr": true,
       "det": false
   }

2. OCR识别:
   POST http://localhost:8000/ocr
   {
       "image": "base64_encoded_image",
       "color_filter_colors": ["red", "blue"]
   }

3. 查看API文档:
   http://localhost:8000/docs
"""
    print(examples)


if __name__ == "__main__":
    main()
