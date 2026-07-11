# K8s Management Console Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Django REST Framework + Vue 3 web console for managing a Kubernetes cluster, deployed in-cluster in the `prd` namespace.

**Architecture:** Django 5 DRF backend (Token auth, MySQL for users/audit, Redis for token blacklist) + Vue 3 SPA frontend (Nginx serve static). Ingress routes `/api/*` → Django, `/` → Vue. Backend uses `kubernetes-client/python` with in-cluster ServiceAccount + ClusterRole for full cluster access. MySQL and Redis are reused from the existing `database` namespace.

**Tech Stack:** Python 3.12, Django 5.2, Django REST Framework 3.16, kubernetes-client 34.1, mysqlclient 2.2, redis-py 7, Vue 3, Vite, Vue Router, Pinia, CodeMirror 6, Docker, Kubernetes.

---

## File Structure Map

```
backend/
├── requirements.txt                 # Python dependencies
├── manage.py                        # Django CLI entry
├── k8s_console/                     # Django project config
│   ├── __init__.py
│   ├── settings.py                  # DB, Redis, SECRET_KEY, K8s config
│   ├── urls.py                      # Root URL router
│   ├── wsgi.py                      # WSGI entry
│   └── middleware.py                # AuditLoggerMiddleware
├── apps/
│   ├── __init__.py
│   ├── auth_app/                    # User auth + management
│   │   ├── __init__.py
│   │   ├── models.py                # User model (custom), PasswordResetToken
│   │   ├── views.py                 # Login/logout/change-password/user CRUD
│   │   └── urls.py
│   ├── resources/                   # K8s resource operations
│   │   ├── __init__.py
│   │   ├── k8s_client.py            # Unified K8s API wrapper
│   │   ├── views.py                 # Resource list/detail/scale/rollback/delete/apply
│   │   └── urls.py
│   └── audit/                       # Audit logging
│       ├── __init__.py
│       ├── models.py                # AuditLog model
│       ├── views.py                 # Audit log list
│       └── urls.py
├── utils/
│   ├── __init__.py
│   ├── response.py                  # Unified JSON response helpers
│   └── k8s_helper.py               # K8s error wrapping
└── Dockerfile                       # Multi-stage Python build

frontend/
├── package.json
├── vite.config.js
├── index.html
├── nginx.conf                       # Nginx config for serving SPA
├── Dockerfile                       # Multi-stage Node build + Nginx runtime
└── src/
    ├── main.js                      # Vue app entry
    ├── App.vue                      # Root component (layout shell)
    ├── styles/
    │   └── main.css                 # Global styles
    ├── router/
    │   └── index.js                 # Vue Router config
    ├── stores/
    │   └── auth.js                  # Pinia auth store
    ├── api/
    │   ├── client.js                # Axios instance + interceptors
    │   ├── auth.js                  # Login/logout/change-password
    │   ├── resources.js             # K8s resource CRUD
    │   ├── users.js                 # User management
    │   └── audit.js                 # Audit log queries
    ├── components/
    │   ├── AppSidebar.vue           # Left navigation
    │   ├── AppToast.vue             # Toast notification system
    │   ├── ScaleModal.vue           # Scale replicas modal
    │   ├── DeleteModal.vue          # Delete confirmation modal (type-to-confirm)
    │   ├── RollbackModal.vue        # Rollback revision picker modal
    │   └── YamlModal.vue            # Read-only YAML viewer modal
    └── views/
        ├── LoginPage.vue            # Login form
        ├── DashboardPage.vue        # Cluster overview
        ├── ResourceListPage.vue     # Generic resource table (reused for all types)
        ├── ApplyYamlPage.vue        # YAML editor + apply
        ├── UserManagementPage.vue   # Admin user CRUD
        └── AuditLogPage.vue         # Audit log table with filters

deploy/prd/console/
├── 01-sa-rbac.yaml                  # ServiceAccount + ClusterRole + ClusterRoleBinding
├── 02-configmap.yaml                # Django ConfigMap
├── 03-secret.yaml                   # Django SECRET_KEY + DB credentials
├── 04-backend.yaml                  # Django Deployment + Service
├── 05-frontend.yaml                 # Vue Deployment + Service
└── 06-ingress.yaml                  # Ingress: /api/* → backend, / → frontend
```

---

## Part A: Backend Foundation

### Task 1: Create backend project scaffold

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/manage.py`
- Create: `backend/k8s_console/__init__.py`
- Create: `backend/apps/__init__.py`
- Create: `backend/apps/auth_app/__init__.py`
- Create: `backend/apps/resources/__init__.py`
- Create: `backend/apps/audit/__init__.py`
- Create: `backend/utils/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
django>=5.0,<5.3
djangorestframework>=3.16,<3.17
kubernetes>=34.0,<35.0
mysqlclient>=2.2,<2.3
redis>=7.0,<8.0
gunicorn>=23.0,<24.0
```

- [ ] **Step 2: Create manage.py**

```python
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "k8s_console.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Create empty `__init__.py` files**

Create empty files at:
- `backend/k8s_console/__init__.py`
- `backend/apps/__init__.py`
- `backend/apps/auth_app/__init__.py`
- `backend/apps/resources/__init__.py`
- `backend/apps/audit/__init__.py`
- `backend/utils/__init__.py`

- [ ] **Step 4: Commit**

```bash
git add backend/
git commit -m "feat: create backend project scaffold"
```

### Task 2: Create Django settings

**Files:**
- Create: `backend/k8s_console/settings.py`
- Create: `backend/k8s_console/wsgi.py`

- [ ] **Step 1: Write settings.py**

```python
"""Django settings for k8s_console."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "insecure-dev-key-change-me")

DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "apps.auth_app",
    "apps.resources",
    "apps.audit",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "k8s_console.middleware.AuditLoggerMiddleware",
    "k8s_console.middleware.TokenBlacklistMiddleware",
]

ROOT_URLCONF = "k8s_console.urls"

WSGI_APPLICATION = "k8s_console.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get("MYSQL_DATABASE", "appdb"),
        "USER": os.environ.get("MYSQL_USER", "appuser"),
        "PASSWORD": os.environ.get("MYSQL_PASSWORD", "UserPass2024!"),
        "HOST": os.environ.get("MYSQL_HOST", "mysql.database.svc"),
        "PORT": os.environ.get("MYSQL_PORT", "3306"),
        "OPTIONS": {"charset": "utf8mb4"},
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"redis://:{os.environ.get('REDIS_PASSWORD', 'RedisPass2024!')}"
                    f"@{os.environ.get('REDIS_HOST', 'redis.database.svc')}"
                    f":{os.environ.get('REDIS_PORT', '6379')}/1",
    }
}

REDIS_URL = (
    f"redis://:{os.environ.get('REDIS_PASSWORD', 'RedisPass2024!')}"
    f"@{os.environ.get('REDIS_HOST', 'redis.database.svc')}"
    f":{os.environ.get('REDIS_PORT', '6379')}"
)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.auth_app.views.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "UNAUTHENTICATED_USER": None,
}

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# K8s in-cluster config
K8S_IN_CLUSTER = True

# Audit middleware: paths excluded from audit logging
AUDIT_EXCLUDE_PATHS = ["/api/auth/login", "/api/auth/logout"]
```

- [ ] **Step 2: Write wsgi.py**

```python
"""WSGI config for k8s_console."""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "k8s_console.settings")
application = get_wsgi_application()
```

- [ ] **Step 3: Commit**

```bash
git add backend/k8s_console/settings.py backend/k8s_console/wsgi.py
git commit -m "feat: add Django settings with MySQL/Redis/K8s config"
```

### Task 3: Create unified response helpers

**Files:**
- Create: `backend/utils/response.py`

- [ ] **Step 1: Write response.py**

```python
"""Unified JSON response format."""
from rest_framework.response import Response
from rest_framework import status


def success(data=None, message="ok"):
    return Response({"code": 0, "message": message, "data": data})


def error(code, message, detail=None, http_status=status.HTTP_400_BAD_REQUEST):
    body = {"code": code, "message": message}
    if detail is not None:
        body["detail"] = detail
    return Response(body, status=http_status)


# Error codes
ERR_AUTH_FAILED = 1001
ERR_TOKEN_INVALID = 1002
ERR_TOKEN_BLACKLISTED = 1003
ERR_USER_NOT_FOUND = 1004
ERR_USER_INACTIVE = 1005
ERR_WRONG_PASSWORD = 1006

ERR_RESOURCE_NOT_FOUND = 2001
ERR_K8S_API_ERROR = 2002
ERR_INVALID_YAML = 2003
ERR_UNSUPPORTED_RESOURCE = 2004
ERR_NAMESPACE_REQUIRED = 2005

ERR_PERMISSION_DENIED = 3001
ERR_VALIDATION = 3002
```

- [ ] **Step 2: Commit**

```bash
git add backend/utils/response.py
git commit -m "feat: add unified JSON response helpers"
```

### Task 4: Create K8s error helper

**Files:**
- Create: `backend/utils/k8s_helper.py`

- [ ] **Step 1: Write k8s_helper.py**

```python
"""K8s API error wrapping utilities."""
from kubernetes.client.rest import ApiException


def wrap_k8s_error(exc):
    """Convert a kubernetes ApiException into (code, message, detail) tuple."""
    if not isinstance(exc, ApiException):
        return 2002, "K8s API 调用失败", str(exc)

    status_code = exc.status
    body = {}
    try:
        import json
        body = json.loads(exc.body) if exc.body else {}
    except (json.JSONDecodeError, TypeError):
        pass

    if status_code == 404:
        return 2001, "资源不存在", exc.reason or str(exc)
    elif status_code == 403:
        return 3001, "权限不足", body.get("message", exc.reason or str(exc))
    elif status_code == 409:
        return 2002, "资源冲突", body.get("message", exc.reason or str(exc))
    elif status_code == 422:
        return 3002, "请求验证失败", body.get("message", exc.reason or str(exc))
    else:
        return 2002, f"K8s API 错误 (HTTP {status_code})", body.get("message", exc.reason or str(exc))
```

- [ ] **Step 2: Commit**

```bash
git add backend/utils/k8s_helper.py
git commit -m "feat: add K8s error wrapping utility"
```

---

## Part B: Backend Apps — Auth, Resources, Audit

### Task 5: Create User and PasswordResetToken models

**Files:**
- Create: `backend/apps/auth_app/models.py`

- [ ] **Step 1: Write models.py**

```python
"""Custom User model and PasswordResetToken."""
from django.db import models


class User(models.Model):
    ROLE_CHOICES = [
        ("admin", "管理员"),
        ("user", "普通用户"),
    ]

    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=255)  # Django hashed
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="user")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def __str__(self):
        return self.username

    class Meta:
        db_table = "user"


class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reset_tokens")
    token = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        db_table = "password_reset_token"
```

- [ ] **Step 2: Commit**

```bash
git add backend/apps/auth_app/models.py
git commit -m "feat: add User and PasswordResetToken models"
```

### Task 6: Create AuditLog model

**Files:**
- Create: `backend/apps/audit/models.py`

- [ ] **Step 1: Write models.py**

```python
"""AuditLog model for tracking all write operations."""
from django.db import models


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ("scale", "扩缩容"),
        ("rollback", "回滚"),
        ("delete", "删除"),
        ("apply", "应用YAML"),
        ("create_user", "创建用户"),
        ("toggle_active", "启用/禁用用户"),
        ("reset_password", "重置密码"),
        ("change_password", "修改密码"),
    ]

    RESULT_CHOICES = [
        ("success", "成功"),
        ("fail", "失败"),
    ]

    user = models.ForeignKey("auth_app.User", on_delete=models.SET_NULL, null=True, related_name="audit_logs")
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    resource_type = models.CharField(max_length=50)
    resource_name = models.CharField(max_length=255, blank=True, default="")
    namespace = models.CharField(max_length=100, blank=True, default="")
    detail = models.JSONField(default=dict, blank=True)
    result = models.CharField(max_length=20, choices=RESULT_CHOICES)
    error_msg = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_log"
        ordering = ["-created_at"]
```

- [ ] **Step 2: Commit**

```bash
git add backend/apps/audit/models.py
git commit -m "feat: add AuditLog model"
```

### Task 7: Create Token-based authentication

**Files:**
- Create: `backend/apps/auth_app/views.py`

- [ ] **Step 1: Write auth views (login, logout, change-password)**

```python
"""Auth views: login, logout, change-password, user management."""
import hashlib
import secrets
import redis

from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny

from apps.auth_app.models import User
from utils.response import (
    success, error,
    ERR_AUTH_FAILED, ERR_TOKEN_INVALID, ERR_TOKEN_BLACKLISTED,
    ERR_USER_NOT_FOUND, ERR_USER_INACTIVE, ERR_WRONG_PASSWORD,
    ERR_PERMISSION_DENIED, ERR_VALIDATION,
)


def _get_redis():
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def _generate_token():
    return secrets.token_hex(20)


def _get_user_from_token(token):
    """Validate token and return user, or None."""
    if not token:
        return None
    r = _get_redis()
    # Check blacklist
    if r.exists(f"token:blacklist:{token}"):
        return None
    # Look up token → user_id
    user_id = r.get(f"token:auth:{token}")
    if not user_id:
        return None
    try:
        return User.objects.get(id=int(user_id), is_active=True)
    except User.DoesNotExist:
        return None


class TokenAuthentication:
    """DRF-compatible token authentication class."""
    keyword = "Token"

    @staticmethod
    def authenticate(request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Token "):
            return None
        token = auth_header[6:].strip()
        user = _get_user_from_token(token)
        if user is None:
            return None
        return (user, token)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def login(request):
    """Login: {username, password} → {token, user}"""
    username = request.data.get("username", "").strip()
    password = request.data.get("password", "")

    if not username or not password:
        return error(ERR_AUTH_FAILED, "用户名和密码不能为空")

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return error(ERR_AUTH_FAILED, "用户名或密码错误")

    if not user.is_active:
        return error(ERR_USER_INACTIVE, "用户已被禁用")

    if not check_password(password, user.password):
        return error(ERR_AUTH_FAILED, "用户名或密码错误")

    token = _generate_token()
    r = _get_redis()
    r.setex(f"token:auth:{token}", 86400 * 7, str(user.id))  # 7-day expiry

    return success(data={
        "token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
        }
    }, message="登录成功")


@api_view(["POST"])
def logout(request):
    """Logout: blacklist current token in Redis with TTL."""
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if auth_header.startswith("Token "):
        token = auth_header[6:].strip()
        r = _get_redis()
        user_id = r.get(f"token:auth:{token}")
        ttl = r.ttl(f"token:auth:{token}")
        if ttl > 0:
            r.setex(f"token:blacklist:{token}", ttl, user_id or "")
        r.delete(f"token:auth:{token}")
    return success(message="已登出")


@api_view(["POST"])
def change_password(request):
    """Self password change: {old_password, new_password}"""
    user = request.user
    if not isinstance(user, User):
        return error(ERR_AUTH_FAILED, "未认证", http_status=401)

    old_password = request.data.get("old_password", "")
    new_password = request.data.get("new_password", "")

    if not old_password or not new_password:
        return error(ERR_VALIDATION, "旧密码和新密码不能为空")

    if len(new_password) < 6:
        return error(ERR_VALIDATION, "新密码长度至少6位")

    if not check_password(old_password, user.password):
        return error(ERR_WRONG_PASSWORD, "旧密码错误")

    user.password = make_password(new_password)
    user.save()
    return success(message="密码修改成功")
```

- [ ] **Step 2: Commit**

```bash
git add backend/apps/auth_app/views.py
git commit -m "feat: add login/logout/change-password views with Redis token store"
```

### Task 8: Create user management views

**Files:**
- Modify: `backend/apps/auth_app/views.py` — append user management functions

- [ ] **Step 1: Append user management views to views.py**

```python
def _require_admin(user):
    """Raise if user is not admin. Returns None on success."""
    if not isinstance(user, User) or user.role != "admin":
        return error(ERR_PERMISSION_DENIED, "仅管理员可执行此操作")


@api_view(["POST"])
def user_create(request):
    """Admin creates user: {username, role} → {username, password}"""
    admin_err = _require_admin(request.user)
    if admin_err:
        return admin_err

    username = request.data.get("username", "").strip()
    role = request.data.get("role", "user").strip()

    if not username:
        return error(ERR_VALIDATION, "用户名不能为空")

    if role not in ("admin", "user"):
        return error(ERR_VALIDATION, "角色必须为 admin 或 user")

    if User.objects.filter(username=username).exists():
        return error(ERR_VALIDATION, "用户名已存在")

    random_password = secrets.token_urlsafe(8)
    user = User(
        username=username,
        role=role,
        password=make_password(random_password),
    )
    user.save()

    return success(data={
        "username": user.username,
        "password": random_password,
    }, message=f"用户 {username} 创建成功")


@api_view(["POST"])
def user_list(request):
    """Admin lists all users."""
    admin_err = _require_admin(request.user)
    if admin_err:
        return admin_err

    users = User.objects.all().values("id", "username", "role", "is_active", "created_at")
    return success(data=list(users))


@api_view(["POST"])
def user_toggle_active(request):
    """Admin enable/disable user: {id}"""
    admin_err = _require_admin(request.user)
    if admin_err:
        return admin_err

    user_id = request.data.get("id")
    if user_id is None:
        return error(ERR_VALIDATION, "缺少用户ID")

    try:
        target_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return error(ERR_USER_NOT_FOUND, "用户不存在")

    if target_user.id == request.user.id:
        return error(ERR_VALIDATION, "不能禁用自己")

    target_user.is_active = not target_user.is_active
    target_user.save()

    action_text = "启用" if target_user.is_active else "禁用"
    return success(message=f"用户 {target_user.username} 已{action_text}")


@api_view(["POST"])
def user_reset_password(request):
    """Admin resets user password: {id} → {username, password}"""
    admin_err = _require_admin(request.user)
    if admin_err:
        return admin_err

    user_id = request.data.get("id")
    if user_id is None:
        return error(ERR_VALIDATION, "缺少用户ID")

    try:
        target_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return error(ERR_USER_NOT_FOUND, "用户不存在")

    new_password = secrets.token_urlsafe(8)
    target_user.password = make_password(new_password)
    target_user.save()

    return success(data={
        "username": target_user.username,
        "password": new_password,
    }, message="密码已重置")
```

- [ ] **Step 2: Commit**

```bash
git add backend/apps/auth_app/views.py
git commit -m "feat: add admin user management views (create/list/toggle/reset)"
```

### Task 9: Create auth app URLs

**Files:**
- Create: `backend/apps/auth_app/urls.py`

- [ ] **Step 1: Write auth URLs**

```python
"""Auth app URL config."""
from django.urls import path
from . import views

urlpatterns = [
    path("auth/login", views.login, name="auth_login"),
    path("auth/logout", views.logout, name="auth_logout"),
    path("auth/change-password", views.change_password, name="auth_change_password"),
    path("users/create", views.user_create, name="user_create"),
    path("users/list", views.user_list, name="user_list"),
    path("users/toggle-active", views.user_toggle_active, name="user_toggle_active"),
    path("users/reset-password", views.user_reset_password, name="user_reset_password"),
]
```

- [ ] **Step 2: Commit**

```bash
git add backend/apps/auth_app/urls.py
git commit -m "feat: add auth app URL routing"
```

### Task 10: Create K8s client module

**Files:**
- Create: `backend/apps/resources/k8s_client.py`

- [ ] **Step 1: Write k8s_client.py**

```python
"""Unified K8s API client — single entry point for all cluster operations."""
import yaml as _yaml

from kubernetes import client, config
from kubernetes.client.rest import ApiException

# Supported resource types and their client methods
_RESOURCE_MAP = {
    "namespace": {
        "api": "CoreV1Api",
        "list": "list_namespace",
        "read": "read_namespace",
        "delete": "delete_namespace",
        "namespaced": False,
    },
    "deployment": {
        "api": "AppsV1Api",
        "list": "list_namespaced_deployment",
        "read": "read_namespaced_deployment",
        "delete": "delete_namespaced_deployment",
        "scale": True,  # Special case: scale API
        "rollback": True,
        "namespaced": True,
    },
    "pod": {
        "api": "CoreV1Api",
        "list": "list_namespaced_pod",
        "read": "read_namespaced_pod",
        "delete": "delete_namespaced_pod",
        "namespaced": True,
    },
    "service": {
        "api": "CoreV1Api",
        "list": "list_namespaced_service",
        "read": "read_namespaced_service",
        "delete": "delete_namespaced_service",
        "namespaced": True,
    },
    "ingress": {
        "api": "NetworkingV1Api",
        "list": "list_namespaced_ingress",
        "read": "read_namespaced_ingress",
        "delete": "delete_namespaced_ingress",
        "namespaced": True,
    },
    "daemonset": {
        "api": "AppsV1Api",
        "list": "list_namespaced_daemon_set",
        "read": "read_namespaced_daemon_set",
        "delete": "delete_namespaced_daemon_set",
        "namespaced": True,
    },
    "statefulset": {
        "api": "AppsV1Api",
        "list": "list_namespaced_stateful_set",
        "read": "read_namespaced_stateful_set",
        "delete": "delete_namespaced_stateful_set",
        "namespaced": True,
    },
    "configmap": {
        "api": "CoreV1Api",
        "list": "list_namespaced_config_map",
        "read": "read_namespaced_config_map",
        "delete": "delete_namespaced_config_map",
        "namespaced": True,
    },
    "secret": {
        "api": "CoreV1Api",
        "list": "list_namespaced_secret",
        "read": "read_namespaced_secret",
        "delete": "delete_namespaced_secret",
        "namespaced": True,
    },
    "role": {
        "api": "RbacAuthorizationV1Api",
        "list": "list_namespaced_role",
        "read": "read_namespaced_role",
        "delete": "delete_namespaced_role",
        "namespaced": True,
    },
    "rolebinding": {
        "api": "RbacAuthorizationV1Api",
        "list": "list_namespaced_role_binding",
        "read": "read_namespaced_role_binding",
        "delete": "delete_namespaced_role_binding",
        "namespaced": True,
    },
    "clusterrole": {
        "api": "RbacAuthorizationV1Api",
        "list": "list_cluster_role",
        "read": "read_cluster_role",
        "delete": "delete_cluster_role",
        "namespaced": False,
    },
    "clusterrolebinding": {
        "api": "RbacAuthorizationV1Api",
        "list": "list_cluster_role_binding",
        "read": "read_cluster_role_binding",
        "delete": "delete_cluster_role_binding",
        "namespaced": False,
    },
    "serviceaccount": {
        "api": "CoreV1Api",
        "list": "list_namespaced_service_account",
        "read": "read_namespaced_service_account",
        "delete": "delete_namespaced_service_account",
        "namespaced": True,
    },
}


def _get_api(api_name):
    """Get a configured API client instance."""
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()

    api_map = {
        "CoreV1Api": client.CoreV1Api(),
        "AppsV1Api": client.AppsV1Api(),
        "NetworkingV1Api": client.NetworkingV1Api(),
        "RbacAuthorizationV1Api": client.RbacAuthorizationV1Api(),
    }
    return api_map[api_name]


def _get_meta(name, namespace):
    """Get API, resource info, and function kwargs for a resource type."""
    info = _RESOURCE_MAP.get(name)
    if not info:
        return None, None, None
    api = _get_api(info["api"])
    kwargs = {}
    if info["namespaced"]:
        kwargs["namespace"] = namespace
    return api, info, kwargs


def _sanitize(obj):
    """Strip Kubernetes internal fields for display."""
    if obj is None:
        return None
    # Remove noisy metadata sub-structures
    for field in ["managed_fields", "resource_version", "uid", "self_link", "generation"]:
        obj.metadata.__dict__.pop(field, None)
    if hasattr(obj.metadata, "annotations"):
        # Remove last-applied-configuration (huge)
        if obj.metadata.annotations and "kubectl.kubernetes.io/last-applied-configuration" in obj.metadata.annotations:
            del obj.metadata.annotations["kubectl.kubernetes.io/last-applied-configuration"]
    return obj


def list_resources(resource_type, namespace=None):
    """List all resources of given type. Returns list of dicts."""
    api, info, kwargs = _get_meta(resource_type, namespace)
    if not api:
        raise ValueError(f"不支持资源类型: {resource_type}")
    method = getattr(api, info["list"])
    try:
        if info["namespaced"]:
            result = method(namespace, **kwargs) if namespace else method(_for_all_namespaces=True)
        else:
            result = method()
        items = []
        for item in result.items:
            _sanitize(item)
            item_dict = item.to_dict()
            items.append(item_dict)
        return items
    except ApiException as e:
        raise e


def get_resource(resource_type, name, namespace=None):
    """Get single resource as dict."""
    api, info, kwargs = _get_meta(resource_type, namespace)
    if not api:
        raise ValueError(f"不支持资源类型: {resource_type}")
    kwargs["name"] = name
    method = getattr(api, info["read"])
    try:
        result = method(**kwargs)
        _sanitize(result)
        return result.to_dict()
    except ApiException as e:
        raise e


def get_resource_yaml(resource_type, name, namespace=None):
    """Get resource as YAML string (sanitized)."""
    api, info, kwargs = _get_meta(resource_type, namespace)
    if not api:
        raise ValueError(f"不支持资源类型: {resource_type}")
    kwargs["name"] = name
    method = getattr(api, info["read"])
    try:
        result = method(**kwargs)
        _sanitize(result)
        # Convert to dict, strip noisy fields, dump as YAML
        d = result.to_dict()
        d.get("metadata", {}).pop("managed_fields", None)
        d.get("metadata", {}).pop("resource_version", None)
        d.get("metadata", {}).pop("uid", None)
        d.get("metadata", {}).pop("self_link", None)
        d.get("metadata", {}).pop("generation", None)
        d.get("metadata", {}).pop("creation_timestamp", None)
        return _yaml.dump(d, default_flow_style=False, allow_unicode=True)
    except ApiException as e:
        raise e


def scale_resource(resource_type, name, namespace, replicas):
    """Scale a Deployment or StatefulSet."""
    if resource_type not in ("deployment", "statefulset"):
        raise ValueError("仅支持对 Deployment 和 StatefulSet 执行 scale 操作")
    api = _get_api("AppsV1Api")
    kwargs = {"name": name, "namespace": namespace}
    try:
        if resource_type == "deployment":
            body = api.read_namespaced_deployment_scale(**kwargs)
            body.spec.replicas = replicas
            return api.replace_namespaced_deployment_scale(**kwargs, body=body)
        else:
            # StatefulSet scale uses patch
            body = {"spec": {"replicas": replicas}}
            return api.patch_namespaced_stateful_set(**kwargs, body=body)
    except ApiException as e:
        raise e


def rollback_deployment(name, namespace, revision=None):
    """Rollback a Deployment to a specific revision."""
    api = _get_api("AppsV1Api")
    body = client.V1RollbackConfig(
        name=name,
        revision=revision,
    )
    rollback_body = client.V1DeploymentRollback(
        name=name,
        rollback_to=body,
    )
    try:
        return api.create_namespaced_deployment_rollback(name=name, namespace=namespace, body=rollback_body)
    except ApiException as e:
        raise e


def delete_resource(resource_type, name, namespace=None):
    """Delete a resource."""
    api, info, kwargs = _get_meta(resource_type, namespace)
    if not api:
        raise ValueError(f"不支持资源类型: {resource_type}")
    kwargs["name"] = name
    method = getattr(api, info["delete"])
    try:
        return method(**kwargs)
    except ApiException as e:
        raise e


def apply_yaml(yaml_content):
    """Apply YAML content using the dynamic client. Returns result dict."""
    from kubernetes.dynamic import DynamicClient
    from kubernetes.dynamic.exceptions import DynamicApiError

    # Parse YAML documents
    docs = list(_yaml.safe_load_all(yaml_content))
    if not docs:
        raise ValueError("YAML 内容为空")

    results = []
    dyn_client = DynamicClient(client.ApiClient())

    for doc in docs:
        if doc is None:
            continue
        kind = doc.get("kind", "").lower()
        api_version = doc.get("apiVersion", "v1")
        metadata = doc.get("metadata", {})
        name = metadata.get("name", "")
        namespace = metadata.get("namespace", "default")

        # Build resource path
        group = ""
        if "/" in api_version:
            group, version = api_version.split("/", 1)
        else:
            version = api_version

        # Determine API group and resource name
        resource_name_map = {
            "deployment": ("apps", "deployments"),
            "statefulset": ("apps", "statefulsets"),
            "daemonset": ("apps", "daemonsets"),
            "replicaset": ("apps", "replicasets"),
            "service": ("", "services"),
            "pod": ("", "pods"),
            "configmap": ("", "configmaps"),
            "secret": ("", "secrets"),
            "namespace": ("", "namespaces"),
            "ingress": ("networking.k8s.io", "ingresses"),
            "role": ("rbac.authorization.k8s.io", "roles"),
            "rolebinding": ("rbac.authorization.k8s.io", "rolebindings"),
            "clusterrole": ("rbac.authorization.k8s.io", "clusterroles"),
            "clusterrolebinding": ("rbac.authorization.k8s.io", "clusterrolebindings"),
            "serviceaccount": ("", "serviceaccounts"),
        }

        api_group, resource_name = resource_name_map.get(kind, (group, kind + "s"))

        try:
            if kind == "namespace" or kind in ("clusterrole", "clusterrolebinding"):
                # Cluster-scoped resources
                api_resource = dyn_client.resources.get(api_version=api_version, kind=doc["kind"])
                try:
                    existing = api_resource.get(name=name)
                    result = api_resource.patch(body=doc, content_type="application/merge-patch+json")
                    results.append({"resource": f"{kind}/{name}", "action": "patched", "uid": result.metadata.uid})
                except DynamicApiError:
                    result = api_resource.create(body=doc)
                    results.append({"resource": f"{kind}/{name}", "action": "created", "uid": result.metadata.uid})
            else:
                # Namespace-scoped resources
                api_resource = dyn_client.resources.get(
                    api_version=api_version, kind=doc["kind"],
                )
                try:
                    existing = api_resource.get(name=name, namespace=namespace)
                    result = api_resource.patch(body=doc, namespace=namespace, content_type="application/merge-patch+json")
                    results.append({"resource": f"{kind}/{name}", "action": "patched", "namespace": namespace, "uid": result.metadata.uid})
                except DynamicApiError:
                    result = api_resource.create(body=doc, namespace=namespace)
                    results.append({"resource": f"{kind}/{name}", "action": "created", "namespace": namespace, "uid": result.metadata.uid})
        except DynamicApiError as e:
            raise e

    return results
```

- [ ] **Step 2: Install Python dependencies to verify imports**

Run: `cd backend && pip install -r requirements.txt`
Expected: dependencies install successfully

- [ ] **Step 3: Commit**

```bash
git add backend/apps/resources/k8s_client.py
git commit -m "feat: add unified K8s API client (list/read/yaml/scale/rollback/delete/apply)"
```

### Task 11: Create resource API views

**Files:**
- Create: `backend/apps/resources/views.py`

- [ ] **Step 1: Write resources views.py**

```python
"""K8s resource CRUD views."""
from kubernetes.client.rest import ApiException

from rest_framework.decorators import api_view

from apps.resources.k8s_client import (
    list_resources, get_resource, get_resource_yaml,
    scale_resource, rollback_deployment, delete_resource, apply_yaml,
    _RESOURCE_MAP,
)
from utils.response import (
    success, error,
    ERR_RESOURCE_NOT_FOUND, ERR_K8S_API_ERROR,
    ERR_INVALID_YAML, ERR_UNSUPPORTED_RESOURCE, ERR_NAMESPACE_REQUIRED,
)
from utils.k8s_helper import wrap_k8s_error


def _check_namespaced(resource_type, namespace):
    """Return error response if resource needs namespace but none provided."""
    info = _RESOURCE_MAP.get(resource_type)
    if info and info["namespaced"] and not namespace:
        return error(ERR_NAMESPACE_REQUIRED, "此资源类型需要指定 namespace")
    return None


def _handle_api_error(exc, default_code=None):
    """Convert an exception to a DRF error response."""
    if isinstance(exc, ValueError):
        return error(ERR_UNSUPPORTED_RESOURCE, str(exc))
    if isinstance(exc, ApiException):
        code, msg, detail = wrap_k8s_error(exc)
        return error(code, msg, detail)
    return error(default_code or ERR_K8S_API_ERROR, str(exc))


@api_view(["POST"])
def resource_list(request):
    """List resources: {resource_type, namespace?}"""
    resource_type = request.data.get("resource_type", "").strip().lower()
    namespace = request.data.get("namespace", "").strip() or None

    if resource_type not in _RESOURCE_MAP:
        return error(ERR_UNSUPPORTED_RESOURCE, f"不支持的资源类型: {resource_type}")

    if resource_type in ("clusterrole", "clusterrolebinding"):
        namespace = None

    try:
        items = list_resources(resource_type, namespace=namespace)
        return success(data={"items": items, "count": len(items)})
    except (ApiException, ValueError) as e:
        return _handle_api_error(e)


@api_view(["POST"])
def resource_detail(request):
    """Get resource detail as JSON: {resource_type, name, namespace?}"""
    resource_type = request.data.get("resource_type", "").strip().lower()
    name = request.data.get("name", "").strip()
    namespace = request.data.get("namespace", "").strip() or None

    if not name:
        return error(ERR_VALIDATION, "缺少资源名称")

    if resource_type not in _RESOURCE_MAP:
        return error(ERR_UNSUPPORTED_RESOURCE, f"不支持的资源类型: {resource_type}")

    err = _check_namespaced(resource_type, namespace)
    if err:
        return err

    try:
        data = get_resource(resource_type, name, namespace=namespace)
        return success(data=data)
    except (ApiException, ValueError) as e:
        return _handle_api_error(e)


@api_view(["POST"])
def resource_yaml(request):
    """Get resource YAML: {resource_type, name, namespace?}"""
    resource_type = request.data.get("resource_type", "").strip().lower()
    name = request.data.get("name", "").strip()
    namespace = request.data.get("namespace", "").strip() or None

    if not name:
        return error(ERR_VALIDATION, "缺少资源名称")

    if resource_type not in _RESOURCE_MAP:
        return error(ERR_UNSUPPORTED_RESOURCE, f"不支持的资源类型: {resource_type}")

    err = _check_namespaced(resource_type, namespace)
    if err:
        return err

    try:
        yaml_str = get_resource_yaml(resource_type, name, namespace=namespace)
        return success(data={"yaml": yaml_str})
    except (ApiException, ValueError) as e:
        return _handle_api_error(e)


@api_view(["POST"])
def resource_scale(request):
    """Scale replicas: {resource_type, name, namespace?, replicas}"""
    resource_type = request.data.get("resource_type", "").strip().lower()
    name = request.data.get("name", "").strip()
    namespace = request.data.get("namespace", "").strip() or None
    replicas = request.data.get("replicas")

    if not name:
        return error(ERR_VALIDATION, "缺少资源名称")

    if replicas is None or not isinstance(replicas, int) or replicas < 0:
        return error(ERR_VALIDATION, "副本数必须是非负整数")

    if resource_type not in ("deployment", "statefulset"):
        return error(ERR_UNSUPPORTED_RESOURCE, "仅支持对 Deployment 和 StatefulSet 执行 scale 操作")

    err = _check_namespaced(resource_type, namespace)
    if err:
        return err

    try:
        result = scale_resource(resource_type, name, namespace, replicas)
        return success(data={
            "resource_type": resource_type,
            "name": name,
            "namespace": namespace,
            "replicas": replicas,
        }, message=f"已将 {resource_type}/{name} 副本数调整为 {replicas}")
    except (ApiException, ValueError) as e:
        return _handle_api_error(e)


@api_view(["POST"])
def resource_rollback(request):
    """Rollback Deployment: {resource_type, name, namespace?, revision?}"""
    resource_type = request.data.get("resource_type", "").strip().lower()
    name = request.data.get("name", "").strip()
    namespace = request.data.get("namespace", "").strip() or None
    revision = request.data.get("revision")

    if not name:
        return error(ERR_VALIDATION, "缺少资源名称")

    if resource_type != "deployment":
        return error(ERR_UNSUPPORTED_RESOURCE, "仅支持对 Deployment 执行回滚操作")

    err = _check_namespaced(resource_type, namespace)
    if err:
        return err

    try:
        result = rollback_deployment(name, namespace, revision=revision)
        rev_text = f"到版本 {revision}" if revision else "到上一个版本"
        return success(message=f"Deployment {name} 已回滚{rev_text}")
    except (ApiException, ValueError) as e:
        return _handle_api_error(e)


@api_view(["POST"])
def resource_delete(request):
    """Delete resource: {resource_type, name, namespace?}"""
    resource_type = request.data.get("resource_type", "").strip().lower()
    name = request.data.get("name", "").strip()
    namespace = request.data.get("namespace", "").strip() or None

    if not name:
        return error(ERR_VALIDATION, "缺少资源名称")

    if resource_type not in _RESOURCE_MAP:
        return error(ERR_UNSUPPORTED_RESOURCE, f"不支持的资源类型: {resource_type}")

    err = _check_namespaced(resource_type, namespace)
    if err:
        return err

    try:
        delete_resource(resource_type, name, namespace=namespace)
        return success(message=f"已删除 {resource_type}/{name}")
    except (ApiException, ValueError) as e:
        return _handle_api_error(e)


@api_view(["POST"])
def resource_apply(request):
    """Apply YAML: {yaml_content}"""
    yaml_content = request.data.get("yaml_content", "")

    if not yaml_content or not yaml_content.strip():
        return error(ERR_INVALID_YAML, "YAML 内容为空")

    try:
        results = apply_yaml(yaml_content)
        return success(data={"results": results}, message=f"成功处理 {len(results)} 个资源")
    except (ApiException, ValueError, Exception) as e:
        if isinstance(e, ApiException):
            return _handle_api_error(e)
        return error(ERR_INVALID_YAML, "YAML 解析或执行失败", str(e))
```

- [ ] **Step 2: Commit**

```bash
git add backend/apps/resources/views.py
git commit -m "feat: add resource CRUD views (list/detail/yaml/scale/rollback/delete/apply)"
```

### Task 12: Create resource app URLs

**Files:**
- Create: `backend/apps/resources/urls.py`

- [ ] **Step 1: Write resources URLs**

```python
"""Resources app URL config."""
from django.urls import path
from . import views

urlpatterns = [
    path("resources/list", views.resource_list, name="resource_list"),
    path("resources/detail", views.resource_detail, name="resource_detail"),
    path("resources/yaml", views.resource_yaml, name="resource_yaml"),
    path("resources/scale", views.resource_scale, name="resource_scale"),
    path("resources/rollback", views.resource_rollback, name="resource_rollback"),
    path("resources/delete", views.resource_delete, name="resource_delete"),
    path("resources/apply", views.resource_apply, name="resource_apply"),
]
```

- [ ] **Step 2: Commit**

```bash
git add backend/apps/resources/urls.py
git commit -m "feat: add resources app URL routing"
```

### Task 13: Create audit log views

**Files:**
- Create: `backend/apps/audit/views.py`

- [ ] **Step 1: Write audit views.py**

```python
"""Audit log query views."""
from datetime import datetime, timedelta

from django.db.models import Q
from rest_framework.decorators import api_view

from apps.audit.models import AuditLog
from utils.response import success, error, ERR_VALIDATION, ERR_PERMISSION_DENIED


@api_view(["POST"])
def audit_list(request):
    """List audit logs with optional filters: {action?, resource_type?, namespace?, result?, start_time?, end_time?, page?, page_size?}"""
    # Only admins can view audit logs
    if request.user.role != "admin":
        return error(ERR_PERMISSION_DENIED, "仅管理员可查看审计日志")

    queryset = AuditLog.objects.select_related("user").all()

    # Filters
    action = request.data.get("action", "").strip()
    if action:
        queryset = queryset.filter(action=action)

    resource_type = request.data.get("resource_type", "").strip()
    if resource_type:
        queryset = queryset.filter(resource_type=resource_type)

    namespace = request.data.get("namespace", "").strip()
    if namespace:
        queryset = queryset.filter(namespace=namespace)

    result = request.data.get("result", "").strip()
    if result:
        queryset = queryset.filter(result=result)

    start_time = request.data.get("start_time", "").strip()
    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time)
            queryset = queryset.filter(created_at__gte=start_dt)
        except ValueError:
            return error(ERR_VALIDATION, "start_time 格式无效，请使用 ISO 8601 格式")

    end_time = request.data.get("end_time", "").strip()
    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time)
            queryset = queryset.filter(created_at__lte=end_dt)
        except ValueError:
            return error(ERR_VALIDATION, "end_time 格式无效，请使用 ISO 8601 格式")

    # Pagination
    page = max(1, request.data.get("page", 1) or 1)
    page_size = min(100, max(1, request.data.get("page_size", 20) or 20))
    offset = (page - 1) * page_size

    total = queryset.count()
    logs = queryset[offset:offset + page_size]

    items = []
    for log in logs:
        items.append({
            "id": log.id,
            "username": log.user.username if log.user else None,
            "action": log.action,
            "action_display": log.get_action_display(),
            "resource_type": log.resource_type,
            "resource_name": log.resource_name,
            "namespace": log.namespace,
            "detail": log.detail,
            "result": log.result,
            "error_msg": log.error_msg,
            "created_at": log.created_at.isoformat(),
        })

    return success(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })
```

- [ ] **Step 2: Commit**

```bash
git add backend/apps/audit/views.py
git commit -m "feat: add audit log list view with filters and pagination"
```

### Task 14: Create audit app URLs

**Files:**
- Create: `backend/apps/audit/urls.py`

- [ ] **Step 1: Write audit URLs**

```python
"""Audit app URL config."""
from django.urls import path
from . import views

urlpatterns = [
    path("audit/list", views.audit_list, name="audit_list"),
]
```

- [ ] **Step 2: Commit**

```bash
git add backend/apps/audit/urls.py
git commit -m "feat: add audit app URL routing"
```

### Task 15: Create middleware (audit logger + token blacklist)

**Files:**
- Create: `backend/k8s_console/middleware.py`

- [ ] **Step 1: Write middleware.py**

```python
"""Middleware: AuditLoggerMiddleware and TokenBlacklistMiddleware."""
import json
import re
from django.conf import settings
from django.http import JsonResponse
from apps.auth_app.views import _get_user_from_token, _get_redis


class TokenBlacklistMiddleware:
    """Check if token is blacklisted before auth processing."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Token "):
            token = auth_header[6:].strip()
            r = _get_redis()
            if r.exists(f"token:blacklist:{token}"):
                return JsonResponse(
                    {"code": 1003, "message": "Token 已被登出", "detail": ""},
                    status=401,
                )
        return self.get_response(request)


class AuditLoggerMiddleware:
    """Log all POST requests (except excluded paths) to AuditLog."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only log POST requests
        if request.method != "POST":
            return response

        # Skip excluded paths
        path = request.path.rstrip("/")
        for excluded in settings.AUDIT_EXCLUDE_PATHS:
            if path.startswith(excluded.rstrip("/")):
                return response

        # Determine user
        user = None
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Token "):
            token = auth_header[6:].strip()
            user = _get_user_from_token(token)

        # Parse path to determine action
        action_map = {
            "resources/scale": "scale",
            "resources/rollback": "rollback",
            "resources/delete": "delete",
            "resources/apply": "apply",
            "users/create": "create_user",
            "users/toggle-active": "toggle_active",
            "users/reset-password": "reset_password",
            "auth/change-password": "change_password",
        }

        action = "apply"  # default
        for path_prefix, action_name in action_map.items():
            if path.startswith(f"/api/{path_prefix}"):
                action = action_name
                break

        # Extract resource info from request body
        resource_type = ""
        resource_name = ""
        namespace = ""

        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            body = {}

        resource_type = body.get("resource_type", "")
        resource_name = body.get("name", "")
        namespace = body.get("namespace", "")

        # Determine result from response
        import time as _time
        from apps.audit.models import AuditLog

        is_success = 200 <= response.status_code < 300
        result = "success" if is_success else "fail"
        error_msg = ""
        if not is_success:
            try:
                resp_data = json.loads(response.content.decode("utf-8"))
                error_msg = resp_data.get("message", "")
            except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                error_msg = str(response.status_code)

        # Build detail
        detail = {}
        if action == "scale":
            detail = {"replicas": body.get("replicas")}
        elif action == "rollback":
            detail = {"revision": body.get("revision")}

        AuditLog.objects.create(
            user=user,
            action=action,
            resource_type=resource_type,
            resource_name=resource_name,
            namespace=namespace or "",
            detail=detail,
            result=result,
            error_msg=error_msg,
        )

        return response
```

- [ ] **Step 2: Commit**

```bash
git add backend/k8s_console/middleware.py
git commit -m "feat: add audit logger and token blacklist middleware"
```

### Task 16: Create Django root URL configuration

**Files:**
- Create: `backend/k8s_console/urls.py`

- [ ] **Step 1: Write project urls.py**

```python
"""K8s Console URL configuration."""
from django.urls import path, include

urlpatterns = [
    path("api/", include("apps.auth_app.urls")),
    path("api/", include("apps.resources.urls")),
    path("api/", include("apps.audit.urls")),
]
```

- [ ] **Step 2: Add missing import in resources/views.py**

The resources views reference `ERR_VALIDATION` from `utils.response` but it's not imported in views.py. Fix by updating the import in `backend/apps/resources/views.py`:

```
from utils.response import (
    success, error,
    ERR_RESOURCE_NOT_FOUND, ERR_K8S_API_ERROR,
    ERR_INVALID_YAML, ERR_UNSUPPORTED_RESOURCE, ERR_NAMESPACE_REQUIRED,
    ERR_VALIDATION,
)
```

- [ ] **Step 3: Commit**

```bash
git add backend/k8s_console/urls.py backend/apps/resources/views.py
git commit -m "feat: add project root URL configuration"
```

### Task 17: Create Django backend Dockerfile

**Files:**
- Create: `backend/Dockerfile`

- [ ] **Step 1: Write backend Dockerfile**

```dockerfile
# Stage 1: Build dependencies
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
COPY . .
EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate && gunicorn k8s_console.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120"]
```

- [ ] **Step 2: Commit**

```bash
git add backend/Dockerfile
git commit -m "feat: add backend multi-stage Dockerfile"
```

---

## Part C: Frontend

### Task 18: Create frontend project scaffold

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/index.html`

- [ ] **Step 1: Write package.json**

```json
{
  "name": "k8s-console-frontend",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.5.0",
    "vue-router": "^4.5.0",
    "pinia": "^2.3.0",
    "axios": "^1.8.0",
    "codemirror": "^6.0.0",
    "@codemirror/lang-yaml": "^6.1.0",
    "@codemirror/theme-one-dark": "^6.1.0",
    "@codemirror/view": "^6.35.0",
    "@codemirror/state": "^6.5.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.2.0",
    "vite": "^6.2.0"
  }
}
```

- [ ] **Step 2: Write vite.config.js**

```javascript
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    assetsDir: "assets",
  },
});
```

- [ ] **Step 3: Write index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>☸️ K8s Management Console</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  </style>
</head>
<body>
  <div id="app"></div>
  <script type="module" src="/src/main.js"></script>
</body>
</html>
```

- [ ] **Step 4: Commit**

```bash
git add frontend/package.json frontend/vite.config.js frontend/index.html
git commit -m "feat: create frontend project scaffold (Vite + Vue 3)"
```

### Task 19: Create Vue app entry and router

**Files:**
- Create: `frontend/src/main.js`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/router/index.js`
- Create: `frontend/src/stores/auth.js`

- [ ] **Step 1: Write main.js**

```javascript
import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import "./styles/main.css";

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.mount("#app");
```

- [ ] **Step 2: Write router/index.js**

```javascript
import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "../stores/auth";

const routes = [
  {
    path: "/login",
    name: "Login",
    component: () => import("../views/LoginPage.vue"),
    meta: { requiresAuth: false },
  },
  {
    path: "/",
    name: "Dashboard",
    component: () => import("../views/DashboardPage.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/resources/:type",
    name: "ResourceList",
    component: () => import("../views/ResourceListPage.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/apply",
    name: "ApplyYaml",
    component: () => import("../views/ApplyYamlPage.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/users",
    name: "UserManagement",
    component: () => import("../views/UserManagementPage.vue"),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    path: "/audit",
    name: "AuditLog",
    component: () => import("../views/AuditLogPage.vue"),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, from, next) => {
  const auth = useAuthStore();
  if (to.meta.requiresAuth !== false && !auth.token) {
    next("/login");
  } else if (to.path === "/login" && auth.token) {
    next("/");
  } else if (to.meta.requiresAdmin && auth.user?.role !== "admin") {
    next("/");
  } else {
    next();
  }
});

export default router;
```

- [ ] **Step 3: Write stores/auth.js**

```javascript
import { defineStore } from "pinia";

const TOKEN_KEY = "k8s_console_token";
const USER_KEY = "k8s_console_user";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || "",
    user: JSON.parse(localStorage.getItem(USER_KEY) || "null"),
  }),

  getters: {
    isLoggedIn: (state) => !!state.token,
    isAdmin: (state) => state.user?.role === "admin",
  },

  actions: {
    setAuth(token, user) {
      this.token = token;
      this.user = user;
      localStorage.setItem(TOKEN_KEY, token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    },

    clearAuth() {
      this.token = "";
      this.user = null;
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    },
  },
});
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/main.js frontend/src/App.vue frontend/src/router/index.js frontend/src/stores/auth.js
git commit -m "feat: add Vue app entry, router, and Pinia auth store"
```

### Task 20: Create main App.vue shell layout

**Files:**
- Modify: `frontend/src/App.vue` — replace stub with full layout

- [ ] **Step 1: Write App.vue**

```vue
<template>
  <div v-if="!auth.isLoggedIn" class="app-login-shell">
    <router-view />
  </div>
  <div v-else class="app-shell">
    <AppSidebar />
    <main class="app-main">
      <router-view />
    </main>
    <AppToast />
  </div>
</template>

<script setup>
import { useAuthStore } from "./stores/auth";
import AppSidebar from "./components/AppSidebar.vue";
import AppToast from "./components/AppToast.vue";

const auth = useAuthStore();
</script>
```

- [ ] **Step 2: Create global styles**

Create `frontend/src/styles/main.css`:

```css
:root {
  --sidebar-width: 220px;
  --color-bg: #f1f5f9;
  --color-surface: #ffffff;
  --color-border: #e2e8f0;
  --color-text: #1e293b;
  --color-text-secondary: #64748b;
  --color-primary: #2563eb;
  --color-danger: #dc2626;
  --color-success: #16a34a;
  --color-warning: #d97706;
}

html, body, #app {
  height: 100%;
  background: var(--color-bg);
  color: var(--color-text);
}

.app-shell {
  display: flex;
  min-height: 100vh;
}

.app-main {
  flex: 1;
  margin-left: var(--sidebar-width);
  padding: 24px;
  min-height: 100vh;
}

.app-login-shell {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
}

/* Buttons */
.btn {
  padding: 8px 16px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-surface);
  color: var(--color-text);
  cursor: pointer;
  font-size: 13px;
  transition: all 0.15s;
}
.btn:hover { background: #f8fafc; }
.btn-primary {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}
.btn-primary:hover { background: #1d4ed8; }
.btn-danger {
  background: var(--color-danger);
  color: #fff;
  border-color: var(--color-danger);
}
.btn-danger:hover { background: #b91c1c; }

/* Tables */
.data-table {
  width: 100%;
  border-collapse: collapse;
  background: var(--color-surface);
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--color-border);
}
.data-table th, .data-table td {
  padding: 10px 14px;
  text-align: left;
  font-size: 13px;
}
.data-table th {
  background: #f8fafc;
  font-weight: 600;
  color: var(--color-text-secondary);
  border-bottom: 2px solid var(--color-border);
}
.data-table td {
  border-bottom: 1px solid #f1f5f9;
}
.data-table tr:hover td {
  background: #f8fafc;
}

/* Cards */
.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 20px;
}

/* Forms */
.form-group {
  margin-bottom: 16px;
}
.form-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 4px;
  color: var(--color-text-secondary);
}
.form-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.15s;
}
.form-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

/* Modal overlay */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal-box {
  background: var(--color-surface);
  border-radius: 10px;
  padding: 24px;
  min-width: 420px;
  max-width: 640px;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}
.modal-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 16px;
}
.modal-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 20px;
}

/* Tags */
.tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}
.tag-blue { background: #e0e7ff; color: #3730a3; }
.tag-green { background: #dcfce7; color: #166534; }
.tag-red { background: #fee2e2; color: #991b1b; }

/* Toast */
.toast-container {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 2000;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.toast {
  padding: 12px 20px;
  border-radius: 8px;
  font-size: 14px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  animation: slideIn 0.3s ease;
  min-width: 280px;
}
.toast-success { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
.toast-error { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
@keyframes slideIn {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.vue frontend/src/styles/main.css
git commit -m "feat: add App.vue shell layout and global styles"
```

### Task 21: Create API client layer

**Files:**
- Create: `frontend/src/api/client.js`
- Create: `frontend/src/api/auth.js`
- Create: `frontend/src/api/resources.js`
- Create: `frontend/src/api/users.js`
- Create: `frontend/src/api/audit.js`

- [ ] **Step 1: Write api/client.js — Axios instance with interceptors**

```javascript
import axios from "axios";
import { useAuthStore } from "../stores/auth";

const client = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

// Request interceptor: attach token
client.interceptors.request.use((config) => {
  const auth = useAuthStore();
  if (auth.token) {
    config.headers.Authorization = `Token ${auth.token}`;
  }
  return config;
});

// Response interceptor: unwrap unified format, handle auth errors
client.interceptors.response.use(
  (response) => {
    const body = response.data;
    if (body.code === 0) {
      return body; // { code: 0, message, data }
    }
    // Non-0 code from backend
    const error = new Error(body.message || "Unknown error");
    error.code = body.code;
    error.detail = body.detail;
    throw error;
  },
  (error) => {
    if (error.response) {
      const body = error.response.data;
      // Handle token errors
      if (body && (body.code === 1002 || body.code === 1003)) {
        const auth = useAuthStore();
        auth.clearAuth();
        window.location.href = "/login";
      }
      const err = new Error(body?.message || error.message);
      err.code = body?.code;
      err.detail = body?.detail;
      throw err;
    }
    throw error;
  }
);

export default client;
```

- [ ] **Step 2: Write api/auth.js**

```javascript
import client from "./client";

export function login(username, password) {
  return client.post("/auth/login", { username, password });
}

export function logout() {
  return client.post("/auth/logout");
}

export function changePassword(oldPassword, newPassword) {
  return client.post("/auth/change-password", {
    old_password: oldPassword,
    new_password: newPassword,
  });
}
```

- [ ] **Step 3: Write api/resources.js**

```javascript
import client from "./client";

export function listResources(resourceType, namespace) {
  return client.post("/resources/list", {
    resource_type: resourceType,
    namespace: namespace || undefined,
  });
}

export function getResourceDetail(resourceType, name, namespace) {
  return client.post("/resources/detail", {
    resource_type: resourceType,
    name,
    namespace: namespace || undefined,
  });
}

export function getResourceYaml(resourceType, name, namespace) {
  return client.post("/resources/yaml", {
    resource_type: resourceType,
    name,
    namespace: namespace || undefined,
  });
}

export function scaleResource(resourceType, name, namespace, replicas) {
  return client.post("/resources/scale", {
    resource_type: resourceType,
    name,
    namespace,
    replicas,
  });
}

export function rollbackDeployment(name, namespace, revision) {
  return client.post("/resources/rollback", {
    resource_type: "deployment",
    name,
    namespace,
    revision: revision || undefined,
  });
}

export function deleteResource(resourceType, name, namespace) {
  return client.post("/resources/delete", {
    resource_type: resourceType,
    name,
    namespace,
  });
}

export function applyYaml(yamlContent) {
  return client.post("/resources/apply", {
    yaml_content: yamlContent,
  });
}
```

- [ ] **Step 4: Write api/users.js**

```javascript
import client from "./client";

export function listUsers() {
  return client.post("/users/list", {});
}

export function createUser(username, role) {
  return client.post("/users/create", { username, role });
}

export function toggleUserActive(id) {
  return client.post("/users/toggle-active", { id });
}

export function resetUserPassword(id) {
  return client.post("/users/reset-password", { id });
}
```

- [ ] **Step 5: Write api/audit.js**

```javascript
import client from "./client";

export function listAuditLogs(filters = {}) {
  return client.post("/audit/list", filters);
}
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/
git commit -m "feat: add API client layer (axios + interceptors + all endpoints)"
```

### Task 22: Create AppSidebar component

**Files:**
- Create: `frontend/src/components/AppSidebar.vue`

- [ ] **Step 1: Write AppSidebar.vue**

```vue
<template>
  <aside class="sidebar">
    <div class="sidebar-brand">☸️ K8s Console</div>

    <router-link to="/" class="sidebar-item" active-class="active" exact>
      📊 仪表盘
    </router-link>

    <div class="sidebar-section-label">📦 资源管理</div>
    <router-link
      v-for="r in resourceTypes"
      :key="r.type"
      :to="`/resources/${r.type}`"
      class="sidebar-item sidebar-sub"
      active-class="active"
    >
      {{ r.label }}
    </router-link>

    <div class="sidebar-divider"></div>

    <router-link to="/apply" class="sidebar-item" active-class="active">
      🛠 Apply YAML
    </router-link>
    <router-link to="/users" v-if="auth.isAdmin" class="sidebar-item" active-class="active">
      👤 用户管理
    </router-link>
    <router-link to="/audit" v-if="auth.isAdmin" class="sidebar-item" active-class="active">
      📋 审计日志
    </router-link>

    <div class="sidebar-footer">
      <span class="sidebar-user">{{ auth.user?.username }}</span>
      <button class="btn" @click="doLogout" style="width:100%;margin-top:8px;">登出</button>
    </div>
  </aside>
</template>

<script setup>
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { logout } from "../api/auth";

const auth = useAuthStore();
const router = useRouter();

const resourceTypes = [
  { type: "namespace", label: "Namespace" },
  { type: "deployment", label: "Deployment" },
  { type: "pod", label: "Pod" },
  { type: "service", label: "Service" },
  { type: "ingress", label: "Ingress" },
  { type: "daemonset", label: "DaemonSet" },
  { type: "statefulset", label: "StatefulSet" },
  { type: "configmap", label: "ConfigMap" },
  { type: "secret", label: "Secret" },
  { type: "role", label: "Role" },
  { type: "rolebinding", label: "RoleBinding" },
  { type: "clusterrole", label: "ClusterRole" },
  { type: "clusterrolebinding", label: "ClusterRoleBinding" },
  { type: "serviceaccount", label: "ServiceAccount" },
];

async function doLogout() {
  try { await logout(); } catch (e) { /* ignore */ }
  auth.clearAuth();
  router.push("/login");
}
</script>

<style scoped>
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: var(--sidebar-width);
  background: #1e293b;
  color: #cbd5e1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  z-index: 100;
}

.sidebar-brand {
  padding: 16px;
  font-size: 16px;
  font-weight: 700;
  color: #fff;
}

.sidebar-section-label {
  padding: 12px 16px 4px;
  font-size: 11px;
  text-transform: uppercase;
  color: #64748b;
  letter-spacing: 0.5px;
}

.sidebar-item {
  padding: 10px 16px;
  color: #94a3b8;
  text-decoration: none;
  font-size: 13px;
  display: block;
  transition: all 0.15s;
  border-left: 3px solid transparent;
}
.sidebar-item:hover {
  background: #334155;
  color: #e2e8f0;
}
.sidebar-item.active {
  background: #334155;
  color: #fff;
  border-left-color: #3b82f6;
}

.sidebar-sub {
  padding-left: 28px;
  font-size: 12px;
}

.sidebar-divider {
  margin: 8px 16px;
  border-top: 1px solid #334155;
}

.sidebar-footer {
  margin-top: auto;
  padding: 16px;
  border-top: 1px solid #334155;
}
.sidebar-user {
  font-size: 13px;
  color: #e2e8f0;
  display: block;
  text-align: center;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/AppSidebar.vue
git commit -m "feat: add sidebar navigation component"
```

### Task 23: Create AppToast notification component

**Files:**
- Create: `frontend/src/components/AppToast.vue`

- [ ] **Step 1: Write AppToast.vue**

```vue
<template>
  <div class="toast-container">
    <div
      v-for="toast in toasts"
      :key="toast.id"
      :class="['toast', `toast-${toast.type}`]"
    >
      {{ toast.message }}
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";

const toasts = ref([]);
let nextId = 0;

function show(message, type = "success", duration = 3000) {
  const id = nextId++;
  toasts.value.push({ id, message, type });
  setTimeout(() => {
    toasts.value = toasts.value.filter((t) => t.id !== id);
  }, duration);
}

// Expose globally
import { provide } from "vue";
provide("toast", { show });
</script>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/AppToast.vue
git commit -m "feat: add toast notification component"
```

### Task 24: Create modal components (Scale, Delete, Rollback, YAML)

**Files:**
- Create: `frontend/src/components/ScaleModal.vue`
- Create: `frontend/src/components/DeleteModal.vue`
- Create: `frontend/src/components/RollbackModal.vue`
- Create: `frontend/src/components/YamlModal.vue`

- [ ] **Step 1: Write ScaleModal.vue**

```vue
<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-box">
      <h3 class="modal-title">Scale 操作</h3>
      <p style="color:#64748b;font-size:13px;margin-bottom:16px;">⚠️ 此操作将修改副本数，请确认</p>
      <div class="form-group">
        <label class="form-label">资源</label>
        <div class="form-input" style="background:#f8fafc;">{{ resourceType }} / {{ name }} ({{ namespace }})</div>
      </div>
      <div class="form-group">
        <label class="form-label">当前副本数</label>
        <div class="form-input" style="background:#f8fafc;">{{ currentReplicas ?? '未知' }}</div>
      </div>
      <div class="form-group">
        <label class="form-label">目标副本数</label>
        <input v-model.number="replicas" type="number" class="form-input" min="0" />
      </div>
      <div class="modal-actions">
        <button class="btn" @click="$emit('close')">取消</button>
        <button class="btn btn-primary" :disabled="replicas === null" @click="$emit('confirm', replicas)">确认 Scale</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from "vue";

const props = defineProps({
  visible: Boolean,
  resourceType: String,
  name: String,
  namespace: String,
  currentReplicas: Number,
});

defineEmits(["close", "confirm"]);

const replicas = ref(null);

watch(() => props.visible, (v) => {
  if (v) replicas.value = props.currentReplicas;
});
</script>
```

- [ ] **Step 2: Write DeleteModal.vue**

```vue
<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-box">
      <h3 class="modal-title" style="color:#dc2626;">🚨 删除资源</h3>
      <p style="color:#dc2626;font-size:13px;margin-bottom:16px;">此操作不可逆！请输入资源名称确认</p>
      <div class="form-group">
        <label class="form-label">资源</label>
        <div class="form-input" style="background:#f8fafc;">{{ resourceType }} / {{ name }} ({{ namespace }})</div>
      </div>
      <div class="form-group">
        <label class="form-label">输入 "<code>{{ name }}</code>" 确认删除</label>
        <input v-model="confirmText" class="form-input" :placeholder="name" />
      </div>
      <div class="modal-actions">
        <button class="btn" @click="$emit('close')">取消</button>
        <button class="btn btn-danger" :disabled="confirmText !== name" @click="$emit('confirm')">确认删除</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from "vue";

const props = defineProps({
  visible: Boolean,
  resourceType: String,
  name: String,
  namespace: String,
});

defineEmits(["close", "confirm"]);

const confirmText = ref("");

watch(() => props.visible, (v) => {
  if (v) confirmText.value = "";
});
</script>
```

- [ ] **Step 3: Write RollbackModal.vue**

```vue
<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-box">
      <h3 class="modal-title">Rollback 操作</h3>
      <p class="form-group" style="color:#64748b;font-size:13px;">⚠️ 此操作将回滚 Deployment 到指定版本</p>
      <div class="form-group">
        <label class="form-label">Deployment</label>
        <div class="form-input" style="background:#f8fafc;">{{ name }} ({{ namespace }})</div>
      </div>
      <div class="form-group">
        <label class="form-label">回滚版本 (留空回滚到上一个版本)</label>
        <input v-model.number="revision" type="number" class="form-input" min="1" placeholder="留空 = 上一个版本" />
      </div>
      <div class="modal-actions">
        <button class="btn" @click="$emit('close')">取消</button>
        <button class="btn btn-primary" @click="$emit('confirm', revision || undefined)">确认 Rollback</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from "vue";

const props = defineProps({
  visible: Boolean,
  name: String,
  namespace: String,
});

defineEmits(["close", "confirm"]);

const revision = ref(null);

watch(() => props.visible, (v) => {
  if (v) revision.value = null;
});
</script>
```

- [ ] **Step 4: Write YamlModal.vue**

```vue
<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-box" style="min-width:640px;max-width:800px;">
      <h3 class="modal-title">YAML — {{ resourceType }}/{{ name }}</h3>
      <pre class="yaml-viewer"><code>{{ yamlContent || '加载中...' }}</code></pre>
      <div class="modal-actions">
        <button class="btn" @click="copyYaml">📋 复制</button>
        <button class="btn" @click="$emit('close')">关闭</button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  visible: Boolean,
  resourceType: String,
  name: String,
  yamlContent: String,
});

defineEmits(["close"]);

function copyYaml() {
  navigator.clipboard.writeText(this.yamlContent);
}
</script>

<script>
export default {
  methods: {
    copyYaml() {
      navigator.clipboard.writeText(this.yamlContent || "");
    },
  },
};
</script>

<style scoped>
.yaml-viewer {
  background: #1e293b;
  color: #e2e8f0;
  padding: 16px;
  border-radius: 8px;
  overflow: auto;
  max-height: 50vh;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre;
  font-family: "Fira Code", "Cascadia Code", monospace;
}
</style>
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ScaleModal.vue frontend/src/components/DeleteModal.vue frontend/src/components/RollbackModal.vue frontend/src/components/YamlModal.vue
git commit -m "feat: add modal components (Scale, Delete, Rollback, YAML viewer)"
```

### Task 25: Create LoginPage view

**Files:**
- Create: `frontend/src/views/LoginPage.vue`

- [ ] **Step 1: Write LoginPage.vue**

```vue
<template>
  <div class="login-card">
    <h1 style="text-align:center;color:#fff;margin-bottom:24px;">☸️ K8s Console</h1>
    <form @submit.prevent="doLogin" class="card" style="width:380px;">
      <h2 style="margin-bottom:20px;">登录</h2>
      <div class="form-group">
        <label class="form-label">用户名</label>
        <input v-model="username" class="form-input" autofocus />
      </div>
      <div class="form-group">
        <label class="form-label">密码</label>
        <input v-model="password" type="password" class="form-input" />
      </div>
      <p v-if="error" style="color:#dc2626;font-size:13px;margin-bottom:12px;">{{ error }}</p>
      <button type="submit" class="btn btn-primary" style="width:100%;" :disabled="loading">
        {{ loading ? '登录中...' : '登录' }}
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { login } from "../api/auth";

const username = ref("");
const password = ref("");
const error = ref("");
const loading = ref(false);
const router = useRouter();
const auth = useAuthStore();

async function doLogin() {
  error.value = "";
  if (!username.value || !password.value) {
    error.value = "请输入用户名和密码";
    return;
  }
  loading.value = true;
  try {
    const res = await login(username.value, password.value);
    auth.setAuth(res.data.token, res.data.user);
    router.push("/");
  } catch (e) {
    error.value = e.message || "登录失败";
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-card {
  display: flex;
  flex-direction: column;
  align-items: center;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/LoginPage.vue
git commit -m "feat: add LoginPage view"
```

### Task 26: Create DashboardPage view

**Files:**
- Create: `frontend/src/views/DashboardPage.vue`

- [ ] **Step 1: Write DashboardPage.vue**

```vue
<template>
  <div>
    <h2 style="margin-bottom:20px;">📊 集群概览</h2>
    <div class="dashboard-grid">
      <div class="card stat-card" v-for="stat in stats" :key="stat.label">
        <div class="stat-value">{{ stat.value }}</div>
        <div class="stat-label">{{ stat.label }}</div>
      </div>
    </div>
    <div v-if="error" class="card" style="margin-top:16px;color:#dc2626;">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { listResources } from "../api/resources";

const stats = ref([
  { label: "Namespace", value: "..." },
  { label: "Deployment", value: "..." },
  { label: "Pod", value: "..." },
  { label: "Service", value: "..." },
  { label: "Ingress", value: "..." },
]);
const error = ref("");

onMounted(async () => {
  const types = [
    { key: "namespace", label: "Namespace" },
    { key: "deployment", label: "Deployment" },
    { key: "pod", label: "Pod" },
    { key: "service", label: "Service" },
    { key: "ingress", label: "Ingress" },
  ];
  const results = [];
  for (const t of types) {
    try {
      const res = await listResources(t.key);
      results.push({ label: t.label, value: res.data?.count ?? 0 });
    } catch (e) {
      results.push({ label: t.label, value: "错误" });
    }
  }
  stats.value = results;
});
</script>

<style scoped>
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
}
.stat-card {
  text-align: center;
  padding: 24px 16px;
}
.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--color-primary);
}
.stat-label {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-top: 4px;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/DashboardPage.vue
git commit -m "feat: add DashboardPage with cluster overview stats"
```

### Task 27: Create ResourceListPage view

**Files:**
- Create: `frontend/src/views/ResourceListPage.vue`

- [ ] **Step 1: Write ResourceListPage.vue**

```vue
<template>
  <div>
    <h2 style="margin-bottom:16px;">📦 {{ title }}</h2>

    <!-- Namespace filter for namespaced resources -->
    <div v-if="isNamespaced" style="margin-bottom:16px;display:flex;gap:8px;flex-wrap:wrap;">
      <span
        :class="['tag', ns === currentNamespace ? 'tag-blue' : '']"
        style="cursor:pointer;"
        @click="currentNamespace = ns"
        v-for="ns in namespaces"
        :key="ns"
      >{{ ns }}</span>
    </div>

    <div v-if="loading" style="color:#64748b;">加载中...</div>
    <div v-else-if="error" class="card" style="color:#dc2626;">{{ error }}</div>
    <table v-else class="data-table">
      <thead>
        <tr>
          <th v-for="col in columns" :key="col.key">{{ col.label }}</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in items" :key="itemKey(item)">
          <td v-for="col in columns" :key="col.key">
            <template v-if="col.key === 'status'">
              <span :class="['tag', statusClass(item)]">{{ statusText(item) }}</span>
            </template>
            <template v-else>{{ getNested(item, col.key) }}</template>
          </td>
          <td class="actions-cell">
            <button class="btn" @click="viewYaml(item)" style="font-size:12px;">YAML</button>
            <button v-if="canScale" class="btn" @click="openScale(item)" style="font-size:12px;">Scale</button>
            <button v-if="resourceType === 'deployment'" class="btn" @click="openRollback(item)" style="font-size:12px;">Rollback</button>
            <button v-if="resourceType !== 'namespace'" class="btn" @click="openDelete(item)" style="font-size:12px;color:#dc2626;">删除</button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="items.length === 0 && !loading" style="color:#64748b;margin-top:16px;">暂无资源</p>

    <!-- Modals -->
    <ScaleModal :visible="scaleVisible" :resourceType="resourceType" :name="selectedName"
      :namespace="selectedNamespace" :currentReplicas="currentReplicas"
      @close="scaleVisible = false" @confirm="doScale" />
    <DeleteModal :visible="deleteVisible" :resourceType="resourceType" :name="selectedName"
      :namespace="selectedNamespace"
      @close="deleteVisible = false" @confirm="doDelete" />
    <RollbackModal :visible="rollbackVisible" :name="selectedName" :namespace="selectedNamespace"
      @close="rollbackVisible = false" @confirm="doRollback" />
    <YamlModal :visible="yamlVisible" :resourceType="resourceType" :name="selectedName"
      :yamlContent="yamlContent"
      @close="yamlVisible = false" />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, inject } from "vue";
import { useRoute } from "vue-router";
import { listResources, getResourceYaml, scaleResource, rollbackDeployment, deleteResource } from "../api/resources";
import ScaleModal from "../components/ScaleModal.vue";
import DeleteModal from "../components/DeleteModal.vue";
import RollbackModal from "../components/RollbackModal.vue";
import YamlModal from "../components/YamlModal.vue";

const route = useRoute();
const toast = inject("toast");

const resourceType = computed(() => route.params.type);
const title = computed(() => {
  const map = {
    namespace: "Namespace", deployment: "Deployment", pod: "Pod",
    service: "Service", ingress: "Ingress", daemonset: "DaemonSet",
    statefulset: "StatefulSet", configmap: "ConfigMap", secret: "Secret",
    role: "Role", rolebinding: "RoleBinding", clusterrole: "ClusterRole",
    clusterrolebinding: "ClusterRoleBinding", serviceaccount: "ServiceAccount",
  };
  return map[resourceType.value] || resourceType.value;
});

const clusterScoped = ["namespace", "clusterrole", "clusterrolebinding"];
const isNamespaced = computed(() => !clusterScoped.includes(resourceType.value));
const canScale = computed(() => ["deployment", "statefulset"].includes(resourceType.value));

const items = ref([]);
const loading = ref(false);
const error = ref("");
const namespaces = ref(["全部"]);
const currentNamespace = ref("全部");

// Modal state
const scaleVisible = ref(false);
const deleteVisible = ref(false);
const rollbackVisible = ref(false);
const yamlVisible = ref(false);
const selectedName = ref("");
const selectedNamespace = ref("");
const currentReplicas = ref(0);
const yamlContent = ref("");

// Column definitions per resource type
const columns = computed(() => {
  const base = { name: "metadata.name" };
  if (isNamespaced.value) base.namespace = "metadata.namespace";
  const extras = {
    deployment: { replicas: "spec.replicas", image: "spec.template.spec.containers[0].image" },
    pod: { status: "status" },
    service: { type: "spec.type", cluster_ip: "spec.cluster_ip" },
    ingress: { hosts: "spec.rules[0].host" },
    daemonset: {},
    statefulset: { replicas: "spec.replicas" },
    configmap: {},
    secret: { type: "type" },
    role: {},
    rolebinding: {},
    clusterrole: {},
    clusterrolebinding: {},
    serviceaccount: {},
    namespace: { status: "status" },
  };
  const all = { ...base, ...(extras[resourceType.value] || {}) };
  return Object.entries(all).map(([key, val]) => ({ key: val, label: key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()) }));
});

// Helpers
function getNested(obj, path) {
  if (!obj) return "";
  const parts = path.replace(/\[(\d+)\]/g, ".$1").split(".");
  let val = obj;
  for (const p of parts) {
    if (val == null) return "";
    val = val[p];
  }
  if (Array.isArray(val)) val = val.join(", ");
  return val ?? "";
}

function itemKey(item) {
  const name = getNested(item, "metadata.name");
  const ns = getNested(item, "metadata.namespace");
  return `${ns || ""}/${name}`;
}

function statusText(item) {
  if (resourceType.value === "pod") return getNested(item, "status.phase") || "Unknown";
  if (resourceType.value === "namespace") return getNested(item, "status.phase") || "Active";
  return "";
}

function statusClass(item) {
  const s = statusText(item);
  if (s === "Running" || s === "Active") return "tag-green";
  if (s === "Pending" || s === "Terminating") return "tag-red";
  return "tag-blue";
}

function openScale(item) {
  selectedName.value = getNested(item, "metadata.name");
  selectedNamespace.value = getNested(item, "metadata.namespace");
  currentReplicas.value = getNested(item, "spec.replicas") || 0;
  scaleVisible.value = true;
}

function openDelete(item) {
  selectedName.value = getNested(item, "metadata.name");
  selectedNamespace.value = getNested(item, "metadata.namespace") || "";
  deleteVisible.value = true;
}

function openRollback(item) {
  selectedName.value = getNested(item, "metadata.name");
  selectedNamespace.value = getNested(item, "metadata.namespace");
  rollbackVisible.value = true;
}

async function viewYaml(item) {
  selectedName.value = getNested(item, "metadata.name");
  selectedNamespace.value = getNested(item, "metadata.namespace") || "";
  yamlContent.value = "加载中...";
  yamlVisible.value = true;
  try {
    const res = await getResourceYaml(resourceType.value, selectedName.value, selectedNamespace.value || undefined);
    yamlContent.value = res.data.yaml;
  } catch (e) {
    yamlContent.value = `错误: ${e.message}`;
  }
}

async function doScale(replicas) {
  try {
    await scaleResource(resourceType.value, selectedName.value, selectedNamespace.value, replicas);
    toast.show(`已将副本数调整为 ${replicas}`, "success");
    scaleVisible.value = false;
    fetchData();
  } catch (e) {
    toast.show(e.message || "Scale 失败", "error");
  }
}

async function doDelete() {
  try {
    await deleteResource(resourceType.value, selectedName.value, selectedNamespace.value || undefined);
    toast.show(`已删除 ${resourceType.value}/${selectedName.value}`, "success");
    deleteVisible.value = false;
    fetchData();
  } catch (e) {
    toast.show(e.message || "删除失败", "error");
  }
}

async function doRollback(revision) {
  try {
    await rollbackDeployment(selectedName.value, selectedNamespace.value, revision);
    toast.show("回滚成功", "success");
    rollbackVisible.value = false;
    fetchData();
  } catch (e) {
    toast.show(e.message || "回滚失败", "error");
  }
}

async function fetchData() {
  loading.value = true;
  error.value = "";
  try {
    const ns = currentNamespace.value === "全部" ? undefined : currentNamespace.value;
    const res = await listResources(resourceType.value, ns);
    items.value = res.data?.items || [];
  } catch (e) {
    error.value = e.message || "加载失败";
    items.value = [];
  } finally {
    loading.value = false;
  }
}

// Fetch namespace list for filter
async function fetchNamespaces() {
  try {
    const res = await listResources("namespace");
    const nsList = (res.data?.items || []).map(i => i.metadata?.name).filter(Boolean);
    namespaces.value = ["全部", ...nsList];
  } catch (e) { /* ignore */ }
}

onMounted(() => {
  fetchNamespaces();
  fetchData();
});

watch(resourceType, () => {
  currentNamespace.value = "全部";
  fetchData();
});

watch(currentNamespace, () => fetchData());
</script>

<style scoped>
.actions-cell {
  white-space: nowrap;
}
.actions-cell .btn {
  margin-right: 4px;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/ResourceListPage.vue
git commit -m "feat: add generic ResourceListPage with filters and action modals"
```

### Task 28: Create ApplyYamlPage view

**Files:**
- Create: `frontend/src/views/ApplyYamlPage.vue`

- [ ] **Step 1: Write ApplyYamlPage.vue**

```vue
<template>
  <div>
    <h2 style="margin-bottom:16px;">🛠 Apply YAML</h2>
    <div class="apply-layout">
      <div class="editor-panel">
        <textarea
          ref="editorEl"
          v-model="yamlContent"
          class="yaml-editor"
          placeholder="在此粘贴或编辑 YAML..."
          spellcheck="false"
        ></textarea>
      </div>
      <div class="result-panel">
        <button class="btn btn-primary" style="width:100%;margin-bottom:8px;" :disabled="!yamlContent.trim() || applying" @click="doApply">
          {{ applying ? 'Applying...' : 'Apply' }}
        </button>
        <button class="btn" style="width:100%;margin-bottom:16px;" @click="yamlContent = ''; result = null;">清空</button>
        <div v-if="result" :class="['result-box', result.success ? 'result-success' : 'result-error']">
          <div style="font-size:20px;margin-bottom:8px;">{{ result.success ? '✅' : '❌' }}</div>
          <div style="font-weight:600;">{{ result.message }}</div>
          <div v-for="r in result.results" :key="r.resource" style="font-size:12px;color:#64748b;margin-top:4px;">
            {{ r.resource }} — {{ r.action }}
          </div>
        </div>
        <p style="font-size:11px;color:#94a3b8;margin-top:8px;">💡 支持在线编辑 YAML，粘贴或直接修改后点击 Apply</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, inject } from "vue";
import { applyYaml } from "../api/resources";

const toast = inject("toast");
const yamlContent = ref("");
const applying = ref(false);
const result = ref(null);

async function doApply() {
  if (!yamlContent.value.trim()) return;
  applying.value = true;
  result.value = null;
  try {
    const res = await applyYaml(yamlContent.value);
    result.value = { success: true, message: res.message, results: res.data?.results || [] };
    toast.show(res.message, "success");
  } catch (e) {
    result.value = { success: false, message: e.message || "Apply 失败", results: [] };
    toast.show(e.message || "Apply 失败", "error");
  } finally {
    applying.value = false;
  }
}
</script>

<style scoped>
.apply-layout {
  display: flex;
  gap: 16px;
  height: calc(100vh - 140px);
}
.editor-panel {
  flex: 2;
  display: flex;
}
.yaml-editor {
  flex: 1;
  background: #1e293b;
  color: #e2e8f0;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 16px;
  font-family: "Fira Code", "Cascadia Code", monospace;
  font-size: 13px;
  line-height: 1.6;
  resize: none;
  outline: none;
}
.yaml-editor::placeholder {
  color: #64748b;
}
.result-panel {
  flex: 1;
}
.result-box {
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}
.result-success {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
}
.result-error {
  background: #fef2f2;
  border: 1px solid #fecaca;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/ApplyYamlPage.vue
git commit -m "feat: add ApplyYamlPage with YAML editor and result panel"
```

### Task 29: Create UserManagementPage view

**Files:**
- Create: `frontend/src/views/UserManagementPage.vue`

- [ ] **Step 1: Write UserManagementPage.vue**

```vue
<template>
  <div>
    <h2 style="margin-bottom:16px;">👤 用户管理</h2>

    <!-- Create user -->
    <div class="card" style="margin-bottom:20px;">
      <h3 style="margin-bottom:12px;">创建用户</h3>
      <form @submit.prevent="doCreate" style="display:flex;gap:8px;align-items:flex-end;">
        <div class="form-group" style="margin:0;flex:1;">
          <label class="form-label">用户名</label>
          <input v-model="newUsername" class="form-input" required />
        </div>
        <div class="form-group" style="margin:0;">
          <label class="form-label">角色</label>
          <select v-model="newRole" class="form-input">
            <option value="user">普通用户</option>
            <option value="admin">管理员</option>
          </select>
        </div>
        <button type="submit" class="btn btn-primary" :disabled="creating">{{ creating ? '创建中...' : '创建' }}</button>
      </form>
      <p v-if="createdUser" style="margin-top:12px;color:#16a34a;">
        ✅ 用户 <strong>{{ createdUser.username }}</strong> 创建成功，初始密码: <code>{{ createdUser.password }}</code>
      </p>
    </div>

    <!-- User list -->
    <table class="data-table">
      <thead>
        <tr>
          <th>用户名</th>
          <th>角色</th>
          <th>状态</th>
          <th>创建时间</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="u in users" :key="u.id">
          <td>{{ u.username }}</td>
          <td><span :class="['tag', u.role === 'admin' ? 'tag-blue' : '']">{{ u.role }}</span></td>
          <td><span :class="['tag', u.is_active ? 'tag-green' : 'tag-red']">{{ u.is_active ? '启用' : '禁用' }}</span></td>
          <td style="font-size:12px;">{{ u.created_at }}</td>
          <td>
            <button class="btn" @click="doToggle(u)" style="font-size:12px;">{{ u.is_active ? '禁用' : '启用' }}</button>
            <button class="btn" @click="doReset(u)" style="font-size:12px;">重置密码</button>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Reset password result -->
    <div v-if="resetResult" class="card" style="margin-top:16px;background:#fefce8;">
      <p>🔑 用户 <strong>{{ resetResult.username }}</strong> 密码已重置为: <code>{{ resetResult.password }}</code></p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, inject } from "vue";
import { listUsers, createUser, toggleUserActive, resetUserPassword } from "../api/users";

const toast = inject("toast");
const users = ref([]);
const newUsername = ref("");
const newRole = ref("user");
const creating = ref(false);
const createdUser = ref(null);
const resetResult = ref(null);

async function fetchUsers() {
  try {
    const res = await listUsers();
    users.value = res.data || [];
  } catch (e) {
    toast.show(e.message, "error");
  }
}

async function doCreate() {
  creating.value = true;
  createdUser.value = null;
  try {
    const res = await createUser(newUsername.value, newRole.value);
    createdUser.value = res.data;
    newUsername.value = "";
    toast.show(res.message, "success");
    fetchUsers();
  } catch (e) {
    toast.show(e.message, "error");
  } finally {
    creating.value = false;
  }
}

async function doToggle(user) {
  try {
    const res = await toggleUserActive(user.id);
    toast.show(res.message, "success");
    fetchUsers();
  } catch (e) {
    toast.show(e.message, "error");
  }
}

async function doReset(user) {
  try {
    const res = await resetUserPassword(user.id);
    resetResult.value = res.data;
    toast.show(res.message, "success");
  } catch (e) {
    toast.show(e.message, "error");
  }
}

onMounted(fetchUsers);
</script>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/UserManagementPage.vue
git commit -m "feat: add UserManagementPage (create/list/toggle/reset)"
```

### Task 30: Create AuditLogPage view

**Files:**
- Create: `frontend/src/views/AuditLogPage.vue`

- [ ] **Step 1: Write AuditLogPage.vue**

```vue
<template>
  <div>
    <h2 style="margin-bottom:16px;">📋 审计日志</h2>

    <!-- Filters -->
    <div class="card" style="margin-bottom:16px;display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end;">
      <div class="form-group" style="margin:0;">
        <label class="form-label">操作类型</label>
        <select v-model="filterAction" class="form-input">
          <option value="">全部</option>
          <option value="scale">Scale</option>
          <option value="rollback">Rollback</option>
          <option value="delete">Delete</option>
          <option value="apply">Apply</option>
          <option value="create_user">创建用户</option>
          <option value="toggle_active">启用/禁用</option>
          <option value="reset_password">重置密码</option>
          <option value="change_password">修改密码</option>
        </select>
      </div>
      <div class="form-group" style="margin:0;">
        <label class="form-label">结果</label>
        <select v-model="filterResult" class="form-input">
          <option value="">全部</option>
          <option value="success">成功</option>
          <option value="fail">失败</option>
        </select>
      </div>
      <button class="btn btn-primary" @click="fetchData(currentPage = 1)">查询</button>
    </div>

    <table class="data-table">
      <thead>
        <tr>
          <th>用户</th>
          <th>操作</th>
          <th>资源</th>
          <th>Namespace</th>
          <th>结果</th>
          <th>时间</th>
          <th>详情</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="log in logs" :key="log.id">
          <td>{{ log.username }}</td>
          <td><span class="tag tag-blue">{{ log.action_display }}</span></td>
          <td>{{ log.resource_type }}{{ log.resource_name ? '/' + log.resource_name : '' }}</td>
          <td>{{ log.namespace }}</td>
          <td><span :class="['tag', log.result === 'success' ? 'tag-green' : 'tag-red']">{{ log.result }}</span></td>
          <td style="font-size:12px;">{{ log.created_at }}</td>
          <td style="font-size:12px;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" :title="JSON.stringify(log.detail)">
            {{ log.error_msg || JSON.stringify(log.detail) }}
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Pagination -->
    <div v-if="total > pageSize" style="display:flex;gap:8px;justify-content:center;margin-top:16px;">
      <button class="btn" :disabled="currentPage <= 1" @click="fetchData(currentPage - 1)">上一页</button>
      <span style="padding:8px;">{{ currentPage }} / {{ Math.ceil(total / pageSize) }}</span>
      <button class="btn" :disabled="currentPage >= Math.ceil(total / pageSize)" @click="fetchData(currentPage + 1)">下一页</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, inject } from "vue";
import { listAuditLogs } from "../api/audit";

const toast = inject("toast");
const logs = ref([]);
const total = ref(0);
const currentPage = ref(1);
const pageSize = 20;

const filterAction = ref("");
const filterResult = ref("");

async function fetchData(page = 1) {
  try {
    const filters = { page, page_size: pageSize };
    if (filterAction.value) filters.action = filterAction.value;
    if (filterResult.value) filters.result = filterResult.value;
    const res = await listAuditLogs(filters);
    logs.value = res.data?.items || [];
    total.value = res.data?.total || 0;
    currentPage.value = res.data?.page || page;
  } catch (e) {
    toast.show(e.message, "error");
  }
}

onMounted(() => fetchData());
</script>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/AuditLogPage.vue
git commit -m "feat: add AuditLogPage with filters and pagination"
```

### Task 31: Create frontend Dockerfile and Nginx config

**Files:**
- Create: `frontend/Dockerfile`
- Create: `frontend/nginx.conf`

- [ ] **Step 1: Write frontend Dockerfile**

```dockerfile
# Stage 1: Build Vue app
FROM node:22-alpine AS builder
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:1.27-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

- [ ] **Step 2: Write nginx.conf**

```nginx
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # API proxy — fallback to backend (or handled by Ingress)
    # In-cluster: /api/* goes to Django via Ingress, so this is just for SPA

    # SPA history mode: serve index.html for all non-file routes
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Gzip
    gzip on;
    gzip_types text/css application/javascript application/json image/svg+xml;
    gzip_min_length 256;
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/Dockerfile frontend/nginx.conf
git commit -m "feat: add frontend multi-stage Dockerfile and nginx config"
```

---

## Part D: K8s Deployment Manifests

### Task 32: Create ServiceAccount + ClusterRole + ClusterRoleBinding

**Files:**
- Create: `deploy/prd/console/01-sa-rbac.yaml`

- [ ] **Step 1: Write 01-sa-rbac.yaml**

```yaml
# ServiceAccount for k8s-console
apiVersion: v1
kind: ServiceAccount
metadata:
  name: k8s-console
  namespace: prd
---
# ClusterRole: full read for resources managed by console
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: k8s-console
rules:
  - apiGroups: [""]
    resources:
      - namespaces
      - pods
      - services
      - configmaps
      - secrets
      - serviceaccounts
      - events
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources:
      - deployments
      - deployments/scale
      - deployments/rollback
      - daemonsets
      - statefulsets
      - statefulsets/scale
    verbs: ["get", "list", "watch", "update", "patch"]
  - apiGroups: ["networking.k8s.io"]
    resources:
      - ingresses
    verbs: ["get", "list", "watch"]
  - apiGroups: ["rbac.authorization.k8s.io"]
    resources:
      - roles
      - rolebindings
      - clusterroles
      - clusterrolebindings
    verbs: ["get", "list", "watch"]
  # Delete permission for all managed resources
  - apiGroups: [""]
    resources:
      - pods
      - services
      - configmaps
      - secrets
      - serviceaccounts
    verbs: ["delete"]
  - apiGroups: ["apps"]
    resources:
      - deployments
      - daemonsets
      - statefulsets
    verbs: ["delete"]
  - apiGroups: ["networking.k8s.io"]
    resources:
      - ingresses
    verbs: ["delete"]
  - apiGroups: ["rbac.authorization.k8s.io"]
    resources:
      - roles
      - rolebindings
      - clusterroles
      - clusterrolebindings
    verbs: ["delete"]
  # Create/update for apply
  - apiGroups: [""]
    resources:
      - pods
      - services
      - configmaps
      - secrets
      - serviceaccounts
      - namespaces
    verbs: ["create", "update", "patch"]
  - apiGroups: ["apps"]
    resources:
      - deployments
      - daemonsets
      - statefulsets
    verbs: ["create", "update", "patch"]
  - apiGroups: ["networking.k8s.io"]
    resources:
      - ingresses
    verbs: ["create", "update", "patch"]
  - apiGroups: ["rbac.authorization.k8s.io"]
    resources:
      - roles
      - rolebindings
      - clusterroles
      - clusterrolebindings
    verbs: ["create", "update", "patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: k8s-console
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: k8s-console
subjects:
  - kind: ServiceAccount
    name: k8s-console
    namespace: prd
```

- [ ] **Step 2: Commit**

```bash
git add deploy/prd/console/01-sa-rbac.yaml
git commit -m "feat: add k8s-console ServiceAccount + ClusterRole + ClusterRoleBinding"
```

### Task 33: Create backend ConfigMap and Secret

**Files:**
- Create: `deploy/prd/console/02-configmap.yaml`
- Create: `deploy/prd/console/03-secret.yaml`

- [ ] **Step 1: Write 02-configmap.yaml**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: k8s-console-config
  namespace: prd
data:
  DJANGO_DEBUG: "False"
  MYSQL_HOST: "mysql.database.svc"
  MYSQL_PORT: "3306"
  MYSQL_DATABASE: "appdb"
  REDIS_HOST: "redis.database.svc"
  REDIS_PORT: "6379"
```

- [ ] **Step 2: Write 03-secret.yaml**

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: k8s-console-secret
  namespace: prd
type: Opaque
stringData:
  DJANGO_SECRET_KEY: "k8s-console-prod-secret-key-change-in-production"
  MYSQL_USER: "appuser"
  MYSQL_PASSWORD: "UserPass2024!"
  REDIS_PASSWORD: "RedisPass2024!"
```

- [ ] **Step 3: Commit**

```bash
git add deploy/prd/console/02-configmap.yaml deploy/prd/console/03-secret.yaml
git commit -m "feat: add k8s-console ConfigMap and Secret"
```

### Task 34: Create backend Deployment + Service

**Files:**
- Create: `deploy/prd/console/04-backend.yaml`

- [ ] **Step 1: Write 04-backend.yaml**

```yaml
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: k8s-console-backend
  namespace: prd
  labels:
    app: k8s-console-backend
    component: backend
spec:
  replicas: 1
  selector:
    matchLabels:
      app: k8s-console-backend
  template:
    metadata:
      labels:
        app: k8s-console-backend
        component: backend
    spec:
      serviceAccountName: k8s-console
      containers:
        - name: django
          image: k8s-console-backend:latest
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 8000
              protocol: TCP
          envFrom:
            - configMapRef:
                name: k8s-console-config
            - secretRef:
                name: k8s-console-secret
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
          readinessProbe:
            httpGet:
              path: /api/auth/login
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /api/auth/login
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 20
---
apiVersion: v1
kind: Service
metadata:
  name: k8s-console-backend
  namespace: prd
  labels:
    app: k8s-console-backend
spec:
  type: ClusterIP
  selector:
    app: k8s-console-backend
  ports:
    - name: http
      port: 8000
      targetPort: 8000
      protocol: TCP
```

- [ ] **Step 2: Commit**

```bash
git add deploy/prd/console/04-backend.yaml
git commit -m "feat: add backend Deployment + Service manifest"
```

### Task 35: Create frontend Deployment + Service

**Files:**
- Create: `deploy/prd/console/05-frontend.yaml`

- [ ] **Step 1: Write 05-frontend.yaml**

```yaml
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: k8s-console-frontend
  namespace: prd
  labels:
    app: k8s-console-frontend
    component: frontend
spec:
  replicas: 1
  selector:
    matchLabels:
      app: k8s-console-frontend
  template:
    metadata:
      labels:
        app: k8s-console-frontend
        component: frontend
    spec:
      containers:
        - name: nginx
          image: k8s-console-frontend:latest
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 80
              protocol: TCP
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
              port: 80
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 15
            periodSeconds: 20
---
apiVersion: v1
kind: Service
metadata:
  name: k8s-console-frontend
  namespace: prd
  labels:
    app: k8s-console-frontend
spec:
  type: ClusterIP
  selector:
    app: k8s-console-frontend
  ports:
    - name: http
      port: 80
      targetPort: 80
      protocol: TCP
```

- [ ] **Step 2: Commit**

```bash
git add deploy/prd/console/05-frontend.yaml
git commit -m "feat: add frontend Deployment + Service manifest"
```

### Task 36: Create Ingress for routing /api/* and /

**Files:**
- Create: `deploy/prd/console/06-ingress.yaml`

- [ ] **Step 1: Write 06-ingress.yaml**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: k8s-console
  namespace: prd
  labels:
    app: k8s-console
spec:
  ingressClassName: nginx
  rules:
    - host: console.k8s.local
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: k8s-console-backend
                port:
                  number: 8000
          - path: /
            pathType: Prefix
            backend:
              service:
                name: k8s-console-frontend
                port:
                  number: 80
```

- [ ] **Step 2: Commit**

```bash
git add deploy/prd/console/06-ingress.yaml
git commit -m "feat: add Ingress manifest (console.k8s.local, /api/* → backend, / → frontend)"
```

---

## Part E: Integration & First Admin User

### Task 37: Create initial migration + first admin user bootstrap script

**Files:**
- Create: `backend/k8s_console/management/__init__.py`
- Create: `backend/k8s_console/management/commands/__init__.py`
- Create: `backend/k8s_console/management/commands/init_admin.py`

- [ ] **Step 1: Create Django management command for init_admin**

```python
"""Django management command: create initial admin user."""
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from apps.auth_app.models import User
import secrets
import os


class Command(BaseCommand):
    help = "Create initial admin user if none exists"

    def handle(self, *args, **options):
        if User.objects.filter(role="admin").exists():
            self.stdout.write(self.style.SUCCESS("Admin user already exists, skipping."))
            return

        username = os.environ.get("ADMIN_USERNAME", "admin")
        password = os.environ.get("ADMIN_PASSWORD", secrets.token_urlsafe(12))

        User.objects.create(
            username=username,
            password=make_password(password),
            role="admin",
            is_active=True,
        )

        # Print password only on first creation
        self.stdout.write(self.style.SUCCESS(f"Admin user created: {username}"))
        self.stdout.write(self.style.WARNING(f"Initial password: {password}"))
        self.stdout.write("⚠️  Please change this password immediately after first login.")
```

- [ ] **Step 2: Update backend Dockerfile to run init_admin**

Modify `backend/Dockerfile` — change the CMD line to:

```dockerfile
CMD ["sh", "-c", "python manage.py migrate && python manage.py init_admin && gunicorn k8s_console.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120"]
```

- [ ] **Step 3: Commit**

```bash
git add backend/k8s_console/management/ backend/Dockerfile
git commit -m "feat: add init_admin management command and update Dockerfile startup"
```

### Task 38: Test the full stack locally

- [ ] **Step 1: Create a test Django app configuration for local development**

Create `backend/k8s_console/settings_dev.py`:

```python
"""Local development settings override."""
from .settings import *

DEBUG = True
DATABASES["default"]["HOST"] = "127.0.0.1"
DATABASES["default"]["PORT"] = "3306"
REDIS_URL = "redis://127.0.0.1:6379"
CACHES["default"]["LOCATION"] = "redis://127.0.0.1:6379/1"
```

- [ ] **Step 2: Verify Django can start**

Run: `cd backend && python manage.py check --settings=k8s_console.settings_dev`
Expected: "System check identified no issues (0 silenced)."
(May warn about DB connection — that's expected if MySQL is not running locally)

- [ ] **Step 3: Verify frontend can build**

Run: `cd frontend && npm install && npm run build`
Expected: Successful build with `dist/` output

- [ ] **Step 4: Commit**

```bash
git add backend/k8s_console/settings_dev.py
git commit -m "feat: add local dev settings override"
```

---

## Summary

**Total: 38 tasks across 5 parts**

| Part | Tasks | Description |
|------|-------|-------------|
| A | 1–4 | Backend Foundation (scaffold, settings, utils) |
| B | 5–17 | Backend Apps (auth, resources, audit, middleware, Dockerfile) |
| C | 18–31 | Frontend (scaffold, API layer, components, views, Dockerfile) |
| D | 32–36 | K8s Deployment Manifests |
| E | 37–38 | Integration & Testing |

**Resources to be managed:** namespace, deployment, pod, service, ingress, daemonset, statefulset, configmap, secret, role, rolebinding, clusterrole, clusterrolebinding, serviceaccount

**Operations supported:** List, View YAML (read-only), Scale (Deployment/StatefulSet), Rollback (Deployment), Delete, Apply YAML
