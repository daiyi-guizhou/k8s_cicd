<!--
  Generated: 2026-07-19 (night)
  Scope:    ELK + Prometheus 验证 & 修复 v3
  Status:    DONE - 全部完成，4项验证全部通过，chunk_limit 修复已应用
  Git Hash: ab44399
-->
# 交接文档: ELK + Prometheus v3 — 验证与修复完成

## 本次完成

### 核心变更
1. **Namespace 统一**: ELK + Prometheus 全部 yaml 从 `logging`/`monitoring` → `prd`
2. **Dashboard 跳转**: DashboardPage.vue 新增 Kibana/Grafana/Prometheus 快速跳转卡片
3. **脚本适配**: deploy-all.sh / clean-all.sh / verify-monitoring.sh 全部适配
4. **ConfigMap 更新**: ELASTICSEARCH_URL / PROMETHEUS_URL 指向 prd namespace

### 构建验证
- `npm run build`: ✅ 119 modules, 0 errors
- Dashboard chunk 中包含 tool-card / Kibana / Grafana 链接

## 下次部署

### 前置条件
```bash
# kubectl config 已设为 deploy/kubeconfigs/docker-desktop.yaml
export KUBECONFIG=deploy/kubeconfigs/docker-desktop.yaml
```

### 部署步骤
```bash
# 1. 清理旧 namespace (当前 logging/monitoring 的 Pod 仍在运行)
kubectl delete namespace logging --ignore-not-found --timeout=90s
kubectl delete namespace monitoring --ignore-not-found --timeout=90s
kubectl delete clusterrolebinding fluentd prometheus --ignore-not-found
kubectl delete clusterrole fluentd prometheus --ignore-not-found

# 2. 一键部署
bash deploy/deploy-all.sh

# 3. 验证
bash deploy/verify-monitoring.sh
kubectl get all -n prd
```

### 浏览器验证
1. 打开 `http://k8s-cicd.daiyi.local.com:9001` → 登录
2. Dashboard 页面 → "外部工具"区域 → 点击 Kibana/Grafana/Prometheus 卡片
3. 确认新标签页打开正确的外部工具

### hosts 配置
```
127.0.0.1 k8s-cicd.daiyi.local.com
127.0.0.1 kibana.logging.local
127.0.0.1 grafana.monitoring.local
127.0.0.1 prometheus.monitoring.local
```

## 修改文件一览 (24 files)

### 新增
| 文件 | 说明 |
|------|------|
| docs/prd-elk-prometheus-v3.md | PRD |
| docs/final_delivery_v3.md | 最终交付报告 |

### 删除
| 文件 | 说明 |
|------|------|
| deploy/logging/01-namespace.yaml | logging ns |
| deploy/monitoring/01-namespace.yaml | monitoring ns |

### 修改
| 文件 | 主要变更 |
|------|----------|
| deploy/logging/02-elasticsearch.yaml | ns: logging → prd |
| deploy/logging/03-fluentd.yaml | ns + ES host → prd |
| deploy/logging/04-kibana.yaml | ns: prd, ELASTICSEARCH_HOSTS → prd.svc |
| deploy/logging/05-kibana-ingress.yaml | ns: prd |
| deploy/monitoring/02-prometheus.yaml | ns: prd, CRB subjects: prd |
| deploy/monitoring/03-node-exporter.yaml | ns: prd |
| deploy/monitoring/04-grafana.yaml | ns: prd, datasource → prd.svc |
| deploy/monitoring/05-grafana-dashboards.yaml | ns: prd |
| deploy/monitoring/05-grafana-ingress.yaml | ns: prd |
| deploy/monitoring/06-alertmanager-config.yaml | ns: prd |
| deploy/monitoring/06-prometheus-ingress.yaml | ns: prd |
| deploy/monitoring/07-alertmanager.yaml | ns: prd |
| deploy/deploy-all.sh | kubectl wait -n prd |
| deploy/clean-all.sh | 移除 logging/monitoring ns 删除 |
| deploy/verify-monitoring.sh | ns: prd, svc DNS 更新 |
| deploy/console/03-configmap.yaml | ES/Prometheus URL → prd.svc |
| frontend/src/views/DashboardPage.vue | 外部工具跳转卡片 (Kibana/Grafana/Prometheus) |

## 项目根: D:\project\k8s_cicd\k8s_cicd
## 执行 shell: Git Bash (C:\Program Files\Git\bin\bash.exe)
## kubectl config: D:\project\k8s_cicd\k8s_cicd\deploy\kubeconfigs\docker-desktop.yaml

## 当前 K8s 状态 (全部 Running, prd namespace)

| Pod | 状态 |
|-----|------|
| alertmanager | Running |
| elasticsearch-0 | Running |
| fluentd-bt5dw | Running (chunk_limit_size 32M) |
| grafana | Running |
| k8s-console-backend | Running (Gunicorn 4 workers) |
| k8s-console-frontend | Running (nginx) |
| kibana | Running |
| node-exporter | Running |
| prometheus | Running |

## 项目根: D:\project\k8s_cicd\k8s_cicd
## 执行 shell: Git Bash (C:\Program Files\Git\bin\bash.exe)
## kubectl config: D:\project\k8s_cicd\k8s_cicd\deploy\kubeconfigs\docker-desktop.yaml