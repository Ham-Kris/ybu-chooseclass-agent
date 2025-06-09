# YBU 延边大学自动选课代理系统

本项目是一个延边大学教务系统自动选课代理系统，能够自动登录并选择所有可选课程，仅供学习和研究使用，禁止任何人在任何平台出售/出租本程序提供的服务。

## 🎯 项目特性

- **智能登录**：支持配置文件和命令行参数两种登录方式，自动处理登录流程和 Cookie 管理
- **验证码识别**：集成DdddOcr自动识别，支持自动识别和手动输入两种模式
- **账户隔离**：使用自定义登录时自动清理数据，确保不同账户间数据不混淆
- **智能课程筛选**：支持课程类型、关键词、优先级等多维度筛选
- **自动选课**：支持单门课程抢课和批量自动选课
- **时间窗口检测**：智能检测选课时间，非选课时间提供友好提示
- **冲突检测**：智能检测时间冲突，避免选课冲突
- **可视化界面**：丰富的命令行界面和彩色日志输出

## 🏗️ 系统架构

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  CLIInterface   │    │   BrowserAgent   │    │ CaptchaSolver   │
│     Agent       │◄──►│                  │◄──►│     Agent       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
          │                       │                       
          ▼                       ▼                       
┌─────────────────┐    ┌──────────────────┐              
│  DataManager    │    │   Scheduler      │              
│     Agent       │    │     Agent        │              
└─────────────────┘    └──────────────────┘              
```

## 🚀 快速开始

### 🖥️ 硬件配置要求

#### 最低配置
- **CPU**: 双核心处理器 (2.0GHz+)
- **内存**: 4GB RAM
- **存储**: 2GB 可用磁盘空间
- **GPU**: 无要求（CPU模式运行）
- **网络**: 稳定的网络连接（建议有线连接或强WiFi信号）
- **显示**: 支持1024x768分辨率（手动输入验证码时需要）

#### 推荐配置
- **CPU**: 四核心处理器 (2.5GHz+)
- **内存**: 8GB+ RAM
- **存储**: 5GB+ 可用磁盘空间（SSD推荐）
- **GPU**: 可选 - 支持CUDA的NVIDIA显卡（2GB+ VRAM）或集成显卡
- **网络**: 10Mbps+ 带宽，延迟 < 50ms
- **显示**: 1920x1080分辨率

#### GPU加速支持
- **NVIDIA GPU**: 支持CUDA加速，可显著提升验证码识别速度
- **集成显卡**: Intel/AMD集成显卡可提供基础GPU加速
- **CPU模式**: 无GPU时自动回退到CPU模式，功能完全正常
- **性能对比**: 
  - GPU模式: 验证码识别 < 0.5秒
  - CPU模式: 验证码识别 1-3秒

#### 系统要求
- **操作系统**: Windows 10+, macOS 10.14+, Ubuntu 18.04+
- **Python**: 3.8+ (推荐3.11+)
- **浏览器**: 支持Chromium内核（Playwright自动安装）

#### 性能说明
- **DdddOcr验证码识别**: 需要500MB-1GB RAM用于模型推理
- **GPU加速模式**: 额外需要1-2GB VRAM，CPU占用降低60-80%
- **Playwright浏览器**: 需要200-500MB RAM运行
- **选课高峰期**: 建议使用有线网络，确保网络稳定性
- **多账户使用**: 每个额外账户约需200MB额外内存

**注意事项:**
- 选课开始时服务器压力大，低配置设备可能出现响应延迟
- 验证码AI识别对CPU性能有一定要求，低端设备可切换至手动模式
- GPU加速可选但不必需，系统会自动检测并选择最优运行模式
- 推荐在选课前关闭其他占用网络和GPU资源的应用程序

### 1. 环境准备

#### Windows 用户（推荐）
```cmd
# 克隆项目
git clone https://github.com/Ham-Kris/ybu-chooseclass-agent.git
cd ybu-chooseclass-agent

# 使用完整交互式启动脚本（推荐，持续使用）
start_windows.bat

# 或者使用快速启动脚本（单次操作）
quick_start.bat

# 或者手动安装
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

#### macOS/Linux 用户
```bash
# 克隆项目
git clone https://github.com/Ham-Kris/ybu-chooseclass-agent.git
cd ybu-chooseclass-agent

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

**注意事项：**
- Windows 用户建议使用 `start_windows.bat` 脚本，自动处理异步兼容性问题
- 推荐使用 Python 3.8+ 版本，以获得更好的异步支持
- 验证码识别已集成DdddOcr模型，支持自动识别，同时保留手动输入备选方案

### 2. 配置设置

```bash
# 复制配置文件
cp env.example .env

# 编辑配置文件，填写学号和密码
nano .env
```

配置文件示例：
```bash
# 用户凭据
YBU_USER=202xxxxx      # 学号
YBU_PASS=********      # 密码

# 浏览器设置
HEADLESS=true          # 无头模式

# 验证码识别设置
CAPTCHA_MODEL=ai        # 验证码识别模式：ai（DdddOcr自动识别）或 manual（手动输入）
```

### 3. 首次使用

```bash
# 清理旧数据（可选，如遇登录问题时使用）
python3 main.py clean

# 首次登录（会保存 cookies）
python3 main.py login

# 使用自定义账号密码登录（推荐，避免配置文件泄露）
python3 main.py login -u 学号 -p "密码"

# 如登录失败，使用清理参数重试
python3 main.py login --clean

# 获取课程列表（需要在选课时间内）
python3 main.py list --refresh

# 查看系统状态
python3 main.py status
```

## 📖 使用指南

### 基本命令

```bash
# 清理旧数据（解决登录问题）
python3 main.py clean                     # 清理登录文件
python3 main.py clean --all               # 清理所有数据文件

# 登录系统
python3 main.py login                     # 从配置文件读取凭据登录
python3 main.py login --clean             # 清理后登录
python3 main.py login -u 学号 -p "密码"   # 使用自定义账号密码登录（自动清理旧数据）

# 查看课程列表
python3 main.py list
python3 main.py list --type professional  # 只看专业课程
python3 main.py list --refresh            # 刷新课程数据

# 立即抢课
python3 main.py grab COURSE_ID

# 测试选课流程
python3 main.py test-select COURSE_ID

# 查看系统状态
python3 main.py status
```

### 🔐 登录方式说明

系统支持两种登录方式：

#### 1. 配置文件登录（传统方式）
```bash
# 编辑 .env 文件设置凭据
nano .env

# 使用配置文件登录
python3 main.py login
```

#### 2. 命令行参数登录（推荐）
```bash
# 直接指定账号密码（更安全，不会保存到文件）
python3 main.py login -u 学号 -p "密码"

# 密码包含特殊字符时必须用引号
python3 main.py login -u 2021001 -p "my@pass123!"
python3 main.py login -u 2021002 -p "pass word with space"
```

**重要提示：**
- 使用命令行参数登录时，系统会自动清理旧的cookie和数据库文件，确保账户数据不混淆
- 密码包含特殊字符（如@、!、$、空格等）时，必须用引号包围
- 命令行登录更安全，避免敏感信息存储在配置文件中

### 🎯 智能自动选课 (核心功能)

**auto-select-all** 是本系统的核心功能，支持智能筛选和批量自动选课：

```bash
# 基础自动选课（最多5门课程）
python3 main.py auto-select-all

# 只选择专业课，最多3门
python3 main.py auto-select-all --course-type professional --max-courses 3

# 优先选择包含"计算机"的课程，排除"体育"课程
python3 main.py auto-select-all --priority-keywords 计算机 数学 --exclude-keywords 体育 实验

# 模拟运行测试（不实际选课）
python3 main.py auto-select-all --dry-run

# 设置最少名额要求为5个，选课前刷新数据
python3 main.py auto-select-all --min-slots 5 --refresh-data

# 跳过重修课程，设置选课间隔
python3 main.py auto-select-all --skip-retakes --delay 2
```

#### auto-select-all 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `--dry-run` | 模拟运行，不实际选课 | `--dry-run` |
| `--max-courses` | 最大选课数量（默认无限制） | `--max-courses 3` |
| `--course-type` | 课程类型筛选 | `--course-type professional` |
| `--priority-keywords` | 优先选择包含关键词的课程 | `--priority-keywords 计算机 数学` |
| `--exclude-keywords` | 排除包含关键词的课程 | `--exclude-keywords 体育 实验` |
| `--min-slots` | 最少剩余名额要求（默认1个） | `--min-slots 5` |
| `--skip-retakes` | 跳过重修课程 | `--skip-retakes` |
| `--delay` | 选课间隔时间（秒，默认1秒） | `--delay 2` |
| `--refresh-data` | 选课前先刷新课程数据 | `--refresh-data` |

### 智能选课规划

```bash
# 根据规则文件规划选课
python3 main.py plan rules.yml
```

编辑 `rules.yml` 文件来自定义选课偏好：

```yaml
# 课程类型偏好
course_types:
  - professional
  - public

# 关键词筛选
keywords:
  - "计算机"
  - "软件"

# 优先级设置
priority_keywords:
  "计算机": 3.0
  "软件工程": 2.5
```

### 自动化调度

```bash
# 启动调度器
python3 main.py scheduler start

# 添加自动选课任务
python3 main.py scheduler auto COURSE_ID1 COURSE_ID2 --interval 2

# 查看调度器状态
python3 main.py scheduler status

# 停止调度器
python3 main.py scheduler stop
```

## 🔧 高级功能

### 验证码处理机制

系统已集成DdddOcr验证码识别能力：

1. **AI自动识别**：使用DdddOcr模型自动识别验证码，支持多种验证码类型
2. **手动输入模式**：当自动识别失败时自动回退到手动输入模式
3. **图像预处理**：自动进行图像灰度化、OTSU自适应二值化等预处理优化识别效果
4. **验证码刷新**：自动刷新验证码确保最新状态

**验证码识别特点：**
- 支持YBU教务系统验证码的多种变形
- OpenCV灰度化+OTSU自适应二值化预处理提升识别准确率
- 预处理图像优先，原始图像备选的双重识别策略
- 自动降级到手动输入确保可用性

## 🔧 验证码处理示例

**处理前（原始验证码）：**

![](example_captcha-jaejp.jpg)

**处理后（OpenCV灰度化+OTSU二值化）：**

![](processed_captcha-jaejp.jpg)

---

**处理流程：**
```python
import cv2
import ddddocr

# 读取图片
img = cv2.imread('captcha.jpg')
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# OTSU自适应二值化
_, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
cv2.imwrite('processed.png', binary)

# OCR识别
ocr = ddddocr.DdddOcr()
with open('processed.png', 'rb') as f:
    result = ocr.classification(f.read())
```

**识别结果：** `jaejp`

**技术优势：**
- ✅ OpenCV专业图像处理算法
- ✅ OTSU自适应阈值选择最佳二值化
- ✅ 经典验证码预处理方案

### 时间窗口智能检测

- **选课时间内**：正常显示课程列表和选课功能
- **非选课时间**：友好提示当前不在选课窗口，避免无意义的错误

### 可视化调试

使用 `--headless false` 参数可以看到浏览器操作过程：

```bash
python3 main.py auto-select-all --headless false
```

### 日志分析

系统会生成 JSON Lines 格式的日志文件 `ybu_agent.jsonl`：

```json
{"timestamp": "2024-12-22T10:30:00", "level": "INFO", "action": "login", "message": "Login successful"}
{"timestamp": "2024-12-22T10:31:00", "level": "INFO", "action": "auto_select_all", "successful": 3, "failed": 1}
```

### 数据库管理

系统使用 SQLite 数据库存储课程信息和选课记录：

- `ybu_courses.db`: 主数据库文件
- 包含课程表、时间表、选课记录等

## 🧪 测试和调试

```bash
# 测试登录功能
python3 main.py login

# 测试选课流程（不实际选课）
python3 main.py test-select COURSE_ID

# 模拟自动选课
python3 main.py auto-select-all --dry-run

# 查看详细调试信息
python3 main.py auto-select-all --dry-run --max-courses 2
```

## 📁 项目结构

```
ybu-chooseclass-agent/
├── agents/                      # 代理模块
│   ├── __init__.py
│   ├── browser_agent.py         # 浏览器代理（核心）
│   ├── captcha_solver_agent.py  # 验证码识别代理（DdddOcr集成）
│   ├── data_manager_agent.py    # 数据管理代理
│   ├── scheduler_agent.py       # 调度代理
│   └── cli_interface_agent.py   # 命令行界面代理
├── vision_model/               # 验证码识别模块
│   ├── ddddocr/                # DdddOcr验证码识别库
│   └── ddddocr_requirements.txt # DdddOcr依赖文件
├── tests/                       # 测试文件
│   ├── __init__.py
│   └── test_captcha_solver.py
├── miscellaneous/               # 其他工具
│   ├── chooseclass.py
│   └── pre_captcha.py
├── main.py                      # 主程序入口
├── requirements.txt             # 依赖列表
├── rules.yml                    # 选课规则示例
├── env.example                  # 配置文件示例
├── test_select_course.py        # 测试脚本
├── .gitignore                   # Git 忽略文件
└── README.md                    # 项目文档
```

## 💡 使用技巧

### 选课时间策略

1. **选课开始前**：
   - 使用命令行参数登录：`python3 main.py login -u 学号 -p "密码"`
   - 提前配置好筛选条件，使用 `--dry-run` 测试
2. **选课开始时**：立即运行 `auto-select-all` 进行批量选课
3. **选课期间**：使用 `grab` 命令针对性抢课

### 筛选策略示例

```bash
# 计算机专业学生的典型筛选
python3 main.py auto-select-all \
  --course-type professional \
  --priority-keywords 计算机 软件 算法 数据结构 \
  --exclude-keywords 体育 军事 \
  --max-courses 5 \
  --min-slots 3

# 公共课补选
python3 main.py auto-select-all \
  --course-type public \
  --priority-keywords 英语 数学 \
  --max-courses 2 \
  --min-slots 5
```

## ⚠️ 注意事项

1. **合规使用**：本项目仅供学习研究使用，请遵守学校相关规定
2. **选课时间**：只有在学校规定的选课时间内才能获取课程列表和进行选课
3. **访问频率**：避免过度频繁请求，系统已内置适当的延时
4. **数据安全**：登录凭据仅存储在本地，请保护好您的账号信息
5. **网络环境**：建议在稳定的网络环境下使用
6. **重复选课**：系统会自动检测已选课程，避免重复选择

## 🐛 常见问题

### Q: 提示"当前不在选课时间窗口内"怎么办？
A: 这是正常提示，请在学校规定的选课时间内使用系统。

### Q: 验证码识别失败怎么办？
A: 系统已集成DdddOcr自动识别，如果自动识别失败会自动回退到手动输入模式。请按照提示输入验证码。

### Q: auto-select-all 没有选中任何课程？
A: 检查筛选条件是否过于严格，或当前课程无剩余名额。

### Q: 如何提高选课成功率？
A: 建议在选课开始的瞬间运行，设置合理的筛选条件，使用专业课优先策略。

### Q: 登录时提示需要删除 cookies.json 和 ybu_courses.db 怎么办？
A: 
1. **推荐方案**：使用 `python3 main.py clean` 自动清理
2. **或使用带清理的登录**：`python3 main.py login --clean`
3. **手动删除**：`rm cookies.json ybu_courses.db` (Linux/Mac) 或在Windows中删除这两个文件

系统现在会自动检测过期的登录状态并提供解决建议。

### Q: 系统运行时出现错误怎么办？
A: 请检查网络连接、登录凭据是否正确，并确保在选课时间内运行。

### Q: Windows 系统下出现异步相关错误怎么办？
**特别是 Python 3.13 出现的管道传输错误（`ValueError: I/O operation on closed pipe`）**

A: 
1. **推荐方案**：使用 `start_windows.bat` 启动脚本，已集成最新的异步修复
2. **测试修复**：运行 `python fix_windows_async.py` 测试异步兼容性
3. **手动修复**：
   ```cmd
   # 安装Windows专用依赖
   pip install colorama pywin32
   
   # 设置环境变量禁用警告
   set PYTHONWARNINGS=ignore::ResourceWarning
   
   # 使用修复后的启动方式
   python main.py [命令]
   ```
4. **Python 3.13 用户**：项目已针对最新版本进行优化，包括管道错误修复
5. 确保使用 Python 3.8+ 版本（推荐 3.11+）

### Q: requirements.txt 安装失败怎么办？
A:
1. 升级 pip：`python -m pip install --upgrade pip`
2. 使用国内镜像：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`
3. Windows 用户可以使用 `start_windows.bat` 自动处理

### Q: Windows启动脚本如何选择？
A: 提供两种启动方式：

**1. `start_windows.bat` - 完整交互式控制台（推荐）**
- 提供持续的交互式命令环境
- 执行完一个命令后可以继续输入下一个命令
- 内置帮助系统，输入 `help` 查看所有命令
- 适合需要连续操作的用户

**2. `quick_start.bat` - 快速单次操作**
- 提供简洁的菜单选择界面
- 执行完一个操作后自动退出
- 适合只需要执行单个操作的用户

**3. 直接命令行调用**
```cmd
# 可以为脚本传递参数直接执行
start_windows.bat login
quick_start.bat auto-select-all
```

### Q: 启动脚本提示 "invalid choice: '!command!'" 怎么办？
A: 这个问题已经修复，新版本脚本添加了 `setlocal enabledelayedexpansion` 解决变量扩展问题：
1. **推荐方案**：使用最新的 `start_windows.bat`（已修复）
2. **备选方案**：使用 `quick_start.bat` 菜单模式
3. **直接调用**：`start_windows.bat 命令参数`

### Q: 选课时提示验证码错误或选课失败怎么办？
A: 已针对实际选课页面结构进行了优化：
1. **验证码处理增强**：支持弹窗、iframe和主页面中的验证码
2. **选择器优化**：根据实际HTML结构更新了元素选择器
3. **提交机制改进**：支持多种提交方式（按钮点击、回车键、JavaScript调用）
4. **结果判断优化**：增强了选课成功/失败的判断逻辑
5. **测试脚本**：提供 `test_select_course.py` 用于验证修复效果

### Q: 如何测试修复后的选课功能？
A: 
```cmd
# 运行测试脚本
python test_select_course.py

# 或者直接测试选课
python main.py auto-select-all
```

### Q: 如何使用自定义账号密码登录？
A: 
1. **推荐方式**：`python3 main.py login -u 学号 -p "密码"`
2. **注意事项**：
   - 密码包含特殊字符时必须用引号包围
   - 系统会自动清理旧的cookie和数据库文件
   - 不会将凭据保存到配置文件中

### Q: 为什么密码要用引号？
A: 
密码可能包含shell特殊字符（如@、!、$、空格等），不用引号会导致解析错误。
```bash
# 正确写法
python3 main.py login -u 2021001 -p "my@pass123!"

# 错误写法（会解析失败）
python3 main.py login -u 2021001 -p my@pass123!
```

### Q: 使用自定义登录时为什么会清理旧数据？
A: 
为了避免不同账户的数据混淆，系统在检测到使用自定义账户时会自动清理旧的cookie和数据库文件。这确保每个账户都有独立的会话状态。

### Q: 验证码识别模型如何工作？
A: 
系统已集成DdddOcr验证码识别模型：
1. **自动识别**：使用DdddOcr模型自动识别验证码
2. **双重策略**：同时尝试原始图像和预处理图像识别
3. **智能回退**：自动识别失败时自动回退到手动输入
4. **高准确率**：DdddOcr在多种验证码上都有较高的识别准确率

### Q: 如何切换验证码识别模式？
A: 
在 `.env` 配置文件中设置：
```bash
# 使用AI自动识别（推荐）
CAPTCHA_MODEL=ai

# 使用手动输入
CAPTCHA_MODEL=manual
```

### Q: DdddOcr依赖安装失败怎么办？
A: 
1. 确保安装了所有依赖：`pip install -r requirements.txt`
2. 检查Python版本：建议使用Python 3.8+
3. 如果仍有问题，可以手动安装：`pip install onnxruntime onnx pillow`
4. Windows用户可以使用 `start_windows.bat` 自动处理依赖

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交变更 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

MIT License - 本项目仅供学习研究使用，不得用于商业用途。

## 🙏 致谢

- 感谢 @xuyanhenry，他的[延边大学抢课项目](https://github.com/xuyanhenry/ybu-Grab-classes)为本项目提供了宝贵的参考和启发
- 感谢[DdddOcr项目](https://github.com/sml2h3/ddddocr)提供的优秀验证码识别能力
- 感谢 Playwright 项目提供的浏览器自动化框架
- 感谢所有贡献者的支持和建议