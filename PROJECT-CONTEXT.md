<!--
  PROJECT-CONTEXT.md — SINGLE-FILE ENTRY POINT
  用途: 每次启动只需读这一个文件，无需遍历项目或阅读其他文档
  更新: 2026-07-19 (night) — 全栈部署完成
  版本: v5 — ELK + Prometheus + Console 全部 Running
  当前 commit: ab44399
-->

# ☸️ K8s CICD Console — 项目总入口 (SINGLE FILE)

> **🤖 AI 指令**: 这是项目的唯一入口文件。启动后先读完本文件, 然后直接跳到 [九、NEXT-START](#九next-start) 继续上次未完成的工作。只有在 NEXT-START 明确要求时才需要阅读其他文档。

---

## 一、项目速览

| 维度 | 说明 |
|------|------|
| **名称** | K8s Management Console (k8s_cicd) |
| **定位** | 基于 Django + Vue 的 K8s 集群管理 Web 控制台 |
| **根路径** | `D:\project\k8s_cicd\k8s_cicd` |
| **部署脚本** | Git Bash (MINGW64), 不要在 WSL 或 CMD 中执行 |

## 二、技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3 + Vite + Vue Router 4 + Pinia 2 + Axios + CodeMirror 6 |
| 后端 | Python 3.12 + Django 5.2 + DRF 3.16 + Gunicorn 4 workers |
| 数据库 | MySQL 8.0 (持久) + Redis 7 (Token/缓存) |
| K8s SDK | kubernetes-client/python 34.x, 支持 14 种资源类型 |
| K8s 集群 | Docker Desktop K8s 1.34 + ingress-nginx v1.11.3 |
| 日志收集 | ELK — Elasticsearch 7.17 + Fluentd DaemonSet + Kibana 7.17 |
| 监控 | Prometheus v2.53.3 + Grafana 11.3.1 + Node Exporter + Alertmanager |
| 网关 | Docker nginx:latest 容器 (宿主机 9001 → K8s NodePort 30000) |

## 三、目录结构

```
k8s_cicd/
├── readme.md                  ← 完整项目说明
├── PROJECT-CONTEXT.md         ← 本文件 (总入口)
│
├── backend/
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── manage.py
│   ├── k8s_console/
│   │   ├── settings.py        ← Django 配置 (JSON日志/django-prometheus/logger)
│   │   └── urls.py            ← 主路由
│   └── apps/
│       ├── audit/             ← 审计日志
│       ├── auth_app/          ← 用户认证 (Token)
│       ├── clusters/          ← 多集群管理 + K8s CRUD
│       ├── deploy/            ← CI/CD 部署
│       ├── logging_api/       ← ES 日志搜索 API
│       ├── monitoring/        ← K8s 集群指标 API
│       ├── observability/     ← 统一可观测性 API + metrics export
│       └── resources/         ← K8s 资源管理
│
├── frontend/
│   ├── package.json
│   ├── Dockerfile.local
│   └── src/
│       ├── router/index.js    ← 路由 (11 页)
│       ├── App.vue            ← 主布局 (侧边栏)
│       ├── components/
│       │   └── AppSidebar.vue ← 侧边栏 (📜日志浏览 / 📈集群指标)
│       ├── views/
│       │   ├── DashboardPage.vue        ← 仪表盘 + 🔗外部工具跳转(Kibana/Grafana/Prometheus)
│       │   ├── ResourceListPage.vue     ← K8s 资源管理
│       │   ├── ApplyYamlPage.vue        ← YAML 部署
│       │   ├── ClusterManagementPage.vue← 多集群管理
│       │   ├── DeployManagementPage.vue ← CI/CD 部署
│       │   ├── UserManagementPage.vue   ← 用户管理 (admin only)
│       │   ├── AuditLogPage.vue         ← 审计日志 (admin only)
│       │   ├── LogExplorerPage.vue      ← ES 日志浏览 (轮询/错误高亮/索引选择)
│       │   ├── MetricsDashboardPage.vue ← 集群指标 (CPU/Mem/DB连接/错误率)
│       │   └── LoginPage.vue
│       ├── api/
│       │   └── observability.js ← ES/Prometheus API 客户端
│       └── stores/
│
├── deploy/
│   ├── deploy-all.sh          ← 一键部署 (8 步)
│   ├── clean-all.sh           ← 一键清理
│   ├── verify-monitoring.sh   ← ELK + Prometheus 健康检查
│   ├── kubeconfigs/
│   │   └── docker-desktop.yaml← kubectl 配置文件
│   ├── console/               ← Console 应用 (backend+frontend+ingress+configmap)
│   │   ├── 03-configmap.yaml  ← 含 ELASTICSEARCH_URL / PROMETHEUS_URL
│   │   ├── 05-backend.yaml
│   │   ├── 06-frontend.yaml
│   │   └── 07-ingress.yaml
│   ├── database/              ← MySQL + Redis
│   ├── ingress-nginx/         ← Ingress Controller (NodePort 30000)
│   ├── logging/               ← ELK (ES+Fluentd+Kibana) — 部署到 prd namespace
│   ├── monitoring/            ← Prometheus+Grafana+NodeExporter+Alertmanager — 部署到 prd
│   ├── gateway/               ← nginx 本地网关 (9001 → 30000)
│   └── demo/                  ← 示例应用
│
├── docs/
│   ├── HANDOFF-ELK-PROMETHEUS-v3.md   ← 最新交接文档
│   ├── final_delivery_v3.md           ← 最新交付报告
│   ├── prd-elk-prometheus-v3.md       ← 最新 PRD
│   ├── HANDOFF-ELK-PROMETHEUS.md      ← v1 交接 (参考)
│   ├── prd-elk-prometheus-v2.md       ← v2 PRD (参考)
│   ├── final_delivery.md              ← v2 交付报告 (参考)
│   ├── cicd-deploy.md                 ← CI/CD 部署指南
│   ├── codex多agents说明.md           ← 多 Agent 协作说明
│   ├── K8s集群使用指南.md
│   ├── 数据库部署指南.md
│   ├── 本地网关部署指南.md
│   └── 多集群添加教程.md
│
└── builder/                   ← CI/CD Builder 服务
```

## 四、当前状态

### 代码状态 (已完成)
- [x] **ELK + Prometheus v3 — Namespace 合并**: 全部 yaml 从 `logging`/`monitoring` → `prd` (16 个文件)
- [x] **Dashboard 跳转按钮**: DashboardPage.vue 新增 Kibana / Grafana / Prometheus 跳转卡片
- [x] **ConfigMap 环境变量**: ELASTICSEARCH_URL / PROMETHEUS_URL 指向 `prd.svc`
- [x] **脚本适配**: deploy-all.sh / clean-all.sh / verify-monitoring.sh
- [x] **前端构建**: `npm run build` — 119 modules, 0 errors

### K8s 部署状态 (2026-07-19 22:25 — 全部 Running)
| Namespace | 组件 | 状态 |
|-----------|------|------|
| prd | backend + frontend + ES + Fluentd + Kibana + Prometheus + Grafana + Node Exporter + Alertmanager | **全部 Running** |
| database | MySQL + Redis | Running |
| ingress-nginx | Ingress Controller (NodePort 30000) | Running |

### 待处理
- [x] **P0**: 运行部署脚本清理旧 namespace 并重新部署到 prd ✅
- [x] **P1**: Fluentd config 修复 (移除 relabel/unicode/简化配置)
- [x] **P1**: Backend settings.py `false` → `False` 修复
- [x] **P1**: Backend `urls.py` 空白文件修复
- [x] **P1**: `django-redis` 依赖添加到 requirements.txt
- [x] **P1**: Chrome 浏览器验证 Dashboard 跳转按钮 (4 Host 均 HTTP 200)
- [x] **P1**: Prometheus targets UP 验证 (console-backend 0.004s scrape)
- [x] **P1**: Kibana 索引 `k8s-*` 存在确认 (22,768 docs)
- [ ] **P2**: AlertManager 通知渠道 (钉钉/邮件)
- [ ] **P2**: ES 多节点 HA
- [ ] **P2**: Prometheus ingress 连通性修复 (当前 curl 返回 000)

## 五、访问地址

### hosts 配置
```
127.0.0.1 k8s-cicd.daiyi.local.com
127.0.0.1 kibana.logging.local
127.0.0.1 grafana.monitoring.local
127.0.0.1 prometheus.monitoring.local
```

### 组件 URL
| 组件 | URL | 凭据 |
|------|-----|------|
| Console | `http://k8s-cicd.daiyi.local.com:9001` | admin / 见启动日志 |
| Kibana | `http://kibana.logging.local` | 无 |
| Grafana | `http://grafana.monitoring.local` | admin / admin |
| Prometheus | `kubectl port-forward -n prd svc/prometheus 9090:9090` | 无 |

### 部署链路
```
用户浏览器 → :9001 → Docker nginx 网关 → host.docker.internal:30000
  → K8s ingress-nginx (NodePort) → Ingress 规则 (host 匹配)
  → /api → backend:8000    / → frontend:80
```

## 六、常用命令

```bash
# ⚠️ 以下命令需在 Git Bash 中执行
# kubectl 配置
export KUBECONFIG=deploy/kubeconfigs/docker-desktop.yaml

# 部署
bash deploy/deploy-all.sh              # 完整部署
bash deploy/deploy-all.sh --clean      # 先清理再部署
bash deploy/deploy-all.sh --skip-build # 跳过镜像构建

# 清理
bash deploy/clean-all.sh               # 清理所有

# 验证
bash deploy/verify-monitoring.sh       # ELK + Prometheus 健康检查
kubectl get all -n prd                 # 查看 prd 所有资源
kubectl get pods -A                    # 全部 Pod

# 前端
cd frontend && npm run build           # 构建
cd frontend && npm run dev             # 开发服务器

# 后端
cd backend && python manage.py runserver  # 开发服务器

# 查看 admin 密码
kubectl logs -n prd -l app=k8s-console-backend | grep password
```

## 七、技术决策

| 决策 | 原因 |
|------|------|
| ES 单节点 + 512m heap | Docker Desktop 资源限制 |
| 无 xpack security | 开发环境 |
| 全部 ClusterIP + ingress-nginx | 统一 NodePort 30000 暴露 |
| Fluentd `type_name _doc` | ES 7.x 兼容 |
| 部署在 `prd` namespace | 运维统一管理 |
| deploy 脚本用 Git Bash | node_modules 为 Windows 原生模块, WSL 内 rollup 报错 |
| JSON 日志 formatter | 结构化日志可被 Fluentd 解析 |
| `django-prometheus` | Django metrics 标准化导出 |

## 八、关键约束

1. **Shell 环境**: deploy 脚本必须用 Git Bash, 不可用 WSL
2. **kubectl**: 必须指定 `KUBECONFIG=deploy/kubeconfigs/docker-desktop.yaml`
3. **多 Agent 协作**: main 总控 → 产品PRD → 开发实现 → 测试验证 (仅 main 可 spawn)
4. **浏览器代理**: `*.daiyi.local.com` 需要绕过代理

## 九、NEXT-START — 下次启动从这里开始

### 当前会话快照

| 项 | 值 |
|----|-----|
| 最近 commit | `ab44399` — feat: 一键 trigger, builder 构建镜像, deploy 部署 |
| 工作空间修改 | `settings.py` (false→False), `urls.py` (空白→URLconf), `requirements.txt` (+django-redis), `deploy/logging/03-fluentd.yaml` (简化config), `PROJECT-CONTEXT.md` (v5) |
| 子 agent 状态 | 已全部清理, 无残留 agent |
| Gateway 容器 | `k8s-gateway` 运行中 (nginx:latest, port 9001) |

### 当前 K8s 状态 (2026-07-19 22:25)

```
NAMESPACE      POD                          STATUS
prd            alertmanager                 Running
prd            elasticsearch-0              Running
prd            fluentd                      Running  (config simplified)
prd            grafana                      Running
prd            k8s-console-backend          Running  (Gunicorn 4 workers)
prd            k8s-console-frontend         Running  (nginx)
prd            kibana                       Running
prd            node-exporter                Running
prd            prometheus                   Running
database       mysql-0                      Running
database       redis                        Running
ingress-nginx  ingress-nginx-controller     Running  (NodePort 30000)
```

### 代码层 (本次修复)

- [x] `settings.py`: `"propagate": false` → `"propagate": False` (Python bool)
- [x] `apps/observability/urls.py`: 空白文件 → 完整 URLconf (7 routes)
- [x] `requirements.txt`: 添加 `django-redis>=5.4,<5.5`
- [x] `deploy/logging/03-fluentd.yaml`: 简化 fluent.conf (移除 relabel/unicode, 简洁版)
- [x] 重建 backend Docker 镜像 3 次 (修复迭代)

### 下次启动 (部署已就绪, 直接浏览测试)

```bash
# 1. 确认 Gateway 运行
docker ps -a --filter name=k8s-gateway
# 若未运行:
export KUBECONFIG=deploy/kubeconfigs/docker-desktop.yaml
bash deploy/gateway/start.sh

# 2. 确认全部 Pod
kubectl get pods -n prd

# 3. 浏览器访问
# Console: http://k8s-cicd.daiyi.local.com:9001
# Kibana:  http://kibana.logging.local:9001
# Grafana: http://grafana.monitoring.local:9001
# Prometheus: http://prometheus.monitoring.local:9001 (可能需要 port-forward)
```

### 浏览器验证 (部署后)

| 检查项 | URL | 预期结果 |
|--------|-----|---------|
| Console 登录 | `http://k8s-cicd.daiyi.local.com:9001` | 正常登录 |
| Dashboard 跳转 | Dashboard 页 "外部工具" | Kibana/Grafana/Prometheus 卡片可点击 |
| Kibana | `http://kibana.logging.local` | 打开成功, 索引 `k8s-*` 存在 |
| Grafana | `http://grafana.monitoring.local` | admin/admin, datasource 已连接 |
| Prometheus targets | `kubectl port-forward -n prd svc/prometheus 9090:9090` | 全部 UP |
| /logs 页 | Console → 日志浏览 | 数据加载 |
| /metrics 页 | Console → 集群指标 | 数据加载 |

### 多 Agent 协作 (需新增功能时使用)

```
用户需求 → main (总控, 仅 main 可 spawn)
  ├── product_manager → PRD.md
  ├── dev_engineer    → 代码实现
  └── test_engineer   → 全量测试 → 缺陷报告
→ main 汇总 → final_delivery.md
```

### 参考文档 (仅在必要时阅读)

| 目的 | 文件 |
|------|------|
| 最新手交 | [HANDOFF-ELK-PROMETHEUS-v3.md](D:/project/k8s_cicd/k8s_cicd/docs/HANDOFF-ELK-PROMETHEUS-v3.md) |
| 交付报告 | [final_delivery_v3.md](D:/project/k8s_cicd/k8s_cicd/docs/final_delivery_v3.md) |
| PRD | [prd-elk-prometheus-v3.md](D:/project/k8s_cicd/k8s_cicd/docs/prd-elk-prometheus-v3.md) |
| 项目详细说明 | [readme.md](D:/project/k8s_cicd/k8s_cicd/readme.md) |
*** End of File
