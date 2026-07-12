"""Middleware: ApiLogging, AuditLogger, TokenBlacklist, VersionCheck, TokenRefresh."""
import json
import logging
import time
from datetime import datetime
from django.conf import settings
from django.http import JsonResponse, RawPostDataException
from apps.auth_app.authentication import get_user_from_token
import redis as _redis
from django.conf import settings as _settings

logger = logging.getLogger(__name__)
api_logger = logging.getLogger("api")


class ApiLoggingMiddleware:
    """Log every API request and response — method, URI, params, body, status, duration.

    Register this as the **first** middleware so it wraps the entire stack.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()

        # ---------- request ----------
        method = request.method
        uri = request.build_absolute_uri()
        # GET query params
        params = dict(request.GET.items()) if request.GET else None
        # POST / PUT / PATCH body
        body = None
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            body = request.body  # raw bytes — decode downstream if needed

        try:
            body_str = body.decode("utf-8") if body else None
            if body_str and len(body_str) > 2000:
                body_str = body_str[:2000] + "...<truncated>"
        except Exception:
            body_str = "<non-utf8>"

        api_logger.info(
            ">>> %s %s | params=%s | body=%s",
            method, uri, params, body_str,
        )

        # ---------- response ----------
        response = self.get_response(request)

        elapsed_ms = (time.monotonic() - start) * 1000
        status_code = response.status_code
        # Try to log response body for non-2xx or short responses
        resp_body = ""
        if hasattr(response, "content"):
            try:
                raw = response.content.decode("utf-8")
                resp_body = raw if len(raw) <= 1000 else raw[:1000] + "...<truncated>"
            except Exception:
                resp_body = "<binary>"

        api_logger.info(
            "<<< %s %s → %s | %.1fms | resp=%s",
            method, uri, status_code, elapsed_ms, resp_body,
        )

        return response

def _get_redis():
    return _redis.Redis.from_url(_settings.REDIS_URL, decode_responses=True)


class VersionCheckMiddleware:
    """Detect backend redeploy by comparing token's deploy_version with current.

    On first __init__, writes a deploy version (current timestamp) to Redis.
    On each request with a Token, compares the token's stored deploy_version
    with the current Redis value. A mismatch means the backend was redeployed,
    and the request is rejected with code 1004.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Write deploy version on every startup (redeploy = new version)
        try:
            r = _get_redis()
            version = datetime.now().isoformat()
            r.set("deploy:version", version)
            logger.info(f"Deploy version set: {version}")
        except Exception:
            logger.warning("VersionCheckMiddleware: unable to set deploy:version", exc_info=True)

    def __call__(self, request):
        # Skip for login endpoint
        path = request.path.rstrip("/")
        if path.endswith("/auth/login"):
            return self.get_response(request)

        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Token "):
            return self.get_response(request)

        token = auth_header[6:].strip()
        try:
            r = _get_redis()
            current_version = r.get("deploy:version")
            if current_version is None:
                # No deploy version yet (first deploy before any login) — skip
                return self.get_response(request)

            meta_raw = r.get(f"token:meta:{token}")
            if meta_raw is None:
                # Token expired or invalid — let downstream middleware handle it
                return self.get_response(request)

            meta = json.loads(meta_raw)
            token_version = meta.get("deploy_version", "")

            if token_version and token_version != current_version:
                # Backend was redeployed since this token was issued
                # Clean up the stale token
                r.delete(f"token:auth:{token}")
                r.delete(f"token:meta:{token}")
                return JsonResponse(
                    {"code": 1004, "message": "系统已更新，请刷新页面后重新登录", "detail": ""},
                    status=401,
                )
        except Exception:
            logger.warning("VersionCheckMiddleware: Redis error", exc_info=True)
            # On Redis error, let the request through — don't block users

        return self.get_response(request)


class TokenRefreshMiddleware:
    """Refresh token TTL on each request and enforce 24h absolute expiry.

    On each authenticated request, renews the token:auth key TTL to 8h.
    Checks the absolute_expiry in token:meta — if exceeded, rejects with 1007.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Token "):
            return self.get_response(request)

        token = auth_header[6:].strip()
        try:
            r = _get_redis()
            meta_raw = r.get(f"token:meta:{token}")
            if meta_raw is None:
                # No meta key — token may have expired (meta has 24h TTL)
                return JsonResponse(
                    {"code": 1007, "message": "登录已过期，请重新登录", "detail": ""},
                    status=401,
                )

            meta = json.loads(meta_raw)
            # Check absolute expiry
            absolute_expiry_str = meta.get("absolute_expiry")
            if absolute_expiry_str:
                absolute_expiry = datetime.fromisoformat(absolute_expiry_str)
                if datetime.now() > absolute_expiry:
                    # Absolute expiry reached, clean up and reject
                    r.delete(f"token:auth:{token}")
                    r.delete(f"token:meta:{token}")
                    return JsonResponse(
                        {"code": 1007, "message": "登录已过期，请重新登录", "detail": ""},
                        status=401,
                    )

            # Refresh sliding TTL — reset auth key to 8h
            user_id = r.get(f"token:auth:{token}")
            if user_id:
                r.expire(f"token:auth:{token}", 28800)  # 8 hours
        except Exception:
            logger.warning("TokenRefreshMiddleware: Redis error", exc_info=True)
            # On Redis error, let the request through

        return self.get_response(request)


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
