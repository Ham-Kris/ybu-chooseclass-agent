# YBU 延边大学自动选课代理系统

本项目是一个延边大学教务系统自动选课代理系统，能够自动登录并选择所有可选课程，仅供学习和研究使用，禁止任何人在任何平台出售/出租本程序提供的服务。

## 🎯 项目特性

- **智能登录**：支持配置文件和命令行参数两种登录方式，自动处理登录流程和 Cookie 管理
- **验证码识别**：可选集成 PaddleOCR 引擎，支持自动识别验证码和手动输入模式
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

### 1. 环境准备

#### Windows 用户（推荐）
```cmd
# 克隆项目
git clone https://github.com/Ham-Kris/ybu-chooseclass-agent.git
cd ybu-chooseclass-agent

# 使用一键启动脚本（自动处理环境配置）
start_windows.bat

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
- PaddleOCR 已包含在 requirements.txt 中，自动安装

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

# OCR 引擎设置（可选）
# OCR_ENGINE=paddle    # 验证码识别引擎，注释掉则使用手动输入
# OCR_ENGINE=NONE      # 或设置为NONE禁用自动识别
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
| `--max-courses` | 最大选课数量（默认5门） | `--max-courses 3` |
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

系统支持多种验证码处理方式：

1. **自动识别**：设置 `OCR_ENGINE=paddle` 启用 PaddleOCR 自动识别验证码
2. **手动输入**：不设置 OCR_ENGINE 或设置为 NONE 时使用手动输入模式
3. **验证码刷新**：自动刷新验证码确保最新状态

**OCR引擎配置：**
```bash
# 启用自动识别（需要安装PaddleOCR）
OCR_ENGINE=paddle

# 禁用自动识别，使用手动输入
# OCR_ENGINE=NONE

# 或者直接注释掉/删除这一行
```

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
│   ├── captcha_solver_agent.py  # 验证码识别代理
│   ├── data_manager_agent.py    # 数据管理代理
│   ├── scheduler_agent.py       # 调度代理
│   └── cli_interface_agent.py   # 命令行界面代理
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
A: 系统会自动切换到手动输入模式，按提示操作即可。

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
A: 
1. 使用 `start_windows.bat` 启动脚本，已集成异步修复
2. 确保使用 Python 3.8+ 版本
3. 如果仍有问题，尝试在命令行中运行：`python -c "import asyncio; print(asyncio.get_event_loop_policy())"`
4. 手动安装 Windows 特定依赖：`pip install pywin32 colorama`

### Q: requirements.txt 安装失败怎么办？
A:
1. 升级 pip：`python -m pip install --upgrade pip`
2. 分步安装：先安装基础依赖，再安装 PaddleOCR
3. 使用国内镜像：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`
4. Windows 用户可以使用 `start_windows.bat` 自动处理

### Q: PaddleOCR 安装失败怎么办？
A: 
1. 对于 Windows 用户，确保已安装 Visual Studio Build Tools
2. 可以跳过 PaddleOCR 安装，系统会自动降级到手动输入验证码
3. 或使用 CPU 版本：`pip install paddlepaddle -f https://www.paddlepaddle.org.cn/whl/windows/mkl/avx/stable.html`
4. 在 .env 中注释掉 OCR_ENGINE 或设置为 NONE 来禁用自动识别

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
- 感谢 PaddleOCR 项目提供的 OCR 引擎
- 感谢 Playwright 项目提供的浏览器自动化框架
- 感谢所有贡献者的支持和建议

---

**🎓 延边大学自动选课代理系统 - 让选课变得更智能！** 