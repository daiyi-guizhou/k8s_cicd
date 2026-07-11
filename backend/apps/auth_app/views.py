"""Auth views: login, logout, change-password, user management."""
import hashlib
import json
import secrets
from datetime import datetime, timedelta

import redis

from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny

from apps.auth_app.models import User
from utils.response import (
    success, error,
    ERR_AUTH_FAILED, ERR_TOKEN_BLACKLISTED,
    ERR_USER_NOT_FOUND, ERR_USER_INACTIVE, ERR_WRONG_PASSWORD,
    ERR_PERMISSION_DENIED, ERR_VALIDATION,
)


def _get_redis():
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def _generate_token():
    return secrets.token_hex(20)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def login(request):
    """Login: {username, password} → {token, user}"""

    username = request.data.get("username", "").strip()
    password = request.data.get("password", "")

    if not username or not password:
        return error(ERR_AUTH_FAILED, "用户名和密码不能为空")

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return error(ERR_AUTH_FAILED, "用户名或密码错误")

    if not user.is_active:
        return error(ERR_USER_INACTIVE, "用户已被禁用")

    if not check_password(password, user.password):
        return error(ERR_AUTH_FAILED, "用户名或密码错误")

    token = _generate_token()
    r = _get_redis()

    # 8h sliding TTL for auth key
    auth_ttl = 28800  # 8 hours in seconds

    # 24h absolute expiry for meta key
    meta_ttl = 86400  # 24 hours in seconds
    now = datetime.now()
    absolute_expiry = now + timedelta(hours=24)
    deploy_version = r.get("deploy:version") or "initial"

    meta = json.dumps({
        "user_id": str(user.id),
        "login_at": now.isoformat(),
        "absolute_expiry": absolute_expiry.isoformat(),
        "deploy_version": deploy_version,
    })

    r.setex(f"token:auth:{token}", auth_ttl, str(user.id))
    r.setex(f"token:meta:{token}", meta_ttl, meta)

    return success(data={
        "token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
        },
    }, message="登录成功")


@api_view(["POST"])
def logout(request):
    """Logout: blacklist current token in Redis with TTL."""
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if auth_header.startswith("Token "):
        token = auth_header[6:].strip()
        r = _get_redis()
        user_id = r.get(f"token:auth:{token}")
        ttl = r.ttl(f"token:auth:{token}")
        if ttl > 0:
            r.setex(f"token:blacklist:{token}", ttl, user_id or "")
        r.delete(f"token:auth:{token}")
        r.delete(f"token:meta:{token}")
    return success(message="已登出")


@api_view(["POST"])
def change_password(request):
    """Self password change: {old_password, new_password}"""
    if not isinstance(request.user, User):
        return error(ERR_AUTH_FAILED, "未认证")

    old_password = request.data.get("old_password", "")
    new_password = request.data.get("new_password", "")

    if not old_password or not new_password:
        return error(ERR_VALIDATION, "旧密码和新密码不能为空")

    if len(new_password) < 6:
        return error(ERR_VALIDATION, "新密码长度至少6位")

    if not check_password(old_password, request.user.password):
        return error(ERR_WRONG_PASSWORD, "旧密码错误")

    request.user.password = make_password(new_password)
    request.user.save()
    return success(message="密码修改成功")


def _require_admin(user):
    """Return error response if user is not admin, None otherwise."""
    if not isinstance(user, User) or user.role != "admin":
        return error(ERR_PERMISSION_DENIED, "仅管理员可执行此操作")
    return None


@api_view(["POST"])
def user_create(request):
    """Admin creates user: {username, role} → {username, password}"""
    admin_err = _require_admin(request.user)
    if admin_err:
        return admin_err

    username = request.data.get("username", "").strip()
    role = request.data.get("role", "user").strip()

    if not username:
        return error(ERR_VALIDATION, "用户名不能为空")

    if role not in ("admin", "user"):
        return error(ERR_VALIDATION, "角色必须为 admin 或 user")

    if User.objects.filter(username=username).exists():
        return error(ERR_VALIDATION, "用户名已存在")

    random_password = secrets.token_urlsafe(8)
    user = User(
        username=username,
        role=role,
        password=make_password(random_password),
    )
    user.save()

    return success(data={
        "username": user.username,
        "password": random_password,
    }, message=f"用户 {username} 创建成功")


@api_view(["POST"])
def user_list(request):
    """Admin lists all users."""
    admin_err = _require_admin(request.user)
    if admin_err:
        return admin_err

    users = User.objects.all().values("id", "username", "role", "is_active", "created_at")
    return success(data=list(users))


@api_view(["POST"])
def user_toggle_active(request):
    """Admin enable/disable user: {id}"""
    admin_err = _require_admin(request.user)
    if admin_err:
        return admin_err

    user_id = request.data.get("id")
    if user_id is None:
        return error(ERR_VALIDATION, "缺少用户ID")

    try:
        target_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return error(ERR_USER_NOT_FOUND, "用户不存在")

    if target_user.id == request.user.id:
        return error(ERR_VALIDATION, "不能禁用自己")

    target_user.is_active = not target_user.is_active
    target_user.save()

    action_text = "启用" if target_user.is_active else "禁用"
    return success(message=f"用户 {target_user.username} 已{action_text}")


@api_view(["POST"])
def user_reset_password(request):
    """Admin resets user password: {id} → {username, password}"""
    admin_err = _require_admin(request.user)
    if admin_err:
        return admin_err

    user_id = request.data.get("id")
    if user_id is None:
        return error(ERR_VALIDATION, "缺少用户ID")

    try:
        target_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return error(ERR_USER_NOT_FOUND, "用户不存在")

    new_password = secrets.token_urlsafe(8)
    target_user.password = make_password(new_password)
    target_user.save()

    return success(data={
        "username": target_user.username,
        "password": new_password,
    }, message="密码已重置")
