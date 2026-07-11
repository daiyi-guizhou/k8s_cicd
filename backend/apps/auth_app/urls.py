"""Auth app URL config."""
from django.urls import path
from . import views

urlpatterns = [
    path("auth/login", views.login, name="auth_login"),
    path("auth/logout", views.logout, name="auth_logout"),
    path("auth/change-password", views.change_password, name="auth_change_password"),
    path("users/create", views.user_create, name="user_create"),
    path("users/list", views.user_list, name="user_list"),
    path("users/toggle-active", views.user_toggle_active, name="user_toggle_active"),
    path("users/reset-password", views.user_reset_password, name="user_reset_password"),
]
