#!/bin/bash
# ── 加载 MSYS / Git Bash 路径转换兼容（必须最先执行）──
# 解决 Git Bash 下 MSYS_NO_PATHCONV / MSYS2_ARG_CONV_EXCL 被设置，导致
# kubectl.exe / docker.exe 收到 /d/... POSIX 路径而找不到文件的问题。
source "$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)/_env.sh"
# ============================================
#  部署监控 (Prometheus + Node Exporter + Grafana)
#  独立可运行，也可被 deploy-all.sh 调度
#
#  用法:
#    bash deploy/deploy-prometheus.sh
#
#  说明: prd 命名空间被 ELK / 监控 / Console 三套共享，本脚本只动
#        monitoring/ 目录定义的资源，不会删除 prd 命名空间。
# ============================================
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"

echo "=========================================="
echo "  部署监控 (Prometheus + Grafana)"
echo "=========================================="

# prd 命名空间（ELK + 监控 + Console 共享）
kubectl create namespace prd --dry-run=client -o yaml | kubectl apply -f - 2>/dev/null || true

kubectl apply -f "$ROOT/monitoring/"

# 重启该套所有 workload（Deployment/StatefulSet/DaemonSet）并等待就绪
# 注意: monitoring/ 目录资源均在 prd 命名空间；kubectl get -o name 返回
#       "statefulset.apps/xxx" 这类带 group 的名称，需去掉 group 后缀并用
#       -n prd 显式指定命名空间（否则默认 ns 下找不到资源导致整脚本退出）。
echo "  ⏳ 重启并等待监控组件就绪..."
kubectl get -f "$ROOT/monitoring/" -o name 2>/dev/null | grep -E '^(deployment|statefulset|daemonset)\.' | while read -r r; do
  res="${r%%.*}/${r##*/}"
  kubectl rollout restart "$res" -n prd 2>/dev/null || true
  timeout 200 kubectl rollout status "$res" -n prd --timeout=180s 2>/dev/null || echo "  ⚠️  $r 等待超时"
done
echo "  ✅ 监控就绪 (prd)"
echo "  📊 Grafana:  http://grafana.monitoring.local:9001 (admin/admin)"
echo "  📈 Prometheus: kubectl port-forward -n prd svc/prometheus 9090:9090"
