"""AuditLog model for tracking all write operations."""
from django.db import models


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ("scale", "扩缩容"),
        ("rollback", "回滚"),
        ("delete", "删除"),
        ("apply", "应用YAML"),
        ("create_user", "创建用户"),
        ("toggle_active", "启用/禁用用户"),
        ("reset_password", "重置密码"),
        ("change_password", "修改密码"),
    ]

    RESULT_CHOICES = [
        ("success", "成功"),
        ("fail", "失败"),
    ]

    user = models.ForeignKey("auth_app.User", on_delete=models.SET_NULL, null=True, related_name="audit_logs")
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    resource_type = models.CharField(max_length=50)
    resource_name = models.CharField(max_length=255, blank=True, default="")
    namespace = models.CharField(max_length=100, blank=True, default="")
    cluster_name = models.CharField(max_length=128, blank=True, default="", verbose_name="集群名称")
    detail = models.JSONField(default=dict, blank=True)
    result = models.CharField(max_length=20, choices=RESULT_CHOICES)
    error_msg = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_log"
        ordering = ["-created_at"]
