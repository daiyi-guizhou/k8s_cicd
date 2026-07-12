#!/bin/bash
# Start script for Django backend (used by Builder Service CI/CD deploy)
set -e

echo "[start_app.sh] Starting Django backend..."
echo "APP_NAME=${APP_NAME:-unknown}"
echo "APP_TAG=${APP_TAG:-unknown}"

# Apply migrations
python manage.py migrate --noinput

# Start gunicorn
exec gunicorn k8s_console.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120
