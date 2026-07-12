"""Deploy app URL config."""
from django.urls import path
from . import views

urlpatterns = [
    # Project CRUD
    path("deploy/projects", views.project_list, name="deploy_project_list"),
    path("deploy/project/create", views.project_create, name="deploy_project_create"),
    path("deploy/project/update", views.project_update, name="deploy_project_update"),
    path("deploy/project/delete", views.project_delete, name="deploy_project_delete"),
    # Deploy
    path("deploy/trigger", views.deploy_trigger, name="deploy_trigger"),
    path("deploy/rollback", views.deploy_rollback, name="deploy_rollback"),
    # History
    path("deploy/history", views.deploy_history, name="deploy_history"),
]
