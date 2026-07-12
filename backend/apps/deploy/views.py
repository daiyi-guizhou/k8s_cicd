"""CI/CD deploy views — project CRUD, deploy trigger, rollback."""
import subprocess

from kubernetes.client.rest import ApiException

from rest_framework.decorators import api_view

from apps.deploy.models import AppProject, DeployHistory
from apps.deploy.yaml_gen import generate_k8s_yaml
from apps.resources.k8s_client import apply_yaml
from utils.response import (
    success, error,
    ERR_VALIDATION, ERR_K8S_API_ERROR, ERR_RESOURCE_NOT_FOUND,
)
from utils.admin_guard import require_admin
from utils.http_client import http_post
from django.conf import settings


# ---------------------------------------------------------------------------
# Project CRUD
# ---------------------------------------------------------------------------

@api_view(["POST"])
def project_list(request):
    """List all deploy projects."""
    projects = AppProject.objects.all().values(
        "app_name", "app_type", "local_path", "domain", "port",
        "namespace", "replicas", "enabled", "cluster_id",
        "created_at", "updated_at", "ingress_path",
    )
    return success(data={"items": list(projects), "count": len(projects)})


@api_view(["POST"])
def project_create(request):
    """Create a deploy project. Admin only."""
    admin_err = require_admin(request.user)
    if admin_err:
        return admin_err

    app_name = request.data.get("app_name", "").strip()
    app_type = request.data.get("app_type", "").strip()
    local_path = request.data.get("local_path", "").strip()
    domain = request.data.get("domain", "").strip()
    port = int(request.data.get("port", 8000))
    namespace = request.data.get("namespace", "prd").strip()
    cluster_id = request.data.get("cluster_id")
    replicas = int(request.data.get("replicas", 1))
    enabled = bool(request.data.get("enabled", True))
    # Default ingress_path by app_type: Django → /api, Vue → /
    ingress_path = request.data.get("ingress_path", "").strip()
    if not ingress_path:
        ingress_path = "/api" if app_type == "django" else "/"

    if not app_name:
        return error(ERR_VALIDATION, "应用名称不能为空")
    if app_type not in ("django", "vue"):
        return error(ERR_VALIDATION, "应用类型必须为 django 或 vue")
    if not domain:
        return error(ERR_VALIDATION, "域名不能为空")
    if not cluster_id:
        return error(ERR_VALIDATION, "请选择目标集群")
    if AppProject.objects.filter(app_name=app_name).exists():
        return error(ERR_VALIDATION, f"应用 '{app_name}' 已存在")

    project = AppProject.objects.create(
        app_name=app_name, app_type=app_type, local_path=local_path,
        domain=domain, port=port, namespace=namespace,
        cluster_id=cluster_id, replicas=replicas, enabled=enabled,
        ingress_path=ingress_path,
    )
    return success(data={
        "app_name": project.app_name,
        "app_type": project.app_type,
        "domain": project.domain,
        "ingress_path": project.ingress_path,
    }, message=f"项目 '{app_name}' 已创建")


@api_view(["POST"])
def project_update(request):
    """Update a deploy project. Admin only."""
    admin_err = require_admin(request.user)
    if admin_err:
        return admin_err

    app_name = request.data.get("app_name", "").strip()
    if not app_name:
        return error(ERR_VALIDATION, "应用名称不能为空")

    try:
        project = AppProject.objects.get(app_name=app_name)
    except AppProject.DoesNotExist:
        return error(ERR_RESOURCE_NOT_FOUND, f"项目 '{app_name}' 不存在")

    # Update fields if provided
    for field in ["app_type", "local_path", "domain", "namespace", "ingress_path"]:
        val = request.data.get(field)
        if val is not None and str(val).strip():
            setattr(project, field, str(val).strip())
    for field in ["port", "replicas"]:
        val = request.data.get(field)
        if val is not None:
            setattr(project, field, int(val))
    if "cluster_id" in request.data:
        project.cluster_id = int(request.data["cluster_id"])
    if "enabled" in request.data:
        project.enabled = bool(request.data["enabled"])

    project.save()
    return success(data={"app_name": project.app_name}, message=f"项目 '{app_name}' 已更新")


@api_view(["POST"])
def project_delete(request):
    """Delete a deploy project. Admin only."""
    admin_err = require_admin(request.user)
    if admin_err:
        return admin_err

    app_name = request.data.get("app_name", "").strip()
    if not app_name:
        return error(ERR_VALIDATION, "应用名称不能为空")

    try:
        project = AppProject.objects.get(app_name=app_name)
    except AppProject.DoesNotExist:
        return error(ERR_RESOURCE_NOT_FOUND, f"项目 '{app_name}' 不存在")

    project.delete()
    return success(message=f"项目 '{app_name}' 已删除")


# ---------------------------------------------------------------------------
# Deploy
# ---------------------------------------------------------------------------

@api_view(["POST"])
def deploy_trigger(request):
    """Trigger a deploy: build image → generate YAML → apply to K8s. Admin only."""
    admin_err = require_admin(request.user)
    if admin_err:
        return admin_err

    app_name = request.data.get("app_name", "").strip()
    tag = request.data.get("tag", "").strip()

    if not app_name:
        return error(ERR_VALIDATION, "应用名称不能为空")
    if not tag:
        return error(ERR_VALIDATION, "部署 tag 不能为空")

    try:
        project = AppProject.objects.get(app_name=app_name)
    except AppProject.DoesNotExist:
        return error(ERR_RESOURCE_NOT_FOUND, f"项目 '{app_name}' 不存在")

    if not project.enabled:
        return error(ERR_VALIDATION, f"项目 '{app_name}' 已禁用，请先启用")

    # Create deploy history
    history = DeployHistory.objects.create(
        project=project, tag=tag, status="building",
        operator=request.user.username,
    )

    # Step 1: Call Builder Service
    try:
        build_resp = http_post(
            f"{settings.BUILDER_SERVICE_URL}/api/build",
            json={
                "app_name": app_name,
                "app_type": project.app_type,
                "tag": tag,
                "local_path": project.local_path,
            },
            timeout=600,
        )
        build_resp.raise_for_status()
        build_data = build_resp.json()
    except Exception as e:
        history.status = "failed"
        detail = str(e)
        if hasattr(e, "response") and e.response is not None:
            try:
                detail = e.response.json().get("error", detail)
            except Exception:
                detail = e.response.text[:500]
        history.message = detail
        history.save()
        return error(ERR_VALIDATION, "镜像构建失败", detail)
    except (ValueError, KeyError) as e:
        history.status = "failed"
        history.message = f"解析构建响应失败: {e}"
        history.save()
        return error(ERR_VALIDATION, "镜像构建失败", str(e))

    if build_data.get("code") != 0:
        history.status = "failed"
        history.message = build_data.get("error", build_data.get("message", "未知错误"))
        history.save()
        return error(ERR_VALIDATION, "镜像构建失败", history.message)

    image = build_data["data"]["image"]

    # Step 2: Generate K8s YAML
    yaml_content = generate_k8s_yaml(project, image)

    # Step 3: Apply to K8s
    history.status = "deploying"
    history.save()
    try:
        apply_yaml(project.cluster_id, yaml_content)
    except (ApiException, Exception) as e:
        msg = str(e)
        if hasattr(e, 'body'):
            msg = str(e.body)[:500]
        history.status = "failed"
        history.message = msg
        history.save()
        return error(ERR_K8S_API_ERROR, "K8s 部署失败", msg)

    # Step 4: Mark success
    history.status = "success"
    history.message = f"部署成功，域名: {project.domain}"
    history.save()

    return success(data={
        "domain": project.domain,
        "tag": tag,
        "app_name": app_name,
    }, message="部署成功")


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------

@api_view(["POST"])
def deploy_rollback(request):
    """Rollback to a previously deployed tag. Admin only."""
    admin_err = require_admin(request.user)
    if admin_err:
        return admin_err

    app_name = request.data.get("app_name", "").strip()
    tag = request.data.get("tag", "").strip()

    if not app_name:
        return error(ERR_VALIDATION, "应用名称不能为空")
    if not tag:
        return error(ERR_VALIDATION, "回滚 tag 不能为空")

    try:
        project = AppProject.objects.get(app_name=app_name)
    except AppProject.DoesNotExist:
        return error(ERR_RESOURCE_NOT_FOUND, f"项目 '{app_name}' 不存在")

    # Verify the tag was successfully deployed before
    history_check = DeployHistory.objects.filter(
        project=project, tag=tag, status="success"
    ).first()
    if not history_check:
        return error(ERR_VALIDATION, f"未找到 tag='{tag}' 的成功部署记录，无法回滚")

    # Verify image still exists locally (skip docker check if docker not available)
    image = f"{app_name}:{tag}"
    docker_ok = True
    try:
        result = subprocess.run(
            ["docker", "images", "-q", image],
            capture_output=True, text=True, timeout=10,
        )
        if not result.stdout.strip():
            docker_ok = False
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        # If docker command not available, skip local image check
        docker_ok = True  # allow rollback, image may exist on node

    if not docker_ok:
        return error(ERR_VALIDATION, f"本地镜像 {image} 不存在，无法回滚")

    # Generate YAML and apply
    yaml_content = generate_k8s_yaml(project, image)
    try:
        apply_yaml(project.cluster_id, yaml_content)
    except (ApiException, Exception) as e:
        msg = str(e)
        if hasattr(e, 'body'):
            msg = str(e.body)[:500]
        DeployHistory.objects.create(
            project=project, tag=tag, status="failed",
            operator=request.user.username,
            message=f"回滚失败: {msg}",
        )
        return error(ERR_K8S_API_ERROR, "回滚部署失败", msg)

    # Record rollback
    DeployHistory.objects.create(
        project=project, tag=tag, status="success",
        operator=request.user.username,
        message=f"回滚到 {tag}",
    )

    return success(data={
        "domain": project.domain,
        "tag": tag,
        "app_name": app_name,
    }, message=f"已回滚到 {tag}")


# ---------------------------------------------------------------------------
# Deploy History
# ---------------------------------------------------------------------------

@api_view(["POST"])
def deploy_history(request):
    """List deploy history for a project."""
    app_name = request.data.get("app_name", "").strip()
    if not app_name:
        return error(ERR_VALIDATION, "应用名称不能为空")

    try:
        project = AppProject.objects.get(app_name=app_name)
    except AppProject.DoesNotExist:
        return error(ERR_RESOURCE_NOT_FOUND, f"项目 '{app_name}' 不存在")

    histories = DeployHistory.objects.filter(project=project).values(
        "id", "tag", "status", "operator", "message", "created_at"
    )[:50]
    return success(data={"items": list(histories), "count": len(histories)})
