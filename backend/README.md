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

- Python 3.12+（推荐通过 Miniconda/conda 管理）
- MySQL 8.0 运行中
- Redis 7 运行中
- 可访问的 Kubernetes 集群（kubeconfig 默认位置 `~/.kube/config`）

### 1. 创建 conda 虚拟环境

```bash
conda create -n k8s-console python=3.12 -y
conda activate k8s-console
```

### 2. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 3. MySQL 和 Redis 连接

本项目的 MySQL 和 Redis 运行在 K8s 集群的 `database` namespace 中。本地开发使用 `kubectl port-forward` 将服务映射到本地端口：

```bash
# 端口转发 MySQL 到本地 3306
kubectl port-forward -n database svc/mysql 3306:3306 &

# 端口转发 Redis 到本地 6379
kubectl port-forward -n database svc/redis 6379:6379 &
```

如果你本地已有 MySQL/Redis 实例，也可以直接使用本地服务（确保密码配置匹配）。

### 4. 本地开发配置

使用 `DJANGO_SETTINGS_MODULE` 环境变量切换配置：

```bash
# Dev（本地 Docker Desktop）— 覆盖 DB/Redis 为 127.0.0.1
export DJANGO_SETTINGS_MODULE=k8s_console.settings_dev

# Prd（K8s Pod 内 / 生产镜像）— 从 ConfigMap/Secret 读取地址
# export DJANGO_SETTINGS_MODULE=k8s_console.settings  （默认值，无需显式设置）
```

不设置该变量时默认使用 `k8s_console.settings`（生产配置）。本地开发建议将其写入 conda env 或 shell profile 中自动生效。

### 5. 运行数据库迁移

```bash
# Dev — 使用环境变量（推荐）
export DJANGO_SETTINGS_MODULE=k8s_console.settings_dev
python manage.py migrate
python manage.py init_admin
python manage.py runserver 0.0.0.0:8000

# 或显式传递 --settings 参数
python manage.py migrate --settings=k8s_console.settings_dev
```

**或者使用纯 SQL 初始化（推荐，无需 migration 记录）**：

```bash
python manage.py clean_all_data --settings=k8s_console.settings_dev
python manage.py migrate --fake --settings=k8s_console.settings_dev
```

> 📄 完整建表 SQL 见 [`sql/init_database.sql`](sql/init_database.sql)。每次表结构变更必须同步更新该文件。

### 6. 创建初始管理员

```bash
python manage.py init_admin --settings=k8s_console.settings_dev
```

首次运行会生成随机密码。使用以下命令手动重置密码：

```bash
python manage.py shell --settings=k8s_console.settings_dev
>>> from django.contrib.auth.hashers import make_password
>>> from apps.auth_app.models import User
>>> admin = User.objects.get(username='admin')
>>> admin.password = make_password('admin')
>>> admin.save()
```

### 7. 启动开发服务器

```bash
# Dev（需先 export DJANGO_SETTINGS_MODULE=k8s_console.settings_dev）
python manage.py runserver 0.0.0.0:8000

# 或显式指定
python manage.py runserver 0.0.0.0:8000 --settings=k8s_console.settings_dev
```

启动后访问 `http://localhost:8000/api/auth/login`。

### 8. 验证 API

```bash
# 登录（默认管理员 admin / admin）
curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'

# 查看 Namespace 列表
curl -s -X POST http://localhost:8000/api/resources/list \
  -H "Content-Type: application/json" \
  -H "Authorization: Token <返回的token>" \
  -d '{"resource_type":"namespace"}'

# 查看 Deployment 列表
curl -s -X POST http://localhost:8000/api/resources/list \
  -H "Content-Type: application/json" \
  -H "Authorization: Token <返回的token>" \
  -d '{"resource_type":"deployment","namespace":"prd"}'

# 查看资源 YAML
curl -s -X POST http://localhost:8000/api/resources/yaml \
  -H "Content-Type: application/json" \
  -H "Authorization: Token <返回的token>" \
  -d '{"resource_type":"deployment","name":"prd-app","namespace":"prd"}'

# 查看审计日志
curl -s -X POST http://localhost:8000/api/audit/list \
  -H "Content-Type: application/json" \
  -H "Authorization: Token <返回的token>" \
  -d '{}'

# Logout（Token 加入黑名单）
curl -s -X POST http://localhost:8000/api/auth/logout \
  -H "Content-Type: application/json" \
  -H "Authorization: Token <返回的token>"
```

## 数据库表结构

### user

| 列 | 类型 | 说明 |
|----|------|------|
| id | AutoField | 主键 |
| username | CharField(150) | 唯一用户名 |
| password | CharField(255) | Django hashed 密码 |
| role | CharField(20) | `admin` / `user` |
| is_active | BooleanField | 是否启用 |
| created_at | DateTimeField | 创建时间 |

### cluster (v1.1 新增)

| 列 | 类型 | 说明 |
|----|------|------|
| id | AutoField | 主键 |
| name | CharField(128) | 唯一集群名称 |
| description | TextField | 描述 |
| kubeconfig_content | TextField | kubeconfig YAML 内容；留空则使用默认 ~/.kube/config |
| enabled | BooleanField | 是否启用 |
| created_at | DateTimeField | 创建时间 |
| updated_at | DateTimeField | 更新时间 |

### audit_log (v1.1 新增 cluster_name 列)

| 列 | 类型 | 说明 |
|----|------|------|
| id | AutoField | 主键 |
| user | FK → user | 操作用户 |
| action | CharField(50) | 操作类型 |
| resource_type | CharField(50) | 资源类型 |
| resource_name | CharField(255) | 资源名称 |
| namespace | CharField(100) | 命名空间 |
| cluster_name | CharField(128) | 集群名称 (v1.1 新增) |
| detail | JSONField | 操作详情 |
| result | CharField(20) | `success` / `fail` |
| error_msg | TextField | 错误信息 (v1.1 新增) |
| created_at | DateTimeField | 操作时间 |

## API 概览

所有 API 使用 POST 方法，JSON body 传参。统一响应格式：

```json
// 成功
{"code": 0, "message": "ok", "data": {...}}

// 失败
{"code": 1001, "message": "错误信息", "detail": "..."}
```

### 错误码

| 范围 | 类别 |
|------|------|
| 1001–1006 | 认证相关 |
| 2001–2005 | K8s 资源相关 |
| 3001–3002 | 权限/验证相关 |

### 完整 API 列表

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
| 集群管理 | `/api/clusters/list` | 查看集群列表 |
| 集群管理 | `/api/clusters/create` | 管理员添加集群 |
| 集群管理 | `/api/clusters/update` | 管理员编辑集群 |
| 集群管理 | `/api/clusters/delete` | 管理员删除集群 |
| 集群管理 | `/api/clusters/test` | 测试集群连接 |

### 支持的资源类型

`namespace`, `deployment`, `pod`, `service`, `ingress`, `daemonset`, `statefulset`, `configmap`, `secret`, `role`, `rolebinding`, `clusterrole`, `clusterrolebinding`, `serviceaccount`

## K8s 集群连接

- **本地开发**: 使用 `~/.kube/config` 中的 kubeconfig
- **集群内部署**: 自动使用 ServiceAccount 的 in-cluster config

## 项目结构

```
backend/
├── manage.py
├── requirements.txt
├── Dockerfile
├── k8s_console/              # Django 项目配置
│   ├── settings.py           # 生产/集群内配置
│   ├── settings_dev.py       # 本地开发配置 (override)
│   ├── urls.py
│   ├── wsgi.py
│   └── middleware.py         # 审计日志 + Token 黑名单中间件
├── apps/
│   ├── auth_app/             # 认证 + 用户管理
│   │   ├── models.py         # User, PasswordResetToken
│   │   ├── views.py          # login/logout/change-password/user CRUD
│   │   ├── authentication.py # Token 认证类
│   │   └── urls.py
│   ├── resources/            # K8s 资源操作
│   │   ├── k8s_client.py     # 统一 K8s API 封装
│   │   ├── views.py          # 资源 CRUD 视图
│   │   └── urls.py
│   └── audit/                # 审计日志
│       ├── models.py         # AuditLog
│       ├── views.py          # 审计日志查询
│       └── urls.py
└── utils/
    ├── response.py           # 统一 JSON 响应格式
    └── k8s_helper.py         # K8s 错误包装
```

## Docker 构建

```bash
docker build -t k8s-console-backend:latest .
```
