#!/bin/bash
# K8s Console 本地 NGINX 网关停止脚本

echo "Stopping K8s Console NGINX Gateway..."
docker rm -f k8s-gateway 2>/dev/null && echo "  NGINX container removed" || echo "  No container running"
echo "Done."
