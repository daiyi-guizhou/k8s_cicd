"""K8s API error wrapping utilities."""
from kubernetes.client.rest import ApiException


def wrap_k8s_error(exc):
    """Convert a kubernetes ApiException into (code, message, detail) tuple."""
    if not isinstance(exc, ApiException):
        return 2002, "K8s API 调用失败", str(exc)

    status_code = exc.status
    body = {}
    try:
        import json
        body = json.loads(exc.body) if exc.body else {}
    except (json.JSONDecodeError, TypeError):
        pass

    if status_code == 404:
        return 2001, "资源不存在", exc.reason or str(exc)
    elif status_code == 403:
        return 3001, "权限不足", body.get("message", exc.reason or str(exc))
    elif status_code == 409:
        return 2002, "资源冲突", body.get("message", exc.reason or str(exc))
    elif status_code == 422:
        return 3002, "请求验证失败", body.get("message", exc.reason or str(exc))
    else:
        return 2002, f"K8s API 错误 (HTTP {status_code})", body.get("message", exc.reason or str(exc))
