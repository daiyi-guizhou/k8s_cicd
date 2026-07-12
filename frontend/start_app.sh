#!/bin/bash
set -e
echo "[start_app.sh] Starting Vue frontend..."
echo "APP_NAME=${APP_NAME:-unknown}"
echo "APP_TAG=${APP_TAG:-unknown}"
# Copy nginx config if provided
if [ -f /nginx.conf ]; then
  cp /nginx.conf /etc/nginx/conf.d/default.conf
fi
exec nginx -g "daemon off;"
