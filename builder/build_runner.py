"""Docker build runner — local copy, build, image retention policy."""
import os
import shutil
import subprocess
import uuid


TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

EXCLUDE_PATTERNS = [
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "*.pyc", ".DS_Store", "__MACOSX",
]

# Only allow builds from paths under these prefixes (path traversal protection)
ALLOWED_PATH_PREFIXES = [
    "/data/project/",
    "/d/",
    "/home/",
    "/Users/",
    "D:\\",
    "C:\\",
]


def _detect_python_version(build_dir: str) -> str:
    """Read python_version.txt from build dir, default '3.12'."""
    ver_file = os.path.join(build_dir, "python_version.txt")
    if os.path.isfile(ver_file):
        with open(ver_file) as f:
            version = f.read().strip()
            if version:
                return version
    return "3.12"


def _render_dockerfile(template_path: str, output_path: str, variables: dict):
    """Read template, replace {VAR} placeholders, write to output."""
    with open(template_path) as f:
        content = f.read()
    for key, val in variables.items():
        content = content.replace("{" + key + "}", str(val))
    with open(output_path, "w") as f:
        f.write(content)


def _cleanup_old_images(app_name: str, keep_count: int = 5):
    """Clean old images, keep at most `keep_count` tags per app."""
    result = subprocess.run(
        ["docker", "images", "--filter", f"reference={app_name}",
         "--format", "{{.Tag}}|{{.CreatedAt}}"],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return

    entries = []
    for line in result.stdout.strip().split("\n"):
        parts = line.split("|", 1)
        if len(parts) != 2:
            continue
        tag, created_at = parts[0].strip(), parts[1].strip()
        entries.append((tag, created_at))

    entries.sort(key=lambda x: x[1], reverse=True)

    for tag, _ in entries[keep_count:]:
        image_name = f"{app_name}:{tag}"
        subprocess.run(
            ["docker", "rmi", image_name],
            capture_output=True, text=True,
        )


def build(app_name: str, app_type: str, tag: str, local_path: str) -> dict:
    """Build Docker image from local source.

    Args:
        app_name: Image name, e.g. "my-shop"
        app_type: "django" or "vue"
        tag: Image tag, e.g. "v1.2.0"
        local_path: Source code path on host

    Returns:
        {"image": "my-shop:v1.2.0", "app_name": "my-shop", "tag": "v1.2.0"}

    Raises:
        ValueError: if local_path not found or app_type invalid
        RuntimeError: if docker build fails
    """
    if not os.path.isdir(local_path):
        raise ValueError(f"本地路径不存在: {local_path}")

    # Path traversal protection
    normalized = os.path.abspath(local_path)
    if not any(normalized.startswith(prefix) for prefix in ALLOWED_PATH_PREFIXES):
        raise ValueError(f"不允许的路径前缀: {local_path}")

    if app_type not in ("django", "vue"):
        raise ValueError(f"不支持的应用类型: {app_type}")

    template_subdir = "django" if app_type == "django" else "vue"
    template_dockerfile = os.path.join(TEMPLATE_DIR, template_subdir, "Dockerfile")
    if not os.path.isfile(template_dockerfile):
        raise RuntimeError(f"模板 Dockerfile 不存在: {template_dockerfile}")

    # Create temp build directory
    build_id = str(uuid.uuid4())[:8]
    build_dir = f"/tmp/build-{app_name}-{build_id}"
    os.makedirs(build_dir, exist_ok=True)

    try:
        # Copy source files (excluding patterns)
        for item in os.listdir(local_path):
            src = os.path.join(local_path, item)
            dst = os.path.join(build_dir, item)
            skip = False
            for pattern in EXCLUDE_PATTERNS:
                if "*" in pattern:
                    if item.endswith(pattern[1:]):
                        skip = True
                        break
                elif item == pattern:
                    skip = True
                    break
            if skip:
                continue
            if os.path.isdir(src):
                shutil.copytree(src, dst,
                                ignore=shutil.ignore_patterns(*EXCLUDE_PATTERNS)
                                if EXCLUDE_PATTERNS else None)
            else:
                shutil.copy2(src, dst)

        # Determine Python version for Django
        variables = {"APP_NAME": app_name}
        if app_type == "django":
            variables["PYTHON_VERSION"] = _detect_python_version(build_dir)
            if not os.path.isfile(os.path.join(build_dir, "requirements.txt")):
                raise ValueError("Django 项目必须包含 requirements.txt")
        elif app_type == "vue":
            if not os.path.isfile(os.path.join(build_dir, "package.json")):
                raise ValueError("Vue 项目必须包含 package.json")

        # Verify start_app.sh exists (required by convention)
        if not os.path.isfile(os.path.join(build_dir, "start_app.sh")):
            raise ValueError("项目必须包含 start_app.sh")

        # Render and place Dockerfile
        _render_dockerfile(template_dockerfile,
                           os.path.join(build_dir, "Dockerfile"), variables)

        # Docker build
        image = f"{app_name}:{tag}"
        try:
            result = subprocess.run(
                ["docker", "build", "-t", image, "."],
                cwd=build_dir,
                capture_output=True, text=True,
                timeout=600,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr or result.stdout or "docker build 失败")
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"docker build 超时 (600s): {app_name}:{tag}")

        # Cleanup old images
        _cleanup_old_images(app_name)

        return {"image": image, "app_name": app_name, "tag": tag}

    finally:
        # Clean temp dir
        if os.path.isdir(build_dir):
            shutil.rmtree(build_dir, ignore_errors=True)
