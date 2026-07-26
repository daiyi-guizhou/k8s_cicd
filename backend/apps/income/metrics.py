"""Custom Prometheus metrics for the income app."""
from prometheus_client import Gauge

# 用户最新上报收入（快照值）。按 user_id + plan 打标签。
#
# ⚠️ cardinality 提醒：每个 user_id 会生成一条独立时间序列；
#    若用户量很大（几十万级），只按 user_id 打标会撑爆 Prometheus。
#    这种情况下：要么把指标定义的标签精简成 ["plan"]（只看聚合），
#    要么改用 Histogram 看分布而不按 user_id 下钻。
user_income = Gauge(
    "user_income",
    "Latest self-reported income value per user",
    ["user_id", "plan"],
)
