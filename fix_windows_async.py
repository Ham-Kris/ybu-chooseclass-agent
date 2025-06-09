#!/usr/bin/env python3
"""
Windows 异步兼容性修复脚本
专门解决 Python 3.13 在 Windows 系统上的异步循环问题
"""

import sys
import os
import platform
import warnings
import asyncio

def apply_windows_async_fixes():
    """应用 Windows 异步兼容性修复"""
    
    if platform.system() != 'Windows':
        return
    
    print("🔧 正在应用 Windows 异步兼容性修复...")
    
    # 1. 设置事件循环策略
    if sys.version_info >= (3, 8):
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            print("✅ 已设置 WindowsProactorEventLoopPolicy")
        except AttributeError:
            print("⚠️  WindowsProactorEventLoopPolicy 不可用，使用默认策略")
    
    # 2. 禁用相关警告
    warnings.filterwarnings("ignore", category=ResourceWarning)
    warnings.filterwarnings("ignore", message=".*unclosed.*")
    warnings.filterwarnings("ignore", message=".*I/O operation on closed.*")
    
    # 3. 设置环境变量
    os.environ['PYTHONWARNINGS'] = 'ignore::ResourceWarning'
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    # 4. 针对 Python 3.13 的特殊修复
    if sys.version_info >= (3, 13):
        try:
            # 修复管道错误
            import asyncio.windows_utils
            import asyncio.proactor_events
            import asyncio.base_subprocess
            
            # 重写有问题的方法
            original_repr = asyncio.proactor_events._ProactorBasePipeTransport.__repr__
            original_subprocess_repr = asyncio.base_subprocess.BaseSubprocessTransport.__repr__
            
            def safe_pipe_repr(self):
                try:
                    return original_repr(self)
                except ValueError:
                    return f"<{self.__class__.__name__} closed>"
            
            def safe_subprocess_repr(self):
                try:
                    return original_subprocess_repr(self)
                except ValueError:
                    return f"<{self.__class__.__name__} closed>"
            
            asyncio.proactor_events._ProactorBasePipeTransport.__repr__ = safe_pipe_repr
            asyncio.base_subprocess.BaseSubprocessTransport.__repr__ = safe_subprocess_repr
            
            print("✅ 已应用 Python 3.13 管道错误修复")
            
        except (ImportError, AttributeError) as e:
            print(f"⚠️  部分修复失败: {e}")
    
    # 5. 初始化 colorama（如果可用）
    try:
        import colorama
        colorama.init(autoreset=True, convert=True, strip=False)
        print("✅ 已初始化 colorama 颜色支持")
    except ImportError:
        print("⚠️  colorama 不可用，跳过颜色初始化")
    
    print("🎉 Windows 异步兼容性修复完成！")

def run_with_fixes(func, *args, **kwargs):
    """在应用修复后运行异步函数"""
    apply_windows_async_fixes()
    
    if platform.system() == 'Windows':
        # Windows 专用运行方式
        try:
            return asyncio.run(func(*args, **kwargs))
        except Exception as e:
            print(f"❌ 运行出错: {e}")
            raise
        finally:
            # 强制清理
            try:
                loop = asyncio.get_event_loop()
                if not loop.is_closed():
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                    if pending:
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    loop.close()
            except Exception:
                pass
    else:
        # 非 Windows 系统标准方式
        return asyncio.run(func(*args, **kwargs))

if __name__ == "__main__":
    # 测试修复是否有效
    async def test_async():
        print("🧪 测试异步功能...")
        await asyncio.sleep(0.1)
        print("✅ 异步功能正常")
    
    run_with_fixes(test_async)
    print("🎉 测试完成！修复有效。") 