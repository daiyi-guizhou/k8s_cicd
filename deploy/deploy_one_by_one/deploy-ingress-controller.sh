#!/bin/bash
# ── 加载 MSYS / Git Bash 路径转换兼容（必须最先执行）──
# 解决 Git Bash 下 MSYS_NO_PATHCONV / MSYS2_ARG_CONV_EXCL 被设置，导致
# kubectl.exe / docker.exe 收到 /d/... POSIX 路径而找不到文件的问题。
source "$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)/_env.sh"
# ============================================
#  部署 Ingress-NGINX 控制器
#  独立可运行，也可被 deploy-all.sh 调度
#
#  用法:
#    bash deploy/deploy-ingress-controller.sh
# ============================================
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"

echo "=========================================="
echo "  部署 Ingress-NGINX 控制器"
echo "=========================================="

kubectl apply -f "$ROOT/ingress-nginx/"
echo "  ⏳ 等待控制器就绪..."
timeout 150 kubectl wait --for=condition=ready pod -n ingress-nginx \
  --selector=app.kubernetes.io/component=controller --timeout=120s
echo "  ✅ ingress-nginx 控制器就绪"
