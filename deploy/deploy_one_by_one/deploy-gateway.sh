#!/bin/bash
# ── 加载 MSYS / Git Bash 路径转换兼容（必须最先执行）──
# 解决 Git Bash 下 MSYS_NO_PATHCONV / MSYS2_ARG_CONV_EXCL 被设置，导致
# kubectl.exe / docker.exe 收到 /d/... POSIX 路径而找不到文件的问题。
source "$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)/_env.sh"
# ============================================
#  注册 K8s 集群 + 启动本地网关 (Docker NGINX :9001)
#  独立可运行，也可被 deploy-all.sh 调度
#
#  用法:
#    bash deploy/deploy-gateway.sh
#
#  依赖: Ingress-NGINX 已就绪（NodePort 30000），Console 已部署
# ============================================
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"

echo "=========================================="
echo "  注册集群 + 启动本地网关"
echo "=========================================="

# 6a. 确保 NodePort 30000 可达
echo ""
echo "  [6a] 确保 NodePort 30000 可达..."
NODEPORT_OK=false
if curl -s -o /dev/null -w '%{http_code}' --connect-timeout 3 \
  http://localhost:30000/ -H 'Host: k8s-cicd.daiyi.local.com' 2>/dev/null | grep -q '200\|301\|302\|404\|500'; then
  NODEPORT_OK=true
  echo "  ✅ NodePort 30000 直接可达"
fi

if ! $NODEPORT_OK; then
  echo "  ⚠️  NodePort 30000 不可达，启动 kubectl port-forward 兜底..."
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
  if curl -s -o /dev/null -w '%{http_code}' --connect-timeout 3 \
    http://localhost:30000/ -H 'Host: k8s-cicd.daiyi.local.com' 2>/dev/null | grep -q '200\|301\|302\|404\|500'; then
    echo "  ✅ port-forward 启动成功 (PID: $PF_PID)"
  else
    echo "  ❌ port-forward 仍不可达，请手动排查"
  fi
fi

# 6b. 注册集群（使用 in-cluster config — Pod 内天然可用）
echo ""
echo "  [6b] 注册 K8s 集群 (in-cluster config)..."
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
  KUBECONFIG_CONTENT=""
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
"$BASH" "$ROOT/gateway/start.sh"
echo ""
echo "  ✅ 本地网关已启动: http://k8s-cicd.daiyi.local.com:9001"
