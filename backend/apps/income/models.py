"""Income models — user self-reported income records."""
from django.db import models

from apps.auth_app.models import User


class Income(models.Model):
    """用户上报的收入记录。每次上传新增一条，便于追溯历史。"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="incomes"
    )
    amount = models.DecimalField(
        max_digits=14, decimal_places=2, help_text="收入金额"
    )
    currency = models.CharField(max_length=8, default="CNY")
    source = models.CharField(
        max_length=64, blank=True, default="", help_text="来源/备注"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "用户收入"
        verbose_name_plural = "用户收入"

    def __str__(self):
        return f"{self.user_id}:{self.amount} {self.currency}"
