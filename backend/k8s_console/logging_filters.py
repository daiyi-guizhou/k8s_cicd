"""Logging filters: RequestIDFilter with thread-local storage."""
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
