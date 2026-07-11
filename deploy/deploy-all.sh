#!/bin/bash
# K8s Ingress 网关 + 演示应用 一键部署脚本
# ⚠️ 此脚本部署的是 ingress-nginx 基础设施 + 演示应用 (prd-app, host: myapp.local)
#    k8s-console 控制台应用部署请参考: kubectl apply -f deploy/console/
#    完整部署流程请参考: 项目根目录 README.md
# 用途: 按依赖顺序 apply 所有 YAML 文件
# 用法: bash deploy-all.sh [clean]
#        clean 参数: 先删除所有资源再重新部署

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"

if [ "$1" = "clean" ]; then
  echo "🧹 清理已有资源..."
  kubectl -n prd delete ingress prd-app --ignore-not-found
  kubectl -n prd delete svc prd-app --ignore-not-found
  kubectl -n prd delete deploy prd-app --ignore-not-found
  kubectl -n ingress-nginx delete ds ingress-nginx-controller --ignore-not-found
  kubectl -n ingress-nginx delete svc ingress-nginx-controller --ignore-not-found
  kubectl -n ingress-nginx delete cm ingress-nginx-controller tcp-services udp-services --ignore-not-found
  kubectl delete ingressclass nginx --ignore-not-found
  kubectl delete clusterrolebinding ingress-nginx ingress-nginx-leader --ignore-not-found
  kubectl delete clusterrole ingress-nginx ingress-nginx-leader --ignore-not-found
  kubectl -n ingress-nginx delete sa ingress-nginx --ignore-not-found
  kubectl delete ns ingress-nginx prd --ignore-not-found
  echo "⏳ 等待资源清理完成..."
  sleep 3
fi

echo "📦 1/7 创建 Namespace..."
kubectl apply -f "$DIR/ingress-nginx/01-namespace.yaml"

echo "🔐 2/7 部署 RBAC..."
kubectl apply -f "$DIR/ingress-nginx/02-rbac.yaml"

echo "⚙️  3/7 部署 ConfigMap..."
kubectl apply -f "$DIR/ingress-nginx/03-configmaps.yaml"

echo "🏷️  4/7 创建 IngressClass..."
kubectl apply -f "$DIR/ingress-nginx/06-ingressclass.yaml"

echo "🚀 5/7 部署 Ingress Controller (DaemonSet)..."
kubectl apply -f "$DIR/ingress-nginx/04-daemonset.yaml"

echo "🌐 6/7 创建 Service (NodePort :30000)..."
kubectl apply -f "$DIR/ingress-nginx/05-service.yaml"

echo "🏗️  7/7 部署业务演示应用 (Deployment + Service + Ingress)..."
kubectl apply -f "$DIR/demo/01-prd-app.yaml"

echo ""
echo "⏳ 等待所有 Pod 就绪..."
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s 2>/dev/null || true

kubectl wait --namespace prd \
  --for=condition=ready pod \
  --selector=app=prd-app \
  --timeout=120s 2>/dev/null || true

echo ""
echo "============================================"
echo "✅ 部署完成! 验证命令:"
echo "============================================"
echo ""
echo "# 查看所有 Pod"
echo "kubectl get pods -A"
echo ""
echo "# 通过 port-forward 测试"
echo "kubectl -n ingress-nginx port-forward daemonset/ingress-nginx-controller 8888:80"
echo "curl -H 'Host: myapp.local' http://localhost:8888/"
echo ""
echo "# 通过 NodePort 测试"
echo "curl -H 'Host: myapp.local' http://127.0.0.1:30000/"
echo ""
echo "# 完整链路 (需先部署本地网关)"
echo "curl -H 'Host: myapp.local' http://127.0.0.1:9001/"
