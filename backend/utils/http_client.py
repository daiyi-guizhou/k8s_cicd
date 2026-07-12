"""Logged HTTP client — wraps requests.Session with before/after API logging.

Usage:
    from utils.http_client import http_post, http_get

    resp = http_post("http://builder:9008/api/build", json={...}, timeout=600)
    resp.raise_for_status()
    data = resp.json()
"""
import logging
import time

import requests

api_logger = logging.getLogger("api")


class LoggedSession(requests.Session):
    """Session that logs every outgoing request and its response."""

    def request(self, method, url, **kwargs):
        start = time.monotonic()

        # ---------- before ----------
        params = kwargs.get("params")
        data = kwargs.get("data")
        json_body = kwargs.get("json")
        headers = kwargs.get("headers")

        # Build a clean body representation for logging
        body_repr = None
        if json_body is not None:
            body_repr = json_body
        elif data is not None:
            body_repr = str(data) if len(str(data)) <= 2000 else str(data)[:2000] + "...<truncated>"

        api_logger.info(
            ">>> OUT %s %s | params=%s | body=%s | headers=%s",
            method.upper(), url, params, body_repr, headers,
        )

        # ---------- execute ----------
        try:
            resp = super().request(method, url, **kwargs)
        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            api_logger.info(
                "<<< OUT %s %s → ERROR | %.1fms | err=%s",
                method.upper(), url, elapsed_ms, exc,
            )
            raise

        # ---------- after ----------
        elapsed_ms = (time.monotonic() - start) * 1000
        resp_body = ""
        try:
            text = resp.text
            resp_body = text if len(text) <= 1000 else text[:1000] + "...<truncated>"
        except Exception:
            resp_body = "<binary>"

        api_logger.info(
            "<<< OUT %s %s → %s | %.1fms | resp=%s",
            method.upper(), url, resp.status_code, elapsed_ms, resp_body,
        )
        return resp


# ---- singleton session ----
_session = LoggedSession()


def http_post(url, **kwargs):
    return _session.post(url, **kwargs)


def http_get(url, **kwargs):
    return _session.get(url, **kwargs)


def http_put(url, **kwargs):
    return _session.put(url, **kwargs)


def http_delete(url, **kwargs):
    return _session.delete(url, **kwargs)
