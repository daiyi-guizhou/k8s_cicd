"""Custom Prometheus metrics for observability app."""
from prometheus_client import Counter, Histogram

django_log_errors_total = Counter(
    "django_log_errors_total",
    "Total number of ERROR-level log entries emitted",
    ["logger", "module"],
)

api_request_latency = Histogram(
    "api_request_latency_seconds",
    "API request latency in seconds",
    ["endpoint", "method"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0),
)
