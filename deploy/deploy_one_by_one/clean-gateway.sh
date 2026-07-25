#!/bin/bash
# ── 加载 MSYS / Git Bash 路径转换兼容（必须最先执行）──
# 解决 Git Bash 下 MSYS_NO_PATHCONV / MSYS2_ARG_CONV_EXCL 被设置，导致
# kubectl.exe / docker.exe 收到 /d/... POSIX 路径而找不到文件的问题。
source "$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)/_env.sh"
# ============================================
#  停止本地网关 (Docker NGINX :9001) + 清理 port-forward
#  独立可运行，也可被 clean-all.sh 调度
#
#  用法:
#    bash deploy/clean-gateway.sh
# ============================================
set -e

echo "=========================================="
echo "  停止本地网关 + port-forward"
echo "=========================================="

# 停止本地网关容器
echo "[1/2] 停止本地网关容器..."
docker rm -f k8s-gateway 2>/dev/null && echo "  ✅ k8s-gateway 已停止" || echo "  ℹ️  k8s-gateway 未运行"

# 停止 kubectl port-forward 进程
echo "[2/2] 停止 kubectl port-forward ..."
if [ -f /tmp/k8s-gateway-pf.pid ]; then
  kill $(cat /tmp/k8s-gateway-pf.pid) 2>/dev/null && echo "  ✅ port-forward 已停止" || true
  rm -f /tmp/k8s-gateway-pf.pid
fi
pkill -f "kubectl port-forward.*ingress-nginx.*30000" 2>/dev/null && echo "  ✅ 残留 port-forward 已清理" || echo "  ℹ️  无残留 port-forward"
echo "  ✅ 本地网关已停止"
