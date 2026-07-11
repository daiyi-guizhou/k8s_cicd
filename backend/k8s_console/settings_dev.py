"""Local development settings override."""
from .settings import *

DEBUG = True
DATABASES["default"]["HOST"] = "127.0.0.1"
DATABASES["default"]["PORT"] = "3306"
REDIS_URL = "redis://127.0.0.1:6379"
CACHES["default"]["LOCATION"] = "redis://127.0.0.1:6379/1"
