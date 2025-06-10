"""
BrowserAgent - 浏览器代理
职责：驱动无头浏览器；暴露高阶方法：login(), fetch_courses(), select_course(id)
技术栈：Playwright（Python），Chromium channel
错误处理：检测 302/401 自动刷新 Cookie；重试 3 次后抛出
"""

import asyncio
import json
import base64
from typing import Dict, List, Optional, Any
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from urllib.parse import urlparse, parse_qs
import re
from rich.console import Console
import os
from agents.captcha_solver_agent import CaptchaSolverAgent

console = Console()


class BrowserAgent:
    def __init__(self, headless: bool = True, user_data_dir: str = None):
        """
        初始化浏览器代理
        
        Args:
            headless: 是否无头模式
            user_data_dir: 用户数据目录，用于持久化 cookies
        """
        self.headless = headless
        self.user_data_dir = user_data_dir
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.base_url = "https://jwxt.ybu.edu.cn"
        self.login_url = f"{self.base_url}/jsxsd/"
        self.cookies_file = "cookies.json"
        self.retry_count = 3
        
        # 初始化验证码识别器（避免重复加载模型）
        captcha_mode = os.getenv('CAPTCHA_MODE', 'ai')  # 默认使用AI识别
        self.captcha_solver = CaptchaSolverAgent(mode=captcha_mode)
        console.print(f"🔍 验证码识别器已初始化（模式：{captcha_mode}）", style="green")

    async def start(self):
        """启动浏览器"""
        playwright = await async_playwright().start()
        
        launch_options = {
            "headless": self.headless,
            "args": ["--no-sandbox", "--disable-setuid-sandbox"]
        }
        
        if self.user_data_dir:
            launch_options["user_data_dir"] = self.user_data_dir
            
        self.browser = await playwright.chromium.launch(**launch_options)
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.page = await self.context.new_page()
        
        # 加载已保存的 cookies
        await self._load_cookies()
        
        console.print("🌐 浏览器代理已启动", style="green")

    async def stop(self):
        """停止浏览器"""
        if self.browser:
            await self.browser.close()
        console.print("🌐 浏览器代理已停止", style="red")

    async def _load_cookies(self):
        """加载保存的 cookies"""
        try:
            with open(self.cookies_file, 'r') as f:
                cookies = json.load(f)
            await self.context.add_cookies(cookies)
            console.print("🍪 已加载保存的 cookies", style="blue")
        except FileNotFoundError:
            console.print("🍪 未找到保存的 cookies 文件", style="yellow")

    async def _save_cookies(self):
        """保存 cookies"""
        cookies = await self.context.cookies()
        with open(self.cookies_file, 'w') as f:
            json.dump(cookies, f, indent=2)
        console.print("🍪 已保存 cookies", style="blue")

    async def _retry_on_auth_error(self, func, *args, **kwargs):
        """在认证错误时重试"""
        for attempt in range(self.retry_count):
            try:
                result = await func(*args, **kwargs)
                if await self._check_auth_status():
                    return result
                else:
                    console.print(f"⚠️ 认证失败，第 {attempt + 1} 次重试", style="yellow")
                    if attempt < self.retry_count - 1:
                        await self._refresh_session()
            except Exception as e:
                console.print(f"❌ 操作失败：{e}", style="red")
                if attempt == self.retry_count - 1:
                    raise
        raise Exception("重试次数已用完，操作失败")

    async def _check_auth_status(self) -> bool:
        """检查认证状态"""
        current_url = self.page.url
        return "jsxsd" in current_url and "login" not in current_url.lower()

    async def _refresh_session(self):
        """刷新会话"""
        await self.page.goto(self.login_url)
        await asyncio.sleep(2)

    async def get_captcha_image(self) -> Optional[bytes]:
        """获取验证码图片"""
        try:
            # 尝试多种可能的验证码图片位置
            captcha_selectors = [
                'img[id*="yzm"], img[src*="yzm"]',  # 包含yzm的图片
                '#verifyCodeDiv img',               # 验证码弹窗中的图片
                '#kaptchaImage',                    # 常见的验证码图片ID
                'img[src*="captcha"]',              # 包含captcha的图片
                'img[src*="verify"]',               # 包含verify的图片
                'img[src*="kaptcha"]',              # 包含kaptcha的图片
                'img[onclick*="refresh"], img[onclick*="change"]',  # 可刷新的验证码图片
                'img[alt*="验证码"]',                # alt属性包含验证码的图片
                'img[title*="验证码"]'               # title属性包含验证码的图片
            ]
            
            captcha_element = None
            found_selector = None
            found_context = "main"
            
            # 1. 首先检查是否有新弹窗页面
            try:
                browser_context = self.page.context
                pages = browser_context.pages
                if len(pages) > 1:
                    # 检查最新的弹窗页面
                    popup_page = pages[-1]
                    console.print("🔍 在弹窗页面中查找验证码图片...", style="blue")
                    
                    for selector in captcha_selectors:
                        try:
                            captcha_element = await popup_page.query_selector(selector)
                            if captcha_element and await captcha_element.is_visible():
                                found_selector = selector
                                found_context = "popup"
                                console.print(f"✅ 在弹窗页面找到验证码图片：{selector}", style="green")
                                return await captcha_element.screenshot()
                        except:
                            continue
            except Exception as popup_error:
                console.print(f"⚠️ 检查弹窗页面验证码失败：{popup_error}", style="yellow")
            
            # 2. 在主页面中查找
            console.print("🔍 在主页面中查找验证码图片...", style="blue")
            for selector in captcha_selectors:
                try:
                    captcha_element = await self.page.query_selector(selector)
                    if captcha_element and await captcha_element.is_visible():
                        found_selector = selector
                        found_context = "main"
                        console.print(f"✅ 在主页面找到验证码图片：{selector}", style="green")
                        break
                except:
                    continue
            
            # 3. 如果在主页面找不到，尝试在iframe中查找
            if not captcha_element:
                try:
                    console.print("🔍 在iframe中查找验证码图片...", style="blue")
                    iframe_selectors = [
                        'iframe[src*="xsxk"]',
                        'iframe[name="mainFrame"]',
                        'iframe#mainFrame',
                        'iframe[src*="verify"]'
                    ]
                    
                    for iframe_selector in iframe_selectors:
                        try:
                            iframe = await self.page.query_selector(iframe_selector)
                            if iframe:
                                iframe_content = await iframe.content_frame()
                                if iframe_content:
                                    for selector in captcha_selectors:
                                        try:
                                            captcha_element = await iframe_content.query_selector(selector)
                                            if captcha_element and await captcha_element.is_visible():
                                                found_selector = selector
                                                found_context = "iframe"
                                                console.print(f"✅ 在iframe中找到验证码图片：{selector}", style="green")
                                                # 使用iframe内容进行截图
                                                return await captcha_element.screenshot()
                                        except:
                                            continue
                        except:
                            continue
                except Exception as iframe_error:
                    console.print(f"⚠️ 检查iframe验证码失败：{iframe_error}", style="yellow")
            
            if not captcha_element:
                console.print("❌ 未找到验证码图片元素", style="red")
                return None
            
            # 截取验证码图片
            captcha_image = await captcha_element.screenshot()
            console.print(f"📸 验证码图片截取成功（来源：{found_context}，选择器：{found_selector}）", style="blue")
            return captcha_image
            
        except Exception as e:
            console.print(f"❌ 获取验证码图片失败：{e}", style="red")
            return None

    async def login(self, username: str, password: str, captcha_code: str = None) -> bool:
        """
        登录系统
        
        Args:
            username: 用户名
            password: 密码
            captcha_code: 验证码（如果需要）
            
        Returns:
            登录是否成功
        """
        try:
            # 使用 HTTP 协议进行登录
            login_url_http = self.login_url.replace('https://', 'http://')
            await self.page.goto(login_url_http)
            await self.page.wait_for_load_state("networkidle")

            # 检查是否需要验证码
            captcha_element = await self.page.query_selector("input[name='verifyCode']")
            if captcha_element and not captcha_code:
                console.print("⚠️ 需要验证码，但未提供", style="yellow")
                return False

            # 填写登录信息
            await self.page.fill("input[name='userAccount']", username)
            await self.page.fill("input[name='userPassword']", password)
            
            if captcha_code:
                await self.page.fill("input[name='verifyCode']", captcha_code)

            # 提交登录表单
            await self.page.click("input[type='submit']")
            await self.page.wait_for_load_state("networkidle")

            # 检查登录状态
            current_url = self.page.url
            current_title = await self.page.title()
            console.print(f"🔍 登录后URL: {current_url}", style="blue")
            console.print(f"🔍 登录后标题: {current_title}", style="blue")
            
            auth_status = await self._check_auth_status()
            console.print(f"🔍 认证状态检查: {auth_status}", style="blue")
            
            if auth_status:
                await self._save_cookies()
                console.print("✅ 登录成功", style="green")
                return True
            else:
                console.print("❌ 登录失败", style="red")
                console.print(f"   URL检查: 包含jsxsd={('jsxsd' in current_url)}, 不包含login={('login' not in current_url.lower())}", style="red")
                return False

        except Exception as e:
            console.print(f"❌ 登录过程中出错：{e}", style="red")
            return False

    async def fetch_courses(self) -> Dict[str, Any]:
        """
        获取课程列表
        
        Returns:
            课程数据字典
        """
        async def _fetch():
            # 直接 POST 请求到选课页面（参考 chooseclass.py）
            console.print("📖 正在请求选课页面...", style="blue")
            
            # 使用正确的 HTTP 协议和路径
            base_url_http = self.base_url.replace('https://', 'http://')
            
            response = await self.page.goto(f"{base_url_http}/jsxsd/xsxk/xklc_view", wait_until="networkidle")
            content = await self.page.content()
            
            # 调试：保存页面内容到文件
            with open('debug_xklc_view.html', 'w', encoding='utf-8') as f:
                f.write(content)
            console.print("🔍 选课页面内容已保存到 debug_xklc_view.html", style="dim")
            
            # 检查是否在选课时间内
            if "未查询到选课轮次数据" in content:
                console.print("⚠️ 当前不在选课时间窗口内，无法获取课程列表", style="yellow")
                console.print("💡 提示：请在学校规定的选课时间内使用此功能", style="blue")
                return {
                    'regular': [],
                    'retake': [],
                    'all': []
                }
            
            # 解析课程代码
            match = re.search(r"onclick=\"xsxkOpen\('([A-Z0-9]+)'\)\"", content)
            if not match:
                # 尝试更宽松的匹配
                match = re.search(r"xsxkOpen\('([^']+)'\)", content)
                if not match:
                    # 进一步调试，查找所有可能的模式
                    patterns = [
                        r"onclick=\"xsxkOpen\('([^']+)'\)\"",
                        r"xsxkOpen\('([^']+)'\)",
                        r"jx0502zbid=([A-Z0-9]+)",
                        r"zbid=([A-Z0-9]+)"
                    ]
                    for pattern in patterns:
                        test_match = re.search(pattern, content)
                        if test_match:
                            console.print(f"🔍 找到匹配模式: {pattern} -> {test_match.group(1)}", style="blue")
                            match = test_match
                            break
                    
                    if not match:
                        console.print("🔍 尝试查找所有包含'Open'的onclick事件", style="blue")
                        open_matches = re.findall(r"onclick=\"[^\"]*Open[^\"]*\"", content)
                        for i, open_match in enumerate(open_matches[:5]):  # 只显示前5个
                            console.print(f"🔍 找到 onclick {i+1}: {open_match}", style="dim")
                        raise Exception("当前不在选课时间内或无可用课程")

            code = match.group(1)
            console.print(f"📚 找到课程代码：{code}", style="blue")

            # 先进入选课系统
            console.print("🔗 进入选课系统...", style="blue")
            await self.page.goto(f"{base_url_http}/jsxsd/xsxk/xsxk_index?jx0502zbid={code}", wait_until="networkidle")
            
            # 等待iframe加载完成
            try:
                await self.page.wait_for_selector('#mainFrame', timeout=10000)
                console.print("📱 iframe加载完成", style="blue")
                
                # 获取iframe
                iframe_element = await self.page.query_selector('#mainFrame')
                iframe = await iframe_element.content_frame()
                
                if iframe:
                    console.print("✅ 成功切换到iframe", style="green")
                    
                    # 等待复选框出现
                    await iframe.wait_for_selector('input#sfkkkc[name="sfkkkc"]', timeout=10000)
                    console.print("✅ 找到'显示当前开课课程'复选框", style="green")
                    
                    # 检查并确保复选框已勾选，并触发doKkkc()函数
                    checkbox_result = await iframe.evaluate('''() => {
                        const checkbox = document.querySelector('input#sfkkkc[name="sfkkkc"]');
                        if (checkbox) {
                            // 确保复选框被勾选
                            const wasChecked = checkbox.checked;
                            if (!checkbox.checked) {
                                checkbox.checked = true;
                            }
                            
                            // 无论复选框之前是否勾选，都触发doKkkc()函数来确保课程列表刷新
                            if (window.doKkkc && typeof window.doKkkc === 'function') {
                                try {
                                    window.doKkkc();
                                    return wasChecked ? 'doKkkc_triggered_already_checked' : 'doKkkc_triggered_now_checked';
                                } catch (e) {
                                    return 'doKkkc_error: ' + e.message;
                                }
                            } else if (checkbox.onclick) {
                                try {
                                    if (typeof checkbox.onclick === 'function') {
                                        checkbox.onclick();
                                    } else {
                                        // 如果onclick是字符串，尝试执行
                                        eval(checkbox.onclick);
                                    }
                                    return 'onclick_triggered';
                                } catch (e) {
                                    return 'onclick_error: ' + e.message;
                                }
                            } else {
                                // 尝试触发change事件
                                const event = new Event('change', { bubbles: true });
                                checkbox.dispatchEvent(event);
                                return 'change_event_triggered';
                            }
                        }
                        return 'checkbox_not_found';
                    }''')
                    
                    console.print(f"🔍 复选框处理结果：{checkbox_result}", style="blue")
                    
                    # 如果触发了doKkkc函数，等待页面刷新
                    if 'triggered' in checkbox_result:
                        console.print("⏳ 等待课程列表刷新...", style="blue")
                        await self.page.wait_for_timeout(5000)
                        
                        # 重新获取iframe（页面可能已刷新）
                        iframe_element = await self.page.query_selector('#mainFrame')
                        iframe = await iframe_element.content_frame()
                    
                    # 获取最终的iframe内容
                    if iframe:
                        iframe_content = await iframe.content()
                        
                        # 调试：保存iframe内容到文件
                        with open('debug_iframe_with_checkbox.html', 'w', encoding='utf-8') as f:
                            f.write(iframe_content)
                        console.print("🔍 iframe内容已保存到 debug_iframe_with_checkbox.html", style="dim")
                        
                        return self._parse_courses(iframe_content)
                    else:
                        raise Exception("无法重新获取iframe内容")
                        
                else:
                    raise Exception("无法获取iframe内容")
                    
            except Exception as e:
                console.print(f"❌ iframe处理失败：{e}", style="red")
                # 回退到直接访问方式
                console.print("🔄 回退到直接访问方式", style="blue")
                await self.page.goto(f"{base_url_http}/jsxsd/xsxk/xsxk_xdxx?xkjzsj=2024-12-22%2011:00&sfkkkc=1", wait_until="networkidle")
                
                # 获取最终页面内容
                content = await self.page.content()
                
                # 调试：保存页面内容到文件
                with open('debug_course_page_fallback.html', 'w', encoding='utf-8') as f:
                    f.write(content)
                console.print("🔍 回退页面内容已保存到 debug_course_page_fallback.html", style="dim")
                
                return self._parse_courses(content)

        return await self._retry_on_auth_error(_fetch)

    def _parse_courses(self, html_content: str) -> Dict[str, Any]:
        """解析课程列表 HTML"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html_content, 'html.parser')
        courses = {
            'regular': [],      # 普通选课
            'retake': [],       # 重修选课
            'all': []           # 所有课程
        }

        # 查找课程表格
        table = soup.find('table', id='dataList')
        if not table:
            console.print("❌ 未找到课程表格", style="red")
            return courses

        # 解析表格行
        rows = table.find('tbody').find_all('tr') if table.find('tbody') else table.find_all('tr')
        
        for row in rows:
            tds = row.find_all('td')
            
            # 跳过表头和分组标题行
            if len(tds) < 7:
                continue
                
            # 查找操作列中的选课链接
            operation_td = tds[-1]  # 最后一列是操作列
            link = operation_td.find('a', href=True)
            
            if not link:
                continue
                
            # 提取课程信息
            try:
                # 基本信息提取
                category1 = tds[0].get_text(strip=True) if tds[0].get_text(strip=True) else None
                category2 = tds[1].get_text(strip=True) if tds[1].get_text(strip=True) else None
                course_code = tds[2].get_text(strip=True)
                course_name = tds[3].get_text(strip=True)
                credits = tds[4].get_text(strip=True)
                course_type = tds[5].get_text(strip=True)  # 必修/选修
                grade = tds[6].get_text(strip=True)
                
                # 解析选课链接
                href = link['href']
                url = f"{self.base_url}{href}" if href.startswith('/') else href
                
                # 提取课程ID
                from urllib.parse import urlparse, parse_qs
                parsed_url = urlparse(url)
                query_params = parse_qs(parsed_url.query)
                course_id = query_params.get('kcid', [None])[0]
                
                if not course_id:
                    continue
                
                # 判断课程类型
                is_retake = 'comeInGgxxkxk_Ybdx' in href and 'cxcktype=1' in href
                course_category = 'retake' if is_retake else 'regular'
                
                course_data = {
                    'id': course_id,
                    'code': course_code,
                    'name': course_name,
                    'credits': credits,
                    'type': course_type,
                    'category1': category1,
                    'category2': category2,
                    'grade': grade,
                    'url': url,
                    'href': href,
                    'is_retake': is_retake,
                    'link_text': link.get_text(strip=True)
                }
                
                courses[course_category].append(course_data)
                courses['all'].append(course_data)
                
            except Exception as e:
                console.print(f"⚠️ 解析课程行时出错：{e}", style="yellow")
                continue

        console.print(f"📚 解析完成：普通选课 {len(courses['regular'])} 门，重修选课 {len(courses['retake'])} 门", style="green")
        return courses

    async def check_course_availability(self, course_id: str, is_retake: bool = False) -> Dict[str, Any]:
        """
        检查课程可用性并获取教学班信息
        
        Args:
            course_id: 课程ID
            is_retake: 是否为重修课程
            
        Returns:
            课程可用性信息，包含所有教学班
        """
        async def _check():
            # 使用 HTTP 协议（参考 chooseclass.py）
            base_url_http = self.base_url.replace('https://', 'http://')
            
            if is_retake:
                # 重修课程的可用性检查URL
                url = f"{base_url_http}/jsxsd/xsxkkc/xsxkGgxxkxk?skls=&skxq=&skjc=&sfym=false&sfct=false&szjylb=&sfxx=true&xkkcid={course_id}&iskbxk="
            else:
                # 普通选课的可用性检查URL
                url = f"{base_url_http}/jsxsd/xsxkkc/xsxkBxxk?xkkcid={course_id}&skls=&skxq=&skjc=&sfct=false&iskbxk=&kx="

            response = await self.page.goto(url, wait_until="networkidle")
            content = await self.page.content()
            
            try:
                data = json.loads(content)
                classes = []
                total_available = 0
                
                if 'aaData' in data and len(data['aaData']) > 0:
                    for class_data in data['aaData']:
                        remaining = int(class_data.get('syrs', '0'))
                        if remaining > 0:
                            total_available += remaining
                            
                        classes.append({
                            'jx0404id': class_data.get('jx0404id', ''),
                            'remaining': remaining,
                            'teacher': class_data.get('teacher', ''),
                            'time': class_data.get('time', ''),
                            'location': class_data.get('location', ''),
                            'available': remaining > 0
                        })
                    
                    return {
                        'available': total_available > 0,
                        'total_remaining': total_available,
                        'classes': classes,
                        'best_class': max(classes, key=lambda x: x['remaining']) if classes else None
                    }
            except (json.JSONDecodeError, KeyError, IndexError):
                pass
                
            return {'available': False, 'total_remaining': 0, 'classes': [], 'best_class': None}

        return await self._retry_on_auth_error(_check)

    async def select_course(self, course_id: str, is_retake: bool, jx0404id: str = None) -> bool:
        """
        完整的选课流程
        
        Args:
            course_id: 课程ID
            is_retake: 是否为重修课程
            jx0404id: 指定的教学班ID（可选，如果不指定则自动选择最佳班级）
            
        Returns:
            选课是否成功
        """
        async def _select():
            # 使用 HTTP 协议
            base_url_http = self.base_url.replace('https://', 'http://')
            
            # 初始化变量，确保作用域正确
            selected_jx0404id = jx0404id  # 使用参数传入的值或None
            best_class = None
            
            # 步骤0：检查已选课程，避免重复选择（仅在第一次执行时检查）
            try:
                console.print("📋 检查是否已选择同名课程...", style="blue")
                enrolled_courses = await self.check_enrolled_courses()
                
                # 先进入课程页面获取课程名称
                if is_retake:
                    course_url = f"{base_url_http}/jsxsd/xsxkkc/comeInGgxxkxk_Ybdx?kcid={course_id}&isdyfxkc=0"
                else:
                    course_url = f"{base_url_http}/jsxsd/xsxkkc/comeInBxxk_Ybdx?kcid={course_id}&isdyfxkc=0"
                
                console.print(f"📖 进入课程页面：{course_url[:50]}...", style="blue")
                await self.page.goto(course_url, wait_until="networkidle")
                
                # 等待表格加载并获取课程名称
                try:
                    await self.page.wait_for_function("""
                        () => {
                            const table = document.querySelector('#dataView');
                            return table && table.rows && table.rows.length > 1;
                        }
                    """, timeout=10000)
                    
                    # 从表格中获取课程名称
                    course_name_element = await self.page.query_selector('#dataView tbody tr td:nth-child(2)')
                    if course_name_element:
                        current_course_name = await course_name_element.text_content()
                        current_course_name = current_course_name.strip()
                        console.print(f"📚 当前课程名称：{current_course_name}", style="cyan")
                        
                        # 检查是否已选择过同名课程
                        if current_course_name in enrolled_courses:
                            console.print(f"⏭️ 课程 '{current_course_name}' 已经选择过，跳过选择", style="yellow")
                            return True  # 返回True表示不需要选择（因为已选）
                        else:
                            console.print(f"✅ 课程 '{current_course_name}' 未选择过，继续选课流程", style="green")
                    else:
                        console.print("⚠️ 无法获取课程名称，继续选课流程", style="yellow")
                        
                except Exception as name_error:
                    console.print(f"⚠️ 获取课程名称失败：{name_error}，继续选课流程", style="yellow")
                    
            except Exception as check_error:
                console.print(f"⚠️ 检查已选课程失败：{check_error}，继续选课流程", style="yellow")
            
            # 步骤1：等待并解析教学班表格
            try:
                # 首先等待页面JavaScript执行
                await self.page.wait_for_load_state("networkidle")
                console.print("⏳ 等待教学班数据加载...", style="blue")
                
                # 等待queryKxkcList函数执行完成，通过检查表格内容来判断
                await self.page.wait_for_function("""
                    () => {
                        const table = document.querySelector('#dataView');
                        return table && table.rows && table.rows.length > 1;
                    }
                """, timeout=30000)
                console.print("✅ 教学班列表加载完成", style="green")
            except Exception as e:
                console.print(f"⚠️ 等待教学班表格超时：{e}", style="yellow")
                
                # 手动触发查询，防止页面JavaScript未正确执行
                try:
                    console.print("🔄 手动触发教学班查询...", style="blue")
                    await self.page.evaluate("queryKxkcList()")
                    
                    # 再次等待表格加载
                    await self.page.wait_for_function("""
                        () => {
                            const table = document.querySelector('#dataView');
                            return table && table.rows && table.rows.length > 1;
                        }
                    """, timeout=15000)
                    console.print("✅ 手动触发成功，教学班列表已加载", style="green")
                except Exception as e2:
                    console.print(f"❌ 手动触发也失败：{e2}", style="red")
            
            # 保存页面内容用于调试
            content = await self.page.content()
            with open('debug_course_page.html', 'w', encoding='utf-8') as f:
                f.write(content)
            console.print("💾 页面内容已保存到 debug_course_page.html", style="blue")
            
            # 如果没有指定教学班ID，选择剩余量最多的班级
            if not selected_jx0404id:
                console.print("🔍 正在查找可用教学班...", style="blue")
                # 解析页面中的教学班信息
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(content, 'html.parser')
                
                max_remaining = 0
                
                # 查找表格中的教学班
                table = soup.find('table', id='dataView')
                if table:
                    console.print("📊 找到教学班表格，开始解析...", style="blue")
                    
                    # 检查是否有"对不起，查询不到任何相关数据"
                    empty_cell = table.find('td', class_='dataTables_empty')
                    if empty_cell and '对不起' in empty_cell.get_text():
                        console.print("❌ 该课程暂无可选教学班（查询不到任何相关数据）", style="red")
                        return False
                    
                    rows = table.find_all('tr')[1:]  # 跳过表头
                    console.print(f"📋 找到 {len(rows)} 个教学班", style="blue")
                    
                    # 过滤掉空数据行
                    valid_rows = []
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) >= 10 and not any('dataTables_empty' in cell.get('class', []) for cell in cells):
                            valid_rows.append(row)
                    
                    if not valid_rows:
                        console.print("❌ 没有找到有效的教学班数据", style="red")
                        return False
                    
                    console.print(f"📋 有效教学班：{len(valid_rows)} 个", style="blue")
                    
                    for i, row in enumerate(valid_rows):
                        cells = row.find_all('td')
                        remaining_text = cells[8].get_text(strip=True)  # 剩余量列（第9列，索引8）
                        course_code = cells[0].get_text(strip=True)  # 课程号
                        course_name = cells[1].get_text(strip=True)  # 课程名
                        teacher = cells[4].get_text(strip=True)  # 老师（第5列，索引4）
                        
                        console.print(f"  📚 班级 {i+1}: {course_name} - 老师: {teacher} - 剩余量: {remaining_text}", style="cyan")
                        
                        try:
                            remaining = int(remaining_text) if remaining_text.isdigit() else 0
                            console.print(f"  📊 解析剩余量：{remaining_text} → {remaining}", style="cyan")
                            
                            if remaining > max_remaining:
                                # 提取教学班ID和课程ID
                                operation_cell = cells[10]  # 操作列（第11列，索引10）
                                link = operation_cell.find('a', href=True)
                                if link:
                                    js_call = link.get('href', '')
                                    console.print(f"  🔗 找到选课链接：{js_call}", style="cyan")
                                    import re
                                    
                                    # 支持两种格式：xsxkFun 和 xsxkOper
                                    match = None
                                    jx0404id_val = None
                                    kcid_val = None
                                    
                                    if 'xsxkFun' in js_call:
                                        match = re.search(r"xsxkFun\('([^']+)','([^']+)','[^']*'\)", js_call)
                                        if match:
                                            jx0404id_val = match.group(1)
                                            kcid_val = match.group(2)
                                            console.print(f"  ✅ 解析xsxkFun：jx0404id={jx0404id_val}, kcid={kcid_val}", style="green")
                                    elif 'xsxkOper' in js_call:
                                        match = re.search(r"xsxkOper\('([^']+)','[^']*','[^']*','([^']+)','[^']*'\)", js_call)
                                        if match:
                                            jx0404id_val = match.group(1)
                                            kcid_val = match.group(2)
                                            console.print(f"  ✅ 解析xsxkOper：jx0404id={jx0404id_val}, kcid={kcid_val}", style="green")
                                    
                                    if match and jx0404id_val and kcid_val:
                                        max_remaining = remaining
                                        best_class = {
                                            'jx0404id': jx0404id_val,
                                            'kcid': kcid_val,
                                            'remaining': remaining,
                                            'teacher': teacher,
                                            'course_name': course_name,
                                            'js_function': 'xsxkOper' if 'xsxkOper' in js_call else 'xsxkFun'
                                        }
                                        console.print(f"  ⭐ 当前最佳班级：{teacher} - {remaining} 个名额", style="green")
                                    else:
                                        console.print(f"  ❌ 无法解析选课链接：{js_call}", style="red")
                                else:
                                    console.print(f"  ❌ 操作列中没有找到链接", style="red")
                        except ValueError as e:
                            console.print(f"  ❌ 解析剩余量失败：{e}", style="red")
                            continue
                else:
                    console.print("❌ 未找到教学班表格", style="red")
                
                if best_class:
                    selected_jx0404id = best_class['jx0404id']
                    console.print(f"✅ 选择教学班：{best_class['teacher']} ({selected_jx0404id})，剩余 {best_class['remaining']} 个名额", style="green")
                else:
                    console.print("❌ 未找到可用的教学班", style="red")
                    return False
            
            # 确保jx0404id有值才继续
            if not selected_jx0404id:
                console.print("❌ 无法确定教学班ID", style="red")
                return False
            
            # 步骤3：点击选课按钮，这会触发 JavaScript 函数
            try:
                # 确定要查找的JavaScript函数
                js_function = best_class.get('js_function', 'xsxkFun') if best_class else 'xsxkFun'
                
                # 查找并点击对应的选课链接
                if js_function == 'xsxkOper':
                    select_link = await self.page.wait_for_selector(f'a[href*="xsxkOper(\'{selected_jx0404id}\'"]', timeout=5000)
                else:
                    select_link = await self.page.wait_for_selector(f'a[href*="xsxkFun(\'{selected_jx0404id}\'"]', timeout=5000)
                
                if select_link:
                    console.print(f"🎯 点击选课按钮（{js_function}）...", style="blue")
                    await select_link.click()
                    
                    # 步骤5：等待验证码界面
                    try:
                        # 等待验证码弹窗出现，检查多种可能的位置
                        console.print("⏳ 等待验证码界面...", style="blue")
                        
                        # 首先等待一下让页面完全加载
                        await self.page.wait_for_timeout(2000)
                        
                        # 检查是否有验证码弹窗dialog
                        dialog_found = False
                        iframe_found = False
                        direct_found = False
                        
                        # 方法1：检查是否有新窗口弹出（选课验证码通常在新窗口）
                        try:
                            # 等待可能的新弹窗页面
                            new_page = None
                            browser_context = self.page.context
                            
                            # 设置超时等待新页面
                            console.print("🔍 检查是否有验证码弹窗页面...", style="blue")
                            await self.page.wait_for_timeout(3000)  # 等待弹窗出现
                            
                            pages = browser_context.pages
                            if len(pages) > 1:
                                new_page = pages[-1]  # 获取最新的页面
                                console.print("📝 找到验证码弹窗页面", style="blue")
                                
                                # 等待验证码页面完全加载
                                await new_page.wait_for_load_state("networkidle")
                                
                                # 查找验证码元素
                                verify_input = await new_page.query_selector('input[name="verifyCode"], #verifyCode')
                                if verify_input:
                                    console.print("✅ 在弹窗页面中找到验证码输入框", style="green")
                                    dialog_found = True
                                    # 使用弹窗页面进行验证码处理
                                    working_page = new_page
                                else:
                                    console.print("⚠️ 弹窗页面中未找到验证码输入框", style="yellow")
                        except Exception as popup_error:
                            console.print(f"⚠️ 检查弹窗页面失败：{popup_error}", style="yellow")
                        
                        if not dialog_found:
                            try:
                                # 方法2：检查主页面中的dialog形式验证码
                                await self.page.wait_for_selector('#verifyCodeDiv, .verifyCodeDiv, [id*="verify"]', timeout=5000)
                                verify_div = await self.page.query_selector('#verifyCodeDiv, .verifyCodeDiv, [id*="verify"]')
                                if verify_div and await verify_div.is_visible():
                                    console.print("📝 找到验证码Dialog弹窗", style="blue")
                                    dialog_found = True
                                    working_page = self.page
                            except:
                                pass
                        
                        if not dialog_found:
                            try:
                                # 方法3：检查iframe内的验证码
                                iframe_selector = 'iframe[src*="xsxk"], iframe[name="mainFrame"], iframe#mainFrame'
                                await self.page.wait_for_selector(iframe_selector, timeout=5000)
                                iframe = await self.page.query_selector(iframe_selector)
                                if iframe:
                                    iframe_content = await iframe.content_frame()
                                    if iframe_content:
                                        verify_input = await iframe_content.query_selector('input[name="verifyCode"], #verifyCode')
                                        if verify_input:
                                            console.print("📝 在iframe中找到验证码", style="blue")
                                            iframe_found = True
                                            working_page = iframe_content
                            except:
                                pass
                        
                        if not dialog_found and not iframe_found:
                            # 方法4：直接在主页面查找验证码输入框
                            try:
                                await self.page.wait_for_selector('input[name="verifyCode"], #verifyCode, input[placeholder*="验证码"]', timeout=5000)
                                console.print("📝 在主页面找到验证码输入框", style="blue")
                                direct_found = True
                                working_page = self.page
                            except:
                                console.print("❌ 未找到任何验证码输入界面", style="red")
                                return False
                        
                        # 确定工作页面
                        if not 'working_page' in locals():
                            working_page = self.page
                        
                        # 先刷新验证码图片，确保获取最新的验证码
                        console.print("🔄 刷新验证码图片...", style="blue")
                        try:
                            # 尝试多种可能的验证码图片选择器
                            captcha_img_selectors = [
                                '#kaptchaImage',
                                '#verifyCodeDiv img',
                                'img[src*="kaptcha"]',
                                'img[src*="captcha"]',
                                'img[src*="verify"]',
                                'img[onclick*="refresh"]',
                                'img[onclick*="change"]',
                                'img[alt*="验证码"]',
                                'img[title*="验证码"]'
                            ]
                            
                            captcha_refreshed = False
                            for selector in captcha_img_selectors:
                                try:
                                    captcha_img = await working_page.query_selector(selector)
                                    if captcha_img and await captcha_img.is_visible():
                                        console.print(f"🎯 点击刷新验证码：{selector}", style="blue")
                                        await captcha_img.click()
                                        captcha_refreshed = True
                                        break
                                except:
                                    continue
                            
                            if captcha_refreshed:
                                # 等待验证码刷新完成
                                await working_page.wait_for_timeout(1500)
                                console.print("✅ 验证码已刷新", style="green")
                            else:
                                console.print("⚠️ 未找到可刷新的验证码图片，使用当前验证码", style="yellow")
                                
                        except Exception as e:
                            console.print(f"⚠️ 刷新验证码失败：{e}，使用当前验证码", style="yellow")
                        
                        # 获取验证码图片
                        captcha_image = await self.get_captcha_image()
                        if not captcha_image:
                            # 如果主页面没有验证码图片，尝试从工作页面获取
                            if working_page != self.page:
                                try:
                                    captcha_selectors = [
                                        'img[src*="kaptcha"]',
                                        'img[src*="captcha"]',
                                        'img[src*="verify"]',
                                        'img[alt*="验证码"]'
                                    ]
                                    
                                    for selector in captcha_selectors:
                                        try:
                                            captcha_element = await working_page.query_selector(selector)
                                            if captcha_element and await captcha_element.is_visible():
                                                captcha_image = await captcha_element.screenshot()
                                                console.print(f"📸 从工作页面获取验证码图片：{selector}", style="blue")
                                                break
                                        except:
                                            continue
                                except Exception as img_error:
                                    console.print(f"❌ 从工作页面获取验证码图片失败：{img_error}", style="red")
                        
                        if not captcha_image:
                            console.print("❌ 无法获取验证码图片", style="red")
                            return False
                        
                        # 使用验证码识别服务
                        captcha_code = self.captcha_solver.solve_captcha(captcha_image, manual_fallback=True)
                        
                        if not captcha_code:
                            console.print("❌ 验证码识别失败", style="red")
                            return False
                        
                        console.print(f"🔤 验证码：{captcha_code}", style="blue")
                        
                        # 步骤6：输入验证码并提交
                        console.print("📝 输入验证码...", style="blue")
                        
                        # 查找验证码输入框的多种可能选择器
                        verify_input_selectors = [
                            'input[name="verifyCode"]',
                            '#verifyCode',
                            'input[placeholder*="验证码"]',
                            'input[type="text"][maxlength="5"]',
                            'input[type="text"][maxlength="4"]'
                        ]
                        
                        input_filled = False
                        for selector in verify_input_selectors:
                            try:
                                verify_input = await working_page.query_selector(selector)
                                if verify_input and await verify_input.is_visible():
                                    await verify_input.fill(captcha_code)
                                    console.print(f"✅ 验证码已输入到：{selector}", style="green")
                                    input_filled = True
                                    break
                            except:
                                continue
                        
                        if not input_filled:
                            console.print("❌ 无法找到验证码输入框", style="red")
                            return False
                        
                        # 等待输入被保存
                        await working_page.wait_for_timeout(500)
                        
                        # 如果是弹窗页面，需要设置隐藏字段
                        if dialog_found and working_page != self.page:
                            console.print("🔧 在弹窗页面设置选课参数...", style="blue")
                            try:
                                # 获取当前选择的教学班信息
                                current_jx0404id = selected_jx0404id
                                current_kcid = best_class.get('kcid', course_id) if best_class else course_id
                                
                                # 在弹窗页面设置隐藏字段
                                await working_page.evaluate(f"""
                                    try {{
                                        // 查找或创建隐藏字段
                                        let form = document.querySelector('form') || document.body;
                                        
                                        // 设置或创建 jx0404id 字段
                                        let jx0404idInput = document.querySelector('input[name="jx0404id"]') || 
                                                           document.getElementById('yzmxkJx0404id');
                                        if (!jx0404idInput) {{
                                            jx0404idInput = document.createElement('input');
                                            jx0404idInput.type = 'hidden';
                                            jx0404idInput.name = 'jx0404id';
                                            form.appendChild(jx0404idInput);
                                        }}
                                        jx0404idInput.value = '{current_jx0404id}';
                                        
                                        // 设置或创建 kcid 字段
                                        let kcidInput = document.querySelector('input[name="kcid"]') || 
                                                       document.getElementById('yzmxkKcid');
                                        if (!kcidInput) {{
                                            kcidInput = document.createElement('input');
                                            kcidInput.type = 'hidden';
                                            kcidInput.name = 'kcid';
                                            form.appendChild(kcidInput);
                                        }}
                                        kcidInput.value = '{current_kcid}';
                                        
                                        // 设置其他必要字段
                                        ['xkzy', 'trjf', 'cfbs'].forEach(name => {{
                                            let input = document.querySelector(`input[name="${{name}}"]`);
                                            if (!input) {{
                                                input = document.createElement('input');
                                                input.type = 'hidden';
                                                input.name = name;
                                                form.appendChild(input);
                                            }}
                                            input.value = name === 'cfbs' ? 'null' : '';
                                        }});
                                        
                                        console.log('隐藏字段已设置');
                                    }} catch(e) {{
                                        console.error('设置隐藏字段失败:', e);
                                    }}
                                """)
                                
                                console.print("✅ 弹窗页面参数设置完成", style="green")
                                
                            except Exception as field_error:
                                console.print(f"⚠️ 设置弹窗参数时出错：{field_error}，继续提交", style="yellow")
                        
                        # 设置alert监听器来捕获JavaScript alert信息
                        alert_messages = []
                        
                        def handle_dialog(dialog):
                            alert_messages.append(dialog.message)
                            console.print(f"🚨 捕获到alert消息：{dialog.message}", style="yellow")
                            dialog.accept()
                        
                        working_page.on('dialog', handle_dialog)
                        
                        # 查找提交按钮 - 支持多种形式
                        submit_selectors = [
                            'input[type="submit"]',
                            'button[type="submit"]',
                            '#changeVerifyCode',
                            'a[name="changeVerifyCode"]',
                            'a[onclick*="changeVerifyCode"]',
                            'a[onclick*="submit"]',
                            'button[onclick*="submit"]',
                            'input[value*="确定"]',
                            'input[value*="提交"]',
                            'button:contains("确定")',
                            'button:contains("提交")'
                        ]
                        
                        submit_clicked = False
                        for selector in submit_selectors:
                            try:
                                submit_btn = await working_page.query_selector(selector)
                                if submit_btn and await submit_btn.is_visible():
                                    console.print(f"🎯 点击提交按钮：{selector}", style="blue")
                                    await submit_btn.click()
                                    submit_clicked = True
                                    break
                            except:
                                continue
                        
                        if not submit_clicked:
                            # 尝试按回车键提交
                            console.print("⚠️ 未找到提交按钮，尝试按回车键提交", style="yellow")
                            try:
                                verify_input = await working_page.query_selector('input[name="verifyCode"], #verifyCode')
                                if verify_input:
                                    await verify_input.press('Enter')
                                    submit_clicked = True
                            except:
                                pass
                        
                        if not submit_clicked:
                            console.print("⚠️ 尝试直接调用JavaScript提交函数", style="yellow")
                            try:
                                # 尝试调用常见的提交函数
                                await working_page.evaluate("""
                                    if(typeof changeVerifyCode === 'function') {
                                        changeVerifyCode();
                                    } else if(typeof submitForm === 'function') {
                                        submitForm();
                                    } else {
                                        // 查找表单并提交
                                        const form = document.querySelector('form');
                                        if(form) form.submit();
                                    }
                                """)
                                submit_clicked = True
                            except Exception as js_error:
                                console.print(f"❌ JavaScript提交失败：{js_error}", style="red")
                        
                        if not submit_clicked:
                            console.print("❌ 无法提交验证码", style="red")
                            return False
                        
                        # 等待提交结果
                        console.print("⏳ 等待提交结果...", style="blue")
                        await working_page.wait_for_timeout(3000)
                        
                        # 等待页面响应
                        try:
                            await working_page.wait_for_load_state("networkidle", timeout=10000)
                        except:
                            console.print("⚠️ 页面加载超时，继续检查结果", style="yellow")
                        
                        # 检查选课结果 - 从工作页面获取内容
                        final_content = await working_page.content()
                        
                        # 如果工作页面是弹窗，也检查主页面的内容
                        if working_page != self.page:
                            try:
                                main_content = await self.page.content()
                                final_content = final_content + "\n" + main_content
                            except:
                                pass
                        
                        # 保存最终页面内容用于调试
                        with open('debug_final_page.html', 'w', encoding='utf-8') as f:
                            f.write(final_content)
                        
                        # 如果有alert消息，优先显示和处理
                        if alert_messages:
                            for msg in alert_messages:
                                console.print(f"📢 服务器消息：{msg}", style="cyan")
                                # 检查alert消息中的成功指示
                                if any(keyword in msg for keyword in ["成功", "已选", "选课成功"]):
                                    console.print("🎉 从alert消息确认选课成功！", style="green")
                                    return True
                                elif any(keyword in msg for keyword in ["失败", "错误", "验证码", "已满"]):
                                    console.print("❌ 从alert消息确认选课失败", style="red")
                                    return False
                        
                        # 如果没有alert消息，分析页面内容
                        console.print("🔍 分析页面内容判断选课结果...", style="blue")
                        
                        # 检查选课结果的关键词
                        success_keywords = ["成功", "已选", "选课成功", "添加成功"]
                        error_keywords = ["失败", "错误", "验证码", "已满", "时间", "冲突", "重复"]
                        
                        # 先检查明显的成功指示
                        if any(keyword in final_content for keyword in success_keywords):
                            console.print("🎉 从页面内容确认选课成功！", style="green")
                            return True
                        
                        # 检查明显的失败指示
                        if any(keyword in final_content for keyword in error_keywords):
                            console.print("❌ 从页面内容确认选课失败", style="red")
                            
                            # 尝试提取具体错误信息
                            try:
                                from bs4 import BeautifulSoup
                                soup = BeautifulSoup(final_content, 'html.parser')
                                
                                # 查找包含错误信息的script标签
                                for script in soup.find_all('script'):
                                    if script.string:
                                        for error_word in error_keywords:
                                            if error_word in script.string:
                                                # 提取alert或其他错误信息
                                                import re
                                                alert_match = re.search(r'alert\s*\(\s*["\']([^"\']+)["\']', script.string)
                                                if alert_match:
                                                    error_msg = alert_match.group(1)
                                                    console.print(f"📝 具体错误信息：{error_msg}", style="yellow")
                                                    break
                                
                                # 查找页面中的错误消息元素
                                error_elements = soup.find_all(['div', 'span', 'p'], 
                                    class_=lambda x: x and any(word in x.lower() for word in ['error', 'alert', 'message', 'warning']))
                                
                                for elem in error_elements:
                                    if elem.get_text().strip():
                                        console.print(f"📝 页面错误元素：{elem.get_text().strip()[:100]}", style="yellow")
                                        break
                                        
                            except Exception as parse_error:
                                console.print(f"⚠️ 解析错误信息失败：{parse_error}", style="yellow")
                            
                            return False
                        
                        # 如果没有明确的成功或失败指示，进行更深入的检查
                        console.print("⚠️ 无法从页面内容明确判断选课结果，进行深入检查", style="yellow")
                        
                        try:
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(final_content, 'html.parser')
                            
                            # 检查页面标题
                            title = soup.find('title')
                            if title:
                                title_text = title.get_text().strip()
                                console.print(f"📖 页面标题：{title_text}", style="blue")
                                
                                if any(keyword in title_text for keyword in success_keywords):
                                    console.print("🎉 从页面标题确认选课成功！", style="green")
                                    return True
                                elif any(keyword in title_text for keyword in error_keywords):
                                    console.print("❌ 从页面标题确认选课失败", style="red")
                                    return False
                            
                            # 检查是否返回到选课主页面
                            if "选课" in final_content and "课程列表" in final_content:
                                console.print("🔄 页面返回到选课主界面，可能需要重新检查课程状态", style="yellow")
                                
                                # 尝试重新获取课程信息来确认选课状态
                                try:
                                    updated_courses = await self.fetch_courses()
                                    
                                    # 检查目标课程是否已被选中
                                    if updated_courses and 'selected_courses' in updated_courses:
                                        selected_course_ids = [course.get('kcid') for course in updated_courses['selected_courses']]
                                        if course_id in selected_course_ids:
                                            console.print("🎉 确认课程已在已选课程列表中！", style="green")
                                            return True
                                        else:
                                            console.print("❌ 课程未在已选课程列表中", style="red")
                                            return False
                                            
                                except Exception as fetch_error:
                                    console.print(f"⚠️ 重新获取课程信息失败：{fetch_error}", style="yellow")
                            
                            # 检查是否有JavaScript重定向或其他指示
                            scripts = soup.find_all('script')
                            for script in scripts:
                                if script.string:
                                    script_content = script.string.strip()
                                    
                                    # 检查是否有重定向
                                    if 'location.href' in script_content or 'window.location' in script_content:
                                        console.print("🔄 检测到页面重定向", style="blue")
                                        
                                        # 等待重定向完成
                                        await working_page.wait_for_timeout(2000)
                                        
                                        # 获取重定向后的页面内容
                                        redirected_content = await working_page.content()
                                        
                                        # 再次检查成功/失败关键词
                                        if any(keyword in redirected_content for keyword in success_keywords):
                                            console.print("🎉 重定向后确认选课成功！", style="green")
                                            return True
                                        elif any(keyword in redirected_content for keyword in error_keywords):
                                            console.print("❌ 重定向后确认选课失败", style="red")
                                            return False
                            
                        except Exception as deep_check_error:
                            console.print(f"⚠️ 深入检查失败：{deep_check_error}", style="yellow")
                        
                        # 最终保存调试信息
                        console.print(f"💾 完整页面内容已保存到 debug_final_page.html", style="blue")
                        console.print(f"📄 页面内容片段：{final_content[:300]}...", style="dim")
                        
                        # 如果所有检查都无法确定结果，返回未知状态
                        console.print("❓ 无法确定选课结果，建议手动检查", style="yellow")
                        return False
                        
                    except Exception as e:
                        console.print(f"❌ 验证码处理失败：{e}", style="red")
                        return False
                        
                else:
                    console.print("❌ 未找到选课按钮", style="red")
                    return False
                    
            except Exception as e:
                console.print(f"❌ 点击选课按钮失败：{e}", style="red")
                return False

        return await self._retry_on_auth_error(_select)

    async def check_enrolled_courses(self) -> List[str]:
        """
        检查已选课程表格，获取已选课程名称列表
        
        Returns:
            已选课程名称列表
        """
        try:
            console.print("🔍 检查已选课程表格...", style="blue")
            
            # 进入选课主页面
            main_url = f"{self.base_url}/jsxsd/xsxk/xsxk_index"
            await self.page.goto(main_url, wait_until="networkidle")
            
            # 等待页面加载完成
            await self.page.wait_for_timeout(2000)
            
            # 解析页面内容获取已选课程
            content = await self.page.content()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            enrolled_courses = []
            
            # 查找已选课程表格
            tables = soup.find_all('table', class_='display')
            for table in tables:
                # 检查表头是否包含课程相关字段
                thead = table.find('thead')
                if thead:
                    headers = [th.get_text(strip=True) for th in thead.find_all('th')]
                    if '课程名' in headers and '选课状态' in headers:
                        console.print("📋 找到已选课程表格", style="green")
                        
                        # 解析表格内容
                        tbody = table.find('tbody')
                        if tbody:
                            rows = tbody.find_all('tr')
                            for row in rows:
                                cells = row.find_all('td')
                                if len(cells) >= 10:  # 确保有足够的列
                                    course_name = cells[1].get_text(strip=True)  # 课程名列
                                    status = cells[9].get_text(strip=True)  # 选课状态列
                                    
                                    # 只统计状态为"选中"的课程
                                    if status == "选中" and course_name:
                                        enrolled_courses.append(course_name)
                                        console.print(f"  📚 已选课程：{course_name}", style="cyan")
                        break
            
            console.print(f"✅ 共找到 {len(enrolled_courses)} 门已选课程", style="green")
            return enrolled_courses
            
        except Exception as e:
            console.print(f"❌ 检查已选课程失败：{e}", style="red")
            return [] 