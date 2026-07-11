"""Middleware: AuditLoggerMiddleware and TokenBlacklistMiddleware."""
import json
from django.conf import settings
from django.http import JsonResponse, RawPostDataException
from apps.auth_app.authentication import get_user_from_token
import redis as _redis
from django.conf import settings as _settings

def _get_redis():
    return _redis.Redis.from_url(_settings.REDIS_URL, decode_responses=True)


class TokenBlacklistMiddleware:
    """Check if token is blacklisted before auth processing."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Token "):
            token = auth_header[6:].strip()
            r = _get_redis()
            if r.exists(f"token:blacklist:{token}"):
                return JsonResponse(
                    {"code": 1003, "message": "Token 已被登出", "detail": ""},
                    status=401,
                )
        return self.get_response(request)


class AuditLoggerMiddleware:
    """Log all POST requests (except excluded paths) to AuditLog."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.method != "POST":
            return response

        path = request.path.rstrip("/")
        for excluded in settings.AUDIT_EXCLUDE_PATHS:
            if path.startswith(excluded.rstrip("/")):
                return response

        user = None
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Token "):
            token = auth_header[6:].strip()
            user = get_user_from_token(token)

        action_map = {
            "resources/scale": "scale",
            "resources/rollback": "rollback",
            "resources/delete": "delete",
            "resources/apply": "apply",
            "users/create": "create_user",
            "users/toggle-active": "toggle_active",
            "users/reset-password": "reset_password",
            "auth/change-password": "change_password",
        }

        action = "apply"
        for path_prefix, action_name in action_map.items():
            if path.startswith(f"/api/{path_prefix}"):
                action = action_name
                break

        resource_type = ""
        resource_name = ""
        namespace = ""

        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except (json.JSONDecodeError, UnicodeDecodeError, RawPostDataException):
            body = {}

        resource_type = body.get("resource_type", "")
        resource_name = body.get("name", "")
        namespace = body.get("namespace", "")

        # Resolve cluster_id to cluster name
        cluster_name = ""
        cluster_id_from_body = body.get("cluster_id")
        if cluster_id_from_body:
            try:
                from apps.clusters.models import Cluster
                c = Cluster.objects.only("name").get(id=cluster_id_from_body)
                cluster_name = c.name
            except Exception:
                cluster_name = str(cluster_id_from_body)

        is_success = 200 <= response.status_code < 300
        result = "success" if is_success else "fail"
        error_msg = ""
        if not is_success:
            try:
                resp_data = json.loads(response.content.decode("utf-8"))
                error_msg = resp_data.get("message", "")
            except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                error_msg = str(response.status_code)

        detail = {}
        if action == "scale":
            detail = {"replicas": body.get("replicas")}
        elif action == "rollback":
            detail = {"revision": body.get("revision")}

        from apps.audit.models import AuditLog
        AuditLog.objects.create(
            user=user,
            action=action,
            resource_type=resource_type,
            resource_name=resource_name,
            namespace=namespace or "",
            cluster_name=cluster_name,
            detail=detail,
            result=result,
            error_msg=error_msg,
        )

        return response
