"""Observability views: ELK log search + Prometheus metrics proxy."""
import os
import json

import requests
from rest_framework.decorators import api_view

from apps.auth_app.models import User
from utils.response import success as success_resp, error, ERR_VALIDATION, ERR_PERMISSION_DENIED

# --- Configuration ---
ELASTICSEARCH_URL = os.environ.get(
    "ELASTICSEARCH_URL", "http://elasticsearch.logging.svc:9200"
)
PROMETHEUS_URL = os.environ.get(
    "PROMETHEUS_URL", "http://prometheus.monitoring.svc:9090"
)
REQUEST_TIMEOUT = 30


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


# =============================================================================
# Log Search (Elasticsearch)
# =============================================================================

@api_view(["POST"])
def log_search(request):
    """Search Kubernetes logs via Elasticsearch with filters and pagination."""
    if not _check_admin(request):
        return error(ERR_PERMISSION_DENIED, "需要管理员权限")

    try:
        body = request.data
        query_text = body.get("query", "").strip()
        namespace = body.get("namespace", "").strip()
        pod = body.get("pod", "").strip()
        start_time = body.get("start_time", "")
        end_time = body.get("end_time", "")
        page = max(1, int(body.get("page", 1)))
        page_size = min(200, max(1, int(body.get("page_size", 50))))

        # Build Elasticsearch query DSL
        must_clauses = []
        if query_text:
            must_clauses.append({
                "query_string": {
                    "query": query_text,
                    "default_operator": "AND",
                }
            })

        filters = []
        if namespace:
            filters.append({"term": {"kubernetes.namespace_name.keyword": namespace}})
        if pod:
            filters.append({"term": {"kubernetes.pod_name.keyword": pod}})
        if start_time or end_time:
            time_range = {}
            if start_time:
                time_range["gte"] = start_time
            if end_time:
                time_range["lte"] = end_time
            if time_range:
                filters.append({"range": {"@timestamp": time_range}})

        es_query = {
            "from": (page - 1) * page_size,
            "size": page_size,
            "sort": [{"@timestamp": {"order": "desc"}}],
            "query": {"bool": {}},
        }
        if must_clauses:
            es_query["query"]["bool"]["must"] = must_clauses
        if filters:
            es_query["query"]["bool"]["filter"] = filters
        if not must_clauses and not filters:
            es_query["query"] = {"match_all": {}}

        # Call Elasticsearch
        es_resp = requests.post(
            f"{ELASTICSEARCH_URL}/k8s-*/_search",
            json=es_query,
            timeout=REQUEST_TIMEOUT,
        )
        es_resp.raise_for_status()
        es_data = es_resp.json()

        # Parse hits
        total = es_data.get("hits", {}).get("total", {})
        total_count = total.get("value", 0) if isinstance(total, dict) else total
        hits = es_data.get("hits", {}).get("hits", [])

        items = []
        for h in hits:
            src = h.get("_source", {})
            k8s = src.get("kubernetes", {})
            items.append({
                "id": h.get("_id", ""),
                "timestamp": src.get("@timestamp", ""),
                "log": src.get("log", ""),
                "namespace": k8s.get("namespace_name", ""),
                "pod_name": k8s.get("pod_name", ""),
                "container_name": k8s.get("container_name", ""),
                "host": k8s.get("host", ""),
            })

        return success_resp(data={
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "items": items,
        })

    except requests.exceptions.Timeout:
        return error(ERR_VALIDATION, "Elasticsearch 查询超时")
    except requests.exceptions.ConnectionError:
        return error(ERR_VALIDATION, "无法连接到 Elasticsearch")
    except requests.exceptions.RequestException as e:
        return error(ERR_VALIDATION, f"Elasticsearch 查询失败: {str(e)}")
    except (ValueError, TypeError) as e:
        return error(ERR_VALIDATION, f"请求参数错误: {str(e)}")


@api_view(["POST"])
def log_stats(request):
    """Get log aggregation statistics (grouped by namespace/pod/level)."""
    if not _check_admin(request):
        return error(ERR_PERMISSION_DENIED, "需要管理员权限")

    try:
        body = request.data
        start_time = body.get("start_time", "")
        end_time = body.get("end_time", "")
        group_by = body.get("group_by", "namespace")

        # Map group_by to ES field
        field_map = {
            "namespace": "kubernetes.namespace_name.keyword",
            "pod": "kubernetes.pod_name.keyword",
            "level": "level.keyword",
        }
        field = field_map.get(group_by, "kubernetes.namespace_name.keyword")

        filters = []
        if start_time or end_time:
            time_range = {}
            if start_time:
                time_range["gte"] = start_time
            if end_time:
                time_range["lte"] = end_time
            if time_range:
                filters.append({"range": {"@timestamp": time_range}})

        es_query = {
            "size": 0,
            "query": {"bool": {"filter": filters}} if filters else {"match_all": {}},
            "aggs": {
                "by_field": {
                    "terms": {
                        "field": field,
                        "size": 50,
                        "order": {"_count": "desc"},
                    }
                }
            },
        }

        # Call Elasticsearch
        es_resp = requests.post(
            f"{ELASTICSEARCH_URL}/k8s-*/_search",
            json=es_query,
            timeout=REQUEST_TIMEOUT,
        )
        es_resp.raise_for_status()
        es_data = es_resp.json()

        buckets = es_data.get("aggregations", {}).get("by_field", {}).get("buckets", [])
        result = [{"key": b["key"], "count": b["doc_count"]} for b in buckets]

        return success_resp(data={"buckets": result, "group_by": group_by})

    except requests.exceptions.Timeout:
        return error(ERR_VALIDATION, "Elasticsearch 查询超时")
    except requests.exceptions.ConnectionError:
        return error(ERR_VALIDATION, "无法连接到 Elasticsearch")
    except requests.exceptions.RequestException as e:
        return error(ERR_VALIDATION, f"Elasticsearch 查询失败: {str(e)}")


# =============================================================================
# Metrics (Prometheus)
# =============================================================================

@api_view(["GET"])
def metric_query(request):
    """Prometheus instant query."""
    if not _check_admin(request):
        return error(ERR_PERMISSION_DENIED, "需要管理员权限")

    try:
        query_str = request.GET.get("query", "").strip()
        time_param = request.GET.get("time", "").strip()

        if not query_str:
            return error(ERR_VALIDATION, "缺少 query 参数")

        params = {"query": query_str}
        if time_param:
            params["time"] = time_param

        resp = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "success":
            return error(ERR_VALIDATION, f"Prometheus 查询失败: {data.get('error', 'unknown')}")

        return success_resp(data=data.get("data", {}))

    except requests.exceptions.Timeout:
        return error(ERR_VALIDATION, "Prometheus 查询超时")
    except requests.exceptions.ConnectionError:
        return error(ERR_VALIDATION, "无法连接到 Prometheus")
    except requests.exceptions.RequestException as e:
        return error(ERR_VALIDATION, f"Prometheus 查询失败: {str(e)}")


@api_view(["GET"])
def metric_range(request):
    """Prometheus range query."""
    if not _check_admin(request):
        return error(ERR_PERMISSION_DENIED, "需要管理员权限")

    try:
        query_str = request.GET.get("query", "").strip()
        start = request.GET.get("start", "").strip()
        end = request.GET.get("end", "").strip()
        step = request.GET.get("step", "15s").strip()

        if not query_str:
            return error(ERR_VALIDATION, "缺少 query 参数")
        if not start:
            return error(ERR_VALIDATION, "缺少 start 参数")
        if not end:
            return error(ERR_VALIDATION, "缺少 end 参数")

        params = {
            "query": query_str,
            "start": start,
            "end": end,
            "step": step,
        }

        resp = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query_range",
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "success":
            return error(ERR_VALIDATION, f"Prometheus 查询失败: {data.get('error', 'unknown')}")

        return success_resp(data=data.get("data", {}))

    except requests.exceptions.Timeout:
        return error(ERR_VALIDATION, "Prometheus 查询超时")
    except requests.exceptions.ConnectionError:
        return error(ERR_VALIDATION, "无法连接到 Prometheus")
    except requests.exceptions.RequestException as e:
        return error(ERR_VALIDATION, f"Prometheus 查询失败: {str(e)}")


@api_view(["GET"])
def metric_labels(request):
    """Get Prometheus label names or label values."""
    if not _check_admin(request):
        return error(ERR_PERMISSION_DENIED, "需要管理员权限")

    try:
        label_type = request.GET.get("type", "names").strip()
        name = request.GET.get("name", "").strip()

        if label_type == "values":
            if not name:
                return error(ERR_VALIDATION, "获取 label values 需要提供 name 参数")
            resp = requests.get(
                f"{PROMETHEUS_URL}/api/v1/label/{name}/values",
                timeout=REQUEST_TIMEOUT,
            )
        else:
            resp = requests.get(
                f"{PROMETHEUS_URL}/api/v1/labels",
                timeout=REQUEST_TIMEOUT,
            )

        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "success":
            return error(ERR_VALIDATION, f"Prometheus 查询失败: {data.get('error', 'unknown')}")

        return success_resp(data=data.get("data", []))

    except requests.exceptions.Timeout:
        return error(ERR_VALIDATION, "Prometheus 查询超时")
    except requests.exceptions.ConnectionError:
        return error(ERR_VALIDATION, "无法连接到 Prometheus")
    except requests.exceptions.RequestException as e:
        return error(ERR_VALIDATION, f"Prometheus 查询失败: {str(e)}")


# =============================================================================
# Health Status
# =============================================================================

@api_view(["GET"])
def observability_status(request):
    """Check health of Elasticsearch and Prometheus."""
    status_data = {
        "es_healthy": False,
        "prometheus_healthy": False,
        "es_info": {},
        "prom_info": {},
    }

    # Check Elasticsearch
    try:
        es_resp = requests.get(
            f"{ELASTICSEARCH_URL}/_cluster/health",
            timeout=5,
        )
        es_resp.raise_for_status()
        es_health = es_resp.json()
        status_data["es_healthy"] = es_health.get("status") in ("green", "yellow")
        status_data["es_info"] = {
            "cluster_name": es_health.get("cluster_name", ""),
            "status": es_health.get("status", ""),
            "nodes": es_health.get("number_of_nodes", 0),
            "data_nodes": es_health.get("number_of_data_nodes", 0),
        }
    except Exception as e:
        status_data["es_info"] = {"error": str(e)}

    # Check Prometheus
    try:
        prom_resp = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": "up"},
            timeout=5,
        )
        prom_resp.raise_for_status()
        prom_data = prom_resp.json()
        status_data["prometheus_healthy"] = prom_data.get("status") == "success"
        results = prom_data.get("data", {}).get("result", [])
        status_data["prom_info"] = {
            "targets_up": sum(1 for r in results if r.get("value", [None, "0"])[1] == "1"),
            "targets_total": len(results),
        }
    except Exception as e:
        status_data["prom_info"] = {"error": str(e)}

    return success_resp(data=status_data)

@api_view(["GET"])
def metrics_export(request):
    """Export custom Prometheus metrics (no auth required for scrape)."""
    from prometheus_client import generate_latest, CollectorRegistry, CONTENT_TYPE_LATEST
    from . import metrics as obs_metrics
    registry = CollectorRegistry()
    registry.register(obs_metrics.django_log_errors_total)
    registry.register(obs_metrics.api_request_latency)
    return HttpResponse(generate_latest(registry), content_type=CONTENT_TYPE_LATEST)