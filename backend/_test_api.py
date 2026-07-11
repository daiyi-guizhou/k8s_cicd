import django
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'k8s_console.settings_dev')
django.setup()

# Test database connection
from django.db import connections
try:
    connections['default'].cursor()
    print("DB connection: OK")
except Exception as e:
    print(f"DB connection FAILED: {e}")

# Test Redis
import redis
try:
    r = redis.Redis.from_url("redis://:RedisPass2024!@127.0.0.1:6379", decode_responses=True)
    r.ping()
    print("Redis connection: OK")
except Exception as e:
    print(f"Redis connection FAILED: {e}")

# Test login endpoint
from django.test import Client, RequestFactory
from django.urls import resolve
try:
    client = Client()
    resp = client.post('/api/auth/login', {'username': 'admin', 'password': 'admin'}, content_type='application/json')
    print(f"Login test (GET): {resp.status_code}")
    print(f"Response: {resp.content[:500]}")
except Exception as e:
    print(f"Login test FAILED: {e}")
    import traceback
    traceback.print_exc()
