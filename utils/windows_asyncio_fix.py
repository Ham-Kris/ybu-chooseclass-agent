"""
Windows 异步兼容性修复工具
解决 Windows 系统下异步事件循环的常见问题
"""

import asyncio
import sys
import platform
import logging
from typing import Any, Callable, Optional


def setup_windows_event_loop() -> None:
    """
    设置 Windows 下的事件循环策略
    修复 Windows 系统下的异步兼容性问题
    """
    if platform.system() != 'Windows':
        return
    
    # Python 3.8+ 的修复
    if sys.version_info >= (3, 8):
        try:
            # 使用 ProactorEventLoop 来避免 Windows 下的异步问题
            if hasattr(asyncio, 'WindowsProactorEventLoopPolicy'):
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                logging.info("已设置 Windows ProactorEventLoop 策略")
            else:
                # 手动设置 ProactorEventLoop
                loop = asyncio.ProactorEventLoop()
                asyncio.set_event_loop(loop)
                logging.info("已手动设置 ProactorEventLoop")
        except (AttributeError, RuntimeError) as e:
            logging.warning(f"设置 Windows 事件循环策略失败：{e}")
    
    # Python 3.7 的修复
    elif sys.version_info >= (3, 7):
        try:
            # 在旧版本中手动创建 ProactorEventLoop
            loop = asyncio.ProactorEventLoop()
            asyncio.set_event_loop(loop)
            logging.info("已为 Python 3.7 设置 ProactorEventLoop")
        except Exception as e:
            logging.warning(f"Python 3.7 事件循环设置失败：{e}")


def fix_subprocess_issues() -> None:
    """
    修复 Windows 下子进程相关的异步问题
    """
    if platform.system() != 'Windows':
        return
    
    try:
        # 设置子进程创建标志
        import subprocess
        if hasattr(subprocess, 'CREATE_NO_WINDOW'):
            # 避免在后台任务中创建控制台窗口
            subprocess._default_creationflags = subprocess.CREATE_NO_WINDOW
    except Exception as e:
        logging.warning(f"设置子进程标志失败：{e}")


def setup_signal_handling() -> None:
    """
    设置 Windows 下的信号处理
    """
    if platform.system() != 'Windows':
        return
    
    try:
        import signal
        
        def signal_handler(signum, frame):
            """信号处理器"""
            logging.info(f"收到信号 {signum}，正在清理...")
            # 这里可以添加清理逻辑
            sys.exit(0)
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
    except Exception as e:
        logging.warning(f"设置信号处理失败：{e}")


def run_with_windows_fixes(main_func: Callable, *args, **kwargs) -> Any:
    """
    使用 Windows 修复运行异步函数
    
    Args:
        main_func: 要运行的异步主函数
        *args: 传递给主函数的位置参数
        **kwargs: 传递给主函数的关键字参数
    
    Returns:
        函数执行结果
    """
    # 应用所有 Windows 修复
    setup_windows_event_loop()
    fix_subprocess_issues()
    setup_signal_handling()
    
    try:
        # 运行异步函数
        if asyncio.iscoroutinefunction(main_func):
            return asyncio.run(main_func(*args, **kwargs))
        else:
            return main_func(*args, **kwargs)
    except KeyboardInterrupt:
        logging.info("用户中断程序执行")
        return None
    except Exception as e:
        logging.error(f"程序执行出错：{e}")
        raise


def get_optimal_loop() -> Optional[asyncio.AbstractEventLoop]:
    """
    获取 Windows 下的最优事件循环
    
    Returns:
        最优的事件循环实例
    """
    if platform.system() != 'Windows':
        return None
    
    try:
        # 在 Windows 上优先使用 ProactorEventLoop
        if hasattr(asyncio, 'ProactorEventLoop'):
            return asyncio.ProactorEventLoop()
        else:
            return asyncio.new_event_loop()
    except Exception as e:
        logging.warning(f"创建最优事件循环失败：{e}")
        return None


class WindowsAsyncioManager:
    """Windows 异步IO管理器"""
    
    def __init__(self):
        self.original_policy = None
        self.loop = None
    
    def __enter__(self):
        """进入上下文管理器"""
        if platform.system() == 'Windows':
            # 保存原始策略
            self.original_policy = asyncio.get_event_loop_policy()
            
            # 设置 Windows 优化策略
            setup_windows_event_loop()
            
            # 获取当前循环
            try:
                self.loop = asyncio.get_event_loop()
            except RuntimeError:
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文管理器"""
        if platform.system() == 'Windows' and self.original_policy:
            # 恢复原始策略
            try:
                asyncio.set_event_loop_policy(self.original_policy)
            except Exception as e:
                logging.warning(f"恢复事件循环策略失败：{e}")
    
    async def run_async(self, coro):
        """运行异步协程"""
        return await coro


# 便捷的装饰器
def windows_async_fix(func):
    """
    Windows 异步修复装饰器
    
    使用方法：
    @windows_async_fix
    async def main():
        pass
    """
    def wrapper(*args, **kwargs):
        return run_with_windows_fixes(func, *args, **kwargs)
    return wrapper


if __name__ == "__main__":
    # 测试代码
    async def test_async():
        print("测试 Windows 异步修复...")
        await asyncio.sleep(1)
        print("测试完成！")
    
    run_with_windows_fixes(test_async) 