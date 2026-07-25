#!/bin/bash
# ── 加载 MSYS / Git Bash 路径转换兼容（必须最先执行）──
# 解决 Git Bash 下 MSYS_NO_PATHCONV / MSYS2_ARG_CONV_EXCL 被设置，导致
# kubectl.exe / docker.exe 收到 /d/... POSIX 路径而找不到文件的问题。
source "$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)/_env.sh"
# ============================================
#  清理 Ingress-NGINX 控制器
#  独立可运行，也可被 clean-all.sh 调度
#
#  用法:
#    bash deploy/clean-ingress-controller.sh
# ============================================
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"

echo "=========================================="
echo "  清理 Ingress-NGINX"
echo "=========================================="

kubectl delete -f "$ROOT/ingress-nginx/" --ignore-not-found --wait=false 2>/dev/null || true
k8s_delete_ns ingress-nginx
kubectl delete ingressclass nginx --ignore-not-found 2>/dev/null || true
kubectl delete clusterrole ingress-nginx ingress-nginx-leader --ignore-not-found 2>/dev/null || true
kubectl delete clusterrolebinding ingress-nginx ingress-nginx-leader --ignore-not-found 2>/dev/null || true
echo "  ✅ ingress-nginx 已清理"
