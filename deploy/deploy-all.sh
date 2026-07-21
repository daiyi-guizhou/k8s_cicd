#!/bin/bash
# ============================================
#  K8s Console — 一键部署全部
#  流程: 构建镜像 → 数据库 → Ingress → 日志收集 → 监控 → Console → 注册集群 → 启动网关
#
#  ⚠️  执行环境: Git Bash (MINGW64)，不要在 WSL 中执行！
#     原因: node_modules 为 Windows 平台原生模块，
#     WSL 内 rollup 无法加载 @rollup/rollup-linux-x64-gnu
#
#  用法:
#    bash deploy/deploy-all.sh               # 完整部署（含构建镜像）
#    bash deploy/deploy-all.sh --skip-build  # 跳过镜像构建
#    bash deploy/deploy-all.sh --clean       # 先清理再部署
#    bash deploy/deploy-all.sh --help        # 查看帮助
# ============================================
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
SKIP_BUILD=false
DO_CLEAN=false

# ── 参数解析 ──
for arg in "$@"; do
  case $arg in
    --skip-build) SKIP_BUILD=true ;;
    --clean) DO_CLEAN=true ;;
    --help|-h) cat <<HELP
K8s Console 一键部署脚本

用法: bash deploy/deploy-all.sh [选项]

选项:
  --skip-build  跳过 Docker 镜像构建（已构建过时用）
  --clean       先清理所有资源再部署
  --help        显示此帮助

流程:
  Step 1/8: 构建后端镜像 (Django)
  Step 2/8: 构建前端镜像 (Vue + Nginx)
  Step 3/8: 部署数据库 (MySQL + Redis)
  Step 4/8: 部署 Ingress-NGINX
  Step 5/8: 部署日志收集 (ELK - Elasticsearch + Fluentd + Kibana)
  Step 6/8: 部署监控 (Prometheus + Node Exporter + Grafana)
  Step 7/8: 部署 K8s Console (Backend + Frontend + Ingress)
  Step 8/8: 注册集群 + 启动本地网关

部署后访问: http://k8s-cicd.daiyi.local.com:9001
HELP
    exit 0 ;;
  esac
done

echo "=========================================="
echo "  K8s Console — 一键部署"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# ── 可选: 先清理 ──
if $DO_CLEAN; then
  echo ""
  echo "🧹 --clean: 先清理已有资源..."
  "$BASH" "$DIR/clean-all.sh"
  echo ""
fi

# ── Step 1: 构建后端镜像 ──
echo ""
echo "=========================================="
echo "  Step 1/8: 构建后端镜像"
echo "=========================================="

if $SKIP_BUILD; then
  echo "  ⏭️  跳过 (--skip-build)"
else
  echo "  📦 Building k8s-console-backend:latest ..."
  DOCKER_BUILDKIT=0 docker build --pull=false \
    -t k8s-console-backend:latest \
    -f "$ROOT/backend/Dockerfile" "$ROOT/backend/"
  echo "  ✅ k8s-console-backend:latest"
fi

# ── Step 2: 构建前端镜像 ──
echo ""
echo "=========================================="
echo "  Step 2/8: 构建前端镜像"
echo "=========================================="

if $SKIP_BUILD; then
  echo "  ⏭️  跳过 (--skip-build)"
else
  echo "  📦 npm run build ..."
  cd "$ROOT/frontend" && npm install && npm run build
  echo "  📦 Building k8s-console-frontend:latest ..."
  DOCKER_BUILDKIT=0 docker build --pull=false \
    -t k8s-console-frontend:latest \
    -f "$ROOT/frontend/Dockerfile.local" "$ROOT/frontend/"
  echo "  ✅ k8s-console-frontend:latest"
fi

# ── Step 3: 部署数据库 ──
echo ""
echo "=========================================="
echo "  Step 3/8: 部署数据库 (MySQL + Redis)"
echo "=========================================="

kubectl apply -f "$DIR/database/"
echo "  ⏳ 等待 Pod 就绪..."
kubectl wait --for=condition=ready pod -n database --all --timeout=180s
echo "  ✅ MySQL + Redis 就绪"

# ── Step 4: 部署 Ingress-NGINX ──
echo ""
echo "=========================================="
echo "  Step 4/8: 部署 Ingress-NGINX"
echo "=========================================="

kubectl apply -f "$DIR/ingress-nginx/"
echo "  ⏳ 等待控制器就绪..."
kubectl wait --for=condition=ready pod \
  -n ingress-nginx \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s
echo "  ✅ ingress-nginx 就绪"

# ── Step 5/8: 部署日志收集 (ELK)
echo ""
echo "=========================================="
echo "  Step 5/8: 部署日志收集 (ELK — Elasticsearch + Fluentd + Kibana)"
echo "=========================================="

# Ensure prd namespace exists (ELK + Monitoring + Console share it)
kubectl create namespace prd --dry-run=client -o yaml | kubectl apply -f - 2>/dev/null || true
echo "  ✅ prd namespace ready"
kubectl apply -f "$DIR/logging/"
echo "  ⏳ 等待日志收集 Pod 就绪 (prd)..."
kubectl wait --for=condition=ready pod -n prd --all --timeout=180s
echo "  ✅ Elasticsearch + Fluentd + Kibana 就绪 (prd)"
echo "  🌐 Kibana: http://kibana.logging.local ()"

# ── Step 6/8: 部署监控 (Prometheus + Grafana)
echo ""
echo "=========================================="
echo "  Step 6/8: 部署监控 (Prometheus + Node Exporter + Grafana)"
echo "=========================================="

kubectl apply -f "$DIR/monitoring/"
echo "  ⏳ 等待监控 Pod 就绪 (prd)..."
kubectl wait --for=condition=ready pod -n prd --all --timeout=180s
echo "  ✅ Prometheus + Node Exporter + Grafana 就绪 (prd)"
echo "  📊 Grafana:  http://grafana.monitoring.local (账号 admin/admin)"
echo "  📈 Prometheus: kubectl port-forward -n prd svc/prometheus 9090:9090"

# ── Step 7: 部署 K8s Console ──
echo ""
echo "=========================================="
echo "  Step 7/8: 部署 K8s Console (Backend + Frontend)"
echo "=========================================="

kubectl apply -f "$DIR/console/"
echo "  ⏳ 等待 Pod 就绪..."
kubectl wait --for=condition=ready pod -n prd --all --timeout=120s
echo "  ✅ Backend + Frontend 就绪"

# 等 backend 完全启动（migrate + init_admin + gunicorn）
echo "  ⏳ 等待 Backend 完成启动..."
sleep 5

# 查看 backend 日志（确认 admin 初始密码）
echo ""
echo "  ── Backend 启动日志 ──"
kubectl logs -n prd -l app=k8s-console-backend --tail=8 2>/dev/null | grep -E "Admin|Listening|user created" || \
  kubectl logs -n prd -l app=k8s-console-backend --tail=5 2>/dev/null
echo "  ────────────────────────"

# ── Step 6: 注册集群 + 启动网关 ──
echo ""
echo "=========================================="
echo "  Step 8/8: 注册集群 + 启动本地网关"
echo "=========================================="

# 6a. 启动 port-forward 兜底（确保 NodePort 可用）
echo ""
echo "  [6a] 确保 NodePort 可达..."

# 先检测 NodePort 30000 是否可达
NODEPORT_OK=false
if curl -s -o /dev/null -w '%{http_code}' --connect-timeout 3 \
  http://localhost:30000/ -H 'Host: k8s-cicd.daiyi.local.com' 2>/dev/null | grep -q '200\|301\|302\|404\|500'; then
  NODEPORT_OK=true
  echo "  ✅ NodePort 30000 直接可达"
fi

# 如果不可达，启动 port-forward 兜底
if ! $NODEPORT_OK; then
  echo "  ⚠️  NodePort 30000 不可达，启动 kubectl port-forward 兜底..."

  # 停掉旧的 port-forward
  if [ -f /tmp/k8s-gateway-pf.pid ]; then
    kill $(cat /tmp/k8s-gateway-pf.pid) 2>/dev/null || true
    rm -f /tmp/k8s-gateway-pf.pid
  fi

  nohup kubectl port-forward -n ingress-nginx \
    daemonset/ingress-nginx-controller 30000:80 --address 0.0.0.0 \
    > /tmp/k8s-gateway-pf.log 2>&1 &
  PF_PID=$!
  echo $PF_PID > /tmp/k8s-gateway-pf.pid
  sleep 3

  # 验证
  if curl -s -o /dev/null -w '%{http_code}' --connect-timeout 3 \
    http://localhost:30000/ -H 'Host: k8s-cicd.daiyi.local.com' 2>/dev/null | grep -q '200\|301\|302\|404\|500'; then
    echo "  ✅ port-forward 启动成功 (PID: $PF_PID)"
  else
    echo "  ❌ port-forward 仍不可达，请手动排查"
  fi
fi

# 6b. 注册集群（使用 in-cluster config — Pod 内天然可用）
echo ""
echo "  [6b] 注册 K8s 集群..."
echo "  使用 in-cluster config（Pod 自动连接 API Server）"

# 先获取 admin token（登录）
LOGIN_RESP=$(curl -s --noproxy '*' \
  http://localhost:30000/api/auth/login \
  -H 'Host: k8s-cicd.daiyi.local.com' \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin"}' 2>/dev/null || true)

ADMIN_TOKEN=$(echo "$LOGIN_RESP" | python3 -c \
  "import sys,json; print(json.load(sys.stdin).get('data',{}).get('token',''))" 2>/dev/null || true)

if [ -z "$ADMIN_TOKEN" ]; then
  echo "  ⚠️  admin/admin 登录失败，尝试从日志获取初始密码..."
  INIT_PWD=$(kubectl logs -n prd -l app=k8s-console-backend --tail=50 2>/dev/null | grep -oP 'password: \K\S+' | tail -1 || true)
  if [ -n "$INIT_PWD" ]; then
    LOGIN_RESP=$(curl -s --noproxy '*' \
      http://localhost:30000/api/auth/login \
      -H 'Host: k8s-cicd.daiyi.local.com' \
      -H "Content-Type: application/json" \
      -d "{\"username\":\"admin\",\"password\":\"$INIT_PWD\"}" 2>/dev/null || true)
    ADMIN_TOKEN=$(echo "$LOGIN_RESP" | python3 -c \
      "import sys,json; print(json.load(sys.stdin).get('data',{}).get('token',''))" 2>/dev/null || true)
  fi
fi

  if [ -n "$ADMIN_TOKEN" ]; then
    # ⚠️ 使用空 kubeconfig → Backend 自动 fallback 到 load_incluster_config()
    # 原因: Pod 内连不到宿主机 127.0.0.1，in-cluster config 天然可用
    KUBECONFIG_CONTENT=""

    # 先检查是否已存在同名集群
    REG_RESP=$(curl -s --noproxy '*' \
      http://localhost:30000/api/clusters/create \
      -H 'Host: k8s-cicd.daiyi.local.com' \
      -H 'Content-Type: application/json' \
      -H "Authorization: Token $ADMIN_TOKEN" \
      -d "{\"name\":\"docker-desktop\",\"description\":\"Docker Desktop K8s (in-cluster)\",\"kubeconfig_content\":\"$KUBECONFIG_CONTENT\",\"enabled\":true}" 2>/dev/null || true)

    REG_CODE=$(echo "$REG_RESP" | python3 -c \
      "import sys,json; print(json.load(sys.stdin).get('code',-1))" 2>/dev/null || true)

    if [ "$REG_CODE" = "0" ]; then
      echo "  ✅ 集群 'docker-desktop' 已注册（in-cluster mode）"
    elif echo "$REG_RESP" | grep -q "已存在"; then
      echo "  ℹ️  集群 'docker-desktop' 已存在，跳过注册"
    else
      echo "  ⚠️  集群注册: $REG_RESP"
    fi
  else
    echo "  ⚠️  无法获取 admin token，请手动注册集群"
  fi

# 6c. 启动本地网关
echo ""
echo "  [6c] 启动本地网关..."
"$BASH" "$DIR/gateway/start.sh"

echo ""
echo "=========================================="
echo "  🎉 部署完成！"
echo "=========================================="
echo ""
echo "  访问地址: http://k8s-cicd.daiyi.local.com:9001"
echo "  Kibana:  http://kibana.logging.local (hosts: 127.0.0.1 kibana.logging.local)"
echo "  Grafana: http://grafana.monitoring.local (hosts: 127.0.0.1 grafana.monitoring.local, 账号 admin/admin)"
echo "  Prometheus: kubectl port-forward -n prd svc/prometheus 9090:9090"
echo "  API 健康: curl http://k8s-cicd.daiyi.local.com:9001/api/health"
echo ""
echo "  账号信息:"
echo "    用户名: admin"
echo "    密  码: 见上方 Backend 启动日志 (Initial password)"
echo "    (可通过 kubectl 查看: kubectl logs -n prd -l app=k8s-console-backend | grep password)"
echo ""
echo "  管理命令:"
echo "    清理:  bash deploy/clean-all.sh"
echo "    查看:  kubectl get all -A | grep -E 'database|prd|ingress'"
echo ""
