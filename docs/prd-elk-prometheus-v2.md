<!--
  PRD: ELK + Prometheus 增强 v2
  版本:     2.0
  日期:     2026-07-19
  作者:     root (acting PM)
  状态:     Approved
  前置文档: docs/HANDOFF-ELK-PROMETHEUS.md
-->

# PRD: ELK 日志采集 + Prometheus 监控增强 v2

## 1. 需求概述

在现有 ELK + Prometheus 基础部署之上，增强日志采集粒度和监控指标覆盖面，使 K8s Console 具备面向生产级组件的可观测能力。

### 范围边界

| 包含 | 不包含 |
|------|--------|
| Backend/Django 结构化 JSON 日志 → Fluentd → ES → Kibana | 分布式 Tracing (Jaeger/Zipkin) |
| MySQL/Redis/Nginx 日志采集 | 水平自动扩缩容 (HPA) |
| Prometheus CPU/mem/connection/log_error 指标 | 自定义业务指标大盘 |
| Django log_error counter metrics | 日志告警通知渠道（钉钉/飞书） |

---

## 2. 业务场景与用户故事

### 场景 1: 运维排查 Backend 500 错误
> 作为运维人员，当用户反馈 API 报错时，我需要能在 Kibana 中按时间范围 + 错误级别快速定位 Django 应用日志，看到完整 traceback，以便 5 分钟内定位根因。

### 场景 2: 数据库连接池耗尽告警
> 作为 SRE，当 MySQL 连接数接近上限时，我需要在 Grafana 看到实时连接数曲线，并在超过阈值时收到 Prometheus 告警，避免服务降级。

### 场景 3: 日志错误率监控
> 作为开发负责人，我需要看到每分钟 Django ERROR 级别日志数量的时序曲线，当错误率突增时触发告警以便及时介入。

### 场景 4: 组件健康一览
> 作为运维人员，打开 Console 前端即能看到 ES/Prometheus/MySQL/Redis/Nginx 的连通性状态和基本资源指标。

---

## 3. 需求增量明细（对比 v1 已有基础）

### 3.1 Fluentd 日志采集增强

| 组件 | v1 状态 | v2 增量 |
|------|---------|---------|
| Django Backend | 仅采集 stdout（JSON 解析+多行合并已做） | **增加**: 错误级别统计 tag → ES `k8s-backend-error-*` 索引 |
| MySQL | 未专项采集 | **新增**: slow-query log 采集 route → ES `k8s-mysql-*` 索引 |
| Redis | 未专项采集 | **新增**: Redis 日志采集 route → ES `k8s-redis-*` 索引 |
| Nginx | 未专项采集 | **新增**: access/error log 采集 route → ES `k8s-nginx-*` 索引 |

### 3.2 Django 结构化日志增强

| 维度 | v1 状态 | v2 增量 |
|------|---------|---------|
| 日志格式 | JSON formatter 已定义 | **增强**: 增加 `error_count` 字段用于 Prometheus counter |
| 日志级别 | INFO 级别 | **增强**: django.request logger → WARNING 独立输出 |
| Metrics 暴露 | django-prometheus middleware 已配置 | **新增**: 自定义 `django_log_errors_total` counter |
| 慢请求日志 | 无 | **新增**: 超过 1s 的 API 请求记录 WARNING + 耗时字段 |

### 3.3 Prometheus 监控增强

| 指标 | v1 状态 | v2 增量 |
|------|---------|---------|
| Node CPU/Memory | cAdvisor + node-exporter 已覆盖 | 无需变更 |
| Pod CPU/Memory | cAdvisor 已覆盖 | 无需变更 |
| **DB 连接数** | 无 | **新增**: 通过 MySQL exporter 或 Django DB backend metrics |
| **日志错误计数** | 无 | **新增**: `django_log_errors_total` counter → Prometheus |
| **HTTP 5xx 速率** | AlertManager 已有规则 | **增强**: 增加 namespace/pod 维度标签 |
| **应用连接池** | 无 | **新增**: Django DB connection pool 指标（若启用） |

### 3.4 前端页面增强

| 页面 | v1 状态 | v2 增量 |
|------|---------|---------|
| LogExplorerPage | 搜索/过滤/分页骨架已就位 | **完善**: ES 连接状态实时轮询，stats 图表联动，错误高亮 |
| MetricsDashboardPage | 指标卡片/节点柱状图/PromQL 骨架 | **完善**: CPU/Memory 实时刷新，DB 连接数卡片，Error Rate 折线图 |

### 3.5 已知问题修复

| ID | 描述 | 优先级 |
|----|------|--------|
| P1 | `deploy/console/03-configmap.yaml` 缺少 `ELASTICSEARCH_URL` / `PROMETHEUS_URL` | P0 |
| P2 | `deploy/deploy-all.sh` --help 文本遗漏 Step 5/6 | P2 |

---

## 4. 技术方案

### 4.1 数据流

```
┌──────────┐   JSON stdout   ┌──────────┐   forward   ┌───────────────┐   query   ┌──────────┐
│  Django  │ ───────────────→│ Fluentd  │ ──────────→ │ Elasticsearch │ ←─────── │  Kibana  │
│ Backend  │                 │ DaemonSet│             │   (Stateful)  │          │ (Deploy) │
└──────────┘                 └──────────┘             └───────────────┘          └──────────┘
                                    ↑
┌──────────┐   stdout/stderr       │
│  MySQL   │ ──────────────────────┘
└──────────┘
┌──────────┐
│  Redis   │ ──────────────────────┘
└──────────┘
┌──────────┐   access/error.log
│  Nginx   │ ──────────────────────┘
└──────────┘

┌──────────┐   /metrics    ┌─────────────┐   scrape   ┌──────────┐
│  Django  │ ←─────────── │ Prometheus   │ ─────────→ │ Grafana  │
│ (django- │              │ (Deployment) │            │ (Deploy) │
│prometheus)│             └─────────────┘            └──────────┘
└──────────┘                    ↑
┌──────────┐                    │
│  cAdvisor│ ───────────────────┘
└──────────┘
```

### 4.2 Fluentd 配置增强 (`deploy/logging/03-fluentd.yaml`)

**新增 ConfigMap 段**（在现有 `fluent.conf` 中追加）:

```xml
# ── MySQL slow-query logs ──
<match kubernetes.var.log.containers.**mysql**.log>
  @type relabel
  @label @MYSQL
</match>

<label @MYSQL>
  <match kubernetes.var.log.containers.**mysql**.log>
    @type elasticsearch
    host elasticsearch.logging.svc
    port 9200
    scheme http
    logstash_format true
    logstash_prefix k8s-mysql
    include_tag_key true
    type_name _doc
    flush_interval 5s
  </match>
</label>

# ── Redis logs ──
<match kubernetes.var.log.containers.**redis**.log>
  @type relabel
  @label @REDIS
</match>

<label @REDIS>
  <match kubernetes.var.log.containers.**redis**.log>
    @type elasticsearch
    host elasticsearch.logging.svc
    port 9200
    scheme http
    logstash_format true
    logstash_prefix k8s-redis
    include_tag_key true
    type_name _doc
    flush_interval 5s
  </match>
</label>

# ── Nginx logs (frontend + ingress) ──
<match kubernetes.var.log.containers.**nginx**.log>
  @type relabel
  @label @NGINX
</match>

<label @NGINX>
  <match kubernetes.var.log.containers.**nginx**.log>
    @type elasticsearch
    host elasticsearch.logging.svc
    port 9200
    scheme http
    logstash_format true
    logstash_prefix k8s-nginx
    include_tag_key true
    type_name _doc
    flush_interval 5s
  </match>
</label>

# ── Backend ERROR-only logs ──
<match kubernetes.var.log.containers.**k8s-console-backend**.log>
  @type copy
  <store>
    @type relabel
    @label @BACKEND  # existing route
  </store>
  <store>
    @type grep
    <regexp>
      key log
      pattern "ERROR|CRITICAL|Exception|Traceback"
    </regexp>
    <store>
      @type relabel
      @label @BACKEND_ERRORS
    </store>
  </store>
</match>

<label @BACKEND_ERRORS>
  <match kubernetes.var.log.containers.**k8s-console-backend**.log>
    @type elasticsearch
    host elasticsearch.logging.svc
    port 9200
    scheme http
    logstash_format true
    logstash_prefix k8s-backend-error
    include_tag_key true
    type_name _doc
    flush_interval 5s
  </match>
</label>
```

### 4.3 Django 日志增强 (`backend/k8s_console/settings.py`)

**新增 handler + logger**:

```python
# 新增 — JSON 文件输出（供 Fluentd sidecar 采集）
"json_file": {
    "class": "logging.handlers.RotatingFileHandler",
    "filename": str(LOG_DIR / "api.json.log"),
    "maxBytes": 50 * 1024 * 1024,  # 50 MB
    "backupCount": 3,
    "formatter": "json",
},

# 新增 — django.request logger
"django.request": {
    "handlers": ["json_console", "json_file"],
    "level": "WARNING",
    "propagate": False,
},

# 新增 — 各组件 logger
"django.db.backends": {
    "handlers": ["console"],
    "level": "WARNING",
    "propagate": False,
},
```

**新增 custom metrics** (`backend/apps/observability/metrics.py`):

```python
from prometheus_client import Counter

django_log_errors_total = Counter(
    "django_log_errors_total",
    "Total number of ERROR-level log entries",
    ["logger", "module"],
)
```

### 4.4 Prometheus 配置增强 (`deploy/monitoring/02-prometheus.yaml`)

**新增告警规则**（追加到 `prometheus-rules` ConfigMap）:

```yaml
- alert: DatabaseConnectionHigh
  expr: django_db_connections_total > 80
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Database connections above 80"

- alert: HighLogErrorRate
  expr: rate(django_log_errors_total[5m]) > 2
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Log ERROR rate above 2/sec"
```

### 4.5 Frontend — LogExplorerPage 增强

| 功能 | 实现方式 |
|------|----------|
| ES status 实时轮询 | `setInterval` 每 30s 调用 `/api/observability/status` |
| 错误日志高亮 | 表格行根据 level/ERROR 关键字加红色背景 |
| Stats 联动 | 点击 stats 柱状图中某一项，自动填充 filter |
| 多索引搜索 | API 参数增加 `index` 字段：`k8s-*`, `k8s-backend-*`, `k8s-backend-error-*` |

### 4.6 Frontend — MetricsDashboardPage 增强

| 功能 | 实现方式 |
|------|----------|
| CPU/Memory 实时轮询 | 每 15s 查询 `container_cpu_usage_seconds_total` + `container_memory_working_set_bytes` |
| DB Connections 卡片 | 查询 `django_db_connections_total` |
| Error Rate 折线图 | 查询 `rate(django_log_errors_total[5m])` |
| API Status 指示灯 | 页面顶部 ES/Prometheus 健康状态点 |

---

## 5. 异常流程与兜底

| 场景 | 兜底策略 |
|------|----------|
| ES 不可达 | observability API 返回 `es_healthy: false`，前端显示红色状态点，日志搜索按钮置灰 |
| Prometheus 不可达 | metrics API 返回 503，前端指标卡片显示 `--` |
| Fluentd 采集延迟 | buffer 配置 `retry_forever true`，不丢日志；chunk 上限 8M |
| Django log 文件过大 | RotatingFileHandler 50MB × 3 个备份 = 150MB 上限 |

---

## 6. 验收标准

### 6.1 功能验收

- [ ] Kibana 中可搜索 `k8s-backend*` / `k8s-mysql*` / `k8s-redis*` / `k8s-nginx*` / `k8s-backend-error*` 索引
- [ ] Kibana 中 Backend ERROR 日志可显示完整 traceback
- [ ] Grafana 中 CPU/Memory 面板数据正常
- [ ] Grafana 中 `django_log_errors_total` 指标可查询
- [ ] Console 前端 `/logs` 页面可搜索/过滤/翻页日志
- [ ] Console 前端 `/metrics` 页面显示实时指标
- [ ] Prometheus AlertManager 中 `HighLogErrorRate` 规则已加载

### 6.2 非功能验收

- [ ] `npm run build` 前端构建成功
- [ ] `bash deploy/deploy-all.sh` 8 步流程无报错
- [ ] `bash deploy/verify-monitoring.sh` 健康检查全部通过
- [ ] `deploy/console/03-configmap.yaml` 包含 `ELASTICSEARCH_URL` 和 `PROMETHEUS_URL`

---

## 7. 交付物清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `docs/prd-elk-prometheus-v2.md` | 文档 | 本文档 |
| `deploy/logging/03-fluentd.yaml` | 变更 | Fluentd 增加 MySQL/Redis/Nginx/ERROR 路由 |
| `deploy/monitoring/02-prometheus.yaml` | 变更 | 增加 log_error + DB connection 告警规则 |
| `backend/k8s_console/settings.py` | 变更 | 增加 json_file handler, 组件 logger |
| `backend/apps/observability/metrics.py` | 新增 | 自定义 Prometheus counter |
| `deploy/console/03-configmap.yaml` | 变更 | 增加 ELASTICSEARCH_URL / PROMETHEUS_URL |
| `deploy/deploy-all.sh` | 变更 | --help 补全 |
| `frontend/src/views/LogExplorerPage.vue` | 变更 | 完善交互 |
| `frontend/src/views/MetricsDashboardPage.vue` | 变更 | 完善交互 |
| `readme.md` | 变更 | 更新部署说明 |
| `docs/final_delivery.md` | 新增 | 最终交付报告 |
*** End of File
