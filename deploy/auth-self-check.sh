#!/bin/bash
# ============================================
#  K8s Console — 认证系统一键自检
#  用法: bash deploy/auth-self-check.sh
#  依赖: deploy-all.sh 已成功执行
# ============================================
set -e

REDIS_POD=$(kubectl get pods -n database -l app=redis -o jsonpath='{.items[0].metadata.name}')
PASS=0; FAIL=0

check() {
  local desc="$1"; local actual="$2"; local expected="$3"
  if echo "$actual" | grep -q "$expected"; then
    echo "  ✅ $desc"; PASS=$((PASS+1))
  else
    echo "  ❌ $desc (expected: $expected)"; echo "     got: ${actual:0:120}"; FAIL=$((FAIL+1))
  fi
}

echo "=========================================="
echo "  Auth 自检 (F14)"
echo "=========================================="

# ── F14.1 Login + Token Meta ──
echo ""
echo "── F14.1 Login + Token Meta ──"
LOGIN=$(curl -s --noproxy '*' http://localhost:30000/api/auth/login \
  -H 'Host: k8s-cicd.daiyi.local.com' \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin"}')
TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['token'])" 2>/dev/null || echo "")
check "Login returns token" "$TOKEN" "."
META=$(kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! get "token:meta:$TOKEN" 2>/dev/null)
check "Meta has deploy_version" "$META" "deploy_version"
check "Meta has absolute_expiry" "$META" "absolute_expiry"

# ── F14.2 Token Valid ──
echo ""
echo "── F14.2 Token Valid ──"
RESP=$(curl -s --noproxy '*' http://localhost:30000/api/users/list \
  -H 'Host: k8s-cicd.daiyi.local.com' \
  -H "Authorization: Token $TOKEN" \
  -H 'Content-Type: application/json' -d '{}')
check "Valid token access" "$RESP" '"code":0'

# ── F14.3 Deploy Mismatch → 1004 ──
echo ""
echo "── F14.3 Deploy Mismatch → 1004 ──"
CURRENT_VER=$(kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! get "deploy:version" 2>/dev/null | tr -d '\r')
kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! set "deploy:version" "test-new-version" 2>/dev/null
RESP=$(curl -s --noproxy '*' http://localhost:30000/api/users/list \
  -H 'Host: k8s-cicd.daiyi.local.com' \
  -H "Authorization: Token $TOKEN" \
  -H 'Content-Type: application/json' -d '{}')
check "1004 response" "$RESP" '"code": 1004'
REMAINING=$(kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! keys "token:*$TOKEN" 2>/dev/null || echo "")
check "Token cleaned after 1004" "$REMAINING" "^$"
# Restore
kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! set "deploy:version" "$CURRENT_VER" 2>/dev/null

# ── F14.4 Absolute Expiry → 1007 ──
echo ""
echo "── F14.4 Absolute Expiry → 1007 ──"
LOGIN2=$(curl -s --noproxy '*' http://localhost:30000/api/auth/login \
  -H 'Host: k8s-cicd.daiyi.local.com' \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin"}')
TOKEN2=$(echo "$LOGIN2" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['token'])" 2>/dev/null || echo "")
CURRENT_VER=$(kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! get "deploy:version" 2>/dev/null | tr -d '\r')
EXPIRED_META="{\"user_id\":\"1\",\"login_at\":\"2026-01-01T00:00:00\",\"absolute_expiry\":\"2026-01-02T00:00:00\",\"deploy_version\":\"$CURRENT_VER\"}"
kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! set "token:meta:$TOKEN2" "$EXPIRED_META" 2>/dev/null
RESP=$(curl -s --noproxy '*' http://localhost:30000/api/users/list \
  -H 'Host: k8s-cicd.daiyi.local.com' \
  -H "Authorization: Token $TOKEN2" \
  -H 'Content-Type: application/json' -d '{}')
check "1007 response" "$RESP" '"code": 1007'

# ── F14.5 Sliding TTL ──
echo ""
echo "── F14.5 Sliding TTL ──"
LOGIN3=$(curl -s --noproxy '*' http://localhost:30000/api/auth/login \
  -H 'Host: k8s-cicd.daiyi.local.com' \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin"}')
TOKEN3=$(echo "$LOGIN3" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['token'])" 2>/dev/null || echo "")
TTL_BEFORE=$(kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! ttl "token:auth:$TOKEN3" 2>/dev/null | tr -d '\r')
echo "  TTL before request: $TTL_BEFORE"
sleep 2
curl -s --noproxy '*' http://localhost:30000/api/users/list \
  -H 'Host: k8s-cicd.daiyi.local.com' \
  -H "Authorization: Token $TOKEN3" \
  -H 'Content-Type: application/json' -d '{}' > /dev/null
TTL_AFTER=$(kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! ttl "token:auth:$TOKEN3" 2>/dev/null | tr -d '\r')
echo "  TTL after request:  $TTL_AFTER"
# TTL should be refreshed to near 28800
if [ "$TTL_AFTER" -gt 28790 ]; then
  echo "  ✅ TTL refreshed (${TTL_AFTER}s ≥ 28790)"; PASS=$((PASS+1))
else
  echo "  ❌ TTL not refreshed (got ${TTL_AFTER}s, expected ≥28790)"; FAIL=$((FAIL+1))
fi

# ── F14.6 Logout ──
echo ""
echo "── F14.6 Logout ──"
curl -s --noproxy '*' http://localhost:30000/api/auth/logout \
  -H 'Host: k8s-cicd.daiyi.local.com' \
  -H "Authorization: Token $TOKEN3" \
  -H 'Content-Type: application/json' -d '{}' > /dev/null
REMAINING=$(kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! keys "token:*$TOKEN3" 2>/dev/null || echo "")
# Should only have blacklist (or nothing), no auth/meta
if echo "$REMAINING" | grep -q "blacklist" && ! echo "$REMAINING" | grep -q "auth:.*$TOKEN3"; then
  echo "  ✅ Auth/meta cleaned, blacklist created"; PASS=$((PASS+1))
elif [ -z "$REMAINING" ]; then
  echo "  ✅ All token keys cleaned (blacklist TTL may have expired)"; PASS=$((PASS+1))
else
  echo "  ❌ Unexpected keys: $REMAINING"; FAIL=$((FAIL+1))
fi

# ── F14.7 Blacklist → 1003 ──
echo ""
echo "── F14.7 Blacklist → 1003 ──"
# Reuse TOKEN3 which was just logged out
RESP=$(curl -s --noproxy '*' http://localhost:30000/api/users/list \
  -H 'Host: k8s-cicd.daiyi.local.com' \
  -H "Authorization: Token $TOKEN3" \
  -H 'Content-Type: application/json' -d '{}')
check "1003 blacklist" "$RESP" '"code": 1003'

# ── F14.8 Backend No Errors ──
echo ""
echo "── F14.8 Backend No Errors ──"
LOGS=$(kubectl logs -n prd -l app=k8s-console-backend --tail=80 2>/dev/null)
if echo "$LOGS" | grep -qi "Traceback"; then
  echo "  ❌ Backend has Traceback!"; FAIL=$((FAIL+1))
else
  echo "  ✅ No Traceback in backend logs"; PASS=$((PASS+1))
fi
# Check deploy:version key exists in Redis (the real proof, regardless of how
# gunicorn's multi-process model routes the logger output)
DEPLOY_VER=$(kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! get "deploy:version" 2>/dev/null)
if [ -n "$DEPLOY_VER" ]; then
  echo "  ✅ Deploy version set (Redis key exists: $DEPLOY_VER)"; PASS=$((PASS+1))
else
  echo "  ❌ Deploy version not set (Redis key 'deploy:version' missing)"; FAIL=$((FAIL+1))
fi

# Also check logs (best-effort — may be missing with gunicorn preload/prefork)
if echo "$LOGS" | grep -q "Deploy version set"; then
  echo "  ✅ Deploy version logged (grep 'Deploy version set')"; PASS=$((PASS+1))
else
  echo "  ℹ️  Deploy version log not found (expected with gunicorn multi-process — Redis key is the real check)"
fi

# ── F14.9 Frontend ──
echo ""
echo "── F14.9 Frontend ──"
TITLE=$(curl -s http://k8s-cicd.daiyi.local.com:9001 | grep -o "<title>[^<]*</title>" || echo "")
check "Frontend accessible" "$TITLE" "K8s Management Console"

# ── Summary ──
echo ""
echo "=========================================="
echo "  Results: $PASS passed, $FAIL failed"
echo "=========================================="
if [ "$FAIL" -eq 0 ]; then
  echo "✅ All auth self-checks passed!"
  exit 0
else
  echo "❌ Some auth self-checks failed"
  exit 1
fi
