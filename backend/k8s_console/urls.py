"""K8s Console URL configuration."""
from django.urls import path, include
from django.http import JsonResponse


def health(request):
    """Simple health check endpoint for Kubernetes probes."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("api/health", health, name="health"),
    path("api/", include("apps.auth_app.urls")),
    path("api/", include("apps.resources.urls")),
    path("api/", include("apps.audit.urls")),
    path("api/", include("apps.clusters.urls")),
]
