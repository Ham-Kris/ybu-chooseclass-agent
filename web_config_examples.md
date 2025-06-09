# Web界面配置示例

## 常用配置场景

### 1. 本地开发环境
```bash
# .env 配置
WEB_HOST=127.0.0.1  # 仅本地访问
WEB_PORT=5000       # 默认端口
WEB_DEBUG=true      # 开启调试模式
```

### 2. 局域网共享
```bash
# .env 配置
WEB_HOST=0.0.0.0    # 允许局域网访问
WEB_PORT=8080       # 自定义端口
WEB_DEBUG=false     # 关闭调试模式
```

### 3. 服务器部署
```bash
# .env 配置
WEB_HOST=0.0.0.0    # 监听所有网卡
WEB_PORT=5000       # 标准端口
WEB_DEBUG=false     # 生产环境关闭调试

# 可配合Nginx反向代理
```

### 4. 多实例部署
```bash
# 实例1 - .env
WEB_HOST=0.0.0.0
WEB_PORT=5001
WEB_DEBUG=false

# 实例2 - .env.instance2
WEB_HOST=0.0.0.0
WEB_PORT=5002
WEB_DEBUG=false
```

### 5. Docker部署
```bash
# docker-compose.yml 环境变量
environment:
  - WEB_HOST=0.0.0.0
  - WEB_PORT=5000
  - WEB_DEBUG=false
```

## 端口配置说明

### WEB_HOST 配置
- `127.0.0.1` - 仅本地访问
- `0.0.0.0` - 允许所有网卡访问（局域网/公网）
- 特定IP - 绑定到指定网卡

### WEB_PORT 配置
- `1024-65535` - 可用端口范围
- `5000` - 默认端口
- `8080, 8888, 3000` - 常用开发端口
- 避免使用系统保留端口（1-1023）

### WEB_DEBUG 配置
- `true` - 开启调试模式（开发环境）
  - 代码修改后自动重载
  - 详细错误信息
  - 不适合生产环境
- `false` - 关闭调试模式（生产环境）
  - 更好的性能
  - 隐藏错误详情
  - 推荐生产环境使用

## 启动命令对比

### 使用.env文件（推荐）
```bash
# 创建配置文件
cp env.example .env
# 编辑配置
nano .env
# 启动应用
python start_web.py
```

### 使用环境变量
```bash
# 临时设置
export WEB_PORT=8080
python start_web.py

# 单次运行
WEB_PORT=8080 python start_web.py
```

### 直接修改代码
```python
# 不推荐：直接在app.py中修改
socketio.run(app, host='0.0.0.0', port=8080, debug=False)
```

## 防火墙配置

### Linux (UFW)
```bash
# 开放端口
sudo ufw allow 5000

# 指定协议
sudo ufw allow 5000/tcp
```

### Linux (iptables)
```bash
# 开放端口
sudo iptables -A INPUT -p tcp --dport 5000 -j ACCEPT
```

### 云服务器安全组
- 阿里云ECS：添加安全组规则
- 腾讯云CVM：配置安全组
- AWS EC2：修改Security Groups

## 反向代理配置

### Nginx
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    location /socket.io/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Apache
```apache
<VirtualHost *:80>
    ServerName yourdomain.com
    
    ProxyPreserveHost On
    ProxyRequests Off
    ProxyPass / http://127.0.0.1:5000/
    ProxyPassReverse / http://127.0.0.1:5000/
    
    # WebSocket支持
    RewriteEngine on
    RewriteCond %{HTTP:Upgrade} websocket [NC]
    RewriteCond %{HTTP:Connection} upgrade [NC]
    RewriteRule ^/?(.*) "ws://127.0.0.1:5000/$1" [P,L]
</VirtualHost>
``` 