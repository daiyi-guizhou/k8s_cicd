# Generated migration for Cluster model
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Cluster",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=128, unique=True, verbose_name="集群名称")),
                ("description", models.TextField(blank=True, default="", verbose_name="描述")),
                (
                    "kubeconfig_content",
                    models.TextField(
                        blank=True,
                        default="",
                        verbose_name="kubeconfig 内容",
                        help_text="粘贴完整的 kubeconfig YAML 内容；留空则使用默认 ~/.kube/config",
                    ),
                ),
                ("enabled", models.BooleanField(default=True, verbose_name="启用")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
            ],
            options={
                "db_table": "cluster",
                "ordering": ["-created_at"],
                "verbose_name": "集群",
                "verbose_name_plural": "集群",
            },
        ),
    ]
