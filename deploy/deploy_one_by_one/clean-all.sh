#!/bin/bash
# ── 加载 MSYS / Git Bash 路径转换兼容（必须最先执行）──
# 解决 Git Bash 下 MSYS_NO_PATHCONV / MSYS2_ARG_CONV_EXCL 被设置，导致
# kubectl.exe / docker.exe 收到 /d/... POSIX 路径而找不到文件的问题。
source "$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)/_env.sh"
# ============================================
#  K8s Console — 清理调度器
#  可全量清理，也可只清理指定组件
#
#  组件:
#    ingress-controller  清理 Ingress-NGINX
#    elk                 清理日志收集
#    prometheus          清理监控
#    backend-app         清理 K8s Console
#    gateway             停止本地网关 + port-forward
#
#  说明:
#    - 部分清理（指定组件）只删除该组件目录定义的资源，保留共享的
#      prd / database 命名空间，不影响其他组件。
#    - 全量清理会删除 database / prd / ingress-nginx 命名空间及残留的
#      cluster 级资源。
#
#  用法:
#    bash deploy/deploy_one_by_one/clean-all.sh                      # 清理全部
#    bash deploy/deploy_one_by_one/clean-all.sh elk                  # 只清 ELK
#    bash deploy/deploy_one_by_one/clean-all.sh backend-app elk      # 只清这两套
#    bash deploy/deploy_one_by_one/clean-all.sh --help
# ============================================
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
COMPS=()

for arg in "$@"; do
  case $arg in
    --all) ;;  # 默认即全量
    --help|-h)
      sed -n '3,25p' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    ingress-controller|elk|prometheus|backend-app|gateway)
      COMPS+=("$arg") ;;
    "")
      ;;
    *)
      echo "❌ 未知参数 / 组件: $arg"
      echo "   可用组件: ingress-controller | elk | prometheus | backend-app | gateway"
      exit 1 ;;
  esac
done

echo "=========================================="
echo "  K8s Console — 清理"
echo "=========================================="

run_clean() {
  local c="$1"
  echo ""
  echo ">>> 清理组件: $c"
  "$BASH" "$DIR/clean-$c.sh"
}

# ── 全量模式 ──
if [ ${#COMPS[@]} -eq 0 ]; then
  # 逆序清理：上层（依赖方）先清
  run_clean gateway
  run_clean backend-app
  run_clean prometheus
  run_clean elk
  run_clean ingress-controller

  # 数据库命名空间（级联删除其中的 mysql / redis 等资源）
  echo ""
  echo ">>> 清理数据库命名空间"
  k8s_delete_ns database

  # prd 命名空间（此时内部资源已被各组件 clean 删空）
  echo ">>> 清理 prd 命名空间"
  k8s_delete_ns prd

  # 残留 cluster 级资源
  echo ">>> 清理残留 cluster 级资源"
  kubectl delete ingressclass nginx --ignore-not-found --wait=false 2>/dev/null || true
  kubectl delete clusterrole ingress-nginx ingress-nginx-leader k8s-console fluentd prometheus --ignore-not-found --wait=false 2>/dev/null || true
  kubectl delete clusterrolebinding ingress-nginx ingress-nginx-leader k8s-console fluentd prometheus --ignore-not-found --wait=false 2>/dev/null || true
else
  # ── 指定组件模式 ──
  for c in "${COMPS[@]}"; do
    run_clean "$c"
  done
fi

echo ""
echo "✅ 清理完成！"
echo "重新部署: bash deploy/deploy_one_by_one/deploy-all.sh"
