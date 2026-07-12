# CI/CD 自动化部署子系统 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 K8s Console 项目新增 CI/CD 自动化部署能力：通过前端页面管理部署项目、一键触发 Docker 构建 + K8s 部署（Deployment/Service/Ingress），支持回滚到历史 tag。

**Architecture:** Django Backend（`apps/deploy`）负责 CRUD/YAML 生成/kubectl apply；宿主机 Builder Service（Flask, 端口 9008）负责 docker build + 镜像保留策略（每个 app 最多 5 个）；Vue 前端单页面左右分栏（项目列表 + 部署操作 + 部署历史）。

**Tech Stack:** Django DRF, Python kubernetes SDK, Flask, Vue 3 + Pinia + Axios, Docker

---

## File Structure

```
BACKEND (新增/修改):
  backend/utils/admin_guard.py          ★ 新增 — 提取 _require_admin 公共函数
  backend/apps/deploy/
    ├── __init__.py                     ★ 新增 — 空文件
    ├── models.py                       ★ 新增 — AppProject, DeployHistory
    ├── urls.py                         ★ 新增 — /api/deploy/* 路由
    ├── views.py                        ★ 新增 — CRUD + deploy_trigger + deploy_rollback
    ├── yaml_gen.py                     ★ 新增 — YAML 模板生成
    └── migrations/
      └── 0001_initial.py               ★ 新增 — migration
  backend/k8s_console/
    ├── settings.py                     ★ 修改 — + apps.deploy, + BUILDER_SERVICE_URL
    └── urls.py                         ★ 修改 — + path("api/", include("apps.deploy.urls"))
  backend/apps/clusters/views.py        ★ 修改 — 替换 _require_admin 为公共导入

BUILDER SERVICE (新增):
  builder/
    ├── main.py                         ★ 新增 — Flask 入口
    ├── requirements.txt                ★ 新增 — flask
    ├── build_runner.py                 ★ 新增 — local copy + docker build + 镜像保留策略
    └── templates/
      ├── django/
      │   └── Dockerfile                ★ 新增 — 标准 Django Dockerfile
      └── vue/
        └── Dockerfile                  ★ 新增 — 标准 Vue Dockerfile

FRONTEND (新增/修改):
  frontend/src/api/deploy.js            ★ 新增 — 部署相关 API 调用
  frontend/src/views/DeployManagementPage.vue  ★ 新增 — CI/CD 部署管理页面
  frontend/src/router/index.js          ★ 修改 — + /deploy 路由
  frontend/src/components/AppSidebar.vue  ★ 修改 — + CI/CD 部署 菜单项
```

---

### Task 1: Extract `_require_admin` to shared utility

**Files:**
- Create: `backend/utils/admin_guard.py`
- Modify: `backend/apps/clusters/views.py:10-15`

- [ ] **Step 1: Create `backend/utils/admin_guard.py`**

```python
"""Admin permission guard — reusable across views."""
from apps.auth_app.models import User
from utils.response import error, ERR_PERMISSION_DENIED


def require_admin(user):
    """Return error response if user is not admin, None otherwise."""
    if not isinstance(user, User) or user.role != "admin":
        return error(ERR_PERMISSION_DENIED, "仅管理员可执行此操作")
    return None
```

- [ ] **Step 2: Update `backend/apps/clusters/views.py` to use shared utility**

Remove lines 10-15 (the `_require_admin` function) and replace all `_require_admin(` calls with `require_admin(`. Add import:

```python
from utils.admin_guard import require_admin
```

Also replace the `admin_err = _require_admin(request.user)` pattern — rename to `admin_err = require_admin(request.user)`.

The `cluster_create`, `cluster_update`, and `cluster_delete` functions each call `_require_admin`. Rename all three to `require_admin`.

- [ ] **Step 3: Commit**

```bash
git add backend/utils/admin_guard.py backend/apps/clusters/views.py
git commit -m "refactor: extract require_admin to utils/admin_guard.py"
```

---

### Task 2: Create Django `apps/deploy` app

**Files:**
- Create: `backend/apps/deploy/__init__.py`
- Create: `backend/apps/deploy/models.py`

- [ ] **Step 1: Create app directory and init file**

```bash
mkdir -p backend/apps/deploy
```

Write `backend/apps/deploy/__init__.py`:
```python
```
(empty file)

- [ ] **Step 2: Write `backend/apps/deploy/models.py`**

```python
"""CI/CD deploy models — AppProject and DeployHistory."""
from django.db import models


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

- [ ] **Step 3: Commit**

```bash
git add backend/apps/deploy/__init__.py backend/apps/deploy/models.py
git commit -m "feat: add deploy app with AppProject and DeployHistory models"
```

---

### Task 3: Register deploy app and create migration

**Files:**
- Modify: `backend/k8s_console/settings.py`
- Create: `backend/apps/deploy/migrations/0001_initial.py` (auto-generated)

- [ ] **Step 1: Add `apps.deploy` to INSTALLED_APPS and add BUILDER_SERVICE_URL**

In `backend/k8s_console/settings.py`, add to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "apps.auth_app",
    "apps.resources",
    "apps.audit",
    "apps.clusters",
    "apps.deploy",                        # ★ 新增
]
```

Append at end of file:

```python
# Builder Service
BUILDER_SERVICE_URL = os.environ.get("BUILDER_SERVICE_URL", "http://127.0.0.1:9008")
```

- [ ] **Step 2: Generate migration**

```bash
cd backend && python manage.py makemigrations deploy
```

Expected output: `Migrations for 'deploy': backend/apps/deploy/migrations/0001_initial.py`

- [ ] **Step 3: Apply migration**

```bash
cd backend && python manage.py migrate deploy
```

Expected output: `Applying deploy.0001_initial... OK`

- [ ] **Step 4: Commit**

```bash
git add backend/k8s_console/settings.py backend/apps/deploy/migrations/
git commit -m "feat: register deploy app, add BUILDER_SERVICE_URL config"
```

---

### Task 4: Implement YAML generation

**Files:**
- Create: `backend/apps/deploy/yaml_gen.py`

- [ ] **Step 1: Write `backend/apps/deploy/yaml_gen.py`**

```python
"""Generate K8s YAML (Deployment + Service + Ingress) for deploy targets."""
from apps.deploy.models import AppProject

_DEPLOYMENT_TEMPLATE_DJANGO = """---
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
          image: {image}
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
          - path: {path}
            pathType: Prefix
            backend:
              service:
                name: {app_name}
                port:
                  number: {port}
"""

_DEPLOYMENT_TEMPLATE_VUE = """---
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
          image: {image}
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
              cpu: 50m
              memory: 64Mi
            limits:
              cpu: 200m
              memory: 128Mi
          readinessProbe:
            httpGet:
              path: /
              port: {port}
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /
              port: {port}
            initialDelaySeconds: 15
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
          - path: {path}
            pathType: Prefix
            backend:
              service:
                name: {app_name}
                port:
                  number: {port}
"""


def generate_k8s_yaml(project: AppProject, image: str) -> str:
    """Generate Deployment + Service + Ingress YAML for a project.

    Args:
        project: AppProject instance
        image: Full image reference, e.g. "my-shop:v1.2.0"

    Returns:
        Multi-document YAML string ready for kubectl apply.
    """
    tag = image.split(":")[-1] if ":" in image else "latest"
    template = _DEPLOYMENT_TEMPLATE_VUE if project.app_type == "vue" else _DEPLOYMENT_TEMPLATE_DJANGO

    return template.format(
        app_name=project.app_name,
        namespace=project.namespace,
        replicas=project.replicas,
        port=project.port,
        domain=project.domain,
        image=image,
        tag=tag,
        path=project.ingress_path or "/",
    )
```

- [ ] **Step 2: Commit**

```bash
git add backend/apps/deploy/yaml_gen.py
git commit -m "feat: add K8s YAML generator (Deployment/Service/Ingress) for django/vue"
```

---

### Task 5: Implement deploy views (CRUD + trigger + rollback)

**Files:**
- Create: `backend/apps/deploy/views.py`

- [ ] **Step 1: Write `backend/apps/deploy/views.py`**

```python
"""CI/CD deploy views — project CRUD, deploy trigger, rollback."""
import requests
import subprocess

from kubernetes.client.rest import ApiException

from rest_framework.decorators import api_view

from apps.deploy.models import AppProject, DeployHistory
from apps.deploy.yaml_gen import generate_k8s_yaml
from apps.resources.k8s_client import apply_yaml
from utils.response import (
    success, error,
    ERR_VALIDATION, ERR_K8S_API_ERROR, ERR_RESOURCE_NOT_FOUND,
)
from utils.admin_guard import require_admin
from django.conf import settings


# ---------------------------------------------------------------------------
# Project CRUD
# ---------------------------------------------------------------------------

@api_view(["POST"])
def project_list(request):
    """List all deploy projects."""
    projects = AppProject.objects.all().values(
        "app_name", "app_type", "local_path", "domain", "port",
        "namespace", "replicas", "enabled", "cluster_id",
        "created_at", "updated_at",
    )
    return success(data={"items": list(projects), "count": len(projects)})


@api_view(["POST"])
def project_create(request):
    """Create a deploy project. Admin only."""
    admin_err = require_admin(request.user)
    if admin_err:
        return admin_err

    app_name = request.data.get("app_name", "").strip()
    app_type = request.data.get("app_type", "").strip()
    local_path = request.data.get("local_path", "").strip()
    domain = request.data.get("domain", "").strip()
    port = int(request.data.get("port", 8000))
    namespace = request.data.get("namespace", "prd").strip()
    cluster_id = request.data.get("cluster_id")
    replicas = int(request.data.get("replicas", 1))
    enabled = bool(request.data.get("enabled", True))

    if not app_name:
        return error(ERR_VALIDATION, "应用名称不能为空")
    if app_type not in ("django", "vue"):
        return error(ERR_VALIDATION, "应用类型必须为 django 或 vue")
    if not domain:
        return error(ERR_VALIDATION, "域名不能为空")
    if not cluster_id:
        return error(ERR_VALIDATION, "请选择目标集群")
    if AppProject.objects.filter(app_name=app_name).exists():
        return error(ERR_VALIDATION, f"应用 '{app_name}' 已存在")

    project = AppProject.objects.create(
        app_name=app_name, app_type=app_type, local_path=local_path,
        domain=domain, port=port, namespace=namespace,
        cluster_id=cluster_id, replicas=replicas, enabled=enabled,
    )
    return success(data={
        "app_name": project.app_name,
        "app_type": project.app_type,
        "domain": project.domain,
    }, message=f"项目 '{app_name}' 已创建")


@api_view(["POST"])
def project_update(request):
    """Update a deploy project. Admin only."""
    admin_err = require_admin(request.user)
    if admin_err:
        return admin_err

    app_name = request.data.get("app_name", "").strip()
    if not app_name:
        return error(ERR_VALIDATION, "应用名称不能为空")

    try:
        project = AppProject.objects.get(app_name=app_name)
    except AppProject.DoesNotExist:
        return error(ERR_RESOURCE_NOT_FOUND, f"项目 '{app_name}' 不存在")

    # Update fields if provided
    for field in ["app_type", "local_path", "domain", "namespace"]:
        val = request.data.get(field)
        if val is not None and str(val).strip():
            setattr(project, field, str(val).strip())
    for field in ["port", "replicas"]:
        val = request.data.get(field)
        if val is not None:
            setattr(project, field, int(val))
    if "cluster_id" in request.data:
        project.cluster_id = int(request.data["cluster_id"])
    if "enabled" in request.data:
        project.enabled = bool(request.data["enabled"])

    project.save()
    return success(data={"app_name": project.app_name}, message=f"项目 '{app_name}' 已更新")


@api_view(["POST"])
def project_delete(request):
    """Delete a deploy project. Admin only."""
    admin_err = require_admin(request.user)
    if admin_err:
        return admin_err

    app_name = request.data.get("app_name", "").strip()
    if not app_name:
        return error(ERR_VALIDATION, "应用名称不能为空")

    try:
        project = AppProject.objects.get(app_name=app_name)
    except AppProject.DoesNotExist:
        return error(ERR_RESOURCE_NOT_FOUND, f"项目 '{app_name}' 不存在")

    project.delete()
    return success(message=f"项目 '{app_name}' 已删除")


# ---------------------------------------------------------------------------
# Deploy
# ---------------------------------------------------------------------------

@api_view(["POST"])
def deploy_trigger(request):
    """Trigger a deploy: build image → generate YAML → apply to K8s. Admin only."""
    admin_err = require_admin(request.user)
    if admin_err:
        return admin_err

    app_name = request.data.get("app_name", "").strip()
    tag = request.data.get("tag", "").strip()

    if not app_name:
        return error(ERR_VALIDATION, "应用名称不能为空")
    if not tag:
        return error(ERR_VALIDATION, "部署 tag 不能为空")

    try:
        project = AppProject.objects.get(app_name=app_name)
    except AppProject.DoesNotExist:
        return error(ERR_RESOURCE_NOT_FOUND, f"项目 '{app_name}' 不存在")

    if not project.enabled:
        return error(ERR_VALIDATION, f"项目 '{app_name}' 已禁用，请先启用")

    # Create deploy history
    history = DeployHistory.objects.create(
        project=project, tag=tag, status="building",
        operator=request.user.username,
    )

    # Step 1: Call Builder Service
    try:
        build_resp = requests.post(
            f"{settings.BUILDER_SERVICE_URL}/api/build",
            json={
                "app_name": app_name,
                "app_type": project.app_type,
                "tag": tag,
                "local_path": project.local_path,
            },
            timeout=600,
        )
        build_resp.raise_for_status()
        build_data = build_resp.json()
    except requests.exceptions.RequestException as e:
        history.status = "failed"
        detail = str(e)
        if hasattr(e, "response") and e.response is not None:
            try:
                detail = e.response.json().get("error", detail)
            except Exception:
                detail = e.response.text[:500]
        history.message = detail
        history.save()
        return error(ERR_VALIDATION, "镜像构建失败", detail)
    except (ValueError, KeyError) as e:
        history.status = "failed"
        history.message = f"解析构建响应失败: {e}"
        history.save()
        return error(ERR_VALIDATION, "镜像构建失败", str(e))

    if build_data.get("code") != 0:
        history.status = "failed"
        history.message = build_data.get("error", build_data.get("message", "未知错误"))
        history.save()
        return error(ERR_VALIDATION, "镜像构建失败", history.message)

    image = build_data["data"]["image"]

    # Step 2: Generate K8s YAML
    yaml_content = generate_k8s_yaml(project, image)

    # Step 3: Apply to K8s
    history.status = "deploying"
    history.save()
    try:
        apply_yaml(project.cluster_id, yaml_content)
    except (ApiException, Exception) as e:
        msg = str(e)
        if hasattr(e, 'body'):
            msg = str(e.body)[:500]
        history.status = "failed"
        history.message = msg
        history.save()
        return error(ERR_K8S_API_ERROR, "K8s 部署失败", msg)

    # Step 4: Mark success
    history.status = "success"
    history.message = f"部署成功，域名: {project.domain}"
    history.save()

    return success(data={
        "domain": project.domain,
        "tag": tag,
        "app_name": app_name,
    }, message="部署成功")


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------

@api_view(["POST"])
def deploy_rollback(request):
    """Rollback to a previously deployed tag. Admin only."""
    admin_err = require_admin(request.user)
    if admin_err:
        return admin_err

    app_name = request.data.get("app_name", "").strip()
    tag = request.data.get("tag", "").strip()

    if not app_name:
        return error(ERR_VALIDATION, "应用名称不能为空")
    if not tag:
        return error(ERR_VALIDATION, "回滚 tag 不能为空")

    try:
        project = AppProject.objects.get(app_name=app_name)
    except AppProject.DoesNotExist:
        return error(ERR_RESOURCE_NOT_FOUND, f"项目 '{app_name}' 不存在")

    # Verify the tag was successfully deployed before
    history_check = DeployHistory.objects.filter(
        project=project, tag=tag, status="success"
    ).first()
    if not history_check:
        return error(ERR_VALIDATION, f"未找到 tag='{tag}' 的成功部署记录，无法回滚")

    # Verify image still exists locally (skip docker check if docker not available)
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
        # If docker command not available, skip local image check
        docker_ok = True  # allow rollback, image may exist on node

    if not docker_ok:
        return error(ERR_VALIDATION, f"本地镜像 {image} 不存在，无法回滚")

    # Generate YAML and apply
    yaml_content = generate_k8s_yaml(project, image)
    try:
        apply_yaml(project.cluster_id, yaml_content)
    except (ApiException, Exception) as e:
        msg = str(e)
        if hasattr(e, 'body'):
            msg = str(e.body)[:500]
        return error(ERR_K8S_API_ERROR, "回滚部署失败", msg)

    # Record rollback
    DeployHistory.objects.create(
        project=project, tag=tag, status="success",
        operator=request.user.username,
        message=f"回滚到 {tag}",
    )

    return success(data={
        "domain": project.domain,
        "tag": tag,
        "app_name": app_name,
    }, message=f"已回滚到 {tag}")


# ---------------------------------------------------------------------------
# Deploy History
# ---------------------------------------------------------------------------

@api_view(["POST"])
def deploy_history(request):
    """List deploy history for a project."""
    app_name = request.data.get("app_name", "").strip()
    if not app_name:
        return error(ERR_VALIDATION, "应用名称不能为空")

    try:
        project = AppProject.objects.get(app_name=app_name)
    except AppProject.DoesNotExist:
        return error(ERR_RESOURCE_NOT_FOUND, f"项目 '{app_name}' 不存在")

    histories = DeployHistory.objects.filter(project=project).values(
        "id", "tag", "status", "operator", "message", "created_at"
    )[:50]
    return success(data={"items": list(histories), "count": len(histories)})
```

- [ ] **Step 2: Commit**

```bash
git add backend/apps/deploy/views.py
git commit -m "feat: add deploy views (CRUD, trigger, rollback, history)"
```

---

### Task 6: Wire deploy URLs

**Files:**
- Create: `backend/apps/deploy/urls.py`
- Modify: `backend/k8s_console/urls.py`

- [ ] **Step 1: Write `backend/apps/deploy/urls.py`**

```python
"""Deploy app URL config."""
from django.urls import path
from . import views

urlpatterns = [
    # Project CRUD
    path("deploy/projects", views.project_list, name="deploy_project_list"),
    path("deploy/project/create", views.project_create, name="deploy_project_create"),
    path("deploy/project/update", views.project_update, name="deploy_project_update"),
    path("deploy/project/delete", views.project_delete, name="deploy_project_delete"),
    # Deploy
    path("deploy/trigger", views.deploy_trigger, name="deploy_trigger"),
    path("deploy/rollback", views.deploy_rollback, name="deploy_rollback"),
    # History
    path("deploy/history", views.deploy_history, name="deploy_history"),
]
```

- [ ] **Step 2: Update `backend/k8s_console/urls.py`**

Add `path("api/", include("apps.deploy.urls")),` to urlpatterns:

```python
urlpatterns = [
    path("api/health", health, name="health"),
    path("api/", include("apps.auth_app.urls")),
    path("api/", include("apps.resources.urls")),
    path("api/", include("apps.audit.urls")),
    path("api/", include("apps.clusters.urls")),
    path("api/", include("apps.deploy.urls")),      # ★ 新增
]
```

- [ ] **Step 3: Commit**

```bash
git add backend/apps/deploy/urls.py backend/k8s_console/urls.py
git commit -m "feat: wire deploy URLs to k8s_console urlconf"
```

---

### Task 7: Verify backend with quick smoke test

**Files:**
- (no permanent files, just verification)

- [ ] **Step 1: Verify Django config loads without error**

```bash
cd backend && python -c "import django; import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','k8s_console.settings'); django.setup(); from apps.deploy.models import AppProject; print('OK: AppProject loaded')"
```

Expected: `OK: AppProject loaded`

- [ ] **Step 2: Verify URLs resolve**

```bash
cd backend && python -c "
import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','k8s_console.settings')
import django; django.setup()
from django.urls import resolve
m = resolve('/api/deploy/projects')
print(f'OK: resolve /api/deploy/projects → {m.func.__name__}')
m = resolve('/api/deploy/trigger')
print(f'OK: resolve /api/deploy/trigger → {m.func.__name__}')
m = resolve('/api/deploy/rollback')
print(f'OK: resolve /api/deploy/rollback → {m.func.__name__}')
"
```

Expected: all three resolve to the correct view function name

- [ ] **Step 3: Commit (empty commit for verification record)**

```bash
git commit --allow-empty -m "chore: verify backend deploy app loads correctly"
```

---

### Task 8: Create Builder Service

**Files:**
- Create: `builder/templates/django/Dockerfile`
- Create: `builder/templates/vue/Dockerfile`
- Create: `builder/build_runner.py`
- Create: `builder/main.py`
- Create: `builder/requirements.txt`

- [ ] **Step 1: Create builder directory structure**

```bash
mkdir -p builder/templates/django builder/templates/vue
```

- [ ] **Step 2: Write `builder/templates/django/Dockerfile`**

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

- [ ] **Step 3: Write `builder/templates/vue/Dockerfile`**

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

- [ ] **Step 4: Write `builder/build_runner.py`**

```python
"""Docker build runner — local copy, build, image retention policy."""
import os
import shutil
import subprocess
import uuid


TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

EXCLUDE_PATTERNS = [
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "*.pyc", ".DS_Store", "__MACOSX",
]

# Only allow builds from paths under these prefixes (path traversal protection)
ALLOWED_PATH_PREFIXES = [
    "/data/project/",
    "/d/",
    "/home/",
    "/Users/",
    "D:\\",
    "C:\\",
]


def _detect_python_version(build_dir: str) -> str:
    """Read python_version.txt from build dir, default '3.12'."""
    ver_file = os.path.join(build_dir, "python_version.txt")
    if os.path.isfile(ver_file):
        with open(ver_file) as f:
            version = f.read().strip()
            if version:
                return version
    return "3.12"


def _render_dockerfile(template_path: str, output_path: str, variables: dict):
    """Read template, replace {VAR} placeholders, write to output."""
    with open(template_path) as f:
        content = f.read()
    for key, val in variables.items():
        content = content.replace("{" + key + "}", str(val))
    with open(output_path, "w") as f:
        f.write(content)


def _cleanup_old_images(app_name: str, keep_count: int = 5):
    """Clean old images, keep at most `keep_count` tags per app."""
    result = subprocess.run(
        ["docker", "images", "--filter", f"reference={app_name}",
         "--format", "{{.Tag}}|{{.CreatedAt}}"],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return

    entries = []
    for line in result.stdout.strip().split("\n"):
        parts = line.split("|", 1)
        if len(parts) != 2:
            continue
        tag, created_at = parts[0].strip(), parts[1].strip()
        entries.append((tag, created_at))

    entries.sort(key=lambda x: x[1], reverse=True)

    for tag, _ in entries[keep_count:]:
        image_name = f"{app_name}:{tag}"
        subprocess.run(
            ["docker", "rmi", image_name],
            capture_output=True, text=True,
        )


def build(app_name: str, app_type: str, tag: str, local_path: str) -> dict:
    """Build Docker image from local source.

    Args:
        app_name: Image name, e.g. "my-shop"
        app_type: "django" or "vue"
        tag: Image tag, e.g. "v1.2.0"
        local_path: Source code path on host

    Returns:
        {"image": "my-shop:v1.2.0", "app_name": "my-shop", "tag": "v1.2.0"}

    Raises:
        ValueError: if local_path not found or app_type invalid
        RuntimeError: if docker build fails
    """
    if not os.path.isdir(local_path):
        raise ValueError(f"本地路径不存在: {local_path}")

    # Path traversal protection
    normalized = os.path.abspath(local_path)
    if not any(normalized.startswith(prefix) for prefix in ALLOWED_PATH_PREFIXES):
        raise ValueError(f"不允许的路径前缀: {local_path}")

    if app_type not in ("django", "vue"):
        raise ValueError(f"不支持的应用类型: {app_type}")

    template_subdir = "django" if app_type == "django" else "vue"
    template_dockerfile = os.path.join(TEMPLATE_DIR, template_subdir, "Dockerfile")
    if not os.path.isfile(template_dockerfile):
        raise RuntimeError(f"模板 Dockerfile 不存在: {template_dockerfile}")

    # Create temp build directory
    build_id = str(uuid.uuid4())[:8]
    build_dir = f"/tmp/build-{app_name}-{build_id}"
    os.makedirs(build_dir, exist_ok=True)

    try:
        # Copy source files (excluding patterns)
        for item in os.listdir(local_path):
            src = os.path.join(local_path, item)
            dst = os.path.join(build_dir, item)
            skip = False
            for pattern in EXCLUDE_PATTERNS:
                if "*" in pattern:
                    if item.endswith(pattern[1:]):
                        skip = True
                        break
                elif item == pattern:
                    skip = True
                    break
            if skip:
                continue
            if os.path.isdir(src):
                shutil.copytree(src, dst,
                                ignore=shutil.ignore_patterns(*EXCLUDE_PATTERNS)
                                if EXCLUDE_PATTERNS else None)
            else:
                shutil.copy2(src, dst)

        # Determine Python version for Django
        variables = {"APP_NAME": app_name}
        if app_type == "django":
            variables["PYTHON_VERSION"] = _detect_python_version(build_dir)
            if not os.path.isfile(os.path.join(build_dir, "requirements.txt")):
                raise ValueError("Django 项目必须包含 requirements.txt")
        elif app_type == "vue":
            if not os.path.isfile(os.path.join(build_dir, "package.json")):
                raise ValueError("Vue 项目必须包含 package.json")

        # Verify start_app.sh exists (required by convention)
        if not os.path.isfile(os.path.join(build_dir, "start_app.sh")):
            raise ValueError("项目必须包含 start_app.sh")

        # Render and place Dockerfile
        _render_dockerfile(template_dockerfile,
                           os.path.join(build_dir, "Dockerfile"), variables)

        # Docker build
        image = f"{app_name}:{tag}"
        try:
            result = subprocess.run(
                ["docker", "build", "-t", image, "."],
                cwd=build_dir,
                capture_output=True, text=True,
                timeout=600,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr or result.stdout or "docker build 失败")
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"docker build 超时 (600s): {app_name}:{tag}")

        # Cleanup old images
        _cleanup_old_images(app_name)

        return {"image": image, "app_name": app_name, "tag": tag}

    finally:
        # Clean temp dir
        if os.path.isdir(build_dir):
            shutil.rmtree(build_dir, ignore_errors=True)
```

- [ ] **Step 5: Write `builder/main.py`**

```python
"""Builder Service — Flask HTTP API for Docker image builds."""
import sys
from flask import Flask, request, jsonify

from build_runner import build

app = Flask(__name__)


@app.route("/api/build", methods=["POST"])
def api_build():
    body = request.get_json(silent=True) or {}

    app_name = body.get("app_name", "").strip()
    app_type = body.get("app_type", "").strip()
    tag = body.get("tag", "").strip()
    local_path = body.get("local_path", "").strip()

    if not app_name:
        return jsonify({"code": 1, "message": "缺少 app_name", "error": "app_name 不能为空"}), 400
    if not app_type:
        return jsonify({"code": 1, "message": "缺少 app_type", "error": "app_type 不能为空"}), 400
    if not tag:
        return jsonify({"code": 1, "message": "缺少 tag", "error": "tag 不能为空"}), 400
    if not local_path:
        return jsonify({"code": 1, "message": "缺少 local_path", "error": "local_path 不能为空"}), 400

    try:
        result = build(app_name=app_name, app_type=app_type,
                       tag=tag, local_path=local_path)
        return jsonify({
            "code": 0,
            "message": "镜像构建成功",
            "data": result,
        })
    except ValueError as e:
        return jsonify({"code": 1, "message": "参数错误", "error": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"code": 1, "message": "镜像构建失败", "error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=9008, debug=False)
```

- [ ] **Step 6: Write `builder/requirements.txt`**

```
flask>=3.0,<4.0
```

- [ ] **Step 7: Commit**

```bash
git add builder/
git commit -m "feat: add Builder Service (Flask, port 9008) with Docker templates and image retention"
```

---

### Task 9: Create frontend API module

**Files:**
- Create: `frontend/src/api/deploy.js`

- [ ] **Step 1: Write `frontend/src/api/deploy.js`**

```js
import client from "./client";

// Project CRUD
export function listProjects() {
  return client.post("/deploy/projects", {});
}

export function createProject(data) {
  return client.post("/deploy/project/create", data);
}

export function updateProject(data) {
  return client.post("/deploy/project/update", data);
}

export function deleteProject(appName) {
  return client.post("/deploy/project/delete", { app_name: appName });
}

// Deploy
export function triggerDeploy(appName, tag) {
  return client.post("/deploy/trigger", { app_name: appName, tag });
}

export function rollbackDeploy(appName, tag) {
  return client.post("/deploy/rollback", { app_name: appName, tag });
}

// History
export function listDeployHistory(appName) {
  return client.post("/deploy/history", { app_name: appName });
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/deploy.js
git commit -m "feat: add deploy API module for frontend"
```

---

### Task 10: Add deploy route and sidebar navigation

**Files:**
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/components/AppSidebar.vue`

- [ ] **Step 1: Add `/deploy` route in `frontend/src/router/index.js`**

Add this route entry to the `routes` array (after the `/audit` entry):

```js
  {
    path: "/deploy",
    name: "DeployManagement",
    component: () => import("../views/DeployManagementPage.vue"),
    meta: { requiresAuth: true },
  },
```

- [ ] **Step 2: Add sidebar menu item in `frontend/src/components/AppSidebar.vue`**

Add after the `/apply` entry, before `/users`:

```html
    <div class="sidebar-divider"></div>

    <router-link to="/deploy" class="sidebar-item" active-class="active">
      🚀 CI/CD 部署
    </router-link>

    <router-link to="/users" v-if="auth.isAdmin" class="sidebar-item" active-class="active">
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/router/index.js frontend/src/components/AppSidebar.vue
git commit -m "feat: add /deploy route and sidebar nav item"
```

---

### Task 11: Build DeployManagementPage Vue component

**Files:**
- Create: `frontend/src/views/DeployManagementPage.vue`

- [ ] **Step 1: Write `frontend/src/views/DeployManagementPage.vue`**

```html
<template>
  <div class="deploy-page">
    <h2>🚀 CI/CD 部署管理</h2>

    <div class="deploy-layout">
      <!-- Left: Project List -->
      <div class="deploy-left">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
          <h3 style="margin:0;">项目列表</h3>
          <button class="btn btn-primary" @click="openCreate">+ 新增项目</button>
        </div>

        <div v-if="projectLoading" style="color:#64748b;">加载中...</div>
        <div v-else-if="projectError" style="color:#dc2626;">{{ projectError }}</div>

        <div
          v-for="p in projects"
          :key="p.app_name"
          :class="['project-item', { selected: selectedProject?.app_name === p.app_name }]"
          @click="selectProject(p)"
        >
          <div class="project-item-header">
            <strong>{{ p.app_name }}</strong>
            <span class="tag" :class="p.app_type === 'django' ? 'tag-blue' : 'tag-green'">
              {{ p.app_type === 'django' ? 'Django' : 'Vue' }}
            </span>
          </div>
          <div class="project-item-meta">
            <span>{{ p.domain }}</span>
            <span :class="['tag', p.enabled ? 'tag-green' : 'tag-red']">
              {{ p.enabled ? '已启用' : '已禁用' }}
            </span>
          </div>
        </div>
        <p v-if="projects.length === 0 && !projectLoading" style="color:#64748b;">
          暂无项目，请点击"新增项目"按钮添加。
        </p>
      </div>

      <!-- Right: Deploy Panel -->
      <div class="deploy-right">
        <div v-if="!selectedProject" class="deploy-placeholder">
          <p>← 请从左侧选择一个项目</p>
        </div>

        <template v-else>
          <!-- Project Info -->
          <div class="info-card">
            <h3>{{ selectedProject.app_name }}
              <span class="tag" :class="selectedProject.app_type === 'django' ? 'tag-blue' : 'tag-green'">
                {{ selectedProject.app_type === 'django' ? 'Django' : 'Vue' }}
              </span>
            </h3>
            <div class="info-row"><span class="info-label">域名:</span> <code>{{ selectedProject.domain }}</code></div>
            <div class="info-row"><span class="info-label">路径:</span> <code>{{ selectedProject.local_path }}</code></div>
            <div class="info-row"><span class="info-label">端口:</span> {{ selectedProject.port }} &nbsp;|&nbsp;
              <span class="info-label">副本:</span> {{ selectedProject.replicas }} &nbsp;|&nbsp;
              <span class="info-label">命名空间:</span> {{ selectedProject.namespace }}
            </div>
          </div>

          <!-- Deploy Trigger -->
          <div class="action-card">
            <h3 style="margin-top:0;">一键部署</h3>
            <div class="form-row">
              <div class="form-group" style="flex:1;">
                <label class="form-label">Tag <span style="color:#dc2626;">*</span></label>
                <input v-model="deployTag" class="form-input" placeholder="例如: v1.2.0" />
              </div>
              <button
                class="btn btn-primary"
                style="align-self:flex-end;height:38px;"
                :disabled="!deployTag.trim() || deploying"
                @click="doDeploy"
              >
                {{ deploying ? '部署中...' : '🚀 一键部署' }}
              </button>
            </div>
            <div v-if="deployError" style="color:#dc2626;margin-top:8px;">{{ deployError }}</div>
            <div v-if="deploySuccess" style="color:#16a34a;margin-top:8px;">{{ deploySuccess }}</div>
          </div>

          <!-- Deploy History -->
          <div class="history-card">
            <h3>部署历史</h3>
            <div v-if="historyLoading" style="color:#64748b;">加载中...</div>
            <table v-else-if="history.length > 0" class="data-table">
              <thead>
                <tr>
                  <th>Tag</th>
                  <th>状态</th>
                  <th>操作人</th>
                  <th>时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="h in history" :key="h.id">
                  <td><strong>{{ h.tag }}</strong></td>
                  <td>
                    <span :class="['tag', statusClass(h.status)]">{{ statusLabel(h.status) }}</span>
                  </td>
                  <td>{{ h.operator || '-' }}</td>
                  <td>{{ formatDate(h.created_at) }}</td>
                  <td>
                    <button
                      v-if="h.status === 'success'"
                      class="btn"
                      style="font-size:12px;"
                      :disabled="rollbackTag === h.tag"
                      @click="doRollback(h.tag)"
                    >
                      {{ rollbackTag === h.tag ? '回滚中...' : '🔄 回滚' }}
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
            <p v-else-if="!historyLoading" style="color:#64748b;">暂无部署历史</p>
            <div v-if="historyError" style="color:#dc2626;margin-top:8px;">{{ historyError }}</div>
          </div>
        </template>
      </div>
    </div>

    <!-- Create/Edit Project Modal -->
    <div v-if="showForm" class="modal-overlay" @click.self="showForm = false">
      <div class="modal-box" style="max-width:560px;">
        <h3 style="margin-bottom:16px;">{{ editingProject ? '编辑项目' : '新增项目' }}</h3>

        <div class="form-group">
          <label class="form-label">应用名称 <span style="color:#dc2626;">*</span></label>
          <input v-model="form.app_name" class="form-input"
            placeholder="例如: my-shop" :disabled="!!editingProject" />
        </div>
        <div class="form-group">
          <label class="form-label">应用类型 <span style="color:#dc2626;">*</span></label>
          <select v-model="form.app_type" class="form-input">
            <option value="django">Django</option>
            <option value="vue">Vue</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">本地代码路径 <span style="color:#dc2626;">*</span></label>
          <input v-model="form.local_path" class="form-input" placeholder="例如: /d/projects/my-shop" />
        </div>
        <div class="form-group">
          <label class="form-label">访问域名 <span style="color:#dc2626;">*</span></label>
          <input v-model="form.domain" class="form-input" placeholder="例如: my-shop.daiyi.local.com" />
        </div>
        <div class="form-row">
          <div class="form-group" style="flex:1;">
            <label class="form-label">容器端口</label>
            <input v-model.number="form.port" class="form-input" type="number" />
          </div>
          <div class="form-group" style="flex:1;">
            <label class="form-label">副本数</label>
            <input v-model.number="form.replicas" class="form-input" type="number" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group" style="flex:1;">
            <label class="form-label">命名空间</label>
            <input v-model="form.namespace" class="form-input" placeholder="prd" />
          </div>
          <div class="form-group" style="flex:1;">
            <label class="form-label">目标集群 <span style="color:#dc2626;">*</span></label>
            <select v-model.number="form.cluster_id" class="form-input">
              <option :value="null" disabled>-- 选择集群 --</option>
              <option v-for="c in clusterOptions" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">
            <input type="checkbox" v-model="form.enabled" style="margin-right:6px;" />
            启用
          </label>
        </div>

        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px;">
          <button class="btn" @click="showForm = false">取消</button>
          <button class="btn btn-primary"
            :disabled="!formValid || submitting"
            @click="doSubmit">
            {{ submitting ? '提交中...' : editingProject ? '更新' : '创建' }}
          </button>
        </div>
        <div v-if="formError" style="color:#dc2626;margin-top:8px;">{{ formError }}</div>
      </div>
    </div>

    <!-- Delete Confirm -->
    <div v-if="deleteTarget" class="modal-overlay" @click.self="deleteTarget = null">
      <div class="modal-box">
        <h3 style="margin-bottom:12px;">确认删除</h3>
        <p>确定要删除项目 <strong>{{ deleteTarget.app_name }}</strong> 吗？</p>
        <p style="font-size:12px;color:#64748b;">此操作仅删除控制台中的项目配置，不影响已部署的 K8s 资源。</p>
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px;">
          <button class="btn" @click="deleteTarget = null">取消</button>
          <button class="btn" style="background:#dc2626;color:#fff;" :disabled="deleting" @click="doDelete">
            {{ deleting ? '删除中...' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Rollback Confirm -->
    <div v-if="rollbackConfirmTag" class="modal-overlay" @click.self="rollbackConfirmTag = null">
      <div class="modal-box">
        <h3 style="margin-bottom:12px;">确认回滚</h3>
        <p>确定要将 <strong>{{ selectedProject?.app_name }}</strong> 回滚到 <strong>{{ rollbackConfirmTag }}</strong> 吗？</p>
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px;">
          <button class="btn" @click="rollbackConfirmTag = null">取消</button>
          <button class="btn btn-primary" :disabled="rollingBack" @click="confirmRollback">
            {{ rollingBack ? '回滚中...' : '确认回滚' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, inject } from "vue";
import {
  listProjects, createProject, updateProject, deleteProject,
  triggerDeploy, rollbackDeploy, listDeployHistory,
} from "../api/deploy";
import { getClusterList } from "../api/clusters";
import { useAuthStore } from "../stores/auth";

const toast = inject("toast", null);

/** Fallback toast using window event (in case inject not available) */
function toastShow(message, type = "success") {
  if (toast?.show) {
    toast.show(message, type);
  } else {
    window.dispatchEvent(new CustomEvent("app-toast", { detail: { message, type } }));
  }
}
const auth = useAuthStore();

// Project list
const projects = ref([]);
const projectLoading = ref(false);
const projectError = ref("");
const selectedProject = ref(null);

// Deploy
const deployTag = ref("");
const deploying = ref(false);
const deployError = ref("");
const deploySuccess = ref("");

// History
const history = ref([]);
const historyLoading = ref(false);
const historyError = ref("");

// Rollback
const rollbackTag = ref(null);
const rollbackConfirmTag = ref(null);
const rollingBack = ref(false);

// Form
const showForm = ref(false);
const editingProject = ref(null);
const form = ref({
  app_name: "", app_type: "django", local_path: "", domain: "",
  port: 8000, replicas: 1, namespace: "prd", cluster_id: null, enabled: true,
});
const formError = ref("");
const submitting = ref(false);

// Delete
const deleteTarget = ref(null);
const deleting = ref(false);

// Cluster options
const clusterOptions = ref([]);

const formValid = computed(() => {
  return form.value.app_name.trim() && form.value.domain.trim() &&
    form.value.local_path.trim() && form.value.cluster_id;
});

// ---- Fetch ----
async function fetchProjects() {
  projectLoading.value = true;
  projectError.value = "";
  try {
    const res = await listProjects();
    projects.value = res.data?.items || [];
  } catch (e) {
    projectError.value = e.message || "加载失败";
  } finally {
    projectLoading.value = false;
  }
}

async function fetchClusters() {
  try {
    const res = await getClusterList();
    clusterOptions.value = res.data?.items || [];
  } catch (e) { /* ignore */ }
}

function selectProject(p) {
  selectedProject.value = p;
  deployTag.value = "";
  deployError.value = "";
  deploySuccess.value = "";
  fetchHistory(p.app_name);
}

async function fetchHistory(appName) {
  historyLoading.value = true;
  historyError.value = "";
  try {
    const res = await listDeployHistory(appName);
    history.value = res.data?.items || [];
  } catch (e) {
    historyError.value = e.message || "加载失败";
  } finally {
    historyLoading.value = false;
  }
}

// ---- Deploy ----
async function doDeploy() {
  if (!deployTag.value.trim()) return;
  deploying.value = true;
  deployError.value = "";
  deploySuccess.value = "";
  try {
    const res = await triggerDeploy(selectedProject.value.app_name, deployTag.value.trim());
    toastShow(res.message || "部署成功", "success");
    deploySuccess.value = res.message;
    deployTag.value = "";
    fetchHistory(selectedProject.value.app_name);
  } catch (e) {
    deployError.value = e.message || "部署失败";
    toastShow(deployError.value, "error");
    fetchHistory(selectedProject.value.app_name);
  } finally {
    deploying.value = false;
  }
}

// ---- Rollback ----
function doRollback(tag) {
  rollbackConfirmTag.value = tag;
}

async function confirmRollback() {
  rollingBack.value = true;
  rollbackTag.value = rollbackConfirmTag.value;
  try {
    const res = await rollbackDeploy(selectedProject.value.app_name, rollbackConfirmTag.value);
    toastShow(res.message || "回滚成功", "success");
    rollbackConfirmTag.value = null;
    fetchHistory(selectedProject.value.app_name);
  } catch (e) {
    toastShow(e.message || "回滚失败", "error");
  } finally {
    rollingBack.value = false;
    rollbackTag.value = null;
  }
}

// ---- Form ----
function openCreate() {
  editingProject.value = null;
  form.value = {
    app_name: "", app_type: "django", local_path: "", domain: "",
    port: 8000, replicas: 1, namespace: "prd", cluster_id: clusterOptions.value[0]?.id || null, enabled: true,
  };
  formError.value = "";
  showForm.value = true;
}

function openEdit() {
  editingProject.value = selectedProject.value;
  form.value = {
    app_name: selectedProject.value.app_name,
    app_type: selectedProject.value.app_type,
    local_path: selectedProject.value.local_path,
    domain: selectedProject.value.domain,
    port: selectedProject.value.port,
    replicas: selectedProject.value.replicas,
    namespace: selectedProject.value.namespace,
    cluster_id: selectedProject.value.cluster_id,
    enabled: selectedProject.value.enabled,
  };
  formError.value = "";
  showForm.value = true;
}

async function doSubmit() {
  formError.value = "";
  submitting.value = true;
  try {
    if (editingProject.value) {
      await updateProject(form.value);
      toastShow("项目已更新", "success");
    } else {
      await createProject(form.value);
      toastShow("项目已创建", "success");
    }
    showForm.value = false;
    await fetchProjects();
  } catch (e) {
    formError.value = e.message || "操作失败";
  } finally {
    submitting.value = false;
  }
}

function openDelete() {
  deleteTarget.value = selectedProject.value;
}

async function doDelete() {
  if (!deleteTarget.value) return;
  deleting.value = true;
  try {
    await deleteProject(deleteTarget.value.app_name);
    toastShow("项目已删除", "success");
    if (selectedProject.value?.app_name === deleteTarget.value.app_name) {
      selectedProject.value = null;
      history.value = [];
    }
    deleteTarget.value = null;
    await fetchProjects();
  } catch (e) {
    toastShow(e.message || "删除失败", "error");
  } finally {
    deleting.value = false;
  }
}

// ---- Helpers ----
function statusClass(status) {
  return {
    building: "tag-blue",
    deploying: "tag-blue",
    success: "tag-green",
    failed: "tag-red",
  }[status] || "";
}

function statusLabel(status) {
  return {
    building: "构建中",
    deploying: "部署中",
    success: "成功",
    failed: "失败",
  }[status] || status;
}

function formatDate(s) {
  if (!s) return "-";
  return new Date(s).toLocaleString("zh-CN");
}

onMounted(() => {
  fetchProjects();
  fetchClusters();
});
</script>

<style scoped>
.deploy-page h2 { margin-bottom: 16px; }

.deploy-layout {
  display: flex;
  gap: 20px;
  min-height: calc(100vh - 160px);
}

.deploy-left {
  width: 300px;
  flex-shrink: 0;
  border-right: 1px solid var(--border-color, #334155);
  padding-right: 16px;
  overflow-y: auto;
}

.deploy-right {
  flex: 1;
  min-width: 0;
}

.project-item {
  padding: 10px 12px;
  border: 1px solid var(--border-color, #334155);
  border-radius: 6px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.15s;
}
.project-item:hover { border-color: #3b82f6; }
.project-item.selected {
  border-color: #3b82f6;
  background: rgba(59,130,246,0.08);
}

.project-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.project-item-meta {
  font-size: 12px;
  color: #64748b;
  display: flex;
  justify-content: space-between;
}

.deploy-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #64748b;
}

.info-card, .action-card, .history-card {
  background: var(--card-bg, #1e293b);
  border: 1px solid var(--border-color, #334155);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.info-row { margin: 6px 0; font-size: 14px; }
.info-label { color: #64748b; margin-right: 4px; }
.info-row code { background: #334155; padding: 1px 4px; border-radius: 3px; font-size: 13px; }

.form-row {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.tag-blue { background: #1e40af; color: #bfdbfe; }
.tag-green { background: #166534; color: #bbf7d0; }
.tag-red { background: #991b1b; color: #fecaca; }
.tag { font-size: 11px; padding: 2px 6px; border-radius: 4px; }
</style>
```

- [ ] **Step 2: Verify the build**

```bash
cd frontend && npm run build
```

Expected: builds without errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/DeployManagementPage.vue
git commit -m "feat: add DeployManagementPage Vue component"
```

---

### Task 12: End-to-end verification

**Files:**
- (no permanent files)

- [ ] **Step 1: Start Builder Service and test health**

```bash
cd builder && python main.py &
sleep 2
curl http://127.0.0.1/api/health
kill %1
```

Expected: `{"status":"ok"}`

- [ ] **Step 2: Verify Django backend starts with deploy app**

```bash
cd backend && python manage.py check --deploy 2>&1 | head -5
```

Expected: no errors about deploy app

- [ ] **Step 3: Commit final verification**

```bash
git commit --allow-empty -m "chore: e2e verification — Builder Service and backend deploy app load correctly"
```

---

## Implementation Order

Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6 → Task 7 → Task 8 → Task 9 → Task 10 → Task 11 → Task 12

Tasks 1-6 are backend-only and independent of frontend. Tasks 8 is independent (Builder Service). Tasks 9-11 are frontend, can start after Task 6. Task 12 is final verification.
