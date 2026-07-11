"""K8s resource CRUD views."""
from kubernetes.client.rest import ApiException

from rest_framework.decorators import api_view

from apps.resources.k8s_client import (
    list_resources, get_resource, get_resource_yaml,
    scale_resource, rollback_deployment, delete_resource, apply_yaml,
    _RESOURCE_MAP,
)
from utils.response import (
    success, error,
    ERR_RESOURCE_NOT_FOUND, ERR_K8S_API_ERROR,
    ERR_INVALID_YAML, ERR_UNSUPPORTED_RESOURCE, ERR_NAMESPACE_REQUIRED,
    ERR_VALIDATION,
)
from utils.k8s_helper import wrap_k8s_error


def _check_namespaced(resource_type, namespace):
    """Return error response if resource needs namespace but none provided."""
    info = _RESOURCE_MAP.get(resource_type)
    if info and info["namespaced"] and not namespace:
        return error(ERR_NAMESPACE_REQUIRED, "此资源类型需要指定 namespace")
    return None


def _handle_api_error(exc, default_code=None):
    """Convert an exception to a DRF error response."""
    if isinstance(exc, ValueError):
        return error(ERR_UNSUPPORTED_RESOURCE, str(exc))
    if isinstance(exc, ApiException):
        code, msg, detail = wrap_k8s_error(exc)
        return error(code, msg, detail)
    return error(default_code or ERR_K8S_API_ERROR, str(exc))


@api_view(["POST"])
def resource_list(request):
    """List resources: {resource_type, namespace?}"""
    resource_type = request.data.get("resource_type", "").strip().lower()
    namespace = request.data.get("namespace", "").strip() or None

    if resource_type not in _RESOURCE_MAP:
        return error(ERR_UNSUPPORTED_RESOURCE, f"不支持的资源类型: {resource_type}")

    if resource_type in ("clusterrole", "clusterrolebinding"):
        namespace = None

    try:
        items = list_resources(resource_type, namespace=namespace)
        return success(data={"items": items, "count": len(items)})
    except (ApiException, ValueError) as e:
        return _handle_api_error(e)


@api_view(["POST"])
def resource_detail(request):
    """Get resource detail as JSON: {resource_type, name, namespace?}"""
    resource_type = request.data.get("resource_type", "").strip().lower()
    name = request.data.get("name", "").strip()
    namespace = request.data.get("namespace", "").strip() or None

    if not name:
        return error(ERR_VALIDATION, "缺少资源名称")

    if resource_type not in _RESOURCE_MAP:
        return error(ERR_UNSUPPORTED_RESOURCE, f"不支持的资源类型: {resource_type}")

    err = _check_namespaced(resource_type, namespace)
    if err:
        return err

    try:
        data = get_resource(resource_type, name, namespace=namespace)
        return success(data=data)
    except (ApiException, ValueError) as e:
        return _handle_api_error(e)


@api_view(["POST"])
def resource_yaml(request):
    """Get resource YAML: {resource_type, name, namespace?}"""
    resource_type = request.data.get("resource_type", "").strip().lower()
    name = request.data.get("name", "").strip()
    namespace = request.data.get("namespace", "").strip() or None

    if not name:
        return error(ERR_VALIDATION, "缺少资源名称")

    if resource_type not in _RESOURCE_MAP:
        return error(ERR_UNSUPPORTED_RESOURCE, f"不支持的资源类型: {resource_type}")

    err = _check_namespaced(resource_type, namespace)
    if err:
        return err

    try:
        yaml_str = get_resource_yaml(resource_type, name, namespace=namespace)
        return success(data={"yaml": yaml_str})
    except (ApiException, ValueError) as e:
        return _handle_api_error(e)


@api_view(["POST"])
def resource_scale(request):
    """Scale replicas: {resource_type, name, namespace?, replicas}"""
    resource_type = request.data.get("resource_type", "").strip().lower()
    name = request.data.get("name", "").strip()
    namespace = request.data.get("namespace", "").strip() or None
    replicas = request.data.get("replicas")

    if not name:
        return error(ERR_VALIDATION, "缺少资源名称")

    if replicas is None or not isinstance(replicas, int) or replicas < 0:
        return error(ERR_VALIDATION, "副本数必须是非负整数")

    if resource_type not in ("deployment", "statefulset"):
        return error(ERR_UNSUPPORTED_RESOURCE, "仅支持对 Deployment 和 StatefulSet 执行 scale 操作")

    err = _check_namespaced(resource_type, namespace)
    if err:
        return err

    try:
        result = scale_resource(resource_type, name, namespace, replicas)
        return success(data={
            "resource_type": resource_type,
            "name": name,
            "namespace": namespace,
            "replicas": replicas,
        }, message=f"已将 {resource_type}/{name} 副本数调整为 {replicas}")
    except (ApiException, ValueError) as e:
        return _handle_api_error(e)


@api_view(["POST"])
def resource_rollback(request):
    """Rollback Deployment: {resource_type, name, namespace?, revision?}"""
    resource_type = request.data.get("resource_type", "").strip().lower()
    name = request.data.get("name", "").strip()
    namespace = request.data.get("namespace", "").strip() or None
    revision = request.data.get("revision")

    if not name:
        return error(ERR_VALIDATION, "缺少资源名称")

    if resource_type != "deployment":
        return error(ERR_UNSUPPORTED_RESOURCE, "仅支持对 Deployment 执行回滚操作")

    err = _check_namespaced(resource_type, namespace)
    if err:
        return err

    try:
        result = rollback_deployment(name, namespace, revision=revision)
        rev_text = f"到版本 {revision}" if revision else "到上一个版本"
        return success(message=f"Deployment {name} 已回滚{rev_text}")
    except (ApiException, ValueError) as e:
        return _handle_api_error(e)


@api_view(["POST"])
def resource_delete(request):
    """Delete resource: {resource_type, name, namespace?}"""
    resource_type = request.data.get("resource_type", "").strip().lower()
    name = request.data.get("name", "").strip()
    namespace = request.data.get("namespace", "").strip() or None

    if not name:
        return error(ERR_VALIDATION, "缺少资源名称")

    if resource_type not in _RESOURCE_MAP:
        return error(ERR_UNSUPPORTED_RESOURCE, f"不支持的资源类型: {resource_type}")

    err = _check_namespaced(resource_type, namespace)
    if err:
        return err

    try:
        delete_resource(resource_type, name, namespace=namespace)
        return success(message=f"已删除 {resource_type}/{name}")
    except (ApiException, ValueError) as e:
        return _handle_api_error(e)


@api_view(["POST"])
def resource_apply(request):
    """Apply YAML: {yaml_content}"""
    yaml_content = request.data.get("yaml_content", "")

    if not yaml_content or not yaml_content.strip():
        return error(ERR_INVALID_YAML, "YAML 内容为空")

    try:
        results = apply_yaml(yaml_content)
        return success(data={"results": results}, message=f"成功处理 {len(results)} 个资源")
    except (ApiException, ValueError, Exception) as e:
        if isinstance(e, ApiException):
            return _handle_api_error(e)
        return error(ERR_INVALID_YAML, "YAML 解析或执行失败", str(e))
