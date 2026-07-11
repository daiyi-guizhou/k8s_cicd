"""Audit log query views."""
from datetime import datetime, timedelta

from django.db.models import Q
from rest_framework.decorators import api_view

from apps.audit.models import AuditLog
from utils.response import success, error, ERR_VALIDATION, ERR_PERMISSION_DENIED


@api_view(["POST"])
def audit_list(request):
    """List audit logs with optional filters."""
    if request.user.role != "admin":
        return error(ERR_PERMISSION_DENIED, "仅管理员可查看审计日志")

    queryset = AuditLog.objects.select_related("user").all()

    action = request.data.get("action", "").strip()
    if action:
        queryset = queryset.filter(action=action)

    resource_type = request.data.get("resource_type", "").strip()
    if resource_type:
        queryset = queryset.filter(resource_type=resource_type)

    namespace = request.data.get("namespace", "").strip()
    if namespace:
        queryset = queryset.filter(namespace=namespace)

    result = request.data.get("result", "").strip()
    if result:
        queryset = queryset.filter(result=result)

    start_time = request.data.get("start_time", "").strip()
    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time)
            queryset = queryset.filter(created_at__gte=start_dt)
        except ValueError:
            return error(ERR_VALIDATION, "start_time 格式无效，请使用 ISO 8601 格式")

    end_time = request.data.get("end_time", "").strip()
    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time)
            queryset = queryset.filter(created_at__lte=end_dt)
        except ValueError:
            return error(ERR_VALIDATION, "end_time 格式无效，请使用 ISO 8601 格式")

    page = max(1, request.data.get("page", 1) or 1)
    page_size = min(100, max(1, request.data.get("page_size", 20) or 20))
    offset = (page - 1) * page_size

    total = queryset.count()
    logs = queryset[offset:offset + page_size]

    items = []
    for log in logs:
        items.append({
            "id": log.id,
            "username": log.user.username if log.user else None,
            "action": log.action,
            "action_display": log.get_action_display(),
            "resource_type": log.resource_type,
            "resource_name": log.resource_name,
            "namespace": log.namespace,
            "detail": log.detail,
            "result": log.result,
            "error_msg": log.error_msg,
            "created_at": log.created_at.isoformat(),
        })

    return success(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })
