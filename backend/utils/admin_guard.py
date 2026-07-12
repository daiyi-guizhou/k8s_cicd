"""Admin permission guard — reusable across views."""
from apps.auth_app.models import User
from utils.response import error, ERR_PERMISSION_DENIED


def require_admin(user):
    """Return error response if user is not admin, None otherwise."""
    if not isinstance(user, User) or user.role != "admin":
        return error(ERR_PERMISSION_DENIED, "仅管理员可执行此操作")
    return None
