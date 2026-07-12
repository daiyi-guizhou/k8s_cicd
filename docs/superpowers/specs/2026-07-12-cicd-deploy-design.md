# CI/CD 自动化部署子系统 — 设计文档

**日期**: 2026-07-12
**状态**: ✅ 已实现并验证
**上下文**: 在现有 K8s 管理控制台（Django + Vue + K8s）基础上新增 CI/CD 部署能力
**版本**: v2.1（Local Copy + Rollback + K8s Pod 回滚适配）

---

## 1. 目标与范围

### 1.1 目标

为 Django/Vue 项目提供一键式 K8s 部署自动化：用户在前端输入 tag → 系统自动完成镜像构建 → 生成 K8s YAML（ingress + svc + deployment）→ 部署到集群 → 通过域名访问。支持回滚到任意历史部署的 tag。

### 1.2 范围限定

- **仅支持** Django 项目和 Vue 项目
- **仅部署到** K8s 集群（复用现有 `Cluster` 模型和多集群能力）
- **仅支持** Docker Desktop 本地镜像模式（不推远程 Registry，后续可扩展）
- **仅支持** 本地项目路径（Local Copy），不支持 Git Clone
- 所有 Django 项目使用同一套标准化配置，所有 Vue 项目使用同一套标准化配置
- 支持 **rollback**：可回滚到任意历史部署的 tag
- 每个 app 最多保留 **5 个本地镜像**，超出的按时间顺序自动清理

### 1.3 已验证的路径与网络约束

由于 Builder Service 运行在 Windows 宿主机，而 Backend 运行在 K8s Pod 中：

| 约束 | 解决方案 |
|------|----------|
| **本地路径格式**: `os.path.abspath("/d/path")` → `D:\d\path`（错误） | 必须使用 `D:/path/to/project` 格式 |
| **Pod→宿主机网络**: Pod 的 `192.168.1.24` 不是宿主 | 通过 `192.168.1.24`（Docker Desktop `host.docker.internal`） |
| **Pod 内无 docker 命令**: 回滚时 docker images 检查失败 | 捕获 `FileNotFoundError`, 自动放行（节点上镜像可能仍存在） |
| **ConfigMap 中的 BUILDER_SERVICE_URL** | 部署时设置为 `http://192.168.1.24:9008` |
| **路径白名单**: Windows 盘符需加白名单 | `ALLOWED_PATH_PREFIXES` 包含 `D:\\` 和 `C:\\` |
| **前端 toast inject 不可用**: AppToast 在 `<div v-else>` 内 | 使用 `inject("toast", null)` + window event fallback |

---

## 2. 系统架构

### 2.1 整体架构

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Vue 前端     │────▶│  Django Backend   │────▶│  Builder Service     │
│  (项目管理页)  │     │  (K8s Console)    │     │  (宿主机独立服务)      │
└──────────────┘     └───────┬──────────┘     └──────────┬──────────┘
                             │                           │
                        ┌────┴────┐              ┌───────┴───────┐
                        │  MySQL  │              │  Docker Build  │
                        │         │              │  (本地镜像)     │
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
        │ (域名路由)│  │ (ClusterIP)│  │  (Pod)   │
        └──────────┘  └──────────┘  └──────────┘
```

### 2.2 三层职责

| 层 | 职责 | 关键交互 |
|----|------|----------|
| **Vue 前端** | 项目管理 CRUD；一键部署触发（输入 tag）；部署历史查看；一键回滚 | → Backend API |
| **Django Backend** | AppProject / DeployHistory CRUD；调 Builder Service 构建镜像；生成并 apply K8s YAML；回滚处理 | → Builder Service API；→ K8s API |
| **Builder Service** | 接收构建请求；local copy 获取源码；docker build 构建镜像；镜像保留策略（最多 5 个）；返回构建结果 | 独立服务，监听本地端口 |

### 2.3 部署流程

```
1. 用户在 Vue 前端选择项目，输入 tag，点击"部署"
2. Frontend → POST /api/deploy/trigger { app_name, tag }
3. Backend 查询 AppProject 获取: local_path, app_type, domain, port, namespace, cluster
4. Backend → POST Builder Service { local_path, tag, app_type, app_name }
5. Builder Service:
   a. 检测 {local_path} 是否存在
   b. 检测项目文件: python_version.txt, requirements.txt（Django）
   c. 选择内置模板（Django 或 Vue）
   d. docker build → 本地镜像 tag: {app_name}:{tag}
   e. 清理旧镜像：docker images {app_name}:* → 保留最新的 5 个，删除其余
   f. 返回 { image: "{app_name}:{tag}", status: "success" }
6. Backend 生成 K8s YAML:
   - Deployment（引用构建的镜像）
   - Service（ClusterIP）
   - Ingress（域名规则）
7. Backend 调用 K8s API（已有的 apply_yaml 能力）部署到集群
8. Backend 创建 DeployHistory 记录
9. 返回前端: { domain, status, deploy_time }
10. 用户通过域名访问部署的应用
```

### 2.4 回滚流程

```
1. 用户在 Vue 前端点击某条历史部署记录的"回滚"按钮
2. Frontend → POST /api/deploy/rollback { app_name, tag }
3. Backend 校验：该 tag 的部署历史必须存在（status=success）
4. Backend 尝试验证本地镜像: docker images -q {app_name}:{tag}
   ⚠️ K8s Pod 内无 docker 命令 → 捕获 FileNotFoundError → 放行 (docker_ok=True)
5. Backend 生成 K8s YAML（引用该 tag 的镜像）
6. Backend 调用 apply_yaml（覆盖现有 Deployment/Service/Ingress）
7. Backend 创建新的 DeployHistory 记录（tag=回滚目标tag, status=success）
8. 返回前端: { domain, tag, message: "已回滚到 {tag}" }
```

---

## 3. 数据模型

### 3.1 AppProject（部署项目）

新增 `apps/deploy` app，`AppProject` 以 `app_name` 为主键。

```python
class AppProject(models.Model):
    """需要部署的应用项目"""

    APP_TYPE_CHOICES = [
        ("django", "Django"),
        ("vue", "Vue"),
    ]

    app_name = models.CharField(
        max_length=128, primary_key=True,
        verbose_name="应用名称"
    )
    app_type = models.CharField(
        max_length=16, choices=APP_TYPE_CHOICES,
        verbose_name="应用类型"
    )
    local_path = models.CharField(
        max_length=480, blank=True, default="",
        verbose_name="本地代码地址"
    )
    domain = models.CharField(
        max_length=256,
        verbose_name="访问域名"
    )
    ingress_path = models.CharField(
        max_length=256, default="/",
        verbose_name="Ingress 路径（同域名多个项目时区分路由）"
    )
    port = models.IntegerField(
        default=8000,
        verbose_name="容器端口（Django=8000, Vue=80）"
    )
    namespace = models.CharField(
        max_length=64, default="prd",
        verbose_name="K8s Namespace"
    )
    cluster = models.ForeignKey(
        "clusters.Cluster", on_delete=models.PROTECT,
        verbose_name="目标集群"
    )
    replicas = models.IntegerField(
        default=1,
        verbose_name="Pod 副本数"
    )
    enabled = models.BooleanField(
        default=True,
        verbose_name="启用"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "app_project"
        verbose_name = "部署项目"
        verbose_name_plural = "部署项目"

    def __str__(self):
        return f"{self.app_name} ({self.app_type})"
```

### 3.2 DeployHistory（部署历史）

```python
class DeployHistory(models.Model):
    """部署历史记录"""

    STATUS_CHOICES = [
        ("building", "构建中"),
        ("deploying", "部署中"),
        ("success", "成功"),
        ("failed", "失败"),
    ]

    project = models.ForeignKey(
        AppProject, on_delete=models.CASCADE,
        to_field="app_name", db_column="app_name",
        verbose_name="应用"
    )
    tag = models.CharField(max_length=128, verbose_name="部署 tag")
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default="building",
        verbose_name="状态"
    )
    operator = models.CharField(
        max_length=64, blank=True, default="",
        verbose_name="操作人"
    )
    message = models.TextField(blank=True, default="", verbose_name="结果信息")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="部署时间")

    class Meta:
        db_table = "deploy_history"
        ordering = ["-created_at"]
        verbose_name = "部署历史"
        verbose_name_plural = "部署历史"
```

---

## 4. Builder Service

### 4.1 概述

Builder Service 是运行在宿主机上的独立 Python 服务，监听本地端口（如 `9008`），暴露 HTTP API 供 Django Backend 调用。负责：**构建 Docker 镜像 + 镜像保留策略管理**。

### 4.2 API 定义

**Endpoint**: `POST /api/build`

**Request**:
```json
{
  "app_name": "my-shop",
  "app_type": "django",
  "tag": "v1.2.0",
  "local_path": "/d/projects/my-shop"
}
```

**Response (成功)**:
```json
{
  "code": 0,
  "message": "镜像构建成功",
  "data": {
    "image": "my-shop:v1.2.0",
    "app_name": "my-shop",
    "tag": "v1.2.0"
  }
}
```

**Response (失败)**:
```json
{
  "code": 1,
  "message": "镜像构建失败",
  "error": "docker build 错误详情..."
}
```

### 4.3 构建流程（Local Copy）

```
1. 检测 {local_path} 是否存在，不存在则返回错误
2. 创建临时构建目录 /tmp/build-{app_name}-{uuid}/
3. cp -r {local_path}/* → 构建目录（排除 .git, node_modules, __pycache__ 等）
4. 检测构建目录中项目文件:
   - Django: 需要 requirements.txt，可选 python_version.txt（默认 "3.12"）
   - Vue: 需要 package.json
5. 根据 app_type 选择内置模板 Dockerfile，复制到构建目录
6. docker build -t {app_name}:{tag} .
7. 清理临时目录
8. 执行镜像保留策略（见 4.4）
```

### 4.4 镜像保留策略

构建完成后，清理该 app 的旧镜像，确保最多保留 5 个：

```
1. docker images --filter "reference={app_name}" --format "{{.Tag}} {{.CreatedAt}}"
2. 按创建时间排序（最新的在前）
3. 保留最新的 5 个 tag（包括刚构建的），删除其余
4. docker rmi {app_name}:{old_tag} （逐条删除）
```

注意：当前正在 K8s 中运行的镜像不会被误删，因为 Docker 会阻止删除正在使用的镜像层。

### 4.5 内置模板

Builder Service 在 `templates/` 目录下存放标准模板：

```
builder/templates/
├── django/
│   └── Dockerfile       # 标准 Django 多阶段构建
└── vue/
    └── Dockerfile       # 标准 Vue + Nginx 多阶段构建
```

### 4.6 Django 模板 Dockerfile

```dockerfile
# Stage 1: Build dependencies
FROM python:{PYTHON_VERSION}-slim AS builder
WORKDIR /app
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
    gcc pkg-config default-libmysqlclient-dev && \
    rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:{PYTHON_VERSION}-slim
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
    default-libmysqlclient-dev && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
COPY . .
RUN if [ -f start_app.sh ]; then chmod +x start_app.sh; fi
RUN mkdir -p /data/project/{APP_NAME}/logs
EXPOSE 8000
CMD ["sh", "-c", "./start_app.sh"]
```

- `{PYTHON_VERSION}` 读取项目 `python_version.txt`，默认 `3.12`
- `{APP_NAME}` 用实际 app_name 替换
- 项目路径 `/data/project/{APP_NAME}/`，日志路径 `/data/project/{APP_NAME}/logs/*`

### 4.7 Vue 模板 Dockerfile

```dockerfile
# Stage 1: Build Vue app
FROM node:22-alpine AS builder
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY start_app.sh /start_app.sh
RUN chmod +x /start_app.sh
EXPOSE 80
CMD ["/start_app.sh"]
```

### 4.8 技术实现

Builder Service 最小化实现：Flask 常驻进程，监听 `192.168.1.24`。

---

## 5. Backend API 设计

### 5.1 AppProject CRUD

| Method | Endpoint | 说明 |
|--------|----------|------|
| POST | `/api/deploy/projects` | 列出所有项目 |
| POST | `/api/deploy/project/create` | 创建项目 |
| POST | `/api/deploy/project/update` | 更新项目 |
| POST | `/api/deploy/project/delete` | 删除项目 |

### 5.2 部署触发

| Method | Endpoint | 说明 |
|--------|----------|------|
| POST | `/api/deploy/trigger` | 触发部署（app_name, tag） |

### 5.3 回滚

| Method | Endpoint | 说明 |
|--------|----------|------|
| POST | `/api/deploy/rollback` | 回滚到指定 tag（app_name, tag） |

### 5.4 部署历史

| Method | Endpoint | 说明 |
|--------|----------|------|
| POST | `/api/deploy/history` | 查询某项目的部署历史 |

### 5.5 部署触发接口详细

**Request**:
```json
{
  "app_name": "my-shop",
  "tag": "v1.2.0"
}
```

**Backend 处理逻辑** (`apps/deploy/views.py`):
```python
@api_view(["POST"])
def deploy_trigger(request):
    # 1. 校验参数
    app_name = request.data.get("app_name")
    tag = request.data.get("tag")

    # 2. 查询项目配置
    project = AppProject.objects.get(app_name=app_name)

    # 3. 创建 DeployHistory (building)
    history = DeployHistory.objects.create(
        project=project, tag=tag, status="building",
        operator=request.user.username
    )

    # 4. 调用 Builder Service
    try:
        build_result = requests.post(
            f"{BUILDER_SERVICE_URL}/api/build",
            json={
                "app_name": app_name,
                "app_type": project.app_type,
                "tag": tag,
                "local_path": project.local_path,
            },
            timeout=600  # 构建可能较慢
        )
        build_result.raise_for_status()
    except Exception as e:
        history.status = "failed"
        history.message = str(e)
        history.save()
        return error(...)

    image = build_result.json()["data"]["image"]

    # 5. 生成 K8s YAML
    yaml_content = _generate_k8s_yaml(project, image)

    # 6. kubectl apply
    history.status = "deploying"
    history.save()
    try:
        apply_yaml(project.cluster_id, yaml_content)
    except Exception as e:
        history.status = "failed"
        history.message = str(e)
        history.save()
        return error(...)

    # 7. 标记成功
    history.status = "success"
    history.save()

    return success(data={"domain": project.domain, "tag": tag})
```

### 5.6 回滚接口详细

**Request**:
```json
{
  "app_name": "my-shop",
  "tag": "v1.0.0"
}
```

**Backend 处理逻辑** (`apps/deploy/views.py`):
```python
@api_view(["POST"])
def deploy_rollback(request):
    # 1. 校验参数
    app_name = request.data.get("app_name")
    tag = request.data.get("tag")

    # 2. 查询项目 + 校验 tag 部署历史存在
    project = AppProject.objects.get(app_name=app_name)
    history_check = DeployHistory.objects.filter(
        project=project, tag=tag, status="success"
    ).first()
    if not history_check:
        return error(ERR_VALIDATION, f"未找到 tag='{tag}' 的成功部署记录")

    # 3. 尝试验证本地镜像存在（K8s Pod 内无 docker 则放行）
    image = f"{app_name}:{tag}"
    docker_ok = True
    try:
        result = subprocess.run(
            ["docker", "images", "-q", image],
            capture_output=True, text=True, timeout=10,
        )
        if not result.stdout.strip():
            docker_ok = False
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        docker_ok = True  # Pod 内无 docker, 允许回滚
    if not docker_ok:
        return error(ERR_VALIDATION, f"本地镜像 {image} 不存在，无法回滚")

    # 4. 生成 K8s YAML
    yaml_content = generate_k8s_yaml(project, image)

    # 5. kubectl apply
    try:
        apply_yaml(project.cluster_id, yaml_content)
    except Exception as e:
        return error(ERR_K8S_API_ERROR, "回滚部署失败", str(e))

    # 6. 记录回滚
    DeployHistory.objects.create(
        project=project, tag=tag, status="success",
        operator=request.user.username,
        message=f"回滚到 {tag}"
    )

    return success(data={"domain": project.domain, "tag": tag})
```

---

## 6. K8s YAML 生成逻辑

### 6.1 YAML 模板（Django）

Backend 根据 AppProject 配置动态生成 Deployment + Service + Ingress：

```yaml
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {app_name}
  namespace: {namespace}
  labels:
    app: {app_name}
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: {app_name}
  template:
    metadata:
      labels:
        app: {app_name}
    spec:
      containers:
        - name: {app_name}
          image: {app_name}:{tag}
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: {port}
              protocol: TCP
          env:
            - name: APP_NAME
              value: {app_name}
            - name: APP_TAG
              value: {tag}
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
          readinessProbe:
            tcpSocket:
              port: {port}
            initialDelaySeconds: 10
            periodSeconds: 10
          livenessProbe:
            tcpSocket:
              port: {port}
            initialDelaySeconds: 30
            periodSeconds: 20
---
apiVersion: v1
kind: Service
metadata:
  name: {app_name}
  namespace: {namespace}
  labels:
    app: {app_name}
spec:
  type: ClusterIP
  selector:
    app: {app_name}
  ports:
    - name: http
      port: {port}
      targetPort: {port}
      protocol: TCP
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {app_name}
  namespace: {namespace}
  labels:
    app: {app_name}
spec:
  ingressClassName: nginx
  rules:
    - host: {domain}
      http:
        paths:
          - path: {path}               ← 由 AppProject.ingress_path 指定
            pathType: Prefix
            backend:
              service:
                name: {app_name}
                port:
                  number: {port}
```

### 6.1.1 Ingress Path 默认值

| 应用类型 | 默认 `ingress_path` |
|---------|-------------------|
| Django | `/api` |
| Vue | `/` |

Django 项目默认挂 `/api`，Vue 默认挂 `/`。同域名多项目共存时，通过不同的 Ingress Path 区分路由。

### 6.2 Vue 项目差异

Vue 项目与 Django 项目的 YAML 差异仅在：
- `port`: 80（固定）
- `readinessProbe`: 改用 `httpGet` → `/`（而非 `tcpSocket`）
- `livenessProbe`: 同上

### 6.3 start_app.sh 约定

每个项目仓库根目录必须包含 `start_app.sh` 脚本，Dockerfile 通过 `CMD ["./start_app.sh"]` 调用。

**Django 项目 start_app.sh 示例**:
```bash
#!/bin/bash
# 从环境变量读取 APP_NAME 和 APP_TAG（由 Deployment 注入）
echo "Starting ${APP_NAME}:${APP_TAG}"
cd /app

# 应用自身的启动逻辑（数据库连接、redis 配置等由项目自行实现）
python manage.py migrate
gunicorn ${APP_NAME}.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120
```

**Vue 项目 start_app.sh 示例**:
```bash
#!/bin/bash
echo "Starting ${APP_NAME}:${APP_TAG}"

# 可以用环境变量渲染 nginx 配置等，再启动 nginx
nginx -g "daemon off;"
```

项目团队在自己的 `start_app.sh` 中自行处理：数据库连接、Redis 配置、Secret 读取等。Backend 只负责注入 `APP_NAME` 和 `APP_TAG`。

### 6.3 YAML 生成方式

在 `apps/deploy/yaml_gen.py` 中实现，使用 Python 字符串模板（`.format()`）渲染，参考现有 `deploy/demo/01-prd-app.yaml` 的结构。

---

## 7. 前端页面设计

### 7.1 路由

新增路由 `/deploy`（meta: requiresAuth: true）：

```js
{
  path: "/deploy",
  name: "DeployManagement",
  component: () => import("../views/DeployManagementPage.vue"),
  meta: { requiresAuth: true },
}
```

### 7.2 页面布局

单页面，左右分栏：

```
┌──────────────────────────────────────────────────────────┐
│  CI/CD 部署管理                                           │
├────────────────────────┬─────────────────────────────────┤
│  项目列表                │  部署操作                          │
│                        │                                 │
│  [+ 新增项目]           │  当前项目: my-shop (Django)       │
│                        │  域名: my-shop.daiyi.local.com   │
│  ┌──────────────────┐  │  本地路径: /d/projects/my-shop    │
│  │ my-shop          │  │                                 │
│  │ Django · domain  │  │  Tag:    [v1.2.0____]           │
│  │ ● 已启用          │  │                                 │
│  ├──────────────────┤  │  [🚀 一键部署]                    │
│  │ admin-portal     │  │                                 │
│  │ Vue · domain     │  ├─────────────────────────────────┤
│  │ v0.5.0           │  │  部署历史                         │
│  │ ○ 已禁用          │  │  ┌───────────────────────────┐  │
│  ├──────────────────┤  │  │ v1.1.0 ✅ 成功 · 2小时前    │  │
│  │ ...              │  │  │  [🔄 回滚]                  │  │
│  └──────────────────┘  │  ├───────────────────────────┤  │
│                        │  │ v1.0.0 ✅ 成功 · 1天前     │  │
│                        │  │  [🔄 回滚]                  │  │
│                        │  │ v0.9.0 ❌ 失败 · 1天前     │  │
│                        │  └───────────────────────────┘  │
└────────────────────────┴─────────────────────────────────┘
```

### 7.3 交互逻辑

1. **左侧项目列表**: 点击选中一个项目 → 右侧展示该项目详情和部署操作区
2. **新增/编辑项目**: 弹窗表单（app_name, app_type, local_path, domain, namespace, cluster, replicas）
3. **部署操作区**:
   - Tag 输入框（必填）
   - "一键部署"按钮 → 调用 `POST /api/deploy/trigger`
4. **部署历史**（右侧下方）: 展示当前选中项目的部署历史列表，每条成功记录显示"回滚"按钮
5. **回滚**: 点击历史记录的"回滚"按钮 → 确认弹窗（确认要回滚到 {tag}？）→ 调用 `POST /api/deploy/rollback`

### 7.4 导航栏更新

在左侧导航菜单中添加 "CI/CD 部署" 菜单项。

---

## 8. 项目结构

```
backend/
├── apps/
│   └── deploy/                  # ★ 新增
│       ├── __init__.py
│       ├── models.py            # AppProject, DeployHistory
│       ├── urls.py              # /api/deploy/* 路由
│       ├── views.py             # CRUD + deploy_trigger + deploy_rollback
│       ├── yaml_gen.py          # YAML 模板生成
│       └── migrations/
│           └── 0001_initial.py
├── k8s_console/
│   ├── settings.py              # + apps.deploy, + BUILDER_SERVICE_URL (http://192.168.1.24:9008)
│   └── urls.py                  # + path("api/", include("apps.deploy.urls"))
│
builder/                          # ★ 新增 — Builder Service（宿主机运行）
├── main.py                       # Flask 入口
├── requirements.txt              # flask
├── build_runner.py               # 构建逻辑（local copy + docker build + 镜像保留策略）
└── templates/
    ├── django/
    │   └── Dockerfile
    └── vue/
        └── Dockerfile

frontend/
├── src/
│   ├── views/
│   │   └── DeployManagementPage.vue   # ★ 新增
│   └── router/
│       └── index.js                   # + /deploy 路由
```

---

## 9. 配置项

在 `settings.py` 中新增：

```python
# Builder Service
BUILDER_SERVICE_URL = os.environ.get("BUILDER_SERVICE_URL", "http://192.168.1.24:9008")

INSTALLED_APPS = [
    ...
    "apps.deploy",
]
```

---

## 10. 安全与权限

- 项目 CRUD 操作：管理员权限（复用 `_require_admin`）
- 部署触发：管理员权限
- 回滚：管理员权限
- 部署历史查看：任意认证用户
- Builder Service 仅监听 `192.168.1.24:9008`，不对外暴露

---

## 11. 与现有系统的复用

| 现有能力 | 来源 | 复用方式 |
|----------|------|----------|
| `apply_yaml()` | `apps/resources/k8s_client.py` | 部署/回滚 YAML 时直接调用 |
| 多集群支持 | `Cluster` 模型 | AppProject 外键关联 Cluster |
| `_require_admin()` | `apps/clusters/views.py` | 提取为公共函数或复用模式 |
| `success()` / `error()` | `utils/response.py` | 统一响应格式 |
| 审计日志 | `AuditLoggerMiddleware` | 自动拦截 /api/deploy/ 路径 |
| Token 认证 | `TokenAuthentication` | 前端请求自动带 Token |

---

## 12. 镜像保留策略（详细）

在 Builder Service 的 `build_runner.py` 中实现：

```python
import subprocess
from datetime import datetime

def cleanup_old_images(app_name: str, keep_count: int = 5):
    """清理旧镜像，每个 app 最多保留 keep_count 个 tag。"""
    result = subprocess.run(
        ["docker", "images", "--filter", f"reference={app_name}",
         "--format", "{{.Tag}}|{{.CreatedAt}}"],
        capture_output=True, text=True
    )
    if result.returncode != 0 or not result.stdout.strip():
        return

    # 解析并按时间排序
    entries = []
    for line in result.stdout.strip().split("\n"):
        parts = line.split("|", 1)
        if len(parts) != 2:
            continue
        tag, created_at = parts[0].strip(), parts[1].strip()
        entries.append((tag, created_at))

    # 按创建时间降序排列（最新的在前）
    entries.sort(key=lambda x: x[1], reverse=True)

    # 超过 keep_count 的删除
    for tag, _ in entries[keep_count:]:
        image_name = f"{app_name}:{tag}"
        subprocess.run(["docker", "rmi", image_name],
                       capture_output=True, text=True)
```

---

## 13. 后续迭代方向

1. **远程 Registry 支持**: 配置化支持 Docker Hub / Harbor，构建后 push + imagePullSecrets
2. **Kaniko 模式**: 在 K8s 内创建构建 Job，无需宿主机 Docker
3. **WebSocket 实时日志**: 构建过程中向前端推送实时日志
4. **Webhook 触发**: Git push → Webhook → 自动触发部署
5. **Git Clone 模式**: 后续如需要可从 Git 仓库拉取代码构建
