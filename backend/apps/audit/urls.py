"""Audit app URL config."""
from django.urls import path
from . import views

urlpatterns = [
    path("audit/list", views.audit_list, name="audit_list"),
]
