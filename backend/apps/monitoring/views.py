
"""Monitoring API — Prometheus metrics proxy."""
import json
import urllib.request
import urllib.error

from rest_framework.decorators import api_view

from apps.auth_app.models import User
from utils.response import success as success_resp, error, ERR_PERMISSION_DENIED

PROMETHEUS_URL = "http://prometheus.monitoring.svc:9090"


def _check_admin(request):
    """Return True if the authenticated user has admin role."""
    token = request.META.get("HTTP_AUTHORIZATION", "").replace("Token ", "")
    if not token:
        return False
    try:
        user = User.objects.get(token=token)
        return getattr(user, "role", "") == "admin"
    except User.DoesNotExist:
        return False


def _prom_query(query: str) -> dict:
    """Execute an instant Prometheus query, return parsed result."""
    url = f"{PROMETHEUS_URL}/api/v1/query?query={urllib.request.quote(query)}"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        raise RuntimeError(f"Prometheus unreachable: {e.reason}")
    except Exception as e:
        raise RuntimeError(f"Prometheus error: {str(e)}")


def _scalar(query: str) -> float:
    """Run a query expected to return a scalar (vector with one result)."""
    data = _prom_query(query)
    results = data.get("data", {}).get("result", [])
    if results:
        return float(results[0].get("value", [None, 0])[1])
    return 0.0


@api_view(["POST"])
def overview(request):
    """GET cluster overview: CPU, memory, pods, namespaces, disk."""
    if not _check_admin(request):
        return error(ERR_PERMISSION_DENIED, "需要管理员权限")

    try:
        cpu = _scalar(
            '100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'
        )
        memory = _scalar(
            '(1 - avg(node_memory_MemAvailable_bytes) / avg(node_memory_MemTotal_bytes)) * 100'
        )
        pod_count = _scalar("count(kube_pod_info)")
        ns_count = _scalar("count(kube_namespace_created)")
        disk = _scalar(
            'max((1 - node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100)'
        )

        return success_resp({
            "cpu_percent": round(cpu, 1),
            "memory_percent": round(memory, 1),
            "pod_count": int(pod_count),
            "namespace_count": int(ns_count),
            "disk_percent": round(disk, 1),
        })
    except RuntimeError as e:
        return error(500, str(e))


@api_view(["POST"])
def nodes(request):
    """List node metrics: name, CPU%, memory%, disk%, status."""
    if not _check_admin(request):
        return error(ERR_PERMISSION_DENIED, "需要管理员权限")

    try:
        node_info = _prom_query("kube_node_info")
        nodes = []
        for item in node_info.get("data", {}).get("result", []):
            node_name = item.get("metric", {}).get("node", "unknown")
            nodes.append({
                "name": node_name,
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "disk_percent": 0.0,
                "status": "Ready",
                "pod_count": 0,
            })

        # Enrich with per-node metrics
        for node in nodes:
            instance = node["name"]
            try:
                node["cpu_percent"] = round(_scalar(
                    f'100 - (avg by (instance)(rate(node_cpu_seconds_total{{mode="idle",instance=~"{instance}.+"}}[5m])) * 100)'
                ), 1)
            except Exception:
                pass
            try:
                node["memory_percent"] = round(_scalar(
                    f'(1 - node_memory_MemAvailable_bytes{{instance=~"{instance}.+"}} / node_memory_MemTotal_bytes{{instance=~"{instance}.+"}}) * 100'
                ), 1)
            except Exception:
                pass
            try:
                node["disk_percent"] = round(_scalar(
                    f'max((1 - node_filesystem_avail_bytes{{mountpoint="/",instance=~"{instance}.+"}} / node_filesystem_size_bytes{{mountpoint="/",instance=~"{instance}.+"}}) * 100)'
                ), 1)
            except Exception:
                pass

        return success_resp({"nodes": nodes})
    except RuntimeError as e:
        return error(500, str(e))


@api_view(["POST"])
def pods(request):
    """List pod CPU/Memory for a given namespace."""
    if not _check_admin(request):
        return error(ERR_PERMISSION_DENIED, "需要管理员权限")

    namespace = request.data.get("namespace", "prd")

    try:
        cpu_query = (
            f'sum(rate(container_cpu_usage_seconds_total{{namespace="{namespace}",container!=""}}[5m])) '
            f'by (pod) * 100'
        )
        mem_query = (
            f'sum(container_memory_working_set_bytes{{namespace="{namespace}",container!=""}}) '
            f'by (pod) / 1024 / 1024'
        )

        cpu_data = _prom_query(cpu_query)
        mem_data = _prom_query(mem_query)

        pods_map = {}
        for item in cpu_data.get("data", {}).get("result", []):
            pod = item.get("metric", {}).get("pod", "unknown")
            pods_map[pod] = {
                "pod": pod,
                "cpu_cores": round(float(item.get("value", [None, 0])[1]), 3),
                "memory_mb": 0.0,
            }

        for item in mem_data.get("data", {}).get("result", []):
            pod = item.get("metric", {}).get("pod", "unknown")
            if pod in pods_map:
                pods_map[pod]["memory_mb"] = round(float(item.get("value", [None, 0])[1]), 1)
            else:
                pods_map[pod] = {
                    "pod": pod,
                    "cpu_cores": 0.0,
                    "memory_mb": round(float(item.get("value", [None, 0])[1]), 1),
                }

        return success_resp({"pods": list(pods_map.values()), "namespace": namespace})
    except RuntimeError as e:
        return error(500, str(e))
