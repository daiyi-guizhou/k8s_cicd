"""Unified K8s API client — single entry point for all cluster operations."""
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


def _get_api(api_name):
    """Get a configured API client instance."""
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()

    api_map = {
        "CoreV1Api": client.CoreV1Api(),
        "AppsV1Api": client.AppsV1Api(),
        "NetworkingV1Api": client.NetworkingV1Api(),
        "RbacAuthorizationV1Api": client.RbacAuthorizationV1Api(),
    }
    return api_map[api_name]


def _get_meta(resource_type, namespace=None):
    """Get API, resource info, and kwargs for a resource type."""
    info = _RESOURCE_MAP.get(resource_type)
    if not info:
        return None, None, None
    api = _get_api(info["api"])
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


def list_resources(resource_type, namespace=None):
    """List all resources of given type. Returns list of dicts."""
    api, info, kwargs = _get_meta(resource_type, namespace)
    if not api:
        raise ValueError(f"不支持资源类型: {resource_type}")
    method = getattr(api, info["list"])
    try:
        if info["namespaced"]:
            if namespace:
                result = method(namespace)
            else:
                result = method(_for_all_namespaces=True)
        else:
            result = method()
        items = []
        for item in result.items:
            _sanitize(item)
            items.append(item.to_dict())
        return items
    except ApiException as e:
        raise e


def get_resource(resource_type, name, namespace=None):
    """Get single resource as dict."""
    api, info, kwargs = _get_meta(resource_type, namespace)
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


def get_resource_yaml(resource_type, name, namespace=None):
    """Get resource as YAML string (sanitized)."""
    api, info, kwargs = _get_meta(resource_type, namespace)
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


def scale_resource(resource_type, name, namespace, replicas):
    """Scale a Deployment or StatefulSet."""
    if resource_type not in ("deployment", "statefulset"):
        raise ValueError("仅支持对 Deployment 和 StatefulSet 执行 scale 操作")
    api = _get_api("AppsV1Api")
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


def rollback_deployment(name, namespace, revision=None):
    """Rollback a Deployment to a specific revision."""
    api = _get_api("AppsV1Api")
    body = client.V1RollbackConfig(
        name=name,
        revision=revision,
    )
    rollback_body = client.V1DeploymentRollback(
        name=name,
        rollback_to=body,
    )
    try:
        return api.create_namespaced_deployment_rollback(
            name=name, namespace=namespace, body=rollback_body,
        )
    except ApiException as e:
        raise e


def delete_resource(resource_type, name, namespace=None):
    """Delete a resource."""
    api, info, kwargs = _get_meta(resource_type, namespace)
    if not api:
        raise ValueError(f"不支持资源类型: {resource_type}")
    kwargs["name"] = name
    method = getattr(api, info["delete"])
    try:
        return method(**kwargs)
    except ApiException as e:
        raise e


def apply_yaml(yaml_content):
    """Apply YAML content using the dynamic client. Returns result list."""
    from kubernetes.dynamic import DynamicClient
    from kubernetes.dynamic.exceptions import DynamicApiError

    docs = list(_yaml.safe_load_all(yaml_content))
    if not docs:
        raise ValueError("YAML 内容为空")

    results = []
    dyn_client = DynamicClient(client.ApiClient())

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
