# by @xuyanhenry
# https://github.com/xuyanhenry/ybu-Grab-classes

import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import json
import time
from PIL import Image
import io
from tkinter import Tk, Label
from PIL import Image, ImageTk
import threading
# 全局变量用于线程间通信
close_window_flag = threading.Event()

def show_image_in_thread(image_data):
    """在单独线程中显示 Tkinter 窗口"""
    
    def check_close():
        """定时检查关闭标志"""
        if close_window_flag.is_set():
            root.destroy()  # 关闭窗口
        else:
            root.after(100, check_close)  # 每100ms检查一次

    # 初始化 Tkinter 窗口
    root = Tk()
    root.title("验证码")
    root.attributes('-topmost', True)  # 置顶窗口

    # 将图片加载并转换为 Tkinter 格式
    image = Image.open(io.BytesIO(image_data))
    tk_image = ImageTk.PhotoImage(image)

    # 创建标签显示图片
    label = Label(root, image=tk_image)
    label.pack()

    # 启动检查关闭标志的任务
    root.after(100, check_close)

    # 运行 Tkinter 主循环
    root.mainloop()


# 1. 创建一个 session 对象
session = requests.Session()


test_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36 QIHU 360SE',
    'cookie': 'JSESSIONID=FA46A955D8C31D25EA1E5F032680BE63;SERVERID=pc3;'
}
while 1:
    response = session.post('http://jwxt.ybu.edu.cn/jsxsd/xsxk/xklc_view', headers=test_headers)
    print(f"Cookies after first request: {session.cookies.get_dict()}")
    response_text=response.text
    # print(response.text)

    match = re.search(r"onclick=\"xsxkOpen\('([A-Z0-9]+)'\)\"", response_text)

    if match:
        urls = []  # 用于存储所有的 URL
        ids=[]
        name=[]
        counter = 1  # 用于序号

        code = match.group(1)  # 提取到的参数值
        print(f"Found code: {code}")
        response = session.post(f'http://jwxt.ybu.edu.cn/jsxsd/xsxk/xsxk_index?jx0502zbid={code}', headers=test_headers)
        # print(response.text)
        response = session.post(f'http://jwxt.ybu.edu.cn/jsxsd/xsxk/xsxk_xdxx?xkjzsj=2024-12-22%2011:00', headers=test_headers)#时间随意，为空好像也行
        # print(response.text)
        response_text=response.text
        soup = BeautifulSoup(response_text, 'html.parser')

        # 找到所有的 <tr> 标签
        trs = soup.find_all('tr')

        # 筛选出包含 href="/jsxsd/xsxkkc/comeInBxxk_Ybdx?kcid= 的 <tr>
        for tr in trs:
            a_tag = tr.find('a', href=True)  # 查找 <a> 标签并检查是否有 href 属性
            if a_tag and "comeInBxxk_Ybdx?kcid=" in a_tag['href']:
                # 获取 <td> 中的文本内容
                tds = tr.find_all('td')
                url = 'http://jwxt.ybu.edu.cn' +  a_tag['href']  # 拼接完整 URL
                parsed_url = urlparse(url)

                # 解析查询参数
                query_params = parse_qs(parsed_url.query)

                # 提取 kcid 的值
                kcid = query_params.get('kcid', [None])[0]

                urls.append(url)
                ids.append(kcid)

                td_texts = [td.get_text(strip=True) for td in tds]  # 获取每个 <td> 的文本并去除前后空格
                course_name = tds[3].get_text(strip=True)
                name.append(course_name)
                # 将每两个 <td> 的文本之间加冒号并拼接成字符串
                result = ' : '.join(td_texts)
                result += f" : {url}"
                # 打印带序号的结果
                print(f"{counter}. {result}")
                # 增加序号
                counter += 1

        profetional = counter - 1  # 记录专业课程的最后一个索引        
        for tr in trs:
            a_tag = tr.find('a', href=True)  # 查找 <a> 标签并检查是否有 href 属性
            if a_tag and "comeInGgxxkxk_Ybdx?kcid=" in a_tag['href']:
                # 获取 <td> 中的文本内容
                tds = tr.find_all('td')
                url = 'http://jwxt.ybu.edu.cn' +  a_tag['href']  # 拼接完整 URL
                parsed_url = urlparse(url)

                # 解析查询参数
                query_params = parse_qs(parsed_url.query)

                # 提取 kcid 的值
                kcid = query_params.get('kcid', [None])[0]
                # 
                # 将 URL 存入数组
                urls.append(url)
                ids.append(kcid)
                # 获取每个 <td> 的文本并去除前后空格
                td_texts = [td.get_text(strip=True) for td in tds]
                course_name = tds[3].get_text(strip=True)
                name.append(course_name)
                # 将每两个 <td> 的文本之间加冒号并拼接成字符串
                result = ' : '.join(td_texts)
                result += f" : {url}"
                # 打印带序号的结果
                print(f"{counter}. {result}")
                # 增加序号
                counter += 1



        for index in range(len(ids)):
            id = ids[index]
            course_name=name[index]
            selected_url = urls[index]
            print(index+1)
            # print(f"正在检查 URL: {selected_url}, id: {id}")
            
            # 发出 POST 请求
            if index <= profetional:
                response = session.post(f'https://jwxt.ybu.edu.cn/jsxsd/xsxkkc/xsxkBxxk?xkkcid={id}&skls=&skxq=&skjc=&sfct=false&iskbxk=&kx=', headers=test_headers)
            if index > profetional:
                response = session.post(f'http://jwxt.ybu.edu.cn/jsxsd/xsxkkc/xsxkGgxxkxk?skls=&skxq=&skjc=&sfym=false&sfct=false&szjylb=&sfxx=true&xkkcid={id}&iskbxk=', headers=test_headers)
            
            # 解析响应内容
            try:
                data = response.text
                # print(data)
                json_data = json.loads(data)

                # 提取 syrs 的值
                if 'aaData' in json_data and len(json_data['aaData']) > 0:
                    syrs_value = json_data['aaData'][0].get('syrs')

                    # 如果 syrs 不为零，打印相关的 URL 和 syrs 值
                    if syrs_value and int(syrs_value) > 0:
                        print(f"课程剩余量: {syrs_value}, name: {course_name},网址：{selected_url}")
                    else:
                        print(f"课程已满:{course_name}")
                else:
                    print(f"查询不到此课程:{course_name}")

                # 如果 syrs 不为零，打印相关的 URL 和 syrs 值
                # if syrs_value and int(syrs_value) > 0:
                #     print(f"剩余课程id: {syrs_value}, URL: {selected_url}")
                # else:
                #     print(f"课程已满")
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                print(f"解析响应时出错，URL: {selected_url}, 错误: {e}")




        


        while True:
            user_input = input("请输入课程对应的序号(exit退出): ")
            if user_input=='exit':
                exit()
            try:
                index = int(user_input) - 1  # 转换为索引
                if 0 <= index < len(urls):
                    # 根据用户选择的序号获取 URL
                    id = ids[index]
                    course_name=name[index]
                    selected_url = urls[index]
                    print(index+1,"name:",course_name,"URL:",selected_url)
                    if index > profetional:
                        sorce = session.post(f'http://jwxt.ybu.edu.cn/jsxsd/xsxkkc/xsxkGgxxkxk?skls=&skxq=&skjc=&sfym=false&sfct=false&szjylb=&sfxx=false&xkkcid={id}&iskbxk=', headers=test_headers)
                        case = 1
                                    
                        data = sorce.json()
                        # 提取 `jx0404id` 的值
                        jx0404id = [item.get("jx0404id") for item in data.get("aaData", [])]
                    # if jx0404id==[]:
                    if index <= profetional:
                        sorce = session.post(f'http://jwxt.ybu.edu.cn/jsxsd/xsxkkc/xsxkBxxk?xkkcid={id}&skls=&skxq=&skjc=&sfct=false&iskbxk=&kx=', headers=test_headers)
                        case = 0
                                                
                                        # http://jwxt.ybu.edu.cn/jsxsd/xsxkkc/xsxkBxxk?xkkcid=59EB22ECFEC64CB6A6EA1D7C3906F501&skls=&skxq=&skjc=&sfct=false&iskbxk=&kx=
                        data = sorce.json()
                        # 提取 `jx0404id` 的值
                        jx0404id = [item.get("jx0404id") for item in data.get("aaData", [])]
                    
                    print(jx0404id)

                    # print(f"正在检查 URL: {selected_url}, id: {id}")
                    xsxk_response = session.post(selected_url, headers=test_headers)
                    # print(xsxk_response.text)
                    response_text=xsxk_response.text
                    if "验证码输入错误，请重试！" in response_text:

                        captcha_url = 'https://jwxt.ybu.edu.cn/jsxsd/sys/kaptcha/handleRequestInternal?82'
                        captcha_response = session.get(captcha_url, headers=test_headers)

                        save_path = 'D:/captcha.jpg'

                        if captcha_response.status_code == 200:
                            with open(save_path, 'wb') as f:
                                f.write(captcha_response.content)
                                print("验证码已保存到:", save_path)
                        image_data = captcha_response.content  # 获取图片数据
                        close_window_flag.clear()
                        tk_thread = threading.Thread(target=show_image_in_thread, args=(image_data,))
                        tk_thread.start()

                        # image = Image.open(io.BytesIO(captcha_response.content))
                        # image.show()

                        captcha_code = input("请输入验证码(exit重选): ")
                        if captcha_code=='exit':
                            close_window_flag.set()
                            continue
                        # print(f"https://jwxt.ybu.edu.cn/jsxsd/xsxkkc/ggxxkxkOper?kcid={id}&cfbs=null&jx0404id={jx0404id[0]}&xkzy=&trjf=&verifyCode={captcha_code}")
                        if case==1 and index > profetional:
                            response = session.post(f'https://jwxt.ybu.edu.cn/jsxsd/xsxkkc/ggxxkxkOper?kcid={id}&cfbs=null&jx0404id={jx0404id[0]}&xkzy=&trjf=&verifyCode={captcha_code}', headers=test_headers)
                        elif case==0 and index <= profetional:
                            response = session.post(f'http://jwxt.ybu.edu.cn/jsxsd/xsxkkc/bxxkOper?kcid={id}&cfbs=null&kx=&jx0404id={jx0404id[0]}&xkzy=&trjf=&verifyCode={captcha_code}', headers=test_headers)
                                                # http://jwxt.ybu.edu.cn/jsxsd/xsxkkc/bxxkOper?kcid=59EB22ECFEC64CB6A6EA1D7C3906F501&cfbs=null&kx=&jx0404id=202420252005176&xkzy=&trjf=&verifyCode=jtqwu
                                                # http://jwxt.ybu.edu.cn/jsxsd/xsxkkc/bxxkOper?kcid=ACABEDA95535480C93493DCDA9022978&cfbs=null&kx=&jx0404id=202420252008581&xkzy=&trjf=&verifyCode=h49mq
                        # response = session.post(f'https://jwxt.ybu.edu.cn/jsxsd/xsxkkc/ggxxkxkOper?kcid=0000ZRTXK9&cfbs=null&jx0404id=202420251001016&xkzy=&trjf=&verifyCode={captcha_code}', headers=test_headers)
                        
                        print(response.text)
                        # 发出 POST 请求
                        close_window_flag.set()
                        tk_thread.join()
                        
                    else:
                        print("请求失败，cookies过期")
                    

                else:
                    print("输入的序号不在有效范围内。")
            except ValueError:
                print("请输入有效的数字序号。")



    else:
        print("No match found.")
        time.sleep(1)
        



