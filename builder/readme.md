# Builder Service — Docker 镜像构建服务

> **定位**: CI/CD 部署链路中的"镜像工厂"，接收构建请求 → 本地源码打包 → Docker Build → 产出可用镜像

---

## Build 做了什么

Builder Service 的核心只有一个函数：`build(app_name, app_type, tag, local_path)`。它完成以下工作流：

```
local_path (宿主机源码)
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ 1. 安全校验                                           │
│    • 路径白名单检查（防路径遍历攻击）                      │
│    • 项目文件校验: requirements.txt / package.json      │
│    • app_type 合法性校验 (django | vue)                │
├─────────────────────────────────────────────────────┤
│ 2. 源码准备                                           │
│    • 复制源码到临时构建目录 /tmp/build-{app}-{uuid}       │
│    • 排除: .git, node_modules, __pycache__, .venv 等   │
│    • 读取 python_version.txt (Django, 默认 3.12)      │
├─────────────────────────────────────────────────────┤
│ 3. 渲染 Dockerfile                                    │
│    • 选择模板: templates/django/Dockerfile              │
│              templates/vue/Dockerfile                  │
│    • 注入变量: {APP_NAME}, {PYTHON_VERSION}            │
├─────────────────────────────────────────────────────┤
│ 4. docker build -t {app_name}:{tag} .                 │
│    • 超时: 600s                                       │
│    • 镜像命名: {app_name}:{tag}                        │
│    • 不推远程 Registry（本地 Docker Desktop 模式）       │
├─────────────────────────────────────────────────────┤
│ 5. 镜像保留策略                                        │
│    • 按创建时间排序，保留最新 5 个 tag                    │
│    • 删除旧镜像释放磁盘空间                               │
│    • 正在使用的镜像不会被误删（Docker 层保护）             │
├─────────────────────────────────────────────────────┤
│ 6. 清理临时目录                                        │
│    • finally 块保证 /tmp/build-* 一定被删除              │
└─────────────────────────────────────────────────────┘
    │
    ▼
返回 {"image": "my-app:v1.0", "app_name": "my-app", "tag": "v1.0"}
```

**一句话**: Build 把"宿主机上一份源码"变成"一个本地 Docker 镜像"，供后续 YAML 生成和 K8s 部署使用。

---

## 为什么 Builder 要独立运行

K8s 集群中的 Pod 没有 Docker daemon，无法执行 `docker build`。Builder Service 直接运行在**宿主机**上，调用宿主机的 Docker CLI 进行镜像构建。

```
┌── K8s 集群 (WSL/虚拟机) ──┐     ┌── 宿主机 (Windows) ──┐
│                            │     │                      │
│  k8s-console-backend Pod   │────▶│  Builder Service      │
│  POST /api/build           │     │  0.0.0.0:9008         │
│                            │     │         │             │
└────────────────────────────┘     │         ▼             │
                                   │  docker build ...     │
                                   │  docker images ...    │
                                   │                      │
                                   └──────────────────────┘
```

K8s Pod 内访问 Builder 的网络路径取决于部署环境：
- **Docker Desktop**: `host.docker.internal` → `192.168.65.254:9008`
- **minikube / kind**: 根据实际情况配置

---

## 快速开始

### 启动 Builder Service

```bash
# 在宿主机上（Windows Git Bash）
cd D:/project/k8s_cicd/k8s_cicd/builder
pip install flask        # 首次需要安装依赖
python main.py           # 启动在 0.0.0.0:9008
```

### 验证

```bash
curl http://127.0.0.1:9008/api/health
# → {"status":"ok"}
```

### 手动调用构建

```bash
curl -X POST http://127.0.0.1:9008/api/build \
  -H 'Content-Type: application/json' \
  -d '{
    "app_name": "my-shop",
    "app_type": "django",
    "tag": "v1.0.0",
    "local_path": "D:/project/my-shop"
  }'
# → {"code":0,"message":"镜像构建成功","data":{"image":"my-shop:v1.0.0",...}}
```

---

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/build` | 触发镜像构建（见下方参数） |
| `GET` | `/api/health` | 健康检查 |

### POST /api/build

| 参数 | 类型 | 必填 | 说明 |
|------|------|:---:|------|
| `app_name` | string | ✅ | 镜像名称，也是 K8s Deployment name |
| `app_type` | string | ✅ | `django` 或 `vue` |
| `tag` | string | ✅ | 镜像 tag (如 `v1.0.0`) |
| `local_path` | string | ✅ | 宿主机源码路径 (Windows 格式 `D:/...`) |

**响应**:
```json
// 成功
{"code": 0, "message": "镜像构建成功", "data": {"image": "my-shop:v1.0.0", "app_name": "my-shop", "tag": "v1.0.0"}}

// 失败
{"code": 1, "message": "镜像构建失败", "error": "具体错误信息"}
```

**错误码**:
| code | HTTP Status | 含义 |
|------|-------------|------|
| 1 / 400 | 400 | 参数错误（缺少必填字段 / 路径不存在 / 路径不在白名单） |
| 1 / 500 | 500 | 构建失败（docker build 报错 / 超时 600s） |

---

## Docker 模板

Builder 根据 `app_type` 选择不同的 Dockerfile 模板：

### Django 模板 (`templates/django/Dockerfile`)

```dockerfile
# Stage 1: Build dependencies
FROM python:{PYTHON_VERSION}-slim AS builder
# pip install -r requirements.txt

# Stage 2: Runtime
FROM python:{PYTHON_VERSION}-slim
# COPY start_app.sh . → CMD ["./start_app.sh"]
EXPOSE 8000
```

**生成 YAML 时的端口约定**: Django 默认 **8000**，探针用 `tcpSocket:8000`。

### Vue 模板 (`templates/vue/Dockerfile`)

```dockerfile
# Stage 1: Build Vue app
FROM node:22-alpine AS builder
# npm install → npm run build

# Stage 2: Serve with Nginx
FROM nginx:latest
# COPY dist → /usr/share/nginx/html
EXPOSE 80
CMD ["/start_app.sh"]   # → exec nginx -g "daemon off;"
```

**生成 YAML 时的端口约定**: Vue（nginx）默认 **80**，探针用 `httpGet:/:80`。

### ⚠️ 端口一致性

| `app_type` | Dockerfile EXPOSE | 容器实际监听 | `project.port` 应设为 | 错误示例 |
|------------|-------------------|-------------|----------------------|---------|
| django | 8000 | 8000 (gunicorn) | **8000** | — |
| vue | 80 | 80 (nginx) | **80** | `79` → 探针打 `:79`，nginx 听 `:80` → CrashLoopBackOff |

> **项目创建时 `port` 必须与模板的监听端口一致**。`port` 会被写入 Deployment YAML 的 `containerPort`、Service `targetPort`、以及健康检查 URL。不一致会导致 Pod 反复重启。

---

## 项目标准化要求

Builder 对源码项目有最小约定，构建前会校验：

### Django 项目

| 文件 | 必填 | 说明 |
|------|:---:|------|
| `requirements.txt` | ✅ | pip 依赖列表，用于构建阶段 `pip install` |
| `start_app.sh` | ✅ | 容器启动脚本，Runner 模板 Dockerfile 通过 `CMD ["./start_app.sh"]` 调用 |
| `python_version.txt` | | 指定 Python 版本号（如 `3.12`），未提供时默认 `3.12` |

**start_app.sh 参考实现**:
```bash
#!/bin/bash
set -e
echo "[start_app.sh] Starting Django backend..."
echo "APP_NAME=${APP_NAME:-unknown}"
echo "APP_TAG=${APP_TAG:-unknown}"
python manage.py migrate --noinput
exec gunicorn k8s_console.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120
```

### Vue 项目

| 文件 | 必填 | 说明 |
|------|:---:|------|
| `package.json` | ✅ | npm 依赖 + `build` 脚本 |
| `start_app.sh` | ✅ | 容器启动脚本 |

**start_app.sh 参考实现**:
```bash
#!/bin/bash
echo "Starting ${APP_NAME}:${APP_TAG}..."
exec nginx -g "daemon off;"
```

---

## 安全设计

| 措施 | 说明 |
|------|------|
| **路径白名单** | 只允许构建 `/data/project/`、`D:\`、`C:\`、`/home/`、`/Users/` 等前缀下的路径，防路径遍历 |
| **源码隔离** | 复制到临时目录 `/tmp/build-{app}-{uuid}` 构建，构建完即删 |
| **排除敏感文件** | `.git`、`node_modules`、`__pycache__`、`.venv`、`*.pyc` 等不会进入构建上下文 |
| **超时保护** | Docker build 最长 600s，防止卡死 |
| **SQL 注入防护** | AppProject 的 CRUD 操作使用 Django ORM，无原始 SQL 拼接 |

---

## 镜像保留策略

```
每次构建后自动执行:
1. docker images --filter "reference={app_name}" → 列出所有 tag
2. 按创建时间降序排列
3. 保留最新 5 个 → docker rmi 删除其余
```

- 正在 K8s 中运行的镜像不会被删除（Docker 阻止删除正在使用的镜像层）
- 手动查看: `docker images --filter "reference=my-app"`

---

## 日志

Builder Service 启动后同时输出日志到两个目标：

| 目标 | 路径 | 说明 |
|------|------|------|
| 控制台 | `stdout` | 实时查看 |
| 文件 | `logs/api.log` | 轮转保留，10MB × 5 个备份 |

日志格式: `[2026-07-12 18:00:00] INFO api >>> POST http://... | params=... | body=...`

---

## 常见问题

### 1. "本地路径不存在"

路径必须使用 Windows 格式且真实存在：
- ✅ 正确: `D:/project/k8s_cicd/k8s_cicd/backend`
- ❌ 错误: `/d/project/k8s_cicd/k8s_cicd/backend`（`os.path.abspath()` 会错误解析为 `D:\d\project\...`）

### 2. "项目必须包含 start_app.sh"

Builder 强制要求项目根目录有 `start_app.sh`，因为 Dockerfile 模板使用 `CMD ["./start_app.sh"]`。

创建文件后注意：
- 确保有执行权限: `chmod +x start_app.sh`
- 行尾必须是 **LF**（不是 CRLF），否则容器内 `bad interpreter` 错误

### 3. docker build 超时（600s）

首次构建可能很慢（下载基础镜像 + pip/npm install）。如果超过 10 分钟：
- 检查网络是否正常
- 考虑预拉取基础镜像: `docker pull python:3.12-slim && docker pull node:22-alpine && docker pull nginx:latest`

### 4. 端口不匹配导致 Pod CrashLoopBackOff

YAML 中的端口来自 `project.port`，必须与容器实际监听端口一致：
- Django → `port=8000`
- Vue → `port=80`

如果填错了，先更新项目配置再重新部署。

---

## 文件结构

```
builder/
├── main.py              # Flask HTTP API 入口 (0.0.0.0:9008)
├── build_runner.py      # 核心构建逻辑: build()
├── readme.md            # 本文档
├── requirements.txt     # Flask 依赖
├── templates/
│   ├── django/
│   │   └── Dockerfile   # Django 多阶段构建模板
│   └── vue/
│       └── Dockerfile   # Vue (node + nginx) 多阶段构建模板
└── logs/
    └── api.log          # 运行日志（轮转）
```
