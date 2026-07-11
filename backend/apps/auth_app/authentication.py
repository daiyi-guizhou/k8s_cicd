"""Token-based authentication for DRF."""
import redis as _redis
from django.conf import settings
from apps.auth_app.models import User


def _get_redis():
    return _redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def get_user_from_token(token):
    """Validate token and return user, or None."""
    if not token:
        return None
    r = _get_redis()
    if r.exists(f"token:blacklist:{token}"):
        return None
    user_id = r.get(f"token:auth:{token}")
    if not user_id:
        return None
    try:
        return User.objects.get(id=int(user_id), is_active=True)
    except User.DoesNotExist:
        return None


class TokenAuthentication:
    """DRF-compatible token authentication class."""
    keyword = "Token"

    @staticmethod
    def authenticate(request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Token "):
            return None
        token = auth_header[6:].strip()
        user = get_user_from_token(token)
        if user is None:
            return None
        return (user, token)
