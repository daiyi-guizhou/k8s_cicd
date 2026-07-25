#!/bin/bash
# K8s Console 本地 NGINX 网关一键启动
# 架构: 浏览器 → Docker NGINX (:9001, --network host) → 宿主机 Ingress NodePort (:30000) → Ingress → Service → Pod
#
# ⚠️  执行环境: Git Bash (MINGW64) 或 WSL 均可（仅用 docker + curl）
# 网络: --network host，nginx 经 127.0.0.1:30000 直连宿主机 Ingress NodePort，
#       无需 kubectl port-forward，规避 host.docker.internal 的 IPv4/IPv6 解析错位。
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

# ── 1. 检查 K8s NodePort 是否可达（仅提示，不启动 port-forward）──
echo "[1/3] Checking K8s Ingress NodePort (30000)..."
if curl -s -o /dev/null -w '%{http_code}' --connect-timeout 3 \
  http://127.0.0.1:30000/ -H 'Host: k8s-cicd.daiyi.local.com' 2>/dev/null | grep -q '200\|301\|302\|404\|500'; then
  echo "  ✅ NodePort 30000 reachable"
else
  echo "  ⚠️  NodePort 30000 当前不可达，请确认 ingress-nginx 已部署（bash deploy/deploy_one_by_one/deploy-all.sh）"
fi

# ── 2. 拉取 nginx 镜像 ──
echo "[2/3] Checking nginx image..."
if ! docker image inspect "$IMAGE" > /dev/null 2>&1; then
  echo "  Pulling $IMAGE ..."
  docker pull "$IMAGE"
fi
echo "  ✅ Image ready: $IMAGE"

# ── 3. 停止旧容器 ──
echo "[3/3] Recreating gateway container..."
docker rm -f "$CONTAINER_NAME" 2>/dev/null && echo "  Old container removed" || echo "  No old container"

# ── 4. 启动 NGINX（--network host）──
# Git Bash (MSYS2) 会把 /etc/nginx/conf.d/default.conf 错误翻译成
# C:\Program Files\Git\etc\nginx\... Windows 路径，导致容器启动失败。
# 解决方案: MSYS_NO_PATHCONV=1 + 源文件用 Windows 路径 (pwd -W 转换)
#
# 网络模式: --network host
#   容器共享宿主机网络命名空间，nginx 内的 127.0.0.1 即宿主机回环。
#   Docker Desktop 的 Ingress NodePort 30000 发布在宿主机 127.0.0.1 上，
#   因此 nginx 代理到 http://127.0.0.1:30000 即可直达 Ingress，
#   无需 kubectl port-forward，也避免 host.docker.internal 在 IPv4/IPv6
#   之间解析不一致导致 502 的问题。
WIN_CONF="$(cd "$SCRIPT_DIR" && pwd -W)/nginx.conf"
MSYS_NO_PATHCONV=1 docker run -d --name "$CONTAINER_NAME" \
    --network host \
    -v "${WIN_CONF}:/etc/nginx/conf.d/default.conf:ro" \
    "$IMAGE" > /dev/null
echo "  Container: $CONTAINER_NAME ($IMAGE) [network=host, listen ${HOST_PORT}]"

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
