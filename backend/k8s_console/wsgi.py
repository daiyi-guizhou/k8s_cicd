"""WSGI config for k8s_console."""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "k8s_console.settings")
application = get_wsgi_application()
