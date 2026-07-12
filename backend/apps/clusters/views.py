"""Cluster management CRUD views."""
from kubernetes import config as k8s_config

from rest_framework.decorators import api_view

from .models import Cluster
from utils.response import success, error, ERR_VALIDATION
from utils.admin_guard import require_admin


@api_view(["POST"])
def cluster_list(request):
    """List all clusters. Any authenticated user can view."""
    clusters = Cluster.objects.all().values(
        "id", "name", "description", "enabled", "created_at", "updated_at"
    )
    return success(data={"items": list(clusters), "count": len(clusters)})


@api_view(["POST"])
def cluster_create(request):
    """Create a new cluster config."""
    admin_err = require_admin(request.user)
    if admin_err:
        return admin_err
    name = request.data.get("name", "").strip()
    description = request.data.get("description", "").strip()
    kubeconfig_content = request.data.get("kubeconfig_content", "").strip()

    if not name:
        return error(ERR_VALIDATION, "集群名称不能为空")
    if Cluster.objects.filter(name=name).exists():
        return error(ERR_VALIDATION, f"集群名称 '{name}' 已存在")

    cluster = Cluster.objects.create(
        name=name,
        description=description,
        kubeconfig_content=kubeconfig_content,
        enabled=True,
    )
    return success(data={
        "id": cluster.id,
        "name": cluster.name,
        "description": cluster.description,
        "enabled": cluster.enabled,
        "created_at": cluster.created_at.isoformat(),
    }, message=f"集群 '{name}' 已创建")


@api_view(["POST"])
def cluster_update(request):
    """Update cluster config."""
    admin_err = require_admin(request.user)
    if admin_err:
        return admin_err
    cluster_id = request.data.get("id")
    if not cluster_id:
        return error(ERR_VALIDATION, "缺少集群 ID")

    try:
        cluster = Cluster.objects.get(id=cluster_id)
    except Cluster.DoesNotExist:
        return error(ERR_VALIDATION, "集群不存在")

    name = request.data.get("name")
    if name is not None:
        name = name.strip()
        if name and name != cluster.name and Cluster.objects.filter(name=name).exists():
            return error(ERR_VALIDATION, f"集群名称 '{name}' 已存在")
        if name:
            cluster.name = name
    if "description" in request.data:
        cluster.description = request.data.get("description", "").strip()
    if "kubeconfig_content" in request.data:
        cluster.kubeconfig_content = request.data.get("kubeconfig_content", "").strip()
    if "enabled" in request.data:
        cluster.enabled = bool(request.data.get("enabled", True))

    cluster.save()
    return success(message=f"集群 '{cluster.name}' 已更新")


@api_view(["POST"])
def cluster_delete(request):
    """Delete a cluster config."""
    admin_err = require_admin(request.user)
    if admin_err:
        return admin_err
    cluster_id = request.data.get("id")
    if not cluster_id:
        return error(ERR_VALIDATION, "缺少集群 ID")

    try:
        cluster = Cluster.objects.get(id=cluster_id)
    except Cluster.DoesNotExist:
        return error(ERR_VALIDATION, "集群不存在")

    name = cluster.name
    cluster.delete()
    return success(message=f"集群 '{name}' 已删除")


@api_view(["POST"])
def cluster_test(request):
    """Test cluster connectivity."""
    cluster_id = request.data.get("id")
    if not cluster_id:
        return error(ERR_VALIDATION, "缺少集群 ID")

    try:
        cluster = Cluster.objects.get(id=cluster_id)
    except Cluster.DoesNotExist:
        return error(ERR_VALIDATION, "集群不存在")

    try:
        api = _get_core_api(cluster)
        namespaces = api.list_namespace()
        return success(data={
            "namespace_count": len(namespaces.items),
            "server_version": _get_server_version(cluster),
        }, message="集群连接正常")
    except Exception as e:
        return error(ERR_VALIDATION, "集群连接失败", str(e))


def _get_core_api(cluster):
    """Get a CoreV1Api for testing connectivity."""
    from kubernetes import client
    kubeconfig_text = cluster.get_kubeconfig_text()
    if kubeconfig_text:
        from kubernetes.config import kube_config
        import tempfile, os
        fd, path = tempfile.mkstemp(suffix=".yaml")
        with os.fdopen(fd, "w") as f:
            f.write(kubeconfig_text)
        try:
            loader = kube_config.KubeConfigLoader(path)
            loader.load_and_set(client.Configuration())
            api = client.CoreV1Api()
        finally:
            os.unlink(path)
        return api
    else:
        # Try in-cluster, fallback to default kubeconfig
        try:
            k8s_config.load_incluster_config()
        except k8s_config.ConfigException:
            k8s_config.load_kube_config()
        return client.CoreV1Api()


def _get_server_version(cluster):
    """Get server version string."""
    from kubernetes import client
    kubeconfig_text = cluster.get_kubeconfig_text()
    if kubeconfig_text:
        from kubernetes.config import kube_config
        import tempfile, os
        fd, path = tempfile.mkstemp(suffix=".yaml")
        with os.fdopen(fd, "w") as f:
            f.write(kubeconfig_text)
        try:
            loader = kube_config.KubeConfigLoader(path)
            loader.load_and_set(client.Configuration())
            version = client.VersionApi().get_code()
        finally:
            os.unlink(path)
        return version.git_version
    else:
        try:
            k8s_config.load_incluster_config()
        except k8s_config.ConfigException:
            k8s_config.load_kube_config()
        return client.VersionApi().get_code().git_version
