"""CI/CD deploy models — AppProject and DeployHistory."""
from django.db import models


class AppProject(models.Model):
    """需要部署的应用项目"""

    APP_TYPE_CHOICES = [
        ("django", "Django"),
        ("vue", "Vue"),
    ]

    app_name = models.CharField(
        max_length=128, primary_key=True,
        verbose_name="应用名称"
    )
    app_type = models.CharField(
        max_length=16, choices=APP_TYPE_CHOICES,
        verbose_name="应用类型"
    )
    local_path = models.CharField(
        max_length=480, blank=True, default="",
        verbose_name="本地代码地址"
    )
    domain = models.CharField(
        max_length=256,
        verbose_name="访问域名"
    )
    ingress_path = models.CharField(
        max_length=256, default="/",
        verbose_name="Ingress 路径（同域名多个项目时区分路由）"
    )
    port = models.IntegerField(
        default=8000,
        verbose_name="容器端口（Django=8000, Vue=80）"
    )
    namespace = models.CharField(
        max_length=64, default="prd",
        verbose_name="K8s Namespace"
    )
    cluster = models.ForeignKey(
        "clusters.Cluster", on_delete=models.PROTECT,
        related_name="app_projects",
        verbose_name="目标集群"
    )
    replicas = models.IntegerField(
        default=1,
        verbose_name="Pod 副本数"
    )
    enabled = models.BooleanField(
        default=True,
        verbose_name="启用"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "app_project"
        verbose_name = "部署项目"
        verbose_name_plural = "部署项目"

    def __str__(self):
        return f"{self.app_name} ({self.app_type})"


class DeployHistory(models.Model):
    """部署历史记录"""

    STATUS_CHOICES = [
        ("building", "构建中"),
        ("deploying", "部署中"),
        ("success", "成功"),
        ("failed", "失败"),
    ]

    project = models.ForeignKey(
        AppProject, on_delete=models.CASCADE,
        to_field="app_name", db_column="app_name",
        related_name="deploy_histories",
        verbose_name="应用"
    )
    tag = models.CharField(max_length=128, verbose_name="部署 tag")
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default="building",
        verbose_name="状态"
    )
    operator = models.CharField(
        max_length=64, blank=True, default="",
        verbose_name="操作人"
    )
    message = models.TextField(blank=True, default="", verbose_name="结果信息")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="部署时间")

    class Meta:
        db_table = "deploy_history"
        ordering = ["-created_at"]
        verbose_name = "部署历史"
        verbose_name_plural = "部署历史"
