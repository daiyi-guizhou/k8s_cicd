"""Logging filters: RequestIDFilter with thread-local storage."""
import json
import logging
import os
import threading

_local = threading.local()


def get_request_id():
    return getattr(_local, "request_id", "-")


def set_request_id(request_id: str):
    _local.request_id = request_id


class RequestIDFilter(logging.Filter):
    """Inject request_id and pod name into every log record."""

    def __init__(self, service_name: str = "", name: str = ""):
        super().__init__(name=name)
        self.service_name = service_name or os.environ.get("SERVICE_NAME", "unknown")

    def filter(self, record):
        record.request_id = get_request_id()
        record.service = self.service_name
        record.pod = os.environ.get("HOSTNAME", "unknown")
        return True


class JsonFormatter(logging.Formatter):
    """Serialize each log record as a single, strictly-valid JSON line.

    The previous string-``%`` template produced broken JSON whenever the
    message (or any field) contained a double-quote or newline — e.g. an API
    response body like ``resp={"status": "ok"}`` broke the JSON, which then
    failed to parse downstream in filebeat. ``json.dumps`` escapes everything
    correctly so every line is valid JSON.
    """

    def format(self, record):
        log_obj = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "service": getattr(record, "service", "-"),
            "request_id": getattr(record, "request_id", "-"),
            "pod": getattr(record, "pod", "-"),
            "logger": record.name,
            "message": record.getMessage(),
            "path": record.pathname,
            "lineno": record.lineno,
        }
        return json.dumps(log_obj, ensure_ascii=False)
