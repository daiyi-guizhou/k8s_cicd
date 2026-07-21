
"""Logging API — Elasticsearch log query proxy."""
import json
import urllib.request
import urllib.error

from rest_framework.decorators import api_view

from apps.auth_app.models import User
from utils.response import success as success_resp, error, ERR_PERMISSION_DENIED

ES_URL = "http://elasticsearch.logging.svc:9200"


def _check_admin(request):
    token = request.META.get("HTTP_AUTHORIZATION", "").replace("Token ", "")
    if not token:
        return False
    try:
        user = User.objects.get(token=token)
        return getattr(user, "role", "") == "admin"
    except User.DoesNotExist:
        return False


def _es_request(endpoint: str, data: dict = None, method: str = "GET") -> dict:
    """Send request to Elasticsearch, return parsed JSON."""
    url = f"{ES_URL}/{endpoint}"
    body_bytes = None
    if data is not None:
        body_bytes = json.dumps(data).encode()
        method = "POST"

    req = urllib.request.Request(url, data=body_bytes, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        raise RuntimeError(f"Elasticsearch unreachable: {e.reason}")
    except Exception as e:
        raise RuntimeError(f"Elasticsearch error: {str(e)}")


def _extract_hit(hit: dict) -> dict:
    """Extract key fields from an ES hit."""
    src = hit.get("_source", {})
    kubernetes = src.get("kubernetes", {})
    return {
        "timestamp": src.get("@timestamp", ""),
        "namespace": kubernetes.get("namespace_name", ""),
        "pod": kubernetes.get("pod_name", ""),
        "container": kubernetes.get("container_name", ""),
        "log": src.get("log", ""),
        "level": _guess_level(src.get("log", "")),
    }


def _guess_level(log_line: str) -> str:
    """Infer log level from a log line."""
    upper = log_line.upper()
    if "ERROR" in upper or "FATAL" in upper:
        return "ERROR"
    if "WARN" in upper:
        return "WARNING"
    if "DEBUG" in upper:
        return "DEBUG"
    return "INFO"


@api_view(["POST"])
def search_logs(request):
    """Search logs in Elasticsearch."""
    if not _check_admin(request):
        return error(ERR_PERMISSION_DENIED, "需要管理员权限")

    q = request.data.get("q", "")
    namespace = request.data.get("namespace", "")
    app = request.data.get("app", "")
    level = request.data.get("level", "")
    size = min(request.data.get("size", 50), 200)

    # Build ES bool query
    must = []
    if q:
        must.append({"multi_match": {"query": q, "fields": ["log", "kubernetes.pod_name", "kubernetes.namespace_name"]}})
    if namespace:
        must.append({"term": {"kubernetes.namespace_name": namespace}})
    if app:
        must.append({"term": {"kubernetes.labels.app": app}})
    if level:
        must.append({"match_phrase": {"log": level}})

    query_body = {
        "size": size,
        "sort": [{"@timestamp": {"order": "desc"}}],
        "query": {"bool": {"must": must}} if must else {"match_all": {}},
    }

    try:
        result = _es_request("k8s-*/_search", query_body)
        hits = result.get("hits", {})
        return success_resp({
            "total": hits.get("total", {}).get("value", 0),
            "hits": [_extract_hit(h) for h in hits.get("hits", [])],
        })
    except RuntimeError as e:
        return error(500, str(e))


@api_view(["POST"])
def log_namespaces(request):
    """Get list of namespaces that have logs."""
    if not _check_admin(request):
        return error(ERR_PERMISSION_DENIED, "需要管理员权限")

    try:
        result = _es_request("k8s-*/_search", {
            "size": 0,
            "aggs": {
                "namespaces": {
                    "terms": {"field": "kubernetes.namespace_name", "size": 50}
                }
            }
        })
        buckets = result.get("aggregations", {}).get("namespaces", {}).get("buckets", [])
        return success_resp({
            "namespaces": [{"name": b["key"], "count": b["doc_count"]} for b in buckets]
        })
    except RuntimeError as e:
        return error(500, str(e))


@api_view(["POST"])
def log_apps(request):
    """Get list of apps in a namespace that have logs."""
    if not _check_admin(request):
        return error(ERR_PERMISSION_DENIED, "需要管理员权限")

    namespace = request.data.get("namespace", "")
    must = [{"term": {"kubernetes.namespace_name": namespace}}] if namespace else []

    try:
        result = _es_request("k8s-*/_search", {
            "size": 0,
            "query": {"bool": {"must": must}} if must else {"match_all": {}},
            "aggs": {
                "apps": {
                    "terms": {"field": "kubernetes.labels.app", "size": 50}
                }
            }
        })
        buckets = result.get("aggregations", {}).get("apps", {}).get("buckets", [])
        return success_resp({
            "apps": [{"name": b["key"], "count": b["doc_count"]} for b in buckets]
        })
    except RuntimeError as e:
        return error(500, str(e))


@api_view(["POST"])
def log_stats(request):
    """Get log statistics: counts by level and namespace."""
    if not _check_admin(request):
        return error(ERR_PERMISSION_DENIED, "需要管理员权限")

    try:
        # Level counts
        level_result = _es_request("k8s-*/_search", {
            "size": 0,
            "query": {
                "range": {"@timestamp": {"gte": "now-24h"}}
            },
            "aggs": {
                "by_level": {
                    "filters": {
                        "filters": {
                            "ERROR": {"match_phrase": {"log": "ERROR"}},
                            "WARNING": {"match_phrase": {"log": "WARNING"}},
                            "INFO": {"match_all": {}},
                        }
                    }
                }
            }
        })
        by_level = level_result.get("aggregations", {}).get("by_level", {}).get("buckets", {})

        # Index size
        indices_result = _es_request("_cat/indices/k8s-*?format=json")
        total_size_bytes = sum(int(i.get("store.size", 0)) for i in indices_result if isinstance(i, dict))

        return success_resp({
            "error_count": by_level.get("ERROR", {}).get("doc_count", 0),
            "warning_count": by_level.get("WARNING", {}).get("doc_count", 0),
            "info_count": by_level.get("INFO", {}).get("doc_count", 0),
            "index_size_mb": round(total_size_bytes / 1024 / 1024, 1) if total_size_bytes else 0,
        })
    except RuntimeError as e:
        return error(500, str(e))
