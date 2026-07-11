# K8s Management Console — Design Spec

> **Date:** 2026-07-11 | **Status:** Design Approved

## 1. Overview

A Django REST Framework + Vue.js web console for managing a Kubernetes cluster. Deployed as Pods in the `prd` namespace, connecting to the K8s API Server via ServiceAccount + ClusterRole for full-cluster management.

## 2. Architecture

```
Browser (同一域名)
  │
  ▼
Ingress (nginx, prd namespace)
  ├── /api/*  →  Django Backend Service
  └── /       →  Vue Frontend Service (Nginx serve static)
         │
         ▼
K8s API Server (via in-cluster ServiceAccount + ClusterRole)
         │
         ▼
MySQL + Redis (database namespace, already deployed)
```

| Layer | Technology | Deployment |
|-------|-----------|------------|
| Frontend | Vue 3 + Vite, Nginx serve static | Deployment + Service, prd namespace |
| Backend | Django 5 + Django REST Framework | Deployment + Service, prd namespace |
| K8s Client | kubernetes-client/python (official) | In-cluster ServiceAccount |
| Auth | Django Token Authentication | — |
| Database | MySQL 8.0 (复用 database namespace) | Already deployed |
| Cache | Redis 7 (复用 database namespace) | Already deployed |

## 3. Backend Design

### 3.1 Project Structure

```
backend/
├── manage.py
├── requirements.txt
├── k8s_console/              # Django project config
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── middleware.py
├── apps/
│   ├── auth_app/             # Login/logout/change-password
│   ├── resources/            # K8s resource CRUD
│   └── audit/                # Audit log
├── utils/
│   ├── k8s_helper.py         # Unified error wrapping
│   └── response.py           # Unified response format
└── Dockerfile
```

### 3.2 Database Tables (MySQL)

**user**
| Column | Type | Notes |
|--------|------|-------|
| id | AutoField PK | — |
| username | CharField(150) unique | — |
| password | CharField(255) | Django hash |
| role | CharField(20) | admin / user |
| is_active | BooleanField | default True |
| created_at | DateTimeField | auto_now_add |

**password_reset_token**
| Column | Type | Notes |
|--------|------|-------|
| id | AutoField PK | — |
| user | FK → user | — |
| token | CharField(64) | random generated |
| expires_at | DateTimeField | — |
| used | BooleanField | default False |

**audit_log**
| Column | Type | Notes |
|--------|------|-------|
| id | AutoField PK | — |
| user | FK → user | — |
| action | CharField(50) | scale / rollback / delete / apply / create_user |
| resource_type | CharField(50) | Deployment / Pod / ... |
| resource_name | CharField(255) | resource name (required for delete) |
| namespace | CharField(100) | — |
| detail | JSONField | operation details (e.g. replicas changed) |
| result | CharField(20) | success / fail |
| error_msg | TextField | nullable |
| created_at | DateTimeField | auto_now_add |

### 3.3 API Design

All write APIs use POST method. Read APIs use POST with JSON body (no URI params for resource identifiers). All responses follow `{code, message, data}` format. Errors: `{code, message, detail}`.

| Endpoint | Method | Body | Description |
|----------|--------|------|-------------|
| `/api/auth/login` | POST | `{username, password}` | Login, returns token |
| `/api/auth/logout` | POST | — | Logout, token blacklisted in Redis |
| `/api/auth/change-password` | POST | `{old_password, new_password}` | Self password change |
| `/api/users/create` | POST | `{username, role}` | Admin creates user, returns random password |
| `/api/users/list` | POST | `{}` | Admin lists all users |
| `/api/users/toggle-active` | POST | `{id}` | Admin enable/disable user |
| `/api/users/reset-password` | POST | `{id}` | Admin resets user password |
| `/api/resources/list` | POST | `{resource_type, namespace?}` | List resources of given type |
| `/api/resources/detail` | POST | `{resource_type, name, namespace?}` | Resource detail + YAML (read-only) |
| `/api/resources/scale` | POST | `{resource_type, name, namespace?, replicas}` | Scale replicas (Deployment/StatefulSet) |
| `/api/resources/rollback` | POST | `{resource_type, name, namespace?, revision?}` | Rollback Deployment |
| `/api/resources/delete` | POST | `{resource_type, name, namespace?}` | Delete resource |
| `/api/resources/apply` | POST | `{yaml_content}` | Apply YAML |

Supported resource types: namespace, deployment, pod, service, ingress, daemonset, statefulset, configmap, secret, role, rolebinding, clusterrole, clusterrolebinding, serviceaccount.

### 3.4 Auth & Middleware

- Token-based auth: every request carries `Authorization: Token xxx` header
- Login returns token; logout adds token to Redis blacklist with TTL
- Audit middleware: intercepts all POST requests, logs operation to audit_log (excludes: login, logout, GET requests)
- Token blacklist check middleware: before auth, check if token is in Redis blacklist

### 3.5 K8s Client Module

`apps/resources/k8s_client.py` — single entry point for all K8s API calls:
- `list_resources(resource_type, namespace=None)` → list of resource dicts
- `get_resource(resource_type, name, namespace=None)` → resource dict
- `get_resource_yaml(resource_type, name, namespace=None)` → YAML string
- `scale_resource(resource_type, name, namespace, replicas)` → result
- `rollback_deployment(name, namespace, revision=None)` → result
- `delete_resource(resource_type, name, namespace)` → result
- `apply_yaml(yaml_content)` → result

All methods wrap errors into unified format via `utils/k8s_helper.py`.

### 3.6 Response Format

```json
// Success
{"code": 0, "message": "ok", "data": {...}}

// Error
{"code": 1001, "message": "资源不存在", "detail": "deployment.apps \"xxx\" not found"}
```

### 3.7 Confirmation & Safety

- All write operations (scale / rollback / delete / apply / user management) require secondary confirmation via frontend modal
- Delete: user must type the resource name into a confirmation field
- Scale / Rollback / Apply: confirm button click in modal
- Read operations (list / detail) have no confirmation

## 4. Frontend Design (Vue 3)

### 4.1 Page Structure

Single-page application with left sidebar navigation + right content area.

| Sidebar Menu | Content Page |
|-------------|--------------|
| 📊 Dashboard | Cluster overview: node count, namespace count, total pods, etc. |
| 📦 Resources → Namespace | Namespace list, click to view YAML |
| 📦 Resources → Deployment | Deployment table: name, namespace, replicas, image, actions |
| 📦 Resources → Pod | Pod table: name, namespace, status, node, actions |
| 📦 Resources → Service | Service table: name, namespace, type, ports, actions |
| 📦 Resources → Ingress | Ingress table: name, namespace, hosts, actions |
| 📦 Resources → DaemonSet | DaemonSet table |
| 📦 Resources → StatefulSet | StatefulSet table |
| 📦 Resources → ConfigMap | ConfigMap table |
| 📦 Resources → Secret | Secret table (values masked), click to view |
| 📦 Resources → RBAC | Sub-tabs: Role / RoleBinding / ClusterRole / ClusterRoleBinding / ServiceAccount |
| 🛠 Apply YAML | YAML editor (left) + result panel (right) |
| 👤 User Management | Admin only: user list, create user |
| 📋 Audit Log | Filterable audit log table |

### 4.2 Action Flow per Resource Row

- **YAML**: Open modal → show read-only YAML with syntax highlight + copy button
- **Scale**: Open modal → show current replicas → input target replicas → confirm → execute
- **Rollback**: Open modal → show revision history → select revision → confirm → execute
- **Delete**: Open modal → show resource info → type name to confirm → execute

### 4.3 Apply YAML Page

- Left panel: Monaco/YAML editor (dark theme, syntax highlight, line numbers)
- Right panel: Apply button + result display (success green / error red)
- Clear button to reset editor

### 4.4 Error Display

- API errors shown as toast notifications at top-right
- Form validation errors inline
- K8s API errors rendered with `message` visible prominently, `detail` in collapsible section for debugging

## 5. Deployment (prd namespace)

Each component gets:
- **Deployment** with resource limits
- **Service** (ClusterIP for Django, ClusterIP for Vue Nginx)
- **Ingress** rule: `/api/*` → Django, `/` → Vue
- **ServiceAccount** with ClusterRole for full cluster access
- **Secret** for Django SECRET_KEY, DB credentials
- **ConfigMap** for Django settings (DB host, Redis host, DEBUG=false)

MySQL/Redis connection: Django connects to `mysql.database.svc:3306` and `redis.database.svc:6379` using existing credentials from `database` namespace secrets.

## 6. Scope Boundaries

**In scope:**
- Resource listing, YAML viewing, scale, rollback, delete, apply
- User management (admin creates users, self password change)
- Token auth with blacklist logout
- Audit logging for all write operations
- Unified error handling
- In-cluster deployment

**Out of scope:**
- Multi-cluster management
- WebSocket / real-time updates
- Resource monitoring metrics / graphs
- CronJob / Job management (can be added later)
- Helm chart integration
- CI/CD pipeline integration

## 7. Self-Review Notes

- All API endpoints use POST with JSON body — no resource identifiers in URI
- GET requests are not logged to audit
- Delete operations must log resource_name in audit_log
- YAML viewing is read-only; editing is only through Apply page — these are intentionally separated
- Password has no expiry policy
