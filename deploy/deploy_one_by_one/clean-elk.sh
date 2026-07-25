#!/bin/bash
# ── 加载 MSYS / Git Bash 路径转换兼容（必须最先执行）──
# 解决 Git Bash 下 MSYS_NO_PATHCONV / MSYS2_ARG_CONV_EXCL 被设置，导致
# kubectl.exe / docker.exe 收到 /d/... POSIX 路径而找不到文件的问题。
source "$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)/_env.sh"
# ============================================
#  清理日志收集 (ELK)
#  独立可运行，也可被 clean-all.sh 调度
#
#  用法:
#    bash deploy/clean-elk.sh
#
#  说明: 只删除 logging/ 目录定义的资源 + fluentd 的 cluster 级资源。
#        prd 命名空间由 ELK / 监控 / Console 共享，本脚本不删除它
#        （避免误删另外两套）。PVC 数据保留以便重部署复用。
# ============================================
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"

echo "=========================================="
echo "  清理日志收集 (ELK)"
echo "=========================================="

kubectl delete -f "$ROOT/logging/" --ignore-not-found --wait=false 2>/dev/null || true
kubectl delete clusterrole fluentd --ignore-not-found 2>/dev/null || true
kubectl delete clusterrolebinding fluentd --ignore-not-found 2>/dev/null || true
echo "  ✅ ELK 已清理 (prd 命名空间保留；PVC 数据保留)"
