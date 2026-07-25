#!/bin/bash
# ── 加载 MSYS / Git Bash 路径转换兼容（必须最先执行）──
# 解决 Git Bash 下 MSYS_NO_PATHCONV / MSYS2_ARG_CONV_EXCL 被设置，导致
# kubectl.exe / docker.exe 收到 /d/... POSIX 路径而找不到文件的问题。
source "$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)/_env.sh"
# ============================================
#  部署 K8s Console (Backend + Frontend + Ingress)
#  （即 backend-app：控制台业务 + Ingress 路由规则）
#  独立可运行，也可被 deploy-all.sh 调度
#
#  用法:
#    bash deploy/deploy_one_by_one/deploy-backend-app.sh
#
#  前置: 已构建镜像（先跑 deploy-all.sh，或单独 build 后本脚本会使用
#        本地已有的 k8s-console-backend:latest / k8s-console-frontend:latest）
#
#  说明: prd 命名空间被 ELK / 监控 / Console 三套共享，本脚本只动
#        console/ 目录定义的资源，不会删除 prd 命名空间。
# ============================================
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"

echo "=========================================="
echo "  部署 K8s Console (Backend + Frontend)"
echo "=========================================="

# prd 命名空间（ELK + 监控 + Console 共享）
kubectl create namespace prd --dry-run=client -o yaml | kubectl apply -f - 2>/dev/null || true

kubectl apply -f "$ROOT/console/"

# 重启该套所有 workload（Deployment/StatefulSet/DaemonSet）并等待就绪
# 注意: console/ 目录资源均在 prd 命名空间；kubectl get -o name 返回
#       "deployment.apps/xxx" 这类带 group 的名称，需去掉 group 后缀并用
#       -n prd 显式指定命名空间（否则默认 ns 下找不到资源导致整脚本退出）。
echo "  ⏳ 重启并等待 Console 组件就绪..."
kubectl get -f "$ROOT/console/" -o name 2>/dev/null | grep -E '^(deployment|statefulset|daemonset)\.' | while read -r r; do
  res="${r%%.*}/${r##*/}"
  kubectl rollout restart "$res" -n prd 2>/dev/null || true
  timeout 200 kubectl rollout status "$res" -n prd --timeout=180s 2>/dev/null || echo "  ⚠️  $r 等待超时"
done

# 等 backend 完全启动（migrate + init_admin + gunicorn）
sleep 5
echo "  ── Backend 启动日志 ──"
kubectl logs -n prd -l app=k8s-console-backend --tail=8 2>/dev/null | grep -E "Admin|Listening|user created" || \
  kubectl logs -n prd -l app=k8s-console-backend --tail=5 2>/dev/null
echo "  ────────────────────────"
echo "  ✅ Backend + Frontend 就绪 (prd)"
