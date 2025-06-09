# Windows 系统安装指南

本指南专门针对 Windows 用户，解决常见的安装和运行问题。

## 🚀 一键安装（推荐）

1. **下载项目**
   ```cmd
   git clone https://github.com/Ham-Kris/ybu-chooseclass-agent.git
   cd ybu-chooseclass-agent
   ```

2. **运行一键安装脚本**
   ```cmd
   start_windows.bat
   ```
   
   脚本会自动：
   - 创建虚拟环境
   - 安装所有依赖
   - 配置异步兼容性
   - 安装 Playwright 浏览器
   - 复制配置文件

## 🔧 手动安装

如果一键安装遇到问题，可以按以下步骤手动安装：

### 步骤 1：检查 Python 版本
```cmd
python --version
```
**要求：Python 3.8 或更高版本**

如果版本过低，请从 [Python 官网](https://www.python.org/downloads/) 下载最新版本。

### 步骤 2：创建虚拟环境
```cmd
python -m venv venv
venv\Scripts\activate
```

### 步骤 3：升级 pip
```cmd
python -m pip install --upgrade pip
```

### 步骤 4：安装基础依赖
```cmd
# 先安装基础依赖
pip install playwright requests beautifulsoup4 rich python-dotenv

# 安装异步调度相关
pip install apscheduler pandas pyyaml

# Windows 专用依赖
pip install colorama pywin32

# 安装图像处理依赖
pip install pillow opencv-python numpy
```

### 步骤 5：安装深度学习依赖（验证码模型开发）
```cmd
# 安装PyTorch（用于验证码识别模型开发）
pip install torch torchvision

# 安装验证码生成库
pip install captcha

# 如果上述命令失败，可以跳过此步骤
# 系统目前使用手动验证码输入模式
```

### 步骤 6：安装 Playwright 浏览器
```cmd
playwright install chromium
```

### 步骤 7：配置环境变量
```cmd
copy env.example .env
notepad .env
```

在打开的记事本中填写：
```
YBU_USER=你的学号
YBU_PASS=你的密码
HEADLESS=true
CAPTCHA_MODE=manual
```

## ⚡ 快速测试

```cmd
# 激活虚拟环境（如果尚未激活）
venv\Scripts\activate

# 清理旧数据（如有登录问题）
python main.py clean

# 测试登录
python main.py login

# 如果登录失败，清理后重试
python main.py login --clean

# 查看系统状态
python main.py status
```

## 🐛 常见问题解决

### 问题 1: 异步事件循环错误
**错误信息：** `RuntimeError: asyncio.run() cannot be called from a running event loop`

**解决方案：**
1. 确保使用 Python 3.8+
2. 使用 `start_windows.bat` 启动脚本
3. 项目已自动集成异步修复代码

### 问题 2: PyTorch 安装失败
**错误信息：** 各种编译错误

**解决方案：**
1. 使用官方安装命令：
   ```cmd
   # 访问 https://pytorch.org/ 获取适合你系统的安装命令
   pip install torch torchvision torchaudio
   ```

2. 或者跳过深度学习依赖：
   ```cmd
   # 系统目前使用手动验证码输入模式
   # AI模型识别功能正在开发中
   ```

### 问题 3: Playwright 浏览器下载失败
**解决方案：**
```cmd
# 设置代理（如果需要）
set HTTPS_PROXY=http://proxy.example.com:8080

# 重新安装
playwright install chromium

# 或使用离线安装包
playwright install --force chromium
```

### 问题 4: 权限错误
**解决方案：**
1. 以管理员身份运行命令提示符
2. 或使用 `--user` 参数安装包：
   ```cmd
   pip install --user -r requirements.txt
   ```

### 问题 5: 中文显示乱码
**解决方案：**
```cmd
# 设置控制台编码
chcp 65001

# 或在环境变量中设置
set PYTHONIOENCODING=utf-8
```

## 🎯 优化建议

### 性能优化
1. **使用 SSD 硬盘**：提高文件 IO 性能
2. **关闭实时杀毒**：暂时关闭对项目目录的实时扫描
3. **使用有线网络**：确保网络连接稳定

### 系统设置
1. **调整虚拟内存**：确保至少 4GB 虚拟内存
2. **更新 Windows**：使用最新的 Windows 版本
3. **清理临时文件**：定期清理系统临时文件

## 📋 系统要求

| 组件 | 最低要求 | 推荐配置 |
|------|----------|----------|
| 操作系统 | Windows 10 | Windows 11 |
| Python | 3.8+ | 3.11+ |
| RAM | 4GB | 8GB+ |
| 硬盘空间 | 2GB | 5GB+ |
| 网络 | 宽带连接 | 稳定的有线连接 |

## 🔄 更新项目

```cmd
# 激活虚拟环境
venv\Scripts\activate

# 拉取最新代码
git pull origin main

# 更新依赖
pip install -r requirements.txt --upgrade

# 重新安装浏览器（如果需要）
playwright install chromium
```

## 📞 获取帮助

如果遇到其他问题：

1. **查看日志文件**：`ybu_agent.jsonl`
2. **检查配置文件**：`.env`
3. **提交 Issue**：在 GitHub 项目页面提交问题
4. **查看完整文档**：`README.md`

---

**💡 提示：** 大多数问题都可以通过使用 `start_windows.bat` 脚本来解决！ 