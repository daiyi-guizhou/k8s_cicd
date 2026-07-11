#!/bin/bash
# K8s Console 本地 NGINX 网关一键启动
# 架构: 浏览器 → Docker NGINX (:9001) → K8s Ingress NodePort (:30000) → Ingress → Service → Pod
#
# 注意: ingress-nginx 已通过 NodePort 30000 暴露，无需 kubectl port-forward
# 端口 9001 避免与 WSL wslrelay.exe / Windows 系统代理 冲突

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
IMAGE="nginx:latest"
CONTAINER_NAME="k8s-gateway"
HOST_PORT="9001"

echo "=========================================="
echo "  K8s Console — Local NGINX Gateway"
echo "  http://k8s-cicd.daiyi.local.com:${HOST_PORT}"
echo "=========================================="

# ── 1. 确认 K8s NodePort 可达 ──
echo "[1/4] Checking K8s Ingress NodePort (30000)..."
if curl -s -o /dev/null -w '%{http_code}' http://localhost:30000/ -H 'Host: k8s-cicd.daiyi.local.com' | grep -q '200\|301\|302'; then
  echo "  ✅ NodePort 30000 reachable"
else
  echo "  ⚠️  NodePort 30000 not responding — please check ingress-nginx"
fi

# ── 2. 拉取 nginx 镜像 ──
echo "[2/4] Checking nginx image..."
if ! docker image inspect "$IMAGE" > /dev/null 2>&1; then
  echo "  Pulling $IMAGE ..."
  docker pull "$IMAGE"
fi
echo "  ✅ Image ready: $IMAGE"

# ── 3. 停止旧容器 ──
echo "[3/4] Recreating gateway container..."
docker rm -f "$CONTAINER_NAME" 2>/dev/null && echo "  Old container removed" || echo "  No old container"

# ── 4. 启动 NGINX ──
echo "[4/4] Starting NGINX gateway (port ${HOST_PORT} → 30000)..."
# Git Bash (MSYS2) 会把 /etc/nginx/conf.d/default.conf 错误翻译成
# C:\Program Files\Git\etc\nginx\... Windows 路径，导致容器启动失败。
# 解决方案: MSYS_NO_PATHCONV=1 + 源文件用 Windows 路径 (pwd -W 转换)
WIN_CONF="$(cd "$SCRIPT_DIR" && pwd -W)/nginx.conf"
MSYS_NO_PATHCONV=1 docker run -d --name "$CONTAINER_NAME" \
    -p ${HOST_PORT}:80 \
    -v "${WIN_CONF}:/etc/nginx/conf.d/default.conf:ro" \
    "$IMAGE" > /dev/null
echo "  Container: $CONTAINER_NAME ($IMAGE)"

# ── 5. Verify ──
echo ""
echo "  Verifying..."
sleep 2
echo "  Frontend   : $(curl -s -o /dev/null -w '%{http_code}' http://localhost:${HOST_PORT}/ -H 'Host: k8s-cicd.daiyi.local.com')"
echo "  API Health : $(curl -s -o /dev/null -w '%{http_code}' http://localhost:${HOST_PORT}/api/health -H 'Host: k8s-cicd.daiyi.local.com')"
echo "  Gateway    : $(curl -s -o /dev/null -w '%{http_code}' http://localhost:${HOST_PORT}/gateway-health)"
echo ""
echo "  ✅ Ready: http://k8s-cicd.daiyi.local.com:${HOST_PORT}"
echo "  📋 Stop:  bash $(dirname "$0")/stop.sh"
