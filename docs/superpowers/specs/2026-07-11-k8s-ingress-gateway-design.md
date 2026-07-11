# K8s Ingress 网关体系设计文档

> **状态**: 待用户确认修改 | **日期**: 2026-07-11 | **集群**: Docker Desktop K8s v1.34.3

---

## 1. 架构总览

```
互联网/本地浏览器 (myapp.local)
    │
    ▼
┌─ 本地 OpenResty (127.0.0.1:80) ─────────────────────┐
│  • Lua 限流 (resty.limit.req / resty.limit.conn)     │
│  • Lua Auth (JWT 验证 / HMAC / 自定义)                │
│  • SSL 终止                                          │
│  • proxy_pass → 127.0.0.1:30000                      │
└──────────────────────────────────────────────────────┘
    │
    ▼
┌─ NodePort :30000 ─┐
│  ingress-nginx     │
│  Service           │  (ClusterIP + NodePort)
└────────────────────┘
    │
    ▼
┌─ DaemonSet: ingress-nginx-controller ────────────────┐
│  namespace: ingress-nginx                            │
│  image: registry.k8s.io/ingress-nginx/controller     │
│  leader-election (LeaderRole + LeaderRoleBinding)     │
│  TCP/UDP ConfigMap 映射                               │
└──────────────────────────────────────────────────────┘
    │
    ▼
┌─ Namespace: prd ─────────────────────────────────────┐
│  ┌ Ingress (host: myapp.local) ────────────────────┐ │
│  │  → Service (ClusterIP, port 80)                 │ │
│  │     → Deployment (业务 Pod, 副本数: 2)          │ │
│  └─────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

---

## 2. 命名空间设计

| Namespace | 用途 |
|-----------|------|
| `ingress-nginx` | Ingress Controller 专属空间，RBAC + Config 都在此 |
| `prd` | 生产业务空间，Ingress → Service → Deployment 完整链路 |
| `stg` | 测试业务空间，Ingress → Service → Deployment 完整链路 |

---

## 3. RBAC 安全模型

```
ServiceAccount: ingress-nginx (ns: ingress-nginx)
    │
    ├─ Role: ingress-nginx ──────── 当前 namespace 权限
    │   ├─ Resources: configmaps, endpoints, pods, secrets, ingresses, services, events
    │   └─ Verbs: get, list, watch (只读)
    │   └─ RoleBinding: ingress-nginx → sa: ingress-nginx
    │
    └─ ClusterRole: ingress-nginx-leader ── 集群级 leader 选举
        ├─ Resource: configmaps (resourceNames: [ingress-nginx-leader])
        └─ Verbs: get, update
        └─ ClusterRoleBinding: ingress-nginx-leader → sa: ingress-nginx
```

---

## 4. 资源清单

### 4.1 基础设施层

| 资源 | 名称 | Namespace | 说明 |
|------|------|-----------|------|
| Namespace | `ingress-nginx` | - | Controller 命名空间 |
| Namespace | `prd` | - | 生产业务命名空间 |
| ServiceAccount | `ingress-nginx` | ingress-nginx | Controller 身份 |
| Role | `ingress-nginx` | ingress-nginx | 资源访问权限 |
| RoleBinding | `ingress-nginx` | ingress-nginx | 绑定 Role → SA |
| ClusterRole | `ingress-nginx-leader` | - | Leader 选举权限 |
| ClusterRoleBinding | `ingress-nginx-leader` | - | 绑定 LeaderRole → SA |

### 4.2 配置层

| 资源 | 名称 | Namespace | 说明 |
|------|------|-----------|------|
| ConfigMap | `ingress-nginx-controller` | ingress-nginx | 主配置 (日志格式、超时、proxy-buffer 等) |
| ConfigMap | `tcp-services` | ingress-nginx | TCP 端口映射 (外部端口 → namespace/service:port) |
| ConfigMap | `udp-services` | ingress-nginx | UDP 端口映射 (外部端口 → namespace/service:port) |

### 4.3 密钥层

| 资源 | 名称 | Namespace | 说明 |
|------|------|-----------|------|
| Secret | `docker-registry` | prd | Docker 私有仓库拉取凭证 (imagePullSecrets) |
| Secret | `git-credentials` | prd | Git 仓库访问凭证 (供 CI/CD 工具使用) |

### 4.4 核心组件层

| 资源 | 名称 | Namespace | 说明 |
|------|------|-----------|------|
| DaemonSet | `ingress-nginx-controller` | ingress-nginx | 每个节点一个 Controller Pod |
| Service | `ingress-nginx-controller` | ingress-nginx | ClusterIP + NodePort(:30000) |

### 4.5 业务演示层 (prd namespace)

| 资源 | 名称 | Namespace | 说明 |
|------|------|-----------|------|
| Deployment | `prd-app` | prd | 业务容器 (nginx:latest, replicas: 2) |
| Service | `prd-app` | prd | ClusterIP, port 80 |
| Ingress | `prd-app` | prd | host: myapp.local → prd-app:80 |

---

## 5. 关键配置说明

### 5.1 ConfigMap: ingress-nginx-controller

```yaml
data:
  # 日志格式设置为 JSON，便于后续 ELK/Loki 采集
  log-format-upstream: '{"time":"$time_iso8601","remote_addr":"$remote_addr",...}'

  # proxy 超时
  proxy-connect-timeout: "15"
  proxy-read-timeout: "600"
  proxy-send-timeout: "600"

  # 允许的最大 body 大小
  proxy-body-size: "64m"

  # 启用 SSL 透传 (如果 OpenResty 已做终止)
  use-forwarded-headers: "true"
  compute-full-forward-for: "true"
```

### 5.2 ConfigMap: tcp-services

```yaml
data:
  "5432": "prd/postgres-service:5432"   # 示例: TCP 5432 → postgres
```

### 5.3 ConfigMap: udp-services

```yaml
data:
  "53": "kube-system/kube-dns:53"       # 示例: UDP DNS
```

---

## 6. 流量链路验证

```bash
# 1. 验证 Ingress Controller NodePort
curl -H "Host: myapp.local" http://127.0.0.1:30000/
# 期望 → 200 OK (nginx 欢迎页)

# 2. 验证 prd-app 直接可达
kubectl -n prd port-forward svc/prd-app 8080:80
curl http://localhost:8080/
# 期望 → 200 OK

# 3. 验证 Ingress 路由通过 Controller
kubectl -n ingress-nginx port-forward daemonset/ingress-nginx-controller 8888:80
curl -H "Host: myapp.local" http://localhost:8888/
# 期望 → 200 OK

# 4. 完整链路 (OpenResty 安装后)
curl -H "Host: myapp.local" http://127.0.0.1/
# OpenResty → :30000 → Controller → prd-app
```

---

## 7. 文件结构

部署时按以下顺序 apply：

```
deploy/
├── 01-namespaces.yaml              # ingress-nginx + prd
├── 02-rbac.yaml                    # SA + Role + RoleBinding + ClusterRole + ClusterRoleBinding
├── 03-configmaps.yaml              # controller config + tcp-services + udp-services
├── 04-secrets.yaml                 # docker-registry + git-credentials
├── 05-daemonset.yaml               # ingress-nginx-controller DaemonSet
├── 06-service.yaml                 # NodePort :30000
├── 07-prd-app.yaml                 # Deployment + Service + Ingress
└── openresty/
    └── nginx.conf                  # OpenResty 配置 (Lua 限流 + Auth + proxy_pass)
```

---

## 8. 不在范围内的内容

- OpenResty 的具体安装和 Lua 脚本编写（后续单独设计）
- HTTPS 证书管理 (cert-manager，后续补充)
- 监控/Prometheus 采集
- 日志采集 (ELK/Loki)
