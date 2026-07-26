"""Income views — upload endpoint + Prometheus gauge update."""
from decimal import Decimal, InvalidOperation

from rest_framework import viewsets
from rest_framework.decorators import action

from utils.response import (
    success as success_resp,
    error,
    ERR_VALIDATION,
    ERR_AUTH_FAILED,
)
from apps.auth_app.models import User
from .models import Income
from .metrics import user_income


class IncomeViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["post"], url_path="upload")
    def upload_income(self, request):
        # 本项目由 token 中间件把 request.user 设为 User 实例
        if not isinstance(request.user, User):
            return error(ERR_AUTH_FAILED, "未登录或 token 无效")

        user = request.user
        raw = request.data.get("income")

        # 1) 校验数值（Decimal 避免浮点误差）
        try:
            amount = Decimal(str(raw))
        except (InvalidOperation, TypeError, ValueError):
            return error(ERR_VALIDATION, "income 必须是数值")
        if amount < 0:
            return error(ERR_VALIDATION, "income 不能为负数")

        # 2) 落库：每次上传新增一条记录，便于追溯
        Income.objects.create(
            user=user,
            amount=amount,
            currency=request.data.get("currency", "CNY"),
            source=request.data.get("source", ""),
        )

        # 3) 写监控指标：把“当前收入”设置进 Gauge
        #    plan 取用户套餐字段；User 当前无 plan 字段时落为 unknown，
        #    将来加了套餐/订阅字段，在这里接上即可。
        user_income.labels(
            user_id=user.id,
            plan=getattr(user, "plan", "unknown"),
        ).set(float(amount))

        return success_resp(data={"income": str(amount)})
