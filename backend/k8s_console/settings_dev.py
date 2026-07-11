"""Local development settings override."""
from .settings import *

DEBUG = True
DATABASES["default"]["HOST"] = "127.0.0.1"
CACHES["default"]["LOCATION"] = "redis://:RedisPass2024!@127.0.0.1:6379/1"
REDIS_URL = "redis://:RedisPass2024!@127.0.0.1:6379"
