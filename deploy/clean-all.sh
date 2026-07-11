#!/bin/bash
# ============================================
#  K8s Console — 一键清理所有资源
#  清理: namespace (database/prd/ingress-nginx)
#        + cluster 级别资源 (IngressClass/ClusterRole/ClusterRoleBinding)
#        + 本地网关容器 + port-forward 进程
#
#  ⚠️  执行环境: Git Bash (MINGW64) 或 WSL 均可
#     此脚本仅用 kubectl + docker + pkill，无平台依赖
# ============================================
set -e

echo "=========================================="
echo "  K8s Console — 一键清理"
echo "=========================================="

# 1. 删除 namespace（含所有内部资源 + PVC）
echo "[1/4] 删除 namespace: database prd ingress-nginx ..."
kubectl delete namespace database --ignore-not-found --timeout=90s 2>/dev/null || true
kubectl delete namespace prd --ignore-not-found --timeout=90s 2>/dev/null || true
kubectl delete namespace ingress-nginx --ignore-not-found --timeout=90s 2>/dev/null || true

# 如果 namespace 卡在 Terminating，强制移除 finalizer（ingress-nginx 常见）
for ns in database prd ingress-nginx; do
  if kubectl get ns "$ns" --no-headers 2>/dev/null | grep -q Terminating; then
    echo "  ⚠️  $ns 卡在 Terminating，强制移除 finalizer..."
    kubectl get ns "$ns" -o json 2>/dev/null | \
      python3 -c "import sys,json; d=json.load(sys.stdin); d['spec']['finalizers']=[]; print(json.dumps(d))" 2>/dev/null | \
      kubectl replace --raw "/api/v1/namespaces/$ns/finalize" -f - 2>/dev/null || true
  fi
done

# 2. 删除 cluster 级别资源
echo "[2/4] 删除 cluster 级别资源..."
kubectl delete ingressclass nginx --ignore-not-found 2>/dev/null || true
kubectl delete clusterrolebinding ingress-nginx ingress-nginx-leader k8s-console --ignore-not-found 2>/dev/null || true
kubectl delete clusterrole ingress-nginx ingress-nginx-leader k8s-console --ignore-not-found 2>/dev/null || true

# 3. 停止本地网关容器
echo "[3/4] 停止本地网关容器..."
docker rm -f k8s-gateway 2>/dev/null && echo "  ✅ k8s-gateway 已停止" || echo "  ℹ️  k8s-gateway 未运行"

# 4. 停止 kubectl port-forward 进程
echo "[4/4] 停止 kubectl port-forward ..."
if [ -f /tmp/k8s-gateway-pf.pid ]; then
  kill $(cat /tmp/k8s-gateway-pf.pid) 2>/dev/null && echo "  ✅ port-forward 已停止" || true
  rm -f /tmp/k8s-gateway-pf.pid
fi
pkill -f "kubectl port-forward.*ingress-nginx.*30000" 2>/dev/null && echo "  ✅ 残留 port-forward 已清理" || echo "  ℹ️  无残留 port-forward"

echo ""
echo "✅ 清理完成！"
echo ""
echo "重新部署: bash deploy/deploy-all.sh"
