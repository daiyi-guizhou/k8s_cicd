# ☸️ K8s Management Console — K8s 管理控制台

基于 Django REST Framework + Vue 3 的 Kubernetes 集群管理 Web 控制台，支持多集群管理、资源 CRUD、YAML Apply、用户管理和审计日志。

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端** | Vue 3 + Vite + Vue Router 4 + Pinia 2 + Axios | SPA 单页应用，CodeMirror 6 YAML 编辑器 |
| **后端** | Python 3.12 + Django 5.2 + DRF 3.16 | REST API，Token 认证，Gunicorn 4 workers |
| **数据库** | MySQL 8.0 + Redis 7 | MySQL 存储用户/审计日志/集群配置；Redis 存储 Token 和黑名单 |
| **K8s** | kubernetes-client/python 34.x | 官方 K8s Python SDK，操作 14 种资源类型 |
| **基础设施** | Docker Desktop K8s 1.34 + ingress-nginx v1.11.3 | NodePort 30000 暴露 ingress-nginx |

---

## 完整部署链路

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          用户浏览器 (Windows / Chrome)                         │
│         http://k8s-cicd.daiyi.local.com:9001                                 │
│         hosts: 127.0.0.1 → k8s-cicd.daiyi.local.com                         │
│         代理绕过: *.daiyi.local.com                                           │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │ DNS 解析 → 127.0.0.1:9001
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Layer 1: Docker NGINX 网关容器 (k8s-gateway, nginx:latest)                    │
│ 端口映射: 宿主 9001 → 容器 :80                                               │
│ 配置: deploy/gateway/nginx.conf                                            │
│ proxy_pass http://host.docker.internal:30000                                 │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │ host.docker.internal:30000
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Layer 2: K8s Ingress Controller (ingress-nginx namespace)                     │
│ DaemonSet: ingress-nginx-controller (registry.k8s.io/ingress-nginx:v1.11.3)   │
│ NodePort Service: 80:30000/TCP, 443:30443/TCP                                │
│ 按 host + path 匹配 Ingress 规则，路由到对应的 Service                          │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │ 匹配 host: k8s-cicd.daiyi.local.com
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Layer 3: K8s Ingress (prd namespace, ingressClassName: nginx)                 │
│ /api (Prefix)  → k8s-console-backend:8000 (ClusterIP)                        │
│ /   (Prefix)  → k8s-console-frontend:80  (ClusterIP)                         │
└────────────────────────────┬────────────────────────────────────────────────┘
              ┌──────────────┴──────────────┐
              ▼                              ▼
┌──────────────────────────┐  ┌─────────────────────────────┐
│ Backend Service           │  │ Frontend Service             │
│ k8s-console-backend:8000  │  │ k8s-console-frontend:80      │
│ ClusterIP                 │  │ ClusterIP                    │
└────────────┬─────────────┘  └────────────┬────────────────┘
             │                             │
             ▼                             ▼
┌──────────────────────────┐  ┌─────────────────────────────┐
│ Backend Pod               │  │ Frontend Pod                 │
│ Deployment: 1 replica      │  │ Deployment: 1 replica        │
│ Container: django, port 8000  │  Container: nginx, port 80    │
│ Image: k8s-console-backend   │  │ Image: k8s-console-frontend   │
│                              │  │                              │
│ 启动: Dockerfile 多阶段      │  │ 启动: Dockerfile.local        │
│ 1. migrate                   │  │ 1. COPY dist → /usr/share/    │
│ 2. init_admin                │  │    nginx/html                │
│ 3. gunicorn :8000            │  │ 2. nginx -g "daemon off;"    │
│                              │  │                              │
│ 依赖:                        │  │                              │
│  MySQL (mysql.database.svc)  │  │                              │
│  Redis (redis.database.svc)  │  │                              │
└──────┬───────────────────────┘  └─────────────────────────────┘
       │
       │ BUILDER_SERVICE_URL=http://192.168.65.254:9008
       │ (ConfigMap 注入，触发部署时调用 Builder 构建镜像)
       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Builder Service（宿主机进程，非 K8s Pod）                                       │
│ 监听: 0.0.0.0:9008 | 启动: cd builder && python main.py                      │
│ 作用: 接收 build 请求 → 复制源码 → docker build → 产出镜像                      │
│ 详见: builder/readme.md                                                      │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 数据层 (database namespace)                                                   │
│                                                                              │
│ MySQL 8.0 StatefulSet (1 replica, 10Gi PVC)                                  │
│   Headless Service: mysql.database.svc:3306                                  │
│   用户/密码: appuser / UserPass2024!    数据库: appdb                          │
│                                                                              │
│ Redis 7-alpine Deployment (1 replica, 5Gi PVC)                               │
│   ClusterIP Service: redis.database.svc:6379                                 │
│   密码: RedisPass2024!                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 网络链路逐层解析

浏览器访问 `http://k8s-cicd.daiyi.local.com:9001` 时，请求经过 **4 层网络路由**：

```
浏览器                  Windows                   Docker                   K8s 集群
  │                        │                        │                        │
  │  ① 输入 URL            │                        │                        │
  │  k8s-cicd.daiyi        │                        │                        │
  │  .local.com:9001       │                        │                        │
  │────────────────────────▶                        │                        │
  │                        │  ② Windows hosts 解析   │                        │
  │                        │  127.0.0.1              │                        │
  │                        │  k8s-cicd.daiyi         │                        │
  │                        │  .local.com             │                        │
  │                        │                        │                        │
  │                        │  ③ TCP 127.0.0.1:9001  │                        │
  │                        │────────────────────────▶                        │
  │                        │                        │  ④ NGINX 网关容器       │
  │                        │                        │  k8s-gateway           │
  │                        │                        │  proxy_pass            │
  │                        │                        │  host.docker            │
  │                        │                        │  .internal:30000       │
  │                        │                        │────────────▶           │
  │                        │                        │                        │  ⑤ K8s NodePort
  │                        │                        │                        │  ingress-nginx
  │                        │                        │                        │  :30000
  │                        │                        │                        │──────▶
  │                        │                        │                        │  ⑥ Ingress 规则
  │                        │                        │                        │  host match →
  │                        │                        │                        │  Service → Pod
  │                        │                        │                        │
```

| 层 | 组件 | 地址 | 作用 |
|----|------|------|------|
| ① → ② | **Windows hosts 文件** | `C:\Windows\System32\drivers\etc\hosts` | 将 `*.daiyi.local.com` 解析为 `127.0.0.1`，绕过公网 DNS |
| ③ | **TCP 连接** | `127.0.0.1:9001` | 连接到 Windows 本机 9001 端口 |
| ④ | **Docker NGINX 网关** | `k8s-gateway` 容器 | 反向代理到 `host.docker.internal:30000`（Docker Desktop 宿主机地址） |
| ⑤ | **K8s NodePort** | `ingress-nginx:30000` | ingress-nginx DaemonSet 的 NodePort Service |
| ⑥ | **K8s Ingress 规则** | `k8s-console` Ingress | 按 `host + path` 路由到对应的 Service（`/api` → backend:8000，`/` → frontend:80） |

> 💡 **为什么用 hosts 而不是真正的 DNS？** 域名 `*.daiyi.local.com` 不是公网注册域名，无法通过公共 DNS 解析。Windows hosts 文件将域名映射到 `127.0.0.1`，浏览器就能"找到"本机的 Docker 网关容器。

---

## 快速开始 — 一键部署

### 前置条件

- Windows 11 / WSL2
- Docker Desktop（Kubernetes 已启用，v1.34+）
- kubectl + **Git Bash**（脚本执行环境）
- Node.js 22+（前端本地开发）
- Python 3.12+（后端本地开发）

> ⚠️ **脚本执行环境**: `deploy-all.sh` / `clean-all.sh` / `gateway/start.sh` / `gateway/stop.sh` 必须在 **Git Bash (MINGW64)** 中执行，**不能在 WSL (Linux) 中直接执行**。
>
> **原因**: `npm install` 在 Windows 下安装的是 `@rollup/rollup-win32-x64-*` 原生模块，WSL 内 rollup 会尝试加载 `@rollup/rollup-linux-x64-gnu`（不存在），导致 `MODULE_NOT_FOUND` 错误。脚本中已内置 `npm install` 会自动检测当前平台，但如果 `node_modules` 已存在则不会触发重装。如需在 WSL 中执行，先 `rm -rf frontend/node_modules && cd frontend && npm install`。
>
> 💡 **K8s 集群还没搭好？** 参见 [docs/K8s集群使用指南.md § 0. 集群搭建](docs/K8s集群使用指南.md#0-集群搭建)，包含 Docker Desktop / Minikube / Kind / k3s 四种方案。

### 一键部署

```bash
# 一键部署全部（构建镜像 + 数据库 + Ingress + Console + 注册集群 + 启动网关）
bash deploy/deploy-all.sh

# 如果已构建过镜像，跳过构建步骤
bash deploy/deploy-all.sh --skip-build

# 先清理再重新部署
bash deploy/deploy-all.sh --clean
```

脚本自动完成：
1. 构建后端镜像（Django + Gunicorn）
2. 构建前端镜像（Vue SPA + Nginx）
3. 部署 MySQL + Redis（database namespace）
4. 部署 Ingress-NGINX + NodePort（ingress-nginx namespace）
5. 部署 K8s Console Backend + Frontend + Ingress（prd namespace）
6. 从 `deploy/kubeconfigs/` 自动注册集群 + 启动本地网关

### 一键部署应用（CI/CD）

部署完成后，可通过 Web 控制台的 **CI/CD 部署** 页面对 Django / Vue 项目进行自动化部署。

```
                 k8s-cicd.daiyi.local.com/deploy
                          │
                浏览器 → 网关 → Ingress → k8s-console-backend Pod
                                                    │
                                          ① POST /api/deploy/trigger
                                          ② 调用 Builder Service 构建镜像
                                          ③ 生成 K8s YAML
                                          ④ kubectl apply → 部署到 K8s
                                                    │
                                                    ▼
                                          ┌─────────────────────┐
                                          │  Builder Service      │
                                          │  宿主机 :9008         │
                                          │  docker build ...     │
                                          │  产出: app:v1.0       │
                                          └─────────────────────┘
```

**启动 Builder Service（必须）**:

Builder Service 是独立于 K8s 的**宿主机进程**，负责 Docker 镜像构建。必须在部署前启动：

```bash
# 在宿主机上（Windows Git Bash / PowerShell）
cd D:/project/k8s_cicd/k8s_cicd/builder
pip install flask        # 首次需要安装依赖
python main.py           # 监听 0.0.0.0:9008

# 验证 Builder 是否正常
curl http://127.0.0.1:9008/api/health
# → {"status":"ok"}
```

> ⚠️ **Builder 启动后不要关闭终端**。如果 Builder 未启动，部署会立即失败（"镜像构建失败"）。
>
> **Builder 与 K8s 的关系**: K8s Pod 内没有 Docker daemon，无法执行 `docker build`。Builder Service 必须运行在宿主机上，通过 ConfigMap 中的 `BUILDER_SERVICE_URL=http://192.168.65.254:9008` 让 Pod 访问。详细说明见 [builder/readme.md](builder/readme.md)。

```bash
# 浏览器访问
# http://k8s-cicd.daiyi.local.com:9001/deploy
#    → 注册项目 → 输入 tag → 一键部署
```

### 一键清理

```bash
bash deploy/clean-all.sh
# 删除所有 namespace + cluster 资源 + 本地网关容器 + port-forward 进程
```

### 步骤 0: 搭建 K8s 集群（如尚未搭建）

Docker Desktop → Settings → Kubernetes → ✅ Enable Kubernetes → Apply & Restart。

```bash
kubectl get nodes  # 确认 STATUS=Ready
```

### 步骤 1: （可选）手动分步部署

如果不使用一键脚本，可以按以下步骤手动部署：

```bash
# 1. 部署数据库
kubectl apply -f deploy/database/
kubectl wait --for=condition=ready pod -n database --all --timeout=120s

# 2. 部署 ingress-nginx
kubectl apply -f deploy/ingress-nginx/
kubectl wait --for=condition=ready pod -n ingress-nginx --selector=app.kubernetes.io/component=controller --timeout=120s

# 3. 构建镜像
DOCKER_BUILDKIT=0 docker build --pull=false -t k8s-console-backend:latest -f backend/Dockerfile backend/
cd frontend && npm run build && cd ..
DOCKER_BUILDKIT=0 docker build --pull=false -t k8s-console-frontend:latest -f frontend/Dockerfile.local frontend/

# 4. 部署 K8s Console
kubectl apply -f deploy/console/
kubectl wait --for=condition=ready pod -n prd --all --timeout=120s
```

> 📖 详细说明见 [docs/数据库部署指南.md](docs/数据库部署指南.md)、[docs/本地网关部署指南.md](docs/本地网关部署指南.md)

### 步骤 2: 配置 Windows hosts + 启动网关

```bash
# 1. 配置 Windows hosts（管理员权限）
# C:\Windows\System32\drivers\etc\hosts:
#   127.0.0.1 k8s-cicd.daiyi.local.com

# 2. 配置 Windows 代理绕过（如需要）
# reg add "HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyOverride /t REG_SZ /d "原有值;*.daiyi.local.com" /f

# 3. 启动本地网关（已包含在 deploy-all.sh 中，也可单独执行）
bash deploy/gateway/start.sh

# 4. 浏览器访问
# http://k8s-cicd.daiyi.local.com:9001
```

> 💡 **Windows hosts 与 DNS 解析**: `*.daiyi.local.com` 不是公网域名，浏览器无法通过公共 DNS（如 `8.8.8.8`）解析它。Windows hosts 文件本质上是 **本地 DNS 覆盖**——当浏览器请求解析域名时，Windows 先查 hosts 文件，找到匹配行 `127.0.0.1 xxx.daiyi.local.com` 就直接返回 IP，不再请求上游 DNS。DNS → 网关的完整链路见上文 [网络链路逐层解析](#网络链路逐层解析)。
>
> 💡 `start.sh` 内置 **NodePort + port-forward 双保险**：优先使用 NodePort 30000，不可达时自动启动 `kubectl port-forward` 兜底。
>
> 📖 详细说明见 [docs/本地网关部署指南.md](docs/本地网关部署指南.md)

---

## 文档索引

| 文档 | 说明 |
|------|------|
| [docs/K8s集群使用指南.md](docs/K8s集群使用指南.md) | K8s 集群概览、kubectl 命令速查、PV/PVC、Ingress、Dashboard |
| [docs/数据库部署指南.md](docs/数据库部署指南.md) | MySQL + Redis K8s 部署、连接信息、常用命令 |
| [docs/本地网关部署指南.md](docs/本地网关部署指南.md) | 完整链路架构、本地网关部署、故障排查 6 项 |
| [docs/cicd-deploy.md](docs/cicd-deploy.md) | CI/CD 自动化部署 — Django/Vue 项目一键构建部署回滚 |
| [docs/多集群添加教程.md](docs/多集群添加教程.md) | 添加和管理多个 K8s 集群的教程 |
| [docs/e2e-test-conditions.md](docs/e2e-test-conditions.md) | E2E 测试用例和验收条件（F1-F15） |
| [backend/README.md](backend/README.md) | 后端开发指南（conda 环境、API 概览、数据库表结构） |
| [frontend/README.md](frontend/README.md) | 前端开发指南（页面结构、本地开发、组件树） |

---

## 项目结构

```
k8s_cicd/
├── README.md                            # ← 本文件
├── backend/                             # Django REST Framework 后端
│   ├── README.md
│   ├── Dockerfile                       # 多阶段构建 (builder + runtime)
│   ├── requirements.txt
│   ├── manage.py
│   ├── k8s_console/                     # Django 项目配置
│   │   ├── settings.py                  # 生产/集群内配置
│   │   ├── settings_dev.py              # 本地开发覆盖配置
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── middleware.py                # 审计日志 + Token 黑名单中间件
│   ├── apps/
│   │   ├── auth_app/                    # 认证 + 用户管理
│   │   ├── resources/                   # K8s 资源操作（14 种类型）
│   │   ├── clusters/                    # 多集群管理 (v1.1)
│   │   ├── deploy/                      # CI/CD 部署管理（v1.2）
│   │   └── audit/                       # 审计日志
│   ├── utils/
│   │   ├── response.py                  # 统一 JSON 响应格式
│   │   └── k8s_helper.py                # K8s 错误包装
│   └── sql/
│       └── init_database.sql            # 建表 SQL
├── frontend/                            # Vue 3 前端
│   ├── README.md
│   ├── Dockerfile                       # CI 多阶段构建
│   ├── Dockerfile.local                 # 本地构建
│   ├── nginx.conf                       # 生产 Nginx 配置
│   ├── vite.config.js
│   └── src/
│       ├── main.js                      # Vue 入口
│       ├── App.vue                      # 根组件（侧边栏布局）
│       ├── router/index.js              # Vue Router + 路由守卫
│       ├── stores/                      # Pinia 状态管理 (auth + cluster)
│       ├── api/                         # Axios API 层 (client + 5 个模块)
│       ├── components/                  # 6 个可复用组件
│       └── views/                       # 7 个页面视图
├── builder/                              # Builder Service（宿主机）— Docker 构建
│   ├── readme.md                         # 构建流程、API、端口约定、安全设计
│   ├── main.py                           # Flask 入口，监听 0.0.0.0:9008
│   ├── build_runner.py                   # 构建逻辑 + 镜像保留策略
│   └── templates/                        # Django / Vue 标准 Dockerfile
│       ├── django/Dockerfile
│       └── vue/Dockerfile
├── deploy/                              # K8s 部署清单
│   ├── deploy-all.sh                    # ingress-nginx + 演示应用一键部署
│   ├── ingress-nginx/                   # Ingress-NGINX 网关基础设施
│   │   ├── 01-namespace.yaml            # ingress-nginx Namespace
│   │   ├── 02-rbac.yaml                 # RBAC (SA + Role + ClusterRole)
│   │   ├── 03-configmaps.yaml           # Controller 配置
│   │   ├── 04-daemonset.yaml            # ingress-nginx-controller DaemonSet
│   │   ├── 05-service.yaml              # NodePort Service (:30000)
│   │   └── 06-ingressclass.yaml         # IngressClass nginx
│   ├── database/                        # 数据库部署 (MySQL + Redis)
│   │   ├── 01-namespace.yaml
│   │   ├── 02-secrets.yaml
│   │   ├── 03-configmaps.yaml
│   │   ├── 04-mysql.yaml               # MySQL 8.0 StatefulSet
│   │   └── 05-redis.yaml               # Redis 7 Deployment
│   ├── console/                         # K8s Console 应用部署
│   │   ├── 01-namespace.yaml            # prd Namespace
│   │   ├── 02-sa-rbac.yaml              # SA + ClusterRole + ClusterRoleBinding
│   │   ├── 03-configmap.yaml            # 后端 ConfigMap
│   │   ├── 04-secret.yaml               # 后端 Secret
│   │   ├── 05-backend.yaml              # Backend Deployment + Service
│   │   ├── 06-frontend.yaml             # Frontend Deployment + Service
│   │   └── 07-ingress.yaml              # Ingress 路由
│   ├── demo/                            # 演示应用（验证 ingress-nginx）
│   │   └── 01-prd-app.yaml              # nginx demo (host: myapp.local)
│   └── gateway/                         # 本地 NGINX 网关
│       ├── nginx.conf                   # 网关 NGINX 配置
│       ├── start.sh                     # 一键启动脚本
│       └── stop.sh                      # 停止脚本
└── docs/                                # 文档
    ├── K8s集群使用指南.md
    ├── 数据库部署指南.md
    ├── 本地网关部署指南.md
    ├── 多集群添加教程.md
    └── e2e-test-conditions.md
```

---

## 本地开发

项目维护两套配置：`dev`（本地启动测试）和 `prd`（构建镜像部署 K8s）。

### 后端开发

```bash
cd backend
conda create -n k8s-console python=3.12 -y
conda activate k8s-console
pip install -r requirements.txt

# 端口转发 MySQL 和 Redis
kubectl port-forward -n database svc/mysql 3306:3306 &
kubectl port-forward -n database svc/redis 6379:6379 &

# Dev 环境 — 覆盖 DB/Redis 为 127.0.0.1
export DJANGO_SETTINGS_MODULE=k8s_console.settings_dev
python manage.py migrate
python manage.py init_admin
python manage.py runserver 0.0.0.0:8000
```

### 前端开发

```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:3000
# API 代理目标由 .env.development 的 VITE_API_TARGET 控制（默认 http://localhost:8000）
```

### 环境配置速查

| 配置文件 | 环境 | 切换方式 |
|----------|------|----------|
| `backend/k8s_console/settings_dev.py` | Dev | `export DJANGO_SETTINGS_MODULE=k8s_console.settings_dev` |
| `backend/k8s_console/settings.py` | Prd（默认） | 不设或 `k8s_console.settings` |
| `frontend/.env.development` | Dev | `npm run dev` 自动加载 |
| `frontend/.env.production` | Prd | `npm run build` 自动加载 |
| `frontend/.env.local` | 本地覆盖 | 优先级最高，已 `.gitignore` |

> 前端 Dev 如需直连 K8s 后端（跳过本地 Django），在 `frontend/.env.local` 中设 `VITE_API_TARGET=http://localhost:30000`。
>
> 入门登录: 用户名 `admin`，密码 `admin`

---

## 支持的 K8s 资源类型

`namespace`, `deployment`, `pod`, `service`, `ingress`, `daemonset`, `statefulset`, `configmap`, `secret`, `role`, `rolebinding`, `clusterrole`, `clusterrolebinding`, `serviceaccount`

支持的操作：查看列表、查看详情 (JSON/YAML)、扩缩容、回滚 (Deployment)、删除、YAML Apply。

---

## 设计说明

| 决策 | 原因 |
|------|------|
| 网关使用 `nginx:latest` 而非 OpenResty | 更轻量，功能满足需求 |
| 网关端口 9001 而非 80 | 避免 WSL wslrelay / IIS 抢占 80 端口 |
| NodePort 30000 而非 `kubectl port-forward` | NodePort 随集群存活，不依赖终端常驻 |
| `host.docker.internal` 解析宿主机 | Docker Desktop 内置，无需 `--add-host` |
| `deploy/gateway/`（原 `deploy/openresty/`） | 已重命名为 gateway/，反映实际使用的 nginx:latest |
| `deploy/deploy-all.sh` 部署的是演示应用 | 和 k8s-console 控制台应用是两套独立部署；Console 部署见 `deploy/console/` |
