"""Builder Service — Flask HTTP API for Docker image builds."""
import logging
import logging.handlers
import os
import sys
import time

from flask import Flask, request, jsonify, g

from build_runner import build

# ---------------------------------------------------------------------------
# Logging — console + rotating file in relative logs/ dir
# ---------------------------------------------------------------------------
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

fmt = logging.Formatter(
    fmt="[%(asctime)s] %(levelname)s %(name)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(fmt)

file_handler = logging.handlers.RotatingFileHandler(
    os.path.join(LOG_DIR, "api.log"),
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=5,
)
file_handler.setFormatter(fmt)

logging.basicConfig(level=logging.INFO, handlers=[console_handler, file_handler])
api_logger = logging.getLogger("api")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = Flask(__name__)


@app.before_request
def log_request():
    """Log every incoming request — method, url, params, body."""
    g.start_time = time.monotonic()

    method = request.method
    uri = request.url
    params = dict(request.args) if request.args else None
    body = None

    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        body_raw = request.get_data(as_text=True)
        body = body_raw if body_raw and len(body_raw) <= 2000 else (
            body_raw[:2000] + "...<truncated>" if body_raw else None
        )

    api_logger.info(
        ">>> %s %s | params=%s | body=%s",
        method, uri, params, body,
    )


@app.after_request
def log_response(response):
    """Log every outgoing response — status, elapsed, body."""
    elapsed_ms = (time.monotonic() - g.get("start_time", time.monotonic())) * 1000

    resp_body = ""
    try:
        raw = response.get_data(as_text=True)
        resp_body = raw if len(raw) <= 1000 else raw[:1000] + "...<truncated>"
    except Exception:
        resp_body = "<binary>"

    api_logger.info(
        "<<< %s %s → %s | %.1fms | resp=%s",
        request.method, request.url, response.status_code, elapsed_ms, resp_body,
    )
    return response


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/api/build", methods=["POST"])
def api_build():
    body = request.get_json(silent=True) or {}

    app_name = body.get("app_name", "").strip()
    app_type = body.get("app_type", "").strip()
    tag = body.get("tag", "").strip()
    local_path = body.get("local_path", "").strip()

    if not app_name:
        return jsonify({"code": 1, "message": "缺少 app_name", "error": "app_name 不能为空"}), 400
    if not app_type:
        return jsonify({"code": 1, "message": "缺少 app_type", "error": "app_type 不能为空"}), 400
    if not tag:
        return jsonify({"code": 1, "message": "缺少 tag", "error": "tag 不能为空"}), 400
    if not local_path:
        return jsonify({"code": 1, "message": "缺少 local_path", "error": "local_path 不能为空"}), 400

    try:
        result = build(app_name=app_name, app_type=app_type,
                       tag=tag, local_path=local_path)
        return jsonify({
            "code": 0,
            "message": "镜像构建成功",
            "data": result,
        })
    except ValueError as e:
        return jsonify({"code": 1, "message": "参数错误", "error": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"code": 1, "message": "镜像构建失败", "error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9008, debug=False)
