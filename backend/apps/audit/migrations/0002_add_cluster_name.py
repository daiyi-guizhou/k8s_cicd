# Add cluster_name field to AuditLog
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("audit", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="auditlog",
            name="cluster_name",
            field=models.CharField(blank=True, default="", max_length=128, verbose_name="集群名称"),
        ),
    ]
