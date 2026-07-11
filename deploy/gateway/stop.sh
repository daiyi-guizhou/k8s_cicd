#!/bin/bash
# K8s Console 本地 NGINX 网关停止脚本
# 同时清理 port-forward 进程
#
# ⚠️  执行环境: Git Bash (MINGW64) 或 WSL 均可（仅用 docker + kill）

echo "Stopping K8s Console NGINX Gateway..."

# 1. 清理 port-forward (如果有)
if [ -f /tmp/k8s-gateway-pf.pid ]; then
  kill $(cat /tmp/k8s-gateway-pf.pid) 2>/dev/null && echo "  port-forward stopped" || true
  rm -f /tmp/k8s-gateway-pf.pid
fi
pkill -f "kubectl port-forward.*ingress-nginx.*30000" 2>/dev/null && echo "  residual port-forward cleaned" || true

# 2. 停止容器
docker rm -f k8s-gateway 2>/dev/null && echo "  NGINX container removed" || echo "  No container running"

echo "Done."
