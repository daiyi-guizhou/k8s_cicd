#!/bin/bash
# K8s Console 本地 NGINX 网关一键启动
# 架构: 浏览器 → Docker NGINX (:9001) → K8s Ingress NodePort (:30000) → Ingress → Service → Pod
#
# ⚠️  执行环境: Git Bash (MINGW64) 或 WSL 均可（仅用 docker + kubectl + curl）
# 设计: 优先 NodePort 30000，不可达时自动回退到 kubectl port-forward
# 端口 9001 避免与 WSL wslrelay.exe / Windows 系统代理 冲突

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
IMAGE="nginx:latest"
CONTAINER_NAME="k8s-gateway"
HOST_PORT="9001"
PF_PID_FILE="/tmp/k8s-gateway-pf.pid"

echo "=========================================="
echo "  K8s Console — Local NGINX Gateway"
echo "  http://k8s-cicd.daiyi.local.com:${HOST_PORT}"
echo "=========================================="

# ── 1. 确认 K8s NodePort 可达 ──
echo "[1/4] Checking K8s Ingress NodePort (30000)..."

NODEPORT_OK=false
if curl -s -o /dev/null -w '%{http_code}' --connect-timeout 3 \
  http://localhost:30000/ -H 'Host: k8s-cicd.daiyi.local.com' 2>/dev/null | grep -q '200\|301\|302\|404\|500'; then
  echo "  ✅ NodePort 30000 reachable"
  NODEPORT_OK=true
fi

# 如果 NodePort 不可达，启动 kubectl port-forward 兜底
if ! $NODEPORT_OK; then
  echo "  ⚠️  NodePort 30000 not responding → starting kubectl port-forward fallback..."

  # 停掉旧的 port-forward
  if [ -f "$PF_PID_FILE" ]; then
    kill $(cat "$PF_PID_FILE") 2>/dev/null || true
    rm -f "$PF_PID_FILE"
  fi
  pkill -f "kubectl port-forward.*ingress-nginx.*30000" 2>/dev/null || true
  sleep 1

  nohup kubectl port-forward -n ingress-nginx \
    daemonset/ingress-nginx-controller 30000:80 --address 0.0.0.0 \
    > /tmp/k8s-gateway-pf.log 2>&1 &
  PF_PID=$!
  echo $PF_PID > "$PF_PID_FILE"
  sleep 3

  # 再次验证
  if curl -s -o /dev/null -w '%{http_code}' --connect-timeout 3 \
    http://localhost:30000/ -H 'Host: k8s-cicd.daiyi.local.com' 2>/dev/null | grep -q '200\|301\|302\|404\|500'; then
    echo "  ✅ port-forward started (PID: $PF_PID)"
  else
    echo "  ❌ port-forward also failed — please check ingress-nginx"
  fi
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
