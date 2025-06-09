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
                'img[src*="captcha"]',              # 包含captcha的图片
                'img[src*="verify"]',               # 包含verify的图片
                'img[onclick*="refresh"], img[onclick*="change"]'  # 可刷新的验证码图片
            ]
            
            captcha_element = None
            found_selector = None
            
            # 逐个尝试选择器
            for selector in captcha_selectors:
                try:
                    captcha_element = await self.page.query_selector(selector)
                    if captcha_element and await captcha_element.is_visible():
                        found_selector = selector
                        console.print(f"✅ 找到验证码图片：{selector}", style="green")
                        break
                except:
                    continue
            
            # 如果在主页面找不到，尝试在iframe中查找
            if not captcha_element:
                try:
                    iframe = await self.page.query_selector('iframe[src*="xsxk_xdxx"], iframe[name="mainFrame"]')
                    if iframe:
                        iframe_content = await iframe.content_frame()
                        if iframe_content:
                            for selector in captcha_selectors:
                                try:
                                    captcha_element = await iframe_content.query_selector(selector)
                                    if captcha_element and await captcha_element.is_visible():
                                        console.print(f"✅ 在iframe中找到验证码图片：{selector}", style="green")
                                        # 使用iframe内容进行截图
                                        return await captcha_element.screenshot()
                                except:
                                    continue
                except:
                    pass
            
            if not captcha_element:
                console.print("❌ 未找到验证码图片元素", style="red")
                return None
            
            # 截取验证码图片
            captcha_image = await captcha_element.screenshot()
            console.print("📸 验证码图片截取成功", style="blue")
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
            if await self._check_auth_status():
                await self._save_cookies()
                console.print("✅ 登录成功", style="green")
                return True
            else:
                console.print("❌ 登录失败", style="red")
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
            
            # 步骤1：进入课程选择页面
            if is_retake:
                course_url = f"{base_url_http}/jsxsd/xsxkkc/comeInGgxxkxk_Ybdx?kcid={course_id}&isdyfxkc=0"
            else:
                course_url = f"{base_url_http}/jsxsd/xsxkkc/comeInBxxk_Ybdx?kcid={course_id}&isdyfxkc=0"
            
            console.print(f"📖 进入课程页面：{course_url[:50]}...", style="blue")
            await self.page.goto(course_url, wait_until="networkidle")
            
            # 步骤2：等待并解析教学班表格
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
                    
                    # 步骤4：处理确认弹窗
                    try:
                        # 等待弹窗出现并点击确认
                        await self.page.wait_for_function("() => window.confirm !== undefined", timeout=3000)
                        console.print("✅ 确认选课弹窗", style="blue")
                        # Playwright 会自动处理 confirm 弹窗并返回 true
                    except Exception as e:
                        console.print(f"⚠️ 未检测到确认弹窗：{e}", style="yellow")
                    
                    # 步骤5：等待验证码界面
                    try:
                        # 等待验证码弹窗出现，检查多种可能的位置
                        console.print("⏳ 等待验证码界面...", style="blue")
                        
                        # 检查是否有验证码弹窗dialog
                        dialog_found = False
                        iframe_found = False
                        
                        try:
                            # 方法1：检查dialog形式的验证码弹窗
                            await self.page.wait_for_selector('#verifyCodeDiv', timeout=5000)
                            dialog_visible = await self.page.is_visible('#verifyCodeDiv')
                            if dialog_visible:
                                console.print("📝 找到验证码Dialog弹窗", style="blue")
                                dialog_found = True
                        except:
                            pass
                        
                        if not dialog_found:
                            try:
                                # 方法2：检查iframe内的验证码
                                await self.page.wait_for_selector('iframe[src*="xsxk_xdxx"]', timeout=5000)
                                console.print("📝 找到验证码iframe", style="blue")
                                iframe_found = True
                            except:
                                pass
                        
                        if not dialog_found and not iframe_found:
                            # 方法3：直接查找验证码输入框
                            await self.page.wait_for_selector('input[name="verifyCode"], #verifyCode', timeout=5000)
                            console.print("📝 找到验证码输入框", style="blue")
                        
                        # 先刷新验证码图片，确保获取最新的验证码
                        console.print("🔄 刷新验证码图片...", style="blue")
                        try:
                            # 尝试多种可能的验证码图片选择器
                            captcha_img_selectors = [
                                '#kaptchaImage',
                                '#verifyCodeDiv img',
                                'img[src*="kaptcha"]',
                                'img[src*="captcha"]',
                                'img[onclick*="refresh"]',
                                'img[onclick*="change"]'
                            ]
                            
                            captcha_refreshed = False
                            for selector in captcha_img_selectors:
                                try:
                                    captcha_img = await self.page.query_selector(selector)
                                    if captcha_img and await captcha_img.is_visible():
                                        console.print(f"🎯 点击刷新验证码：{selector}", style="blue")
                                        await captcha_img.click()
                                        captcha_refreshed = True
                                        break
                                except:
                                    continue
                            
                            if captcha_refreshed:
                                # 等待验证码刷新完成
                                await self.page.wait_for_timeout(1000)
                                console.print("✅ 验证码已刷新", style="green")
                            else:
                                console.print("⚠️ 未找到可刷新的验证码图片，使用当前验证码", style="yellow")
                                
                        except Exception as e:
                            console.print(f"⚠️ 刷新验证码失败：{e}，使用当前验证码", style="yellow")
                        
                        # 获取验证码图片
                        captcha_image = await self.get_captcha_image()
                        if not captcha_image:
                            console.print("❌ 无法获取验证码图片", style="red")
                            return False
                        
                        # 使用验证码识别服务
                        from agents.captcha_solver_agent import CaptchaSolverAgent
                        captcha_solver = CaptchaSolverAgent()
                        captcha_code = captcha_solver.solve_captcha(captcha_image, manual_fallback=True)
                        
                        if not captcha_code:
                            console.print("❌ 验证码识别失败", style="red")
                            return False
                        
                        console.print(f"🔤 验证码：{captcha_code}", style="blue")
                        
                        # 步骤6：输入验证码并提交
                        if dialog_found:
                            # Dialog形式 - 直接操作
                            await self.page.fill('#verifyCode', captcha_code)
                            
                            # 等待输入被保存
                            await self.page.wait_for_timeout(500)
                            
                            # 验证输入是否被正确保存
                            saved_code = await self.page.evaluate("document.getElementById('verifyCode').value")
                            console.print(f"📝 验证码输入已保存：{saved_code}", style="blue")
                            
                            # 在提交前，确保隐藏字段被正确设置
                            console.print("🔧 检查验证码提交所需的隐藏字段...", style="blue")
                            try:
                                # 获取当前选择的教学班信息
                                current_jx0404id = selected_jx0404id
                                current_kcid = best_class.get('kcid', course_id) if best_class else course_id
                                
                                # 检查并设置隐藏字段
                                await self.page.evaluate(f"""
                                    // 设置验证码选课所需的隐藏字段
                                    document.getElementById('yzmxkJx0404id').value = '{current_jx0404id}';
                                    document.getElementById('yzmxkXkzy').value = '';  // 选课志愿，通常为空
                                    document.getElementById('yzmxkTrjf').value = '';  // 投入积分，通常为空
                                    document.getElementById('yzmxkKcid').value = '{current_kcid}';
                                    document.getElementById('yzmxkCfbs').value = 'null';  // 重复标识
                                """)
                                
                                # 验证隐藏字段是否设置成功
                                jx0404id_value = await self.page.evaluate("document.getElementById('yzmxkJx0404id').value")
                                kcid_value = await self.page.evaluate("document.getElementById('yzmxkKcid').value")
                                console.print(f"✅ 隐藏字段设置完成 - jx0404id: {jx0404id_value}, kcid: {kcid_value}", style="green")
                                
                            except Exception as field_error:
                                console.print(f"⚠️ 设置隐藏字段时出错：{field_error}，继续提交", style="yellow")
                            
                            # 设置alert监听器来捕获JavaScript alert信息
                            alert_messages = []
                            
                            def handle_dialog(dialog):
                                alert_messages.append(dialog.message)
                                console.print(f"🚨 捕获到alert消息：{dialog.message}", style="yellow")
                                dialog.accept()
                            
                            self.page.on('dialog', handle_dialog)
                            
                            # 查找提交按钮 - 支持多种形式
                            submit_selectors = [
                                '#changeVerifyCode',
                                'a[name="changeVerifyCode"]',
                                'a[onclick*="changeVerifyCode"]',
                                '#verifyCodeDiv input[type="submit"]',
                                '#verifyCodeDiv button[type="submit"]'
                            ]
                            
                            submit_clicked = False
                            for selector in submit_selectors:
                                try:
                                    submit_btn = await self.page.query_selector(selector)
                                    if submit_btn and await submit_btn.is_visible():
                                        console.print(f"🎯 点击提交按钮：{selector}", style="blue")
                                        await submit_btn.click()
                                        submit_clicked = True
                                        break
                                except:
                                    continue
                            
                            if not submit_clicked:
                                console.print("⚠️ 未找到提交按钮，尝试直接调用JavaScript函数", style="yellow")
                                await self.page.evaluate("if(typeof changeVerifyCode === 'function') changeVerifyCode();")
                            
                            # 等待AJAX请求完成
                            await self.page.wait_for_timeout(2000)
                            
                            # 如果有alert消息，显示它们
                            if alert_messages:
                                for msg in alert_messages:
                                    console.print(f"📢 服务器消息：{msg}", style="cyan")
                        elif iframe_found:
                            # iframe形式 - 需要切换到iframe内部
                            iframe = await self.page.query_selector('iframe[src*="xsxk_xdxx"]')
                            if iframe:
                                iframe_content = await iframe.content_frame()
                                if iframe_content:
                                    await iframe_content.fill('input[name="verifyCode"], #verifyCode', captcha_code)
                                    
                                    # 在iframe内查找提交按钮
                                    submit_selectors = ['#changeVerifyCode', 'a[name="changeVerifyCode"]', 'input[type="submit"]']
                                    for selector in submit_selectors:
                                        try:
                                            submit_btn = await iframe_content.query_selector(selector)
                                            if submit_btn:
                                                await submit_btn.click()
                                                break
                                        except:
                                            continue
                        else:
                            # 直接形式
                            input_selectors = ['#verifyCode', 'input[name="verifyCode"]']
                            for selector in input_selectors:
                                try:
                                    input_elem = await self.page.query_selector(selector)
                                    if input_elem:
                                        await input_elem.fill(captcha_code)
                                        break
                                except:
                                    continue
                            
                            # 尝试提交
                            await self.page.keyboard.press('Enter')
                        
                        # 等待提交结果
                        await self.page.wait_for_load_state("networkidle", timeout=10000)
                        
                        # 检查选课结果
                        final_content = await self.page.content()
                        
                        # 保存最终页面内容用于调试
                        with open('debug_final_page.html', 'w', encoding='utf-8') as f:
                            f.write(final_content)
                        
                        # 尝试从页面中提取alert或错误信息
                        try:
                            # 检查是否有JavaScript alert
                            alert_text = await self.page.evaluate("""
                                () => {
                                    // 查找页面中的错误信息
                                    const alertElements = document.querySelectorAll('div[class*="alert"], .error-message, .message');
                                    if (alertElements.length > 0) {
                                        return Array.from(alertElements).map(el => el.textContent.trim()).join('; ');
                                    }
                                    return '';
                                }
                            """)
                            if alert_text:
                                console.print(f"📝 页面错误信息：{alert_text}", style="yellow")
                        except:
                            pass
                        
                        if "成功" in final_content or "已选" in final_content:
                            console.print("🎉 选课成功！", style="green")
                            return True
                        elif "验证码" in final_content and ("错误" in final_content or "过期" in final_content):
                            console.print("❌ 验证码错误或过期", style="red")
                            # 提取更具体的错误信息
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(final_content, 'html.parser')
                            
                            # 查找包含验证码错误的文本
                            for script in soup.find_all('script'):
                                if script.string and '验证码' in script.string:
                                    console.print(f"📝 验证码错误详情：{script.string[:200]}...", style="yellow")
                                    break
                            
                            return False
                        else:
                            console.print("❌ 选课失败或状态未知", style="red")
                            console.print(f"💾 完整页面内容已保存到 debug_final_page.html", style="blue")
                            
                            # 查找可能的错误信息
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(final_content, 'html.parser')
                            
                            # 查找alert内容
                            for script in soup.find_all('script'):
                                if script.string and 'alert' in script.string:
                                    console.print(f"📝 可能的错误信息：{script.string[:200]}...", style="yellow")
                                    break
                            
                            console.print(f"页面内容片段：{final_content[:200]}...", style="yellow")
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