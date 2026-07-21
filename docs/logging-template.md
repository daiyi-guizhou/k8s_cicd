# Django + Vue 日志系统模板：FileHandler → emptyDir → filebeat → Kafka → Fluentd → ES

## 架构全景

┌──────────────── Pod ──────────────────┐
│                                        │
│  app container                         │
│  RotatingFileHandler                   │
│  → /shared/logs/{SERVICE_NAME}.json    │
│  RequestIDMiddleware (thread_local)    │
│                                        │
│  ════════ emptyDir ════════════════   │
│                                        │
│  filebeat sidecar                      │
│  tail → Kafka topic: logs.{SERVICE}    │
│                                        │
└──────────────┬─────────────────────────┘
               │
    ┌──────────▼──────────┐
    │       Kafka          │
    │  1 topic per service │
    └──────────┬──────────┘
               │
    ┌──────────▼──────────┐
    │  Fluentd (Deployment)│
    │  src: rdkafka2       │
    │  out: elasticsearch  │
    └──────────┬──────────┘
               │
    ┌──────────▼──────────┐
    │   Elasticsearch      │
    │   → Kibana           │
    └──────────────────────┘


## 一、Django 服务模板

### 1.1 文件清单（每个 Django 服务需要）

```
{project_root}/
├── k8s_console/
│   ├── logging_filters.py    ← 复用，无需改动
│   ├── middleware.py          ← 加 RequestIDMiddleware
│   └── settings.py            ← 更新 LOGGING + MIDDLEWARE
└── deploy/
    └── {service}/
        └── deployment.yaml    ← 加 emptyDir + filebeat sidecar
```

### 1.2 logging_filters.py

```python
# backend/k8s_console/logging_filters.py
import logging, os, threading

_local = threading.local()

def get_request_id():
    return getattr(_local, "request_id", "-")

def set_request_id(request_id: str):
    _local.request_id = request_id

class RequestIDFilter(logging.Filter):
    """Inject request_id, service, pod into every log record."""
    def __init__(self, service_name: str = "", name: str = ""):
        super().__init__(name=name)
        self.service_name = service_name or os.environ.get("SERVICE_NAME", "unknown")

    def filter(self, record):
        record.request_id = get_request_id()
        record.service = self.service_name
        record.pod = os.environ.get("HOSTNAME", "unknown")
        return True
```

### 1.3 middleware.py

```python
# 在 MIDDLEWARE 列表**第一位**添加:
"k8s_console.middleware.RequestIDMiddleware",
```

```python
# backend/k8s_console/middleware.py — 新增类
class RequestIDMiddleware:
    """Generate/read X-Request-ID, store in thread-local."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        import uuid
        from k8s_console.logging_filters import set_request_id
        request.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        set_request_id(request.request_id)
        response = self.get_response(request)
        response["X-Request-ID"] = request.request_id
        return response
```

### 1.4 settings.py — LOGGING 配置

```python
# 核心变量（通过环境变量注入）
# SERVICE_NAME = "k8s-console-backend"  # 来自 deployment env
# LOG_DIR      = "/shared/logs"          # emptyDir 挂载点

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {
            "()": "k8s_console.logging_filters.RequestIDFilter",
            "service_name": os.environ.get("SERVICE_NAME", "{SERVICE_NAME}"),
        },
    },
    "formatters": {
        "json": {
            "format": (
                '{"time":"%(asctime)s","level":"%(levelname)s",'
                '"service":"%(service)s","request_id":"%(request_id)s",'
                '"pod":"%(pod)s","logger":"%(name)s","message":"%(message)s",'
                '"path":"%(pathname)s","lineno":%(lineno)d}'
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / f"{os.environ.get('SERVICE_NAME', '{SERVICE_NAME}')}.json.log"),
            "maxBytes": 50 * 1024 * 1024,
            "backupCount": 3,
            "formatter": "json",
            "filters": ["request_id"],
        },
    },
    "loggers": {
        "api": {"handlers": ["file"], "level": "INFO", "propagate": False},
        "django.request": {"handlers": ["file"], "level": "WARNING", "propagate": False},
        "django.db.backends": {"handlers": ["file"], "level": "WARNING", "propagate": False},
        "django": {"handlers": ["file"], "level": "WARNING", "propagate": False},
    },
}
```

### 1.5 deployment.yaml — sidecar 模板

```yaml
# 新增环境变量
env:
  - name: SERVICE_NAME
    value: "{SERVICE_NAME}"        # ← 替换为实际服务名
  - name: LOG_DIR
    value: "/shared/logs"

# 新增 volumeMount
volumeMounts:
  - name: shared-logs
    mountPath: /shared/logs

# 新增 sidecar 容器
- name: filebeat
  image: docker.elastic.co/beats/filebeat:8.15.0
  env:
    - name: POD_NAME
      valueFrom:
        fieldRef:
          fieldPath: metadata.name
    - name: POD_NAMESPACE
      valueFrom:
        fieldRef:
          fieldPath: metadata.namespace
  volumeMounts:
    - name: shared-logs
      mountPath: /shared/logs
      readOnly: true
    - name: filebeat-config
      mountPath: /usr/share/filebeat/filebeat.yml
      subPath: filebeat.yml

# 新增 volumes
volumes:
  - name: shared-logs
    emptyDir: {}
  - name: filebeat-config
    configMap:
      name: filebeat-config
```


## 二、Vue 前端模板（预留）

> 前端暂不实现日志采集。计划方案：axios 拦截器把错误/慢请求通过 POST /api/log 发到 backend，统一写入同一链条。


## 三、K8s 基础设施运维

### 3.1 Kafka 部署
```bash
kubectl apply -f deploy/logging/06-kafka.yaml
```

### 3.2 filebeat ConfigMap 部署
```bash
kubectl apply -f deploy/logging/07-filebeat-config.yaml
```

### 3.3 Fluentd Kafka Consumer 部署
```bash
# 先禁用旧的 DaemonSet
kubectl delete daemonset fluentd -n prd --ignore-not-found

# 部署新的 Kafka consumer
kubectl apply -f deploy/logging/08-fluentd-kafka-consumer.yaml
```

### 3.4 新建 topic（每个服务上线时）
```bash
kubectl exec -n prd kafka-0 -- kafka-topics.sh --create \
  --topic logs.{SERVICE_NAME} \
  --bootstrap-server localhost:9092 \
  --partitions 3 --replication-factor 1
```

### 3.5 验证链路
```bash
# 1. Kafka topic 有数据
kubectl exec -n prd kafka-0 -- kafka-console-consumer.sh \
  --topic logs.k8s-console-backend --bootstrap-server localhost:9092 --max-messages 3

# 2. ES 索引有文档
kubectl exec -n prd elasticsearch-0 -- curl -s \
  'localhost:9200/_cat/indices/k8s-*?v'

# 3. Kibana 查看
# 浏览器打开 http://kibana.prd.local.com → Discover → index: k8s-*
```


## 四、日志格式规范

每条日志在 ES 中的结构：
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

Kibana 常用查询：
- 按 service: `service: "k8s-console-backend"`
- 按 pod: `pod: "k8s-console-backend-*"`
- 追踪一次请求: `request_id: "req-abc-123-*"`
- 只看错误: `level: "ERROR"`


## 五、模板变量速查

| 变量 | 说明 | 示例 |
|------|------|------|
| `{SERVICE_NAME}` | 服务标识（Consumed） | `k8s-console-backend` |
| `{KAFKA_TOPIC}` | Kafka 主题名 | `logs.k8s-console-backend` |
| `{SERVICE}` | filebeat 动态提取 | 来自 JSON 的 `service` 字段 |