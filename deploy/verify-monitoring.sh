
#!/bin/bash
# ============================================
#  Verify ELK + Prometheus deployment health
#  Usage: bash deploy/verify-monitoring.sh
# ============================================
set -e

echo "=========================================="
echo "  Verifying Logging (ELK Stack)"
echo "=========================================="

echo "--- Elasticsearch ---"
kubectl get pods -n prd -l app=elasticsearch 2>/dev/null || echo "  (no pods)"

echo "--- Fluentd ---"
kubectl get pods -n prd -l app=fluentd 2>/dev/null || echo "  (no pods)"

echo "--- Kibana ---"
kubectl get pods -n prd -l app=kibana 2>/dev/null || echo "  (no pods)"

echo ""
echo "--- ES Cluster Health ---"
kubectl exec -n prd statefulset/elasticsearch -- curl -s http://localhost:9200/_cluster/health 2>/dev/null | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    print(f'  Status: {d.get(\"status\",\"?\")}')
    print(f'  Nodes: {d.get(\"number_of_nodes\",\"?\")}')
    print(f'  Data Nodes: {d.get(\"number_of_data_nodes\",\"?\")}')
    print(f'  Active Shards: {d.get(\"active_shards\",\"?\")}')
except:
    print('  (ES not ready or unreachable)')
" 2>/dev/null || echo "  (ES not ready yet)"

echo ""
echo "=========================================="
echo "  Verifying Monitoring (Prometheus + Grafana)"
echo "=========================================="

echo "--- Prometheus ---"
kubectl get pods -n prd -l app=prometheus 2>/dev/null || echo "  (no pods)"

echo "--- Node Exporter ---"
kubectl get pods -n prd -l app=node-exporter 2>/dev/null || echo "  (no pods)"

echo "--- Grafana ---"
kubectl get pods -n prd -l app=grafana 2>/dev/null || echo "  (no pods)"

echo ""
echo "--- Prometheus Targets ---"
kubectl exec -n prd deploy/prometheus -- wget -qO- http://localhost:9090/api/v1/targets 2>/dev/null | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    for t in d.get('data',{}).get('activeTargets',[]):
        job=t['labels'].get('job','?')
        health=t.get('health','?')
        print(f'  {job}: {health}')
except:
    print('  (Prometheus not ready or unreachable)')
" 2>/dev/null || echo "  (Prometheus not ready)"

echo ""
echo "--- In-Cluster Test ---"
LOCAL_ES=$(kubectl exec -n prd deploy/k8s-console-backend -- python -c "
import urllib.request,json
try:
    r=urllib.request.urlopen('http://elasticsearch.prd.svc:9200/_cluster/health',timeout=5)
    d=json.loads(r.read())
    print(f'ES: {d.get(\"status\",\"?\")}')
except Exception as e:
    print(f'ES ERR: {e}')
" 2>/dev/null || echo "  ES: unreachable from pod")
echo "  $LOCAL_ES"

LOCAL_PROM=$(kubectl exec -n prd deploy/k8s-console-backend -- python -c "
import urllib.request,json
try:
    r=urllib.request.urlopen('http://prometheus.prd.svc:9090/api/v1/query?query=up',timeout=5)
    d=json.loads(r.read())
    print(f'Prometheus: {d.get(\"status\",\"?\")}')
except Exception as e:
    print(f'Prometheus ERR: {e}')
" 2>/dev/null || echo "  Prometheus: unreachable from pod")
echo "  $LOCAL_PROM"

echo ""
echo "=== Verification Complete ==="
echo ""
echo "  Kibana:  http://kibana.logging.local (hosts: 127.0.0.1 kibana.logging.local)"
echo "  Grafana: http://grafana.monitoring.local (hosts: 127.0.0.1 grafana.monitoring.local, admin/admin)"
echo "  Web Console /monitoring (metrics) and /logging (log explorer)"
