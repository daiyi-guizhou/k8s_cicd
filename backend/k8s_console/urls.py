"""K8s Console URL configuration."""
from django.conf.urls import include as old_include
from django.urls import path, include
from django.http import JsonResponse


def health(request):
    """Simple health check endpoint for Kubernetes probes."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("", old_include("django_prometheus.urls")),
    path("api/health", health, name="health"),
    path("api/", include("apps.auth_app.urls")),
    path("api/", include("apps.resources.urls")),
    path("api/", include("apps.audit.urls")),
    path("api/", include("apps.clusters.urls")),
    path("api/", include("apps.deploy.urls")),
    path("api/monitoring/", include("apps.monitoring.urls")),
    path("api/logging/", include("apps.logging_api.urls")),
    path("api/observability/", include("apps.observability.urls")),
    path("api/", include("apps.income.urls")),

]
