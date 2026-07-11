"""Custom User model and PasswordResetToken."""
from django.db import models


class User(models.Model):
    ROLE_CHOICES = [
        ("admin", "管理员"),
        ("user", "普通用户"),
    ]

    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=255)  # Django hashed
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="user")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def __str__(self):
        return self.username

    class Meta:
        db_table = "user"


class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reset_tokens")
    token = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        db_table = "password_reset_token"
