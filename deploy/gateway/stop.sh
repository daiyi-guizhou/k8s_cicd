#!/bin/bash
# K8s Console 本地 NGINX 网关停止脚本
#
# ⚠️  执行环境: Git Bash (MINGW64) 或 WSL 均可（仅用 docker）
# 说明: 网关以 --network host 运行，无 kubectl port-forward 进程需要清理。

echo "Stopping K8s Console NGINX Gateway..."

# 1. 停止容器
docker rm -f k8s-gateway 2>/dev/null && echo "  NGINX container removed" || echo "  No container running"

echo "Done."
