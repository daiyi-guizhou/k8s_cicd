"""Multi-cluster K8s API client — routes operations to the correct cluster."""
import os
import tempfile
import threading
import yaml as _yaml

from kubernetes import client, config
from kubernetes.client.rest import ApiException

# Supported resource types and their client methods
_RESOURCE_MAP = {
    "namespace": {
        "api": "CoreV1Api",
        "list": "list_namespace",
        "read": "read_namespace",
        "delete": "delete_namespace",
        "namespaced": False,
    },
    "deployment": {
        "api": "AppsV1Api",
        "list": "list_namespaced_deployment",
        "read": "read_namespaced_deployment",
        "delete": "delete_namespaced_deployment",
        "scale": True,
        "rollback": True,
        "namespaced": True,
    },
    "pod": {
        "api": "CoreV1Api",
        "list": "list_namespaced_pod",
        "read": "read_namespaced_pod",
        "delete": "delete_namespaced_pod",
        "namespaced": True,
    },
    "service": {
        "api": "CoreV1Api",
        "list": "list_namespaced_service",
        "read": "read_namespaced_service",
        "delete": "delete_namespaced_service",
        "namespaced": True,
    },
    "ingress": {
        "api": "NetworkingV1Api",
        "list": "list_namespaced_ingress",
        "read": "read_namespaced_ingress",
        "delete": "delete_namespaced_ingress",
        "namespaced": True,
    },
    "daemonset": {
        "api": "AppsV1Api",
        "list": "list_namespaced_daemon_set",
        "read": "read_namespaced_daemon_set",
        "delete": "delete_namespaced_daemon_set",
        "namespaced": True,
    },
    "statefulset": {
        "api": "AppsV1Api",
        "list": "list_namespaced_stateful_set",
        "read": "read_namespaced_stateful_set",
        "delete": "delete_namespaced_stateful_set",
        "namespaced": True,
    },
    "configmap": {
        "api": "CoreV1Api",
        "list": "list_namespaced_config_map",
        "read": "read_namespaced_config_map",
        "delete": "delete_namespaced_config_map",
        "namespaced": True,
    },
    "secret": {
        "api": "CoreV1Api",
        "list": "list_namespaced_secret",
        "read": "read_namespaced_secret",
        "delete": "delete_namespaced_secret",
        "namespaced": True,
    },
    "role": {
        "api": "RbacAuthorizationV1Api",
        "list": "list_namespaced_role",
        "read": "read_namespaced_role",
        "delete": "delete_namespaced_role",
        "namespaced": True,
    },
    "rolebinding": {
        "api": "RbacAuthorizationV1Api",
        "list": "list_namespaced_role_binding",
        "read": "read_namespaced_role_binding",
        "delete": "delete_namespaced_role_binding",
        "namespaced": True,
    },
    "clusterrole": {
        "api": "RbacAuthorizationV1Api",
        "list": "list_cluster_role",
        "read": "read_cluster_role",
        "delete": "delete_cluster_role",
        "namespaced": False,
    },
    "clusterrolebinding": {
        "api": "RbacAuthorizationV1Api",
        "list": "list_cluster_role_binding",
        "read": "read_cluster_role_binding",
        "delete": "delete_cluster_role_binding",
        "namespaced": False,
    },
    "serviceaccount": {
        "api": "CoreV1Api",
        "list": "list_namespaced_service_account",
        "read": "read_namespaced_service_account",
        "delete": "delete_namespaced_service_account",
        "namespaced": True,
    },
}


# ---------------------------------------------------------------------------
# Per-cluster API client cache (thread-safe, TTL-based)
# ---------------------------------------------------------------------------
_cache_lock = threading.Lock()
_client_caches = {}  # {cluster_id: (timestamp, {api_name: api_instance})}
_CACHE_TTL_SECONDS = 300  # 5 minutes


def _get_cluster_kubeconfig_text(cluster_id):
    """Fetch kubeconfig text for a cluster from DB. Returns None for default."""
    from apps.clusters.models import Cluster

    try:
        cluster = Cluster.objects.get(id=cluster_id)
        return cluster.get_kubeconfig_text()
    except Cluster.DoesNotExist:
        raise ValueError(f"集群 ID={cluster_id} 不存在")


def _build_configuration(kubeconfig_text):
    """Build a Kubernetes Configuration object.

    If kubeconfig_text is provided, loads from that YAML.
    Otherwise falls back to in-cluster config → default kubeconfig.
    """
    cfg = client.Configuration()

    if kubeconfig_text:
        fd, path = tempfile.mkstemp(suffix=".yaml")
        with os.fdopen(fd, "w") as f:
            f.write(kubeconfig_text)
        try:
            from kubernetes.config import kube_config
            loader = kube_config.KubeConfigLoader(path)
            loader.load_and_set(cfg)
        finally:
            os.unlink(path)
    else:
        try:
            config.load_incluster_config(client_configuration=cfg)
        except config.ConfigException:
            config.load_kube_config(client_configuration=cfg)

    return cfg


def _get_client_cache(cluster_id):
    """Get or refresh cached API instances for a cluster."""
    import time

    now = time.time()
    with _cache_lock:
        entry = _client_caches.get(cluster_id)
        if entry and (now - entry[0]) < _CACHE_TTL_SECONDS:
            return entry[1]

        # Build fresh
        kubeconfig_text = _get_cluster_kubeconfig_text(cluster_id)
        cfg = _build_configuration(kubeconfig_text)

        api_instances = {
            "CoreV1Api": client.CoreV1Api(api_client=client.ApiClient(cfg)),
            "AppsV1Api": client.AppsV1Api(api_client=client.ApiClient(cfg)),
            "NetworkingV1Api": client.NetworkingV1Api(api_client=client.ApiClient(cfg)),
            "RbacAuthorizationV1Api": client.RbacAuthorizationV1Api(api_client=client.ApiClient(cfg)),
        }
        _client_caches[cluster_id] = (now, api_instances)
        return api_instances


def _get_api_for_cluster(cluster_id, api_name):
    """Get a configured API client for a specific cluster."""
    cache = _get_client_cache(cluster_id)
    api = cache.get(api_name)
    if api is None:
        raise ValueError(f"未知 API 类型: {api_name}")
    return api


def clear_cluster_cache(cluster_id=None):
    """Clear cached API clients so next call reloads kubeconfig.

    Call after updating a Cluster's kubeconfig_content.
    Pass None to clear all caches.
    """
    with _cache_lock:
        if cluster_id is None:
            _client_caches.clear()
        else:
            _client_caches.pop(cluster_id, None)


# ---------------------------------------------------------------------------
# Resource helpers
# ---------------------------------------------------------------------------

def _get_meta(cluster_id, resource_type, namespace=None):
    """Get API, resource info, and kwargs for a resource type on a cluster."""
    info = _RESOURCE_MAP.get(resource_type)
    if not info:
        return None, None, None
    api = _get_api_for_cluster(cluster_id, info["api"])
    kwargs = {}
    if info["namespaced"]:
        kwargs["namespace"] = namespace
    return api, info, kwargs


def _sanitize(obj):
    """Strip Kubernetes internal fields for display."""
    if obj is None:
        return None
    for field in ["managed_fields", "resource_version", "uid", "self_link", "generation"]:
        obj.metadata.__dict__.pop(field, None)
    if hasattr(obj.metadata, "annotations") and obj.metadata.annotations:
        if "kubectl.kubernetes.io/last-applied-configuration" in obj.metadata.annotations:
            del obj.metadata.annotations["kubectl.kubernetes.io/last-applied-configuration"]
    return obj


# ---------------------------------------------------------------------------
# Public resource operations (all take cluster_id as first arg)
# ---------------------------------------------------------------------------

def list_resources(cluster_id, resource_type, namespace=None):
    """List all resources of given type on a cluster."""
    api, info, kwargs = _get_meta(cluster_id, resource_type, namespace)
    if not api:
        raise ValueError(f"不支持资源类型: {resource_type}")
    method = getattr(api, info["list"])
    try:
        if info["namespaced"]:
            if namespace:
                result = method(namespace)
            else:
                result = method(namespace="")
        else:
            result = method()
        items = []
        for item in result.items:
            _sanitize(item)
            items.append(item.to_dict())
        return items
    except ApiException as e:
        raise e


def get_resource(cluster_id, resource_type, name, namespace=None):
    """Get single resource as dict."""
    api, info, kwargs = _get_meta(cluster_id, resource_type, namespace)
    if not api:
        raise ValueError(f"不支持资源类型: {resource_type}")
    kwargs["name"] = name
    method = getattr(api, info["read"])
    try:
        result = method(**kwargs)
        _sanitize(result)
        return result.to_dict()
    except ApiException as e:
        raise e


def get_resource_yaml(cluster_id, resource_type, name, namespace=None):
    """Get resource as YAML string (sanitized)."""
    api, info, kwargs = _get_meta(cluster_id, resource_type, namespace)
    if not api:
        raise ValueError(f"不支持资源类型: {resource_type}")
    kwargs["name"] = name
    method = getattr(api, info["read"])
    try:
        result = method(**kwargs)
        _sanitize(result)
        d = result.to_dict()
        d.get("metadata", {}).pop("managed_fields", None)
        d.get("metadata", {}).pop("resource_version", None)
        d.get("metadata", {}).pop("uid", None)
        d.get("metadata", {}).pop("self_link", None)
        d.get("metadata", {}).pop("generation", None)
        d.get("metadata", {}).pop("creation_timestamp", None)
        return _yaml.dump(d, default_flow_style=False, allow_unicode=True)
    except ApiException as e:
        raise e


def scale_resource(cluster_id, resource_type, name, namespace, replicas):
    """Scale a Deployment or StatefulSet."""
    if resource_type not in ("deployment", "statefulset"):
        raise ValueError("仅支持对 Deployment 和 StatefulSet 执行 scale 操作")
    api = _get_api_for_cluster(cluster_id, "AppsV1Api")
    kwargs = {"name": name, "namespace": namespace}
    try:
        if resource_type == "deployment":
            body = api.read_namespaced_deployment_scale(**kwargs)
            body.spec.replicas = replicas
            return api.replace_namespaced_deployment_scale(**kwargs, body=body)
        else:
            body = {"spec": {"replicas": replicas}}
            return api.patch_namespaced_stateful_set(**kwargs, body=body)
    except ApiException as e:
        raise e


def rollback_deployment(cluster_id, name, namespace, revision=None):
    """Rollback a Deployment to a specific controller revision.

    Uses a patch to trigger redeployment to the target revision.
    In Kubernetes 1.9+, the rollback API was deprecated; we emulate it by
    patching the Deployment with the target revision's template.
    """
    import copy

    api = _get_api_for_cluster(cluster_id, "AppsV1Api")

    if revision is not None:
        # Get the target controller revision and patch with its template
        try:
            rev = api.read_namespaced_controller_revision(
                name=f"{name}-{revision:010d}",
                namespace=namespace,
            )
            # Extract the pod template from the revision
            rev_data = rev.data
            if rev_data and hasattr(rev_data, 'spec') and rev_data.spec:
                template = rev_data.spec.template
                # Patch the deployment to use the template from the target revision
                patch_body = {
                    "spec": {
                        "template": {
                            "spec": template.to_dict() if hasattr(template, 'to_dict') else template
                        }
                    }
                }
                result = api.patch_namespaced_deployment(
                    name=name, namespace=namespace, body=patch_body,
                )
                return result
        except ApiException:
            pass  # Fall through to annotation-based approach

    # If no specific revision, or the above failed, use annotation-based restart
    # This triggers the deployment to redeploy from its current template
    import datetime
    patch_body = {
        "spec": {
            "template": {
                "metadata": {
                    "annotations": {
                        "kubectl.kubernetes.io/restartedAt": datetime.datetime.utcnow().isoformat() + "Z"
                    }
                }
            }
        }
    }
    return api.patch_namespaced_deployment(
        name=name, namespace=namespace, body=patch_body,
    )


def delete_resource(cluster_id, resource_type, name, namespace=None):
    """Delete a resource."""
    api, info, kwargs = _get_meta(cluster_id, resource_type, namespace)
    if not api:
        raise ValueError(f"不支持资源类型: {resource_type}")
    kwargs["name"] = name
    method = getattr(api, info["delete"])
    try:
        return method(**kwargs)
    except ApiException as e:
        raise e


def apply_yaml(cluster_id, yaml_content):
    """Apply YAML content using the dynamic client on a specific cluster."""
    from kubernetes.dynamic import DynamicClient
    from kubernetes.dynamic.exceptions import DynamicApiError

    docs = list(_yaml.safe_load_all(yaml_content))
    if not docs:
        raise ValueError("YAML 内容为空")

    # Build a dynamic client for this cluster
    cache = _get_client_cache(cluster_id)
    # Use any cached api to get the ApiClient — or rebuild config
    kubeconfig_text = _get_cluster_kubeconfig_text(cluster_id)
    cfg = _build_configuration(kubeconfig_text)
    dyn_client = DynamicClient(client.ApiClient(cfg))

    resource_name_map = {
        "deployment": ("apps", "deployments"),
        "statefulset": ("apps", "statefulsets"),
        "daemonset": ("apps", "daemonsets"),
        "replicaset": ("apps", "replicasets"),
        "service": ("", "services"),
        "pod": ("", "pods"),
        "configmap": ("", "configmaps"),
        "secret": ("", "secrets"),
        "namespace": ("", "namespaces"),
        "ingress": ("networking.k8s.io", "ingresses"),
        "role": ("rbac.authorization.k8s.io", "roles"),
        "rolebinding": ("rbac.authorization.k8s.io", "rolebindings"),
        "clusterrole": ("rbac.authorization.k8s.io", "clusterroles"),
        "clusterrolebinding": ("rbac.authorization.k8s.io", "clusterrolebindings"),
        "serviceaccount": ("", "serviceaccounts"),
    }

    results = []
    for doc in docs:
        if doc is None:
            continue
        kind = doc.get("kind", "").lower()
        api_version = doc.get("apiVersion", "v1")
        metadata = doc.get("metadata", {})
        name = metadata.get("name", "")
        namespace = metadata.get("namespace", "default")

        if "/" in api_version:
            group, version = api_version.split("/", 1)
        else:
            group, version = "", api_version

        api_group, resource_name = resource_name_map.get(kind, (group, kind + "s"))

        try:
            api_resource = dyn_client.resources.get(
                api_version=api_version, kind=doc["kind"],
            )
            if kind in ("namespace", "clusterrole", "clusterrolebinding"):
                try:
                    existing = api_resource.get(name=name)
                    result = api_resource.patch(
                        body=doc, content_type="application/merge-patch+json",
                    )
                    results.append({
                        "resource": f"{kind}/{name}", "action": "patched",
                        "uid": result.metadata.uid,
                    })
                except DynamicApiError:
                    result = api_resource.create(body=doc)
                    results.append({
                        "resource": f"{kind}/{name}", "action": "created",
                        "uid": result.metadata.uid,
                    })
            else:
                try:
                    existing = api_resource.get(name=name, namespace=namespace)
                    result = api_resource.patch(
                        body=doc, namespace=namespace,
                        content_type="application/merge-patch+json",
                    )
                    results.append({
                        "resource": f"{kind}/{name}", "action": "patched",
                        "namespace": namespace, "uid": result.metadata.uid,
                    })
                except DynamicApiError:
                    result = api_resource.create(body=doc, namespace=namespace)
                    results.append({
                        "resource": f"{kind}/{name}", "action": "created",
                        "namespace": namespace, "uid": result.metadata.uid,
                    })
        except DynamicApiError as e:
            raise e

    return results


def get_cluster_version(cluster_id):
    """Get server version for a cluster."""
    kubeconfig_text = _get_cluster_kubeconfig_text(cluster_id)
    cfg = _build_configuration(kubeconfig_text)
    api = client.VersionApi(api_client=client.ApiClient(cfg))
    return api.get_code().git_version
