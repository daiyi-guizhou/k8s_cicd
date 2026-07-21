
from django.urls import path
from . import views

urlpatterns = [
    path("search", views.search_logs, name="logging_search"),
    path("namespaces", views.log_namespaces, name="logging_namespaces"),
    path("apps", views.log_apps, name="logging_apps"),
    path("stats", views.log_stats, name="logging_stats"),
]
