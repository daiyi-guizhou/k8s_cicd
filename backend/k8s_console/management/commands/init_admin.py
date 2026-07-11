"""Django management command: create initial admin user."""
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from apps.auth_app.models import User
import secrets
import os


class Command(BaseCommand):
    help = "Create initial admin user if none exists"

    def handle(self, *args, **options):
        if User.objects.filter(role="admin").exists():
            self.stdout.write(self.style.SUCCESS("Admin user already exists, skipping."))
            return

        username = os.environ.get("ADMIN_USERNAME", "admin")
        password = os.environ.get("ADMIN_PASSWORD", secrets.token_urlsafe(12))

        User.objects.create(
            username=username,
            password=make_password(password),
            role="admin",
            is_active=True,
        )

        self.stdout.write(self.style.SUCCESS(f"Admin user created: {username}"))
        self.stdout.write(self.style.WARNING(f"Initial password: {password}"))
        self.stdout.write("⚠️  Please change this password immediately after first login.")
