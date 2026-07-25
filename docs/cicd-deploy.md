# 🚀 CI/CD 自动化部署 — 使用指南

> **适用版本**: K8s Console v1.2+
> **适用项目**: Django + Vue（仅限 K8s 集群部署）

---

## 概述

CI/CD 部署子系统可以让你在 **Web 控制台中一键完成**从源码到 K8s 集群的整个部署流程：

```
输入 tag → Docker 构建镜像 → 生成 Deployment/Service/Ingress YAML → kubectl apply → 域名访问
```

支持 **回滚到任意历史 tag**，每个项目保留最多 **5 个本地镜像**。

---

## 架构概览

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Vue 前端      │────▶│  Django Backend   │────▶│  Builder Service     │
│  /deploy 页面  │     │  K8s Console Pod  │     │  宿主机 :9008         │
└──────────────┘     └───────┬──────────┘     └──────────┬──────────┘
                             │                           │
                        ┌────┴────┐              ┌───────┴───────┐
                        │  MySQL  │              │  Docker Build  │
                        │ (Prd)   │              │ (本地镜像)      │
                        └─────────┘              └───────────────┘
                             │
                    ┌────────┴────────┐
                    │  K8s API Server │
                    │  kubectl apply  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ Ingress  │  │ Service  │  │Deployment│
        │ (域名路由)│  │(ClusterIP)│  │  (Pod)   │
        └──────────┘  └──────────┘  └──────────┘
```

### 关键地址

| 组件 | 地址 | 说明 |
|------|------|------|
| 前端控制台 | `http://k8s-cicd.daiyi.local.com:9001/deploy` | CI/CD 部署管理页面 |
| 后端 API | `http://k8s-cicd.daiyi.local.com:9001/api/deploy/*` | 部署相关接口 |
| Builder Service | `http://127.0.0.1:9008`（宿主机 localhost） | Docker 镜像构建服务 |
| K8s Pod 访问 Builder | `http://192.168.65.254:9008`（Docker Desktop） | K8s Pod 内通过宿主网关访问 |
| 部署后的应用 | `http://{domain}:9001` | 由 Ingress 路由 |

> 💡 **Builder 地址说明**: Builder 监听 `0.0.0.0:9008`（不是 `127.0.0.1`）。宿主机用 `127.0.0.1:9008` 即可；K8s Pod 内需要通过 Docker Desktop 的宿主网关 `192.168.65.254:9008` 访问（由 `BUILDER_SERVICE_URL` ConfigMap 配置）。详见 [builder/readme.md](../builder/readme.md)。

---

## 快速开始

### 前置条件

1. K8s Console 已部署并正常运行（`bash deploy/deploy_one_by_one/deploy-all.sh`）
2. **Builder Service 已在宿主机启动**（见下方）
3. 目标项目的源码必须在宿主机上存在（Local Copy 模式）

### Step 1: 启动 Builder Service

Builder Service 是独立于 K8s Console 的宿主机进程，负责 Docker 镜像构建。

```bash
# 在宿主机上（Windows Git Bash）
cd D:/project/k8s_cicd/k8s_cicd/builder
pip install flask        # 首次需要安装依赖
python main.py           # 启动在 0.0.0.0:9008

# 验证
curl http://127.0.0.1:9008/api/health
# → {"status":"ok"}
```

> 💡 **为什么 Builder Service 要独立运行？** K8s Pod 内没有 Docker daemon，无法执行 `docker build`。Builder Service 运行在宿主机上，直接调用宿主机的 Docker 进行镜像构建。

### Step 2: 注册项目

1. 浏览器打开 `http://k8s-cicd.daiyi.local.com:9001/deploy`
2. 点击左上角 **"+ 新增项目"**
3. 填写表单（见下方字段说明）
4. 点击 **"创建"**

### Step 2.5: 配置 hosts（仅部署新域名时需要）

首次部署到新域名时，需要在 Windows hosts 中添加一条记录，使浏览器能解析该域名到本地网关：

```
# 以管理员身份打开记事本/Notepad，编辑：
# C:\Windows\System32\drivers\etc\hosts
# 添加：
127.0.0.1 <你的域名>
```

例如部署 `my-shop.daiyi.local.com`：
```
127.0.0.1 my-shop.daiyi.local.com
```

> 💡 `k8s-cicd.daiyi.local.com` 已由 `deploy-all.sh` 自动配置。`backend-app.daiyi.local.com` 如已配置则跳过此步骤。

### Step 3: 一键部署

1. 从左侧项目列表选择一个项目
2. 右侧 "一键部署" 卡片 → 输入 Tag（如 `v1.0.0`）
3. 点击 **"🚀 一键部署"**
4. 等待完成（约 10-120 秒，取决于代码量和 Docker 缓存）
5. 页面顶部 **Toast 提示 "部署成功"** → 完成！

### Step 4: 访问部署的应用

浏览器打开 `http://{项目的域名}:9001` 即可访问。完整链路：

```
浏览器 (:9001) → Docker NGINX 网关 → K8s Ingress (:30000 NodePort) → Service → Pod
```

例如部署 `backend-app.daiyi.local.com` 后：

| 访问方式 | 地址 |
|----------|------|
| 浏览器 | `http://backend-app.daiyi.local.com:9001/` → Vue 前端 |
| 浏览器 | `http://backend-app.daiyi.local.com:9001/api/health` → Django API |
| curl | `curl -s --noproxy '*' http://localhost:9001/ -H 'Host: backend-app.daiyi.local.com'` |

---

## 项目注册字段说明

| 字段 | 必填 | 说明 | 默认值 | 示例 |
|------|------|------|--------|------|
| **应用名称** | ✅ | 唯一标识，创建后不可修改 | — | `backend-app` |
| **应用类型** | ✅ | `Django` 或 `Vue` | `Django` | — |
| **本地代码路径** | ✅ | 宿主机上的项目源码路径 | — | `D:/project/k8s_cicd/k8s_cicd/backend` |
| **访问域名** | ✅ | 部署后 Ingress 路由的 host | — | `my-shop.daiyi.local.com` |
| **Ingress Path** | | 同域名多项目路由区分 | `/api` (Django) / `/` (Vue) | `/api` |
| **容器端口** | | 容器内暴露端口，**必须与 app_type 匹配** | 8000 (Django) / **80** (Vue) | `8000` |
| **副本数** | | Pod 副本数量 | 1 | `2` |
| **命名空间** | | K8s Namespace | `prd` | `prd` |
| **目标集群** | ✅ | 部署到哪个 K8s 集群 | — | `docker-desktop` |
| **启用** | | 禁用后无法触发部署 | ✅ | — |

> ⚠️ **端口一致性**: `port` 必须与容器的实际监听端口一致——Django 为 **8000**（gunicorn 默认），Vue 为 **80**（nginx 默认）。端口写错（如 Vue 填 `79`）会导致健康检查打到错误端口 → `connection refused` → Pod CrashLoopBackOff。
>
> ⚠️ **Windows 路径重要提示**: 必须使用 `D:/path/to/project` 格式（正斜杠），不要用 `/d/path/` 格式。
> `/d/project/...` 会被 `os.path.abspath()` 错误解析为 `D:\d\project\...`（多一层目录）。

---

## 一键部署流程（详细）

```
1. 用户点击 "一键部署"
2. Backend 创建 DeployHistory（status=building）
3. Backend → Builder Service 发送构建请求 {app_name, app_type, tag, local_path}
4. Builder Service:
   a. 校验 local_path 是否存在
   b. 路径白名单检查（防路径遍历攻击）
   c. 校验项目文件: requirements.txt (Django) / package.json (Vue)
   d. 读取 python_version.txt (Django，默认 "3.12")
   e. 复制源码到临时构建目录（排除 .git, node_modules, __pycache__ 等）
   f. 渲染模板 Dockerfile → docker build
   g. 镜像保留策略：清理旧镜像，保留最新 5 个
   h. 返回 {image: "app_name:tag"}
5. Backend 生成 Deployment + Service + Ingress YAML
6. Backend 调用 K8s Python SDK 执行 apply
7. DeployHistory.status → "success"，前端刷新历史
```

### 生成的 K8s 资源

每次部署 apply 的 YAML 包含 3 个资源：

| Django 项目 | Vue 项目 |
|-------------|----------|
| Ingress path: `/api`（默认） | Ingress path: `/`（默认） |
| Deployment: tcpSocket 探针 (port=8000) | Deployment: httpGet 探针 (path=/ port=80) |
| 资源: 100m CPU / 128Mi Mem → 500m / 512Mi | 资源: 50m CPU / 64Mi Mem → 200m / 128Mi |
| Service: ClusterIP port=8000 | Service: ClusterIP port=80 |
| Ingress: ingressClassName=nginx | Ingress: ingressClassName=nginx |
| imagePullPolicy: IfNotPresent | imagePullPolicy: IfNotPresent |
| 注入环境变量: APP_NAME, APP_TAG | 注入环境变量: APP_NAME, APP_TAG |

> 💡 **同域名前后端部署**: Django 项目默认 Ingress Path 为 `/api`，Vue 项目默认 `/`，两者使用相同 domain 即可用同一域名同时承载前后端。

---

## 回滚

在部署历史表格中，每条 **成功** 的部署记录都有一个 **"🔄 回滚"** 按钮：

1. 点击 → 弹出确认弹窗
2. 确认 → 重新生成 YAML（使用该 tag 的镜像）→ apply
3. 系统创建新的 DeployHistory 记录（status=success, message="回滚到 {tag}"）

**限制条件**：
- 只能回滚到曾经**部署成功**的 tag（必须有 success 记录）
- 该 tag 的镜像需仍存在于 Docker 中（未被清理策略删除）
- **K8s Pod 内回滚**: 因 Pod 内无 docker 命令，docker 检查失败时自动放行（允许回滚，镜像可能在节点上）

---

## 部署历史

| 状态 | 颜色 | 含义 |
|------|------|------|
| `building` | 🔵 蓝 | Builder Service 正在构建镜像 |
| `deploying` | 🔵 蓝 | 镜像构建完成，正在 apply YAML |
| `success` | 🟢 绿 | 部署完成，可通过域名访问 |
| `failed` | 🔴 红 | 构建或部署失败，查看 message 列 |

---

## 项目标准化要求

### Django 项目

项目根目录必须包含：

| 文件 | 必填 | 说明 |
|------|:---:|------|
| `requirements.txt` | ✅ | pip 依赖列表 |
| `start_app.sh` | ✅ | 容器启动脚本，Dockerfile 通过 `CMD ["./start_app.sh"]` 调用 |
| `python_version.txt` | | Python 版本号（如 `3.12`），未提供时默认 `3.12` |

**start_app.sh 示例**（`backend/start_app.sh`）:
```bash
#!/bin/bash
set -e
echo "[start_app.sh] Starting Django backend..."
echo "APP_NAME=${APP_NAME:-unknown}"
echo "APP_TAG=${APP_TAG:-unknown}"
python manage.py migrate --noinput
exec gunicorn k8s_console.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120
```

> 环境变量 `APP_NAME` 和 `APP_TAG` 由 Deployment YAML 自动注入。

### Vue 项目

项目根目录必须包含：

| 文件 | 必填 | 说明 |
|------|:---:|------|
| `package.json` | ✅ | npm 依赖 + build 脚本 |
| `start_app.sh` | ✅ | 容器启动脚本 |

**start_app.sh 示例**:
```bash
#!/bin/bash
echo "Starting ${APP_NAME}:${APP_TAG}..."
exec nginx -g "daemon off;"
```

---

## 镜像保留策略

Builder Service 每次构建完成后自动清理：

```
1. docker images --filter "reference={app_name}" → 列出所有 tag
2. 按创建时间排序（最新在前）
3. 保留最新 5 个，删除其余
```

- 正在 K8s 中运行的镜像**不会被误删**（Docker 阻止删除正在使用的镜像层）
- 手动查看: `docker images --filter "reference=backend-app"`

---

## 权限控制

| 操作 | admin | 普通用户 |
|------|:---:|:---:|
| 查看项目列表 | ✅ | ✅ |
| 查看部署历史 | ✅ | ✅ |
| 新增项目 | ✅ | ❌ |
| 编辑项目 | ✅ | ❌ |
| 删除项目 | ✅ | ❌ |
| 一键部署 | ✅ | ❌ |
| 回滚 | ✅ | ❌ |

---

## 常见问题

### 1. 浏览器无法访问部署的域名

**现象**: 浏览器打开 `http://xxx.daiyi.local.com:9001` 提示 `ERR_NAME_NOT_RESOLVED`。

**原因**: Windows hosts 未配置该域名 → `127.0.0.1` 的映射。

**解决**: 以管理员身份编辑 `C:\Windows\System32\drivers\etc\hosts`，添加：
```
127.0.0.1 xxx.daiyi.local.com
```
然后刷新浏览器即可。

> 💡 **完整链路**: 浏览器 → `hosts 解析到 127.0.0.1:9001` → Docker NGINX 网关容器（`--network host`）→ `127.0.0.1:30000` → K8s ingress-nginx NodePort → Ingress 规则匹配 host → Service → Pod。

### 2. Builder Service 不可达 → 部署立即失败

**现象**: 点击部署后立即显示 "镜像构建失败"，历史显示 `status=failed`。

**排查**:
```bash
# 宿主机检查
curl http://127.0.0.1:9008/api/health

# K8s Pod 内检查（需要通过 Docker Desktop 宿主网关地址）
kubectl exec -n prd deploy/k8s-console-backend -- python -c "
import urllib.request
print(urllib.request.urlopen('http://192.168.65.254:9008/api/health', timeout=5).read())
"
```

**解决**: 在宿主机 `cd builder && python main.py`

### 3. "本地路径不存在" 错误

**原因**: 路径格式不匹配。Builder Service 运行在 Windows 上，必须使用 Windows 格式。

- ✅ 正确: `D:/project/k8s_cicd/k8s_cicd/backend`
- ❌ 错误: `/d/project/k8s_cicd/k8s_cicd/backend`

可以通过 API 更新路径：
```bash
curl -s --noproxy '*' http://localhost:30000/api/deploy/project/update \
  -H 'Host: k8s-cicd.daiyi.local.com' -H "Authorization: Token $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"app_name":"backend-app","local_path":"D:/project/k8s_cicd/k8s_cicd/backend"}'
```

### 4. 账号无管理员权限 → 看不到操作按钮

**现象**: 侧边栏只有 "仪表盘" + "资源管理" + "CI/CD 部署" + "Apply YAML"，部署页看不到新增/编辑/部署按钮。

**原因**: 只有 `role=admin` 的用户才能操作。确认当前用户角色：查看 users 管理页面或通过 admin 账号检查数据库。

### 5. 部署后 Pod 不健康

**现象**: Pod `CrashLoopBackOff` 或 `Running 0/1`。

**排查**:
```bash
kubectl logs -n prd deploy/{app_name} --tail=100
kubectl describe pod -n prd -l app={app_name}
```

**常见原因**:

| 原因 | 现象 | 修复 |
|------|------|------|
| **端口不匹配**（最常见） | probe 报 `connection refused`，Pod 反复重启 | Vue 项目 `port` 必须为 **80**，Django 必须为 **8000** |
| `start_app.sh` 行尾是 CRLF | 容器内 `/bin/bash^M: bad interpreter` | `dos2unix start_app.sh` 或 IDE 中将行尾设为 LF |
| 缺少 `requirements.txt`（Django）或 `package.json`（Vue） | 构建阶段报文件不存在 | 确保项目根目录包含必需文件 |
| 数据库/Redis 连接配置不正确 | 容器日志打印连接错误 | 检查环境变量和 ConfigMap |
| gunicorn WSGI 模块名错误 | gunicorn 启动报 `ModuleNotFoundError` | 确认 WSGI 模块路径与实际项目结构一致 |

> 💡 **端口不匹配诊断**: `kubectl describe pod -n prd -l app={app_name} | grep -A5 'Liveness\|Readiness'` 可看到探针打的端口。对比 `kubectl exec -n prd deploy/{app_name} -- ss -tlnp` 查看容器实际监听的端口。如果不一致，更新项目 `port` 字段后重新部署。

### 6. 部署触发后页面卡在 "部署中..."

**现象**: 点击部署后按钮一直显示 "部署中..."，没有 Toast。

**原因**: 部署请求超时。Docker 构建可能需要几分钟（首次构建尤其慢）。

**排查**: 
1. 看浏览器 DevTools Network 面板，确认请求状态
2. 查看后端日志: `kubectl logs -n prd deploy/k8s-console-backend --tail=20`
3. 查看 Builder Service 终端输出

**注意**: HTTP 请求超时设为 600s，如果构建超过 10 分钟会失败。

### 7. 回滚在 K8s Pod 中失败

K8s Pod 内没有 `docker` 命令。当前实现已处理此情况：`subprocess.run(["docker", ...])` 失败时自动放行（`docker_ok = True`），允许回滚到存在镜像的 tag。如果节点上确实没有该镜像，回滚会正常失败。

---

## API 参考

### 项目管理

```bash
BASE="http://localhost:30000"
HOST="Host: k8s-cicd.daiyi.local.com"
TOKEN="Token $(...)"  # 通过 /api/auth/login 获取

# 列出所有项目
curl -s --noproxy '*' "$BASE/api/deploy/projects" \
  -H "$HOST" -H "Authorization: $TOKEN" -H 'Content-Type: application/json' -d '{}' | python3 -m json.tool

# 创建项目
curl -s --noproxy '*' "$BASE/api/deploy/project/create" \
  -H "$HOST" -H "Authorization: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"app_name":"my-shop","app_type":"django","local_path":"D:/projects/my-shop","domain":"my-shop.daiyi.local.com","port":8000,"cluster_id":1}'

# 更新项目
curl -s --noproxy '*' "$BASE/api/deploy/project/update" \
  -H "$HOST" -H "Authorization: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"app_name":"my-shop","replicas":2}'

# 删除项目（仅删除配置，不删除 K8s 资源）
curl -s --noproxy '*' "$BASE/api/deploy/project/delete" \
  -H "$HOST" -H "Authorization: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"app_name":"my-shop"}'
```

### 部署操作

```bash
# 触发部署
curl -s --noproxy '*' "$BASE/api/deploy/trigger" \
  -H "$HOST" -H "Authorization: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"app_name":"backend-app","tag":"v1.2.0"}'

# 回滚到指定 tag
curl -s --noproxy '*' "$BASE/api/deploy/rollback" \
  -H "$HOST" -H "Authorization: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"app_name":"backend-app","tag":"v1.0.0"}'

# 查看部署历史
curl -s --noproxy '*' "$BASE/api/deploy/history" \
  -H "$HOST" -H "Authorization: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"app_name":"backend-app"}'
```

---

## 文件索引

| 文件 | 说明 |
|------|------|
| `docs/superpowers/specs/2026-07-12-cicd-deploy-design.md` | 完整设计文档 |
| `docs/superpowers/plans/2026-07-12-cicd-deploy-plan.md` | 实现计划（Task 1-12） |
| `docs/e2e-test-conditions.md` § F15 | E2E 验收条件 |
| `backend/apps/deploy/` | Django deploy app（models/views/urls/yaml_gen） |
| `builder/` | Builder Service（Flask + 构建逻辑 + Docker 模板） |
| `builder/readme.md` | Builder Service 文档 — build() 流程、API、端口约定、安全设计 |
| `backend/start_app.sh` | Django 项目 start_app.sh 参考实现 |
| `frontend/src/views/DeployManagementPage.vue` | 部署管理 Vue 页面 |
| `frontend/src/api/deploy.js` | 部署 API 封装 |

---

## 相关设计决策

| 决策 | 原因 |
|------|------|
| Builder Service 独立运行在宿主机 | K8s Pod 内无 Docker daemon，宿主机 Docker Desktop 可直接构建 |
| K8s Pod 通过 `BUILDER_SERVICE_URL` 访问 Builder | ConfigMap 配置宿主机地址（Docker Desktop: `http://192.168.65.254:9008`） |
| Local Copy（非 Git Clone） | 简化实现，代码已在宿主机上，直接 cp 后构建 |
| `imagePullPolicy: IfNotPresent` | 本地 Docker Desktop 模式，不推远程 Registry |
| 镜像保留策略：最多 5 个 | 平衡磁盘空间与回滚可用性 |
| 回滚时 Pod 内 docker 检查失败自动放行 | K8s Pod 内无 docker 命令，节点上镜像可能仍存在 |
| Windows 路径用 `D:/` 格式 | `os.path.abspath()` 对 `/d/` 路径处理不当 |
| 端口必须与 app_type 的默认监听端口一致 | Django=8000 (gunicorn), Vue=80 (nginx)；不匹配会导致健康检查失败 → Pod 重启循环 |
