<!--
  PROJECT-CONTEXT.md — SINGLE-FILE ENTRY POINT
  用途: 每次启动只需读这一个文件，无需遍历项目或阅读其他文档
  更新: 2026-07-21 — Logging 模块重构 (Filebeat + Kafka + Fluentd)
  版本: v6 — ELK + Kafka + Prometheus + Console
  当前 commit: working tree (logging redesign)
-->

# ☸️ K8s CICD Console — 项目总入口 (SINGLE FILE)

> **🤖 AI 指令**: 启动后先读完本文件，然后直接跳到 [九、NEXT-START](#九next-start) 继续上次未完成的工作。

---

## 一、项目速览

| 维度 | 说明 |
|------|------|
| **名称** | K8s Management Console (k8s_cicd) |
| **定位** | 基于 Django + Vue 的 K8s 集群管理 Web 控制台 |
| **根路径** | `D:\project\k8s_cicd\k8s_cicd` |
| **部署脚本** | Git Bash (MINGW64)，不要在 WSL 或 CMD 中执行 |

## 二、技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3 + Vite + Vue Router 4 + Pinia 2 + Axios + CodeMirror 6 |
| 后端 | Python 3.12 + Django 5.2 + DRF 3.16 + Gunicorn 4 workers |
| 数据库 | MySQL 8.0 + Redis 7 (database namespace) |
| K8s SDK | kubernetes-client/python 34.x，14 种资源类型 |
| K8s | Docker Desktop K8s 1.34 + ingress-nginx v1.11.3 |
| 日志 | RotatingFileHandler → emptyDir → Filebeat sidecar → Kafka 3.7 → Fluentd → ES 7.17 → Kibana |
| 监控 | Prometheus v2.53.3 + Grafana 11.3.1 + Node Exporter + Alertmanager |
| 网关 | Docker nginx:latest 容器 (宿主机 9001 → K8s NodePort 30000) |

## 三、日志采集架构 (v6, 当前)

```
+-------------- Pod ---------------+
|  django container                 |
|  RotatingFileHandler → JSON 格式  |
|  /shared/logs/{SERVICE}.json.log  |
|  (50MB x 3, emptyDir)            |
|  ================================= |
|  filebeat sidecar (8.15.0)       |
|  tail *.json.log → Kafka          |
+--------------|--------------------+
               | logs.{SERVICE_NAME}
    +----------v----------+
    |  Kafka 3.7 (Kraft)   |
    |  StatefulSet x 1     |
    |  auto.create.topics  |
    +----------|-----------+
               |
    +----------v-----------+
    |  Fluentd Deployment  |
    |  rdkafka2 → ES       |
    |  logstash_format     |
    +----------|-----------+
               | k8s-YYYY.MM.DD
    +----------v-----------+
    |  Elasticsearch 7.17  |
    |  → Kibana            |
    +----------------------+
```

## 四、目录结构

```
k8s_cicd/
├── readme.md                     ← 完整项目说明
├── PROJECT-CONTEXT.md            ← 本文件
│
├── backend/
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── manage.py
│   ├── k8s_console/
│   │   ├── settings.py           ← LOGGING (FileHandler+JSON+request_id)
│   │   ├── settings_dev.py       ← 本地开发覆盖
│   │   ├── logging_filters.py    ← RequestIDFilter (thread_local)
│   │   ├── middleware.py          ← RequestIDMiddleware + Audit + Token
│   │   └── urls.py
│   └── apps/
│       ├── auth_app/             ← 认证 + 用户管理
│       ├── resources/            ← K8s 资源 CRUD
│       ├── clusters/             ← 多集群管理
│       ├── deploy/               ← CI/CD 部署
│       ├── audit/                ← 审计日志
│       ├── logging_api/          ← ES 日志搜索 API
│       ├── monitoring/           ← K8s 集群指标 API
│       └── observability/        ← 统一可观测性 + metrics export
│
├── frontend/
│   ├── package.json
│   ├── Dockerfile.local
│   └── src/
│       ├── router/index.js       ← 11 页路由
│       ├── App.vue
│       ├── components/
│       │   └── AppSidebar.vue    ← 侧边栏 (日志浏览/集群指标)
│       └── views/
│           ├── DashboardPage.vue         ← 仪表盘 + Kibana/Grafana/Prometheus 跳转
│           ├── ResourceListPage.vue
│           ├── ApplyYamlPage.vue
│           ├── ClusterManagementPage.vue
│           ├── DeployManagementPage.vue
│           ├── UserManagementPage.vue
│           ├── AuditLogPage.vue
│           ├── LogExplorerPage.vue       ← ES 日志浏览
│           ├── MetricsDashboardPage.vue  ← 集群指标仪表盘
│           └── LoginPage.vue
│
├── deploy/
│   ├── deploy-all.sh                    ← 一键部署 8 步
│   ├── clean-all.sh                     ← 一键清理
│   ├── verify-monitoring.sh             ← ELK+Kafka+Prometheus 健康检查
│   ├── console/                         ← Console 应用
│   │   ├── 03-configmap.yaml            ← ELASTICSEARCH_URL / PROMETHEUS_URL → prd.svc
│   │   ├── 05-backend.yaml              ← Backend + Filebeat sidecar + emptyDir
│   │   ├── 06-frontend.yaml
│   │   └── 07-ingress.yaml
│   ├── database/                        ← MySQL + Redis
│   ├── ingress-nginx/                   ← Ingress Controller (NodePort 30000)
│   ├── logging/                         ← ELK+Kafka (部署到 prd)
│   │   ├── 02-elasticsearch.yaml        ← ES 7.17 StatefulSet
│   │   ├── 04-kibana.yaml               ← Kibana Deployment
│   │   ├── 05-kibana-ingress.yaml       ← Kibana Ingress
│   │   ├── 06-kafka.yaml                ← Kafka 3.7 StatefulSet (Kraft)
│   │   ├── 07-filebeat-config.yaml      ← Filebeat ConfigMap
│   │   └── 08-fluentd-kafka-consumer.yaml ← Fluentd Deployment (Kafka→ES)
│   ├── monitoring/                      ← Prometheus+Grafana (部署到 prd)
│   ├── gateway/                         ← nginx 本地网关 (9001→30000)
│   └── demo/
│
├── docs/
│   ├── HANDOFF-ELK-PROMETHEUS-v4.md     ← 最新交接文档
│   ├── final_delivery_v4.md             ← 最新交付报告
│   ├── logging-template.md              ← Django 日志配置模板
│   ├── cicd-deploy.md
│   ├── codex多agents说明.md
│   ├── e2e-test-conditions.md
│   ├── K8s集群使用指南.md
│   ├── 多集群添加教程.md
│   ├── 数据库部署指南.md
│   └── 本地网关部署指南.md
│
└── builder/                             ← CI/CD Builder 服务 (宿主机端口 9008)
```

## 五、当前状态

### 代码层 — Logging 模块重构 (2026-07-21)
- [x] **旧架构废弃**: stdout→CRI→Fluentd DaemonSet → 改为 Filebeat sidecar + Kafka
- [x] **后端日志**: RotatingFileHandler → JSON → /shared/logs/*.json.log (emptyDir)
- [x] **request_id 追踪**: RequestIDMiddleware + thread_local filter，全链路传递
- [x] **Kafka 解耦**: 每个服务一个 topic `logs.{SERVICE_NAME}`
- [x] **Fluentd 简化**: DaemonSet → Deployment，从 Kafka 消费而非读宿主机文件
- [x] **settings.py**: 4 个 bug 修复 (LOG_DIR 未定义、MIDDLEWARE 损坏、JSON 格式、f-string 引号)
- [x] **文档清理**: docs/ 删除 5 个旧版 handoff/final_delivery/PRD，保留 10 个核心文档
- [x] **readme.md**: ELK 表格、项目树、架构说明全部更新到新架构
- [x] **deploy-*.sh**: deploy-all/clean-all/verify-monitoring 全部同步

### 待部署验证
- [ ] `bash deploy/deploy_one_by_one/deploy-all.sh --clean` 端到端部署
- [ ] Kibana 确认 `logs.k8s-console-backend` topic 数据写入 ES
- [ ] Filebeat sidecar 确认存在 (Backend Pod 应有 2 个容器)
- [ ] Prometheus targets 全部 UP

### 技术债务
- [ ] Vue 前端日志采集 (模板已预留，暂未实现)
- [ ] AlertManager 通知渠道
- [ ] ES 多节点 HA
- [ ] 新 Django 服务按 `logging-template.md` 模板接入

## 六、访问地址

```
127.0.0.1 k8s-cicd.daiyi.local.com
127.0.0.1 kibana.logging.local
127.0.0.1 grafana.monitoring.local
127.0.0.1 prometheus.monitoring.local
```

| 组件 | URL | 凭据 |
|------|-----|------|
| Console | `http://k8s-cicd.daiyi.local.com:9001` | admin / 见启动日志 |
| Kibana | `http://kibana.logging.local` | 无 |
| Grafana | `http://grafana.monitoring.local` | admin / admin |
| Prometheus | `kubectl port-forward -n prd svc/prometheus 9090:9090` | 无 |

## 七、常用命令

```bash
# ⚠️ Git Bash 中执行
export KUBECONFIG=deploy/kubeconfigs/docker-desktop.yaml

# 部署（组件化入口：deploy/deploy_one_by_one/）
bash deploy/deploy_one_by_one/deploy-all.sh              # 完整部署 8 步
bash deploy/deploy_one_by_one/deploy-all.sh --clean      # 清理后重新部署
bash deploy/deploy_one_by_one/deploy-all.sh --skip-build # 跳过镜像构建

# 清理
bash deploy/deploy_one_by_one/clean-all.sh

# 验证
bash deploy/verify-monitoring.sh       # ES + Kafka + Prometheus 全量检查
kubectl get all -n prd

# Kafka 检查
kubectl exec -n prd kafka-0 -- kafka-topics.sh --list --bootstrap-server localhost:9092
kubectl exec -n prd kafka-0 -- kafka-console-consumer.sh --topic logs.k8s-console-backend --bootstrap-server localhost:9092 --max-messages 3

# Filebeat sidecar 确认
kubectl get pods -n prd -l app=k8s-console-backend -o jsonpath=''{.items[*].spec.containers[*].name}''

# 查看 admin 密码
kubectl logs -n prd -l app=k8s-console-backend -c django | grep password
```

## 八、技术决策

| 决策 | 原因 |
|------|------|
| Filebeat 替代 Fluentd DaemonSet | sidecar 模式不依赖宿主机文件系统 (WSL 兼容) |
| Kafka 解耦 | 多 Pod 蓝绿部署时日志不混乱，消息持久化 72h |
| emptyDir (非 PVC) | 日志为临时数据，Pod 重启即丢弃 |
| 一个统一 JSON 文件 | 降低 sidecar 复杂度，filebeat 单 tail 入口 |
| RotatingFileHandler 50MB×3 | 防止磁盘满 |
| thread_local request_id | 多线程安全，一次请求一个 ID 全链路追踪 |
| `auto.create.topics.enable=true` | 新服务上线时自动创建 topic，无需手动 |
| ES 单节点 + 512m heap | Docker Desktop 资源限制 |
| 全部 ClusterIP + ingress-nginx | 统一 NodePort 30000 暴露 |
| deploy 脚本用 Git Bash | node_modules 为 Windows 原生模块 |

## 九、NEXT-START — 下次启动从这里开始

### 上次完成的工作

| 项 | 内容 |
|----|------|
| Logging 重构 | Filebeat sidecar + Kafka → Fluentd → ES (14 个文件变更) |
| Bug 修复 | settings.py: LOG_DIR 未定义、MIDDLEWARE 损坏、JSON 双花括号、f-string 引号 |
| 文档清理 | docs/ 删除 5 个旧版，保留 10 个核心文档 |
| 脚本同步 | deploy-all.sh、clean-all.sh、verify-monitoring.sh 全部更新 |
| PROJECT-CONTEXT | 更新至 v6 |

### 下次继续 — 部署验证

```bash
# 1. 端到端部署
bash deploy/deploy_one_by_one/deploy-all.sh --clean

# 2. 健康检查
bash deploy/verify-monitoring.sh

# 3. 浏览器验证
# Console: http://k8s-cicd.daiyi.local.com:9001
# Kibana:  http://kibana.logging.local → Discover → k8s-* 索引
# Grafana: http://grafana.monitoring.local (admin/admin)
```

### 参考文档 (仅在必要时阅读)

| 目的 | 文件 |
|------|------|
| 最新交接 | [docs/HANDOFF-ELK-PROMETHEUS-v4.md](D:/project/k8s_cicd/k8s_cicd/docs/HANDOFF-ELK-PROMETHEUS-v4.md) |
| 交付报告 | [docs/final_delivery_v4.md](D:/project/k8s_cicd/k8s_cicd/docs/final_delivery_v4.md) |
| 日志模板 | [docs/logging-template.md](D:/project/k8s_cicd/k8s_cicd/docs/logging-template.md) |
| 项目详细说明 | [readme.md](D:/project/k8s_cicd/k8s_cicd/readme.md) |
*** End of File
