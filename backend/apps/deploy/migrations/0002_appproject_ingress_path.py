# Generated migration for ingress_path field
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("deploy", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="appproject",
            name="ingress_path",
            field=models.CharField(
                default="/",
                max_length=256,
                verbose_name="Ingress 路径（同域名多个项目时区分路由）",
            ),
        ),
    ]
