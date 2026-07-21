
from django.urls import path
from . import views

urlpatterns = [
    path("overview", views.overview, name="monitoring_overview"),
    path("nodes", views.nodes, name="monitoring_nodes"),
    path("pods", views.pods, name="monitoring_pods"),
]
