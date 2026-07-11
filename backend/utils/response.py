"""Unified JSON response format."""
from rest_framework.response import Response
from rest_framework import status


def success(data=None, message="ok"):
    return Response({"code": 0, "message": message, "data": data})


def error(code, message, detail=None, http_status=status.HTTP_400_BAD_REQUEST):
    body = {"code": code, "message": message}
    if detail is not None:
        body["detail"] = detail
    return Response(body, status=http_status)


# Error codes
ERR_AUTH_FAILED = 1001
ERR_TOKEN_INVALID = 1002
ERR_TOKEN_BLACKLISTED = 1003
ERR_USER_NOT_FOUND = 1004
ERR_USER_INACTIVE = 1005
ERR_WRONG_PASSWORD = 1006

ERR_RESOURCE_NOT_FOUND = 2001
ERR_K8S_API_ERROR = 2002
ERR_INVALID_YAML = 2003
ERR_UNSUPPORTED_RESOURCE = 2004
ERR_NAMESPACE_REQUIRED = 2005

ERR_PERMISSION_DENIED = 3001
ERR_VALIDATION = 3002
