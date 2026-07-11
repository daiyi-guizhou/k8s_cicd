"""Resources app URL config."""
from django.urls import path
from . import views

urlpatterns = [
    path("resources/list", views.resource_list, name="resource_list"),
    path("resources/detail", views.resource_detail, name="resource_detail"),
    path("resources/yaml", views.resource_yaml, name="resource_yaml"),
    path("resources/scale", views.resource_scale, name="resource_scale"),
    path("resources/rollback", views.resource_rollback, name="resource_rollback"),
    path("resources/delete", views.resource_delete, name="resource_delete"),
    path("resources/apply", views.resource_apply, name="resource_apply"),
]
