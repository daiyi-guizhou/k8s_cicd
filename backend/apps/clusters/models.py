"""Cluster configuration model — stores kubeconfig content in DB, supports multiple clusters."""
from django.db import models


class Cluster(models.Model):
    """Represents a managed Kubernetes cluster."""

    name = models.CharField(max_length=128, unique=True, verbose_name="集群名称")
    description = models.TextField(blank=True, default="", verbose_name="描述")
    kubeconfig_content = models.TextField(
        blank=True, default="",
        verbose_name="kubeconfig 内容",
        help_text="粘贴完整的 kubeconfig YAML 内容；留空则使用默认 ~/.kube/config"
    )
    enabled = models.BooleanField(default=True, verbose_name="启用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "cluster"
        ordering = ["-created_at"]
        verbose_name = "集群"
        verbose_name_plural = "集群"

    def __str__(self):
        return self.name

    def get_kubeconfig_text(self):
        """Return kubeconfig content — falls back to in-cluster config if empty."""
        if self.kubeconfig_content and self.kubeconfig_content.strip():
            return self.kubeconfig_content
        return None  # signal: use load_incluster_config or default kubeconfig
