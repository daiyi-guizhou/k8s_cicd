
"""Observability URL configuration — ELK logs + Prometheus metrics."""
from django.urls import path

from . import views

urlpatterns = [
    # Log search (Elasticsearch proxy)
    path("logs/search", views.log_search, name="observability-log-search"),
    path("logs/stats", views.log_stats, name="observability-log-stats"),
    # Metrics (Prometheus proxy)
    path("metrics/query", views.metric_query, name="observability-metric-query"),
    path("metrics/range", views.metric_range, name="observability-metric-range"),
    path("metrics/labels", views.metric_labels, name="observability-metric-labels"),
    path("metrics/export", views.metrics_export, name="observability-metrics-export"),
    # Health status
    path("status", views.observability_status, name="observability-status"),
]
