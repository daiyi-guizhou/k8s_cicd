# K8s Management Console — Backend

Django REST Framework 后端，为 K8s 集群管理提供 REST API。

## 技术栈

- Python 3.12
- Django 5.2 + Django REST Framework 3.16
- MySQL 8.0（用户 + 审计日志）
- Redis 7（Token 存储 + 黑名单）
- kubernetes-client/python（官方 K8s 客户端）

## 本地开发

### 前置条件

- Python 3.12+
- MySQL 8.0 运行中
- Redis 7 运行中
- 可访问的 Kubernetes 集群（kubeconfig 默认位置 `~/.kube/config`）

### 1. 创建 Python 虚拟环境

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Linux/Mac
# 或
venv\Scripts\activate         # Windows
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 准备数据库

连接你的 MySQL 实例，创建数据库和用户：

```sql
CREATE DATABASE IF NOT EXISTS appdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'appuser'@'localhost' IDENTIFIED BY 'UserPass2024!';
GRANT ALL PRIVILEGES ON appdb.* TO 'appuser'@'localhost';
FLUSH PRIVILEGES;
```

### 4. 本地开发配置

本地开发使用 `settings_dev.py`，它会覆盖默认的 K8s 集群内地址，改为连接本机服务：

```bash
# 默认连接: MySQL 127.0.0.1:3306, Redis 127.0.0.1:6379
# 如需修改，设置环境变量:
export MYSQL_HOST=127.0.0.1
export MYSQL_PORT=3306
export MYSQL_USER=appuser
export MYSQL_PASSWORD=UserPass2024!
export REDIS_HOST=127.0.0.1
export REDIS_PORT=6379
export REDIS_PASSWORD=RedisPass2024!
```

### 5. 运行数据库迁移

```bash
python manage.py migrate --settings=k8s_console.settings_dev
```

### 6. 创建初始管理员

```bash
python manage.py init_admin --settings=k8s_console.settings_dev
```

首次运行会输出随机生成的 admin 密码，请妥善保存。

### 7. 启动开发服务器

```bash
python manage.py runserver 0.0.0.0:8000 --settings=k8s_console.settings_dev
```

启动后访问 `http://localhost:8000/api/auth/login` 可以 POST 测试。

### 8. 验证

```bash
# 登录
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"<你的密码>"}'

# 查看 Deployment 列表 (需要 kubeconfig)
curl -X POST http://localhost:8000/api/resources/list \
  -H "Content-Type: application/json" \
  -H "Authorization: Token <返回的token>" \
  -d '{"resource_type":"deployment"}'
```

## API 概览

所有 API 使用 POST 方法，JSON body 传参。统一响应格式：

```json
// 成功
{"code": 0, "message": "ok", "data": {...}}

// 失败
{"code": 1001, "message": "错误信息", "detail": "..."}
```

| 模块 | 端点 | 说明 |
|------|------|------|
| 认证 | `/api/auth/login` | 登录，返回 Token |
| 认证 | `/api/auth/logout` | 登出，Token 加入黑名单 |
| 认证 | `/api/auth/change-password` | 修改自己的密码 |
| 用户管理 | `/api/users/create` | 管理员创建用户 |
| 用户管理 | `/api/users/list` | 管理员查看用户列表 |
| 用户管理 | `/api/users/toggle-active` | 管理员启用/禁用用户 |
| 用户管理 | `/api/users/reset-password` | 管理员重置用户密码 |
| 资源 | `/api/resources/list` | 列出资源 |
| 资源 | `/api/resources/detail` | 资源详情 (JSON) |
| 资源 | `/api/resources/yaml` | 资源 YAML (只读) |
| 资源 | `/api/resources/scale` | 扩缩容 |
| 资源 | `/api/resources/rollback` | 回滚 Deployment |
| 资源 | `/api/resources/delete` | 删除资源 |
| 资源 | `/api/resources/apply` | 应用 YAML |
| 审计 | `/api/audit/list` | 管理员查看审计日志 |

## K8s 集群连接

- **本地开发**: 使用 `~/.kube/config` 中的 kubeconfig
- **集群内部署**: 自动使用 ServiceAccount 的 in-cluster config

## Docker 构建

```bash
docker build -t k8s-console-backend:latest .
```
