<!--
  Final Delivery: ELK + Prometheus Namespace 合并 + Dashboard 跳转 v3
  日期:     2026-07-19
  状态:     代码变更完成，待实际部署
  前置文档: docs/prd-elk-prometheus-v3.md, docs/HANDOFF-ELK-PROMETHEUS.md
-->
# Final Delivery: Namespace 合并 & Dashboard 跳转 v3

## 交付摘要

本次交付完成两项核心任务：
1. **Namespace 统一**: 将 ELK 日志栈和 Prometheus 监控栈从独立 `logging` / `monitoring` namespace 迁入 `prd` namespace
2. **Dashboard 跳转**: Console Dashboard 新增 Kibana / Grafana / Prometheus 快速跳转按钮

## 变更清单 (24 个文件)

### 新增 (1)
| 文件 | 说明 |
|------|------|
| docs/prd-elk-prometheus-v3.md | Namespace 合并 + 跳转按钮 PRD |

### 删除 (2)
| 文件 | 说明 |
|------|------|
| deploy/logging/01-namespace.yaml | 不再需要独立 logging namespace |
| deploy/monitoring/01-namespace.yaml | 不再需要独立 monitoring namespace |

### 修改 — Deploy Logging (4)
| 文件 | 变更 |
|------|------|
| deploy/logging/02-elasticsearch.yaml | `namespace: logging` → `prd` (4处) |
| deploy/logging/03-fluentd.yaml | namespace → prd; ES host: `elasticsearch.logging.svc` → `prd.svc` (8处) |
| deploy/logging/04-kibana.yaml | namespace → prd; `ELASTICSEARCH_HOSTS` → `prd.svc` |
| deploy/logging/05-kibana-ingress.yaml | namespace → prd |

### 修改 — Deploy Monitoring (8)
| 文件 | 变更 |
|------|------|
| deploy/monitoring/02-prometheus.yaml | namespace → prd; `alertmanager.prd.svc`; ClusterRoleBinding subjects: prd |
| deploy/monitoring/03-node-exporter.yaml | namespace → prd (DaemonSet) |
| deploy/monitoring/04-grafana.yaml | namespace → prd; datasource: `prometheus.prd.svc` |
| deploy/monitoring/05-grafana-dashboards.yaml | namespace → prd |
| deploy/monitoring/05-grafana-ingress.yaml | namespace → prd |
| deploy/monitoring/06-alertmanager-config.yaml | namespace → prd |
| deploy/monitoring/06-prometheus-ingress.yaml | namespace → prd |
| deploy/monitoring/07-alertmanager.yaml | namespace → prd (Svc + PVC + Deployment) |

### 修改 — 脚本 & 配置 (4)
| 文件 | 变更 |
|------|------|
| deploy/deploy-all.sh | Step 5/6: `kubectl wait -n prd`; port-forward 改为 `-n prd` |
| deploy/clean-all.sh | 移除 `logging` / `monitoring` namespace 独立删除 |
| deploy/verify-monitoring.sh | 全部 namespace 改为 `prd`; service DNS 更新 |
| deploy/console/03-configmap.yaml | `ELASTICSEARCH_URL` / `PROMETHEUS_URL` 指向 `prd.svc` |

### 修改 — 前端 (1)
| 文件 | 变更 |
|------|------|
| frontend/src/views/DashboardPage.vue | 集群概览卡片下方新增"外部工具"区域，3 个跳转卡片 (Kibana 🟦 / Grafana 🟠 / Prometheus 🔴)，新窗口打开 |

## 验证结果

### 前端构建
```
npm run build: 119 modules, 0 errors
DashboardPage chunk: tool-card ✅, Kibana ✅, Grafana ✅
```

### K8s 当前状态
```
prd:        backend + frontend (Running)
logging:    ES + Fluentd + Kibana (旧版, 需重新部署)
monitoring: Prometheus + Grafana + Node Exporter + Alertmanager (旧版, 需重新部署)
```

### Dashboard 跳转按钮效果
- Kibana → `http://kibana.logging.local` (新标签页, target="_blank")
- Grafana → `http://grafana.monitoring.local` (新标签页, 账号 admin/admin)
- Prometheus → `http://prometheus.monitoring.local` (新标签页)
- 卡片 hover 效果: 上移 2px + 左侧色条 (蓝/橙/红)

## 下次部署步骤

```bash
# 1. 清理旧部署
kubectl delete namespace logging --ignore-not-found
kubectl delete namespace monitoring --ignore-not-found
kubectl delete clusterrolebinding fluentd prometheus --ignore-not-found
kubectl delete clusterrole fluentd prometheus --ignore-not-found

# 2. 执行新部署
bash deploy/deploy-all.sh

# 3. 验证
kubectl get all -n prd
# 预期: backend, frontend, elasticsearch, fluentd, kibana, prometheus, grafana, node-exporter, alertmanager
```

## 访问地址

| 组件 | URL | 凭据 |
|------|-----|------|
| Console | `http://k8s-cicd.daiyi.local.com:9001` | admin |
| Kibana | `http://kibana.logging.local` | 无 |
| Grafana | `http://grafana.monitoring.local` | admin/admin |
| Prometheus | `kubectl port-forward -n prd svc/prometheus 9090:9090` | 无 |
*** End of File