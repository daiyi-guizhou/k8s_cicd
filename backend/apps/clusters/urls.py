"""Clusters app URL config."""
from django.urls import path
from . import views

urlpatterns = [
    path("clusters/list", views.cluster_list, name="cluster_list"),
    path("clusters/create", views.cluster_create, name="cluster_create"),
    path("clusters/update", views.cluster_update, name="cluster_update"),
    path("clusters/delete", views.cluster_delete, name="cluster_delete"),
    path("clusters/test", views.cluster_test, name="cluster_test"),
]
