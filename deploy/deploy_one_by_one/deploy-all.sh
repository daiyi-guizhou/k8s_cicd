#!/bin/bash
# ── 加载 MSYS / Git Bash 路径转换兼容（必须最先执行）──
# 解决 Git Bash 下 MSYS_NO_PATHCONV / MSYS2_ARG_CONV_EXCL 被设置，导致
# kubectl.exe / docker.exe 收到 /d/... POSIX 路径而找不到文件的问题。
source "$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)/_env.sh"
# ============================================
#  K8s Console — 部署调度器
#  可全量部署，也可只部署 / 重启指定组件
#
#  组件:
#    ingress-controller  部署 Ingress-NGINX 控制器
#    elk                 部署日志收集 (ES + Kafka + Filebeat + Fluentd + Kibana)
#    prometheus          部署监控 (Prometheus + Grafana)
#    backend-app         部署 K8s Console (Backend + Frontend + Ingress)  ← backend-app (console)
#    gateway             注册集群 + 启动本地网关 (Docker NGINX :9001)
#
#  ⚠️  执行环境: Git Bash (MINGW64)！node_modules 为 Windows 原生模块，
#     WSL 内 rollup 无法加载 @rollup/rollup-linux-x64-gnu
#
#  用法:
#    bash deploy/deploy_one_by_one/deploy-all.sh                         # 完整部署（含构建镜像）
#    bash deploy/deploy_one_by_one/deploy-all.sh --skip-build            # 跳过镜像构建
#    bash deploy/deploy_one_by_one/deploy-all.sh --clean                 # 先清理全部再部署
#    bash deploy/deploy_one_by_one/deploy-all.sh elk                     # 只部署 / 重启 ELK
#    bash deploy/deploy_one_by_one/deploy-all.sh backend-app elk         # 只部署这两套
#    bash deploy/deploy_one_by_one/deploy-all.sh --clean backend-app     # 清理 Console 后重新部署
#    bash deploy/deploy_one_by_one/deploy-all.sh --help
# ============================================
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
SKIP_BUILD=false
DO_CLEAN=false
COMPS=()

for arg in "$@"; do
  case $arg in
    --skip-build) SKIP_BUILD=true ;;
    --clean) DO_CLEAN=true ;;
    --all) ;;  # 默认即全量
    --help|-h)
      sed -n '3,30p' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    ingress-controller|elk|prometheus|backend-app|gateway)
      COMPS+=("$arg") ;;
    "")
      ;;
    *)
      echo "❌ 未知参数 / 组件: $arg"
      echo "   可用组件: ingress-controller | elk | prometheus | backend-app | gateway"
      echo "   选项: --skip-build | --clean | --all | --help"
      exit 1 ;;
  esac
done

echo "=========================================="
echo "  K8s Console — 部署"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

run_comp() {
  local c="$1"
  echo ""
  echo ">>> 部署组件: $c"
  "$BASH" "$DIR/deploy-$c.sh"
}

# ── 全量模式 ──
if [ ${#COMPS[@]} -eq 0 ]; then
  if $DO_CLEAN; then
    echo ""
    echo "🧹 --clean: 先清理全部资源..."
    "$BASH" "$DIR/clean-all.sh"
    echo ""
  fi

  echo ""
  echo "== 构建镜像 =="
  if $SKIP_BUILD; then
    echo "  ⏭️  跳过 (--skip-build)"
  else
    echo "  📦 Building k8s-console-backend:latest ..."
    DOCKER_BUILDKIT=0 docker build --pull=false \
      -t k8s-console-backend:latest \
      -f "$ROOT/backend/Dockerfile" "$ROOT/backend/"
    echo "  📦 npm run build ..."
    cd "$ROOT/frontend" && npm install && npm run build
    echo "  📦 Building k8s-console-frontend:latest ..."
    DOCKER_BUILDKIT=0 docker build --pull=false \
      -t k8s-console-frontend:latest \
      -f "$ROOT/frontend/Dockerfile.local" "$ROOT/frontend/"
  fi

  echo ""
  echo "== 部署数据库 (MySQL + Redis) =="
  kubectl apply -f "$ROOT/database/"
  timeout 200 kubectl wait --for=condition=ready pod -n database --all --timeout=180s

  for c in ingress-controller elk prometheus backend-app gateway; do
    run_comp "$c"
  done
else
  # ── 指定组件模式（只跑列出的组件）──
  if $DO_CLEAN; then
    echo ""
    echo "🧹 --clean: 先清理指定组件..."
    for c in "${COMPS[@]}"; do
      "$BASH" "$DIR/clean-$c.sh"
    done
    echo ""
  fi
  for c in "${COMPS[@]}"; do
    run_comp "$c"
  done
fi

echo ""
echo "=========================================="
echo "  🎉 部署完成！"
echo "=========================================="
echo ""
echo "  访问地址: http://k8s-cicd.daiyi.local.com:9001"
echo "  Kibana:  http://kibana.logging.local:9001"
echo "  Grafana: http://grafana.monitoring.local:9001 (admin/admin)"
echo "  API 健康: curl http://k8s-cicd.daiyi.local.com:9001/api/health"
echo ""
echo "  管理命令:"
echo "    全量清理:  bash deploy/deploy_one_by_one/clean-all.sh"
echo "    部分清理:  bash deploy/deploy_one_by_one/clean-all.sh <组件...>"
echo "    部分部署:  bash deploy/deploy_one_by_one/deploy-all.sh <组件...>"
echo ""
