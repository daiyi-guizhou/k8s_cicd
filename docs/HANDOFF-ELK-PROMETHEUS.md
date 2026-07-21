<!--
  Generated: 2026-07-19
  Scope:    ELK 日志收集 + Prometheus 监控 集成到 K8s CICD Console
  Status:   主体完成，3 项收尾待处理
-->

# 交接文档: ELK + Prometheus 集成

## 项目背景

K8s 管理控制台（Django 5 + Vue 3，Docker Desktop K8s）。项目根 `D:\project\k8s_cicd\k8s_cicd`，部署脚本使用 Git Bash 执行，节点模块 Windows 原生不可在 WSL 运行。

---

## 已完成工作

### 1. K8s 部署 Manifest

#### ELK 日志栈 — `deploy/logging/`（5 个文件）

| 文件 | 内容 | 关键参数 |
|------|------|---------|
| `01-namespace.yaml` | `logging` 命名空间 | — |
| `02-elasticsearch.yaml` | ES 7.17.27 StatefulSet | 单节点, 10Gi PVC, heap 512m, Svc `elasticsearch.logging.svc:9200` |
| `03-fluentd.yaml` | Fluentd DaemonSet + RBAC | ClusterRole `fluentd`, 挂载 `/var/log` + `/var/lib/docker/containers`, 输出到 ES |
| `04-kibana.yaml` | Kibana 7.17.27 Deployment | Svc `kibana.logging.svc:5601` |
| `05-kibana-ingress.yaml` | Ingress | `kibana.logging.local` → ingress-nginx |

#### Prometheus 监控栈 — `deploy/monitoring/`（8 个文件）

| 文件 | 内容 | 关键参数 |
|------|------|---------|
| `01-namespace.yaml` | `monitoring` 命名空间 | — |
| `02-prometheus.yaml` | Prometheus v2.53.3 + RBAC | ClusterRole `prometheus`, 6 个 scrape job, 10Gi PVC, 15d retention |
| `03-node-exporter.yaml` | Node Exporter v1.8.2 DaemonSet | hostNetwork |
| `04-grafana.yaml` | Grafana 11.3.1 Deployment | 预配置 Prometheus datasource, 2Gi PVC |
| `05-grafana-dashboards.yaml` | ConfigMap | dashboard provider + K8s Cluster Overview JSON |
| `05-grafana-ingress.yaml` | Ingress | `grafana.monitoring.local` |
| `06-alertmanager-config.yaml` | AlertManager 配置 | 8 条告警规则 |
| `06-prometheus-ingress.yaml` | Ingress | `prometheus.monitoring.local` |
| `07-alertmanager.yaml` | AlertManager Deployment | — |

### 2. 后端 — 3 个 Django App

| App | 路径 | 职责 |
|-----|------|------|
| `logging_api` | `backend/apps/logging_api/` | ES 日志搜索 / 聚合 / 统计 API |
| `monitoring` | `backend/apps/monitoring/` | K8s 集群概览、节点指标、Pod 资源 API |
| `observability` | `backend/apps/observability/` | 统一 observability API（logs + metrics + labels + health check） |

**Settings 修改** (`backend/k8s_console/settings.py`):
- 注册 `django-prometheus` middleware
- JSON 日志 formatter
- 3 个新 app 注册到 `INSTALLED_APPS`

**URL 路由** (`backend/k8s_console/urls.py`):
- `/metrics` 端点（django-prometheus）
- `/api/logs/` → logging_api
- `/api/monitoring/` → monitoring
- `/api/observability/` → observability

**依赖** (`backend/requirements.txt`):
- `django-prometheus>=2.3,<2.4`
- `requests>=2.31,<2.33`

### 3. 前端 — 2 个新页面

| 文件 | 功能 |
|------|------|
| `frontend/src/views/LogExplorerPage.vue` | ES 日志搜索 / 过滤 / 分页 / 图表 |
| `frontend/src/views/MetricsDashboardPage.vue` | 集群指标卡片、节点 CPU/Memory 柱状图、自定义 PromQL |
| `frontend/src/api/observability.js` | API 客户端（6 个方法） |
| `frontend/src/router/index.js` | `/logs` → LogExplorer, `/metrics` → MetricsDashboard |
| `frontend/src/components/AppSidebar.vue` | 侧栏新增 📜 日志浏览 / 📈 集群指标 |

前端构建已通过: `npm run build` 成功（含新页面共 11 页）。

### 4. 部署脚本

| 文件 | 变更 |
|------|------|
| `deploy/deploy-all.sh` | 新增 Step 5 (ELK) + Step 6 (Monitoring)，总 8 步 |
| `deploy/clean-all.sh` | 新增 `logging` / `monitoring` namespace 清理 + `fluentd` / `prometheus` ClusterRole/ClusterRoleBinding 清理 |
| `deploy/verify-monitoring.sh` | 新增 ELK + Prometheus 健康检查脚本 |

### 5. Console YAML 补充

- `deploy/console/05-backend.yaml` — Backend Service 增加 `prometheus.io/scrape` + `prometheus.io/path: /api/health` 注解
- `deploy/console/06-frontend.yaml` — Frontend Service 增加 Prometheus scrape 注解

### 6. 文档

- `readme.md` — 新增 logging/monitoring 章节和项目树

---

## 关键技术决策

| 决策 | 原因 |
|------|------|
| ES 单节点模式 | Docker Desktop 资源有限，不需要集群 |
| 无 xpack security | 开发环境，无需认证 |
| ES heap 512m | 适配 Docker Desktop 内存限制 |
| Fluentd `type_name _doc` | ES 7.x 兼容性 |
| 全部 ClusterIP + ingress-nginx | 统一通过 NodePort 30000 暴露 |
| `django-prometheus` 替换默认 backend | 标准化 metrics 导出 |
| Console Backend 需 ConfigMap 注入 `ELASTICSEARCH_URL` / `PROMETHEUS_URL` | 后端 observability app 需要连接 ES 和 Prometheus |

---

## 访问地址（需配置 hosts）

```
127.0.0.1 k8s-cicd.daiyi.local.com
127.0.0.1 kibana.logging.local
127.0.0.1 grafana.monitoring.local
127.0.0.1 prometheus.monitoring.local
```

| 组件 | URL | 凭据 |
|------|-----|------|
| Console | `http://k8s-cicd.daiyi.local.com:9001` | Console admin |
| Kibana | `http://kibana.logging.local` | 无 |
| Grafana | `http://grafana.monitoring.local` | `admin` / `admin` |
| Prometheus | `kubectl port-forward -n monitoring svc/prometheus 9090:9090` | 无 |

---

## 待处理 (3 项)

### [P1] **ConfigMap 缺少环境变量** — `deploy/console/03-configmap.yaml`

后端 observability app 依赖 `ELASTICSEARCH_URL` 和 `PROMETHEUS_URL`，当前 ConfigMap 未包含。

**修复**: 在 `deploy/console/03-configmap.yaml` 的 `data` 段追加:

```yaml
  ELASTICSEARCH_URL: "http://elasticsearch.logging.svc:9200"
  PROMETHEUS_URL: "http://prometheus.monitoring.svc:9090"
```

### [P2] **Help 文本遗漏** — `deploy/deploy-all.sh` 第 37–43 行

`--help` heredoc 列出了 Step 1–4 和 7–8，但跳过了 Step 5 (ELK) 和 Step 6 (Monitoring)。脚本主体已正确包含这两步，仅 help 输出需补齐。

**修复**: 在 `--help` 的流程段，Step 4 之后插入:

```
  Step 5/8: 部署日志收集 (ELK — Elasticsearch + Fluentd + Kibana)
  Step 6/8: 部署监控 (Prometheus + Node Exporter + Grafana)
```

### [P3] **端到端部署测试**

运行完整 8 步部署:

```bash
bash deploy/deploy-all.sh
```

验证清单:
- [ ] 所有 Pod Running（`kubectl get pods -A`）
- [ ] Console 登录正常（`http://k8s-cicd.daiyi.local.com:9001`）
- [ ] Kibana 可访问（`http://kibana.logging.local`）
- [ ] Grafana 可访问 + datasource 已连接（`http://grafana.monitoring.local`）
- [ ] Prometheus targets 全部 UP（`kubectl port-forward -n monitoring svc/prometheus 9090:9090` → Targets 页）
- [ ] 前端日志浏览页 `/logs` 可加载
- [ ] 前端指标页 `/metrics` 可加载

---

## 下次继续时

1. 先执行 P1 和 P2 的修复（2 个文件小改动）
2. 然后执行 P3 端到端测试
3. 如遇问题，参考 `deploy/verify-monitoring.sh` 逐组件排查

**项目根**: `D:\project\k8s_cicd\k8s_cicd`
**执行 shell**: Git Bash（`C:\Program Files\Git\bin\bash.exe`）
*** End of File
