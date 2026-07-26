from django.apps import AppConfig


class IncomeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.income"

    def ready(self):
        # 应用启动即把自定义指标注册进 prometheus_client 默认 REGISTRY，
        # 这样 django_prometheus 暴露的 /metrics 端点才会导出 user_income。
        from . import metrics  # noqa: F401
