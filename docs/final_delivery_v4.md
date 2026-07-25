<!--
  Final Delivery: Logging 模块重构 v4 — Filebeat sidecar + Kafka
  日期:     2026-07-21
  状态:     代码与文档完成，待端到端部署验证
  前置文档: docs/HANDOFF-ELK-PROMETHEUS-v4.md
-->

# Final Delivery: Logging 模块重构 v4

## 交付摘要

重构整个日志采集架构，从 stdout→CRI→Fluentd DaemonSet 升级为 RotatingFileHandler→Filebeat sidecar→Kafka→Fluentd Deployment，实现:
- 日志采集不依赖宿主机文件系统 (WSL 兼容)
- Kafka 解耦生产与消费，支持多 Pod 降噪
- request_id 全链路追踪
- Django 侧完整的模板化方案 (docs/logging-template.md)

## 变更清单 (14 个文件)

### 新增 (5)
| 文件 | 说明 |
|------|------|
| backend/k8s_console/logging_filters.py | RequestIDFilter + thread-local request_id |
| deploy/logging/06-kafka.yaml | Kafka 3.7 StatefulSet |
| deploy/logging/07-filebeat-config.yaml | Filebeat ConfigMap |
| deploy/logging/08-fluentd-kafka-consumer.yaml | Fluentd Kafka consumer Deployment |
| docs/logging-template.md | Django 日志模板文档 |

### 禁用/重命名 (1)
| 文件 | 说明 |
|------|------|
| deploy/logging/03-fluentd.yaml → .disabled | 旧 DaemonSet 弃用 |

### 修改 (8)
| 文件 | 变更 |
|------|------|
| backend/k8s_console/settings.py | LOGGING 重构 + LOG_DIR + MIDDLEWARE RequestID |
| backend/k8s_console/middleware.py | 新增 RequestIDMiddleware |
| deploy/console/05-backend.yaml | emptyDir + Filebeat sidecar + env 变量 |
| deploy/deploy-all.sh | Step 5 描述 + help 文本（现已组件化为 `deploy/deploy_one_by_one/deploy-all.sh`，原文件保留为 `deploy/deploy-all.sh.bak`） |
| deploy/clean-all.sh | 标题更新（现已组件化为 `deploy/deploy_one_by_one/clean-all.sh`，原文件保留为 `deploy/clean-all.sh.bak`） |
| deploy/verify-monitoring.sh | Kafka + Filebeat 检查 |
| readme.md | 架构/项目树/文档全面更新 |
| docs/* (新增 v4 交接/交付文档) | 完整架构文档 |

### 已修复的 Bug
| 文件 | Bug |
|------|-----|
| settings.py | LOG_DIR 未定义 → NameError |
| settings.py | MIDDLEWARE 行含文字 `\r\n` → SyntaxError |
| settings.py | JSON formatter 双花括号 `{{}}` → 输出非 JSON |
| settings.py | f-string 嵌套双引号 → SyntaxError |

## 架构对比

```
旧: stdout → containerd CRI → /var/log/containers/* → Fluentd DaemonSet (hostPath) → ES
新: RotatingFileHandler → emptyDir → Filebeat sidecar → Kafka → Fluentd Deployment → ES
```

## 部署验证清单

```bash
# 1. 清理 + 重新部署
bash deploy/deploy_one_by_one/deploy-all.sh --clean

# 2. 验证所有组件
bash deploy/verify-monitoring.sh

# 3. 检查 Kafka topic
kubectl exec -n prd kafka-0 -- kafka-topics.sh --list --bootstrap-server localhost:9092
# 预期: logs.k8s-console-backend

# 4. 检查 Filebeat sidecar
kubectl get pods -n prd -l app=k8s-console-backend -o json | python3 -c "..."
# 预期: filebeat=YES

# 5. 浏览器测试
# Kibana: http://kibana.logging.local → Discover → k8s-* 索引
# Grafana: http://grafana.monitoring.local (admin/admin)
```

## 下次继续

1. `bash deploy/deploy_one_by_one/deploy-all.sh --clean` 端到端部署验证
2. Chrome DevTools MCP 测试 Dashboard 跳转按钮
3. 按 docs/logging-template.md 为新 Django 服务接入日志
