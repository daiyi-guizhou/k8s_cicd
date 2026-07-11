import client from "./client";

let _getClusterId = () => null;

/** Called once at app startup to wire the cluster store. */
export function setClusterIdProvider(fn) {
  _getClusterId = fn;
}

function clusterId() {
  return _getClusterId();
}

export function listResources(resourceType, namespace) {
  return client.post("/resources/list", {
    cluster_id: clusterId(),
    resource_type: resourceType,
    namespace: namespace || undefined,
  });
}

export function getResourceDetail(resourceType, name, namespace) {
  return client.post("/resources/detail", {
    cluster_id: clusterId(),
    resource_type: resourceType,
    name,
    namespace: namespace || undefined,
  });
}

export function getResourceYaml(resourceType, name, namespace) {
  return client.post("/resources/yaml", {
    cluster_id: clusterId(),
    resource_type: resourceType,
    name,
    namespace: namespace || undefined,
  });
}

export function scaleResource(resourceType, name, namespace, replicas) {
  return client.post("/resources/scale", {
    cluster_id: clusterId(),
    resource_type: resourceType,
    name,
    namespace,
    replicas,
  });
}

export function rollbackDeployment(name, namespace, revision) {
  return client.post("/resources/rollback", {
    cluster_id: clusterId(),
    resource_type: "deployment",
    name,
    namespace,
    revision: revision || undefined,
  });
}

export function deleteResource(resourceType, name, namespace) {
  return client.post("/resources/delete", {
    cluster_id: clusterId(),
    resource_type: resourceType,
    name,
    namespace,
  });
}

export function applyYaml(yamlContent) {
  return client.post("/resources/apply", {
    cluster_id: clusterId(),
    yaml_content: yamlContent,
  });
}
