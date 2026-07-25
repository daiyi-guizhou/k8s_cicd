<!--
  Generated: 2026-07-21
  Scope:    Logging module redesign — Filebeat sidecar + Kafka + Fluentd consumer
  Summary:  Replaced stdout→CRI→DaemonSet with RotatingFileHandler→emptyDir→Filebeat→Kafka→Fluentd
  Status:   Code & docs complete, pending deployment test
  Git:      working tree
-->

# 交接文档: Logging 模块重构 v4

## 本次完成工作

### 核心架构变更

```
旧: Django StreamHandler → stdout → containerd CRI → /var/log/containers/* → Fluentd DaemonSet → ES
新: Django RotatingFileHandler → /shared/logs/*.json.log (emptyDir) → Filebeat sidecar → Kafka → Fluentd Deployment → ES
```

**原因**:
- 旧方案依赖 containerd CRI 日志路径，WSL 环境下路径不透明
- Fluentd DaemonSet 需要宿主机 `hostPath` 挂载，增删节点时管理复杂
- 新方案: Kafka 解耦生产与消费，sidecar 模式不依赖宿主机文件系统

### 变更文件清单 (9+ 个文件)

#### 新增
| 文件 | 说明 |
|------|------|
| `backend/k8s_console/logging_filters.py` | RequestIDFilter + thread-local request_id |
| `backend/k8s_console/middleware.py` | RequestIDMiddleware (生成/传递 X-Request-ID) |
| `deploy/logging/06-kafka.yaml` | Kafka 3.7 StatefulSet (单节点, Kraft mode) |
| `deploy/logging/07-filebeat-config.yaml` | Filebeat ConfigMap (tail JSON → Kafka) |
| `deploy/logging/08-fluentd-kafka-consumer.yaml` | Fluentd Deployment (Kafka Consumer → ES) |
| `docs/logging-template.md` | Django 日志系统配置模板 |
| `docs/HANDOFF-ELK-PROMETHEUS-v4.md` | 本文档 |

#### 修改
| 文件 | 变更 |
|------|------|
| `backend/k8s_console/settings.py` | LOGGING 重构: FileHandler + JSON formatter + request_id filter + LOG_DIR 定义 |
| `deploy/console/05-backend.yaml` | 新增 emptyDir + Filebeat sidecar + SERVICE_NAME/LOG_DIR 环境变量 |
| `deploy/logging/03-fluentd.yaml` → `.disabled` | 旧 DaemonSet 禁用 |
| `deploy/deploy-all.sh` | Step 5 名称更新, --help 文本更新（现已组件化为 `deploy/deploy_one_by_one/deploy-all.sh`，原文件保留为 `deploy/deploy-all.sh.bak`） |
| `deploy/clean-all.sh` | 标题更新含 Kafka（现已组件化为 `deploy/deploy_one_by_one/clean-all.sh`，原文件保留为 `deploy/clean-all.sh.bak`） |
| `deploy/verify-monitoring.sh` | 新增 Kafka + Filebeat sidecar 检查 |
| `readme.md` | ELK 表格、项目树、日志收集架构全部更新 |
| `docs/final_delivery_v4.md` | 新增最终交付报告 |

## 架构详解

### 日志采集链路

```
┌────────────── Pod ───────────────┐
│   django container                │
│   RotatingFileHandler             │
│   → /shared/logs/{SERVICE}.json   │
│   (50MB × 3, JSON 格式)           │
│                                   │
│   ═══ emptyDir ═══════════════   │
│                                   │
│   filebeat container (sidecar)    │
│   tail *.json.log                 │
│   → Kafka topic: logs.{service}   │
└──────────────┬────────────────────┘
               │
    ┌──────────▼──────────┐
    │  Kafka (prd namespace)│
    │  auto.create.topics  │
    │  72h retention       │
    └──────────┬──────────┘
               │
    ┌──────────▼──────────┐
    │  Fluentd (Deployment) │
    │  rdkafka2 → ES       │
    │  logstash_format     │
    └──────────┬──────────┘
               │
    ┌──────────▼──────────┐
    │  Elasticsearch       │
    │  k8s-YYYY.MM.DD      │
    │  → Kibana            │
    └──────────────────────┘
```

### 关键设计决策

| 决策 | 原因 |
|------|------|
| Filebeat (非 fluent-bit) | 与 ES 生态一致, ARM/x86 通用 |
| 每个服务一个 Kafka topic | `logs.{SERVICE_NAME}`, 隔离 + 独立消费 |
| emptyDir (非 PVC) | 日志为临时数据, Pod 重启即丢弃 |
| 一个统一 JSON 文件 (非多文件) | 降低 sidecar 复杂度 |
| RotatingFileHandler | 50MB × 3, 防止磁盘满 |
| thread_local request_id | 多线程安全, 一次请求一个 ID |
| `json.keys_under_root: true` | Filebeat 把 JSON 字段直接提升到 ES document 顶层 |
| `partition.round_robin` | 多 Pod 场景下日志分布均匀 |

### 日志格式

```json
{
  "@timestamp": "2026-07-21T14:51:23Z",
  "time": "2026-07-21 14:51:23",
  "level": "INFO",
  "service": "k8s-console-backend",
  "request_id": "req-abc-123-def-456",
  "pod": "k8s-console-backend-7f6dbdb446-fpv4b",
  "logger": "api",
  "message": ">>> GET /api/users | params=...",
  "path": "/app/k8s_console/middleware.py",
  "lineno": 64
}
```

## 访问地址

```
Windows hosts:
127.0.0.1 k8s-cicd.daiyi.local.com
127.0.0.1 kibana.logging.local
127.0.0.1 grafana.monitoring.local
127.0.0.1 prometheus.monitoring.local
```

| 组件 | URL | 说明 |
|------|-----|------|
| Console | `http://k8s-cicd.daiyi.local.com:9001` | 主控制台 |
| Kibana | `http://kibana.logging.local` | 日志可视化 |
| Grafana | `http://grafana.monitoring.local` | admin/admin |
| Prometheus | `kubectl port-forward -n prd svc/prometheus 9090:9090` | 指标 |

## 模板复用

`docs/logging-template.md` 是完整的 Django 服务日志模板。新服务接入步骤:
1. 复制 `logging_filters.py` + `middleware.py` 的 RequestIDMiddleware
2. 替换 settings.py LOGGING 配置中的 `{SERVICE_NAME}`
3. deployment.yaml 加 emptyDir + Filebeat sidecar
4. 创建 Kafka topic: `logs.{SERVICE_NAME}`

## 下次继续

1. **部署验证**: `bash deploy/deploy_one_by_one/deploy-all.sh --clean`
2. **浏览器测试**: 确认 Kibana 可见 backend 日志, Grafana 数据正常
3. **前端日志**: Vue 前端暂未接入日志采集 (预留设计在模板文档中)
4. **多 Pod 时序**: Kafka `partition.round_robin` + `request_id` 已保证, 但多 Pod 精确时序需 Kafka message timestamp

## 项目信息

- **根目录**: `D:\project\k8s_cicd\k8s_cicd`
- **Shell**: Git Bash (`C:\Program Files\Git\bin\bash.exe`)
- **Kubectl config**: `D:\project\k8s_cicd\k8s_cicd\deploy\kubeconfigs\docker-desktop.yaml`
- **Namespace**: prd (所有资源统一)
- **K8s 版本**: v1.34.3 (Docker Desktop)

# k8s log 查看
进 Kibana → Stack Management → Index Patterns → 新建 k8s-* → Discover 即可按时间、level、service 等字段检索 backend 日志

