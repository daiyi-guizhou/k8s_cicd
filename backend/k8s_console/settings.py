"""Django settings for k8s_console."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "insecure-dev-key-change-me")

DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_prometheus",
    "apps.auth_app",
    "apps.resources",
    "apps.audit",
    "apps.clusters",
    "apps.deploy",
    "apps.monitoring",
    "apps.logging_api",
    "apps.observability",
    "apps.income.apps.IncomeConfig",
    
]

MIDDLEWARE = [
    "k8s_console.middleware.RequestIDMiddleware",
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "k8s_console.middleware.ApiLoggingMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "k8s_console.middleware.VersionCheckMiddleware",
    "k8s_console.middleware.TokenBlacklistMiddleware",
    "k8s_console.middleware.TokenRefreshMiddleware",
    "k8s_console.middleware.AuditLoggerMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "k8s_console.urls"

WSGI_APPLICATION = "k8s_console.wsgi.application"

STATIC_URL = "static/"

DATABASES = {
    "default": {
        "ENGINE": "django_prometheus.db.backends.mysql",
        "NAME": os.environ.get("MYSQL_DATABASE", "appdb"),
        "USER": os.environ.get("MYSQL_USER", "appuser"),
        "PASSWORD": os.environ.get("MYSQL_PASSWORD", "UserPass2024!"),
        "HOST": os.environ.get("MYSQL_HOST", "mysql.database.svc"),
        "PORT": os.environ.get("MYSQL_PORT", "3306"),
        "OPTIONS": {"charset": "utf8mb4"},
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_prometheus.cache.backends.redis.RedisCache",
        "LOCATION": f"redis://:{os.environ.get('REDIS_PASSWORD', 'RedisPass2024!')}"
                    f"@{os.environ.get('REDIS_HOST', 'redis.database.svc')}"
                    f":{os.environ.get('REDIS_PORT', '6379')}/1",
    }
}

REDIS_URL = (
    f"redis://:{os.environ.get('REDIS_PASSWORD', 'RedisPass2024!')}"
    f"@{os.environ.get('REDIS_HOST', 'redis.database.svc')}"
    f":{os.environ.get('REDIS_PORT', '6379')}"
)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.auth_app.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "UNAUTHENTICATED_USER": None,
}

TIME_ZONE = "Asia/Shanghai"
LANGUAGE_CODE = "zh-hans"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# K8s in-cluster config
K8S_IN_CLUSTER = True

# Audit middleware: paths excluded from audit logging
AUDIT_EXCLUDE_PATHS = ["/api/auth/login", "/api/auth/logout"]

# Builder Service
BUILDER_SERVICE_URL = os.environ.get("BUILDER_SERVICE_URL", "http://192.168.1.24:9008")

# ---------------------------------------------------------------------------
# Log path: shared volume between app container and filebeat sidecar
LOG_DIR = Path(os.environ.get("LOG_DIR", "/shared/logs"))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {
            "()": "k8s_console.logging_filters.RequestIDFilter",
            "service_name": os.environ.get('SERVICE_NAME', 'k8s-console-backend'),
        },
    },
    "formatters": {
        "json": {
            "()": "k8s_console.logging_filters.JsonFormatter",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / f"{os.environ.get('SERVICE_NAME', 'k8s-console-backend')}.json.log"),
            "maxBytes": 50 * 1024 * 1024,
            "backupCount": 3,
            "formatter": "json",
            "filters": ["request_id"],
        },
    },
    "loggers": {
        "api": {
            "handlers": ["file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["file"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["file"],
            "level": "WARNING",
            "propagate": False,
        },
        "django": {
            "handlers": ["file"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}