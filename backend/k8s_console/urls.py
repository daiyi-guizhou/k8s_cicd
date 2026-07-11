"""K8s Console URL configuration."""
from django.urls import path, include

urlpatterns = [
    path("api/", include("apps.auth_app.urls")),
    path("api/", include("apps.resources.urls")),
    path("api/", include("apps.audit.urls")),
]
