import client from "./client";

export function listResources(resourceType, namespace) {
  return client.post("/resources/list", {
    resource_type: resourceType,
    namespace: namespace || undefined,
  });
}

export function getResourceDetail(resourceType, name, namespace) {
  return client.post("/resources/detail", {
    resource_type: resourceType,
    name,
    namespace: namespace || undefined,
  });
}

export function getResourceYaml(resourceType, name, namespace) {
  return client.post("/resources/yaml", {
    resource_type: resourceType,
    name,
    namespace: namespace || undefined,
  });
}

export function scaleResource(resourceType, name, namespace, replicas) {
  return client.post("/resources/scale", {
    resource_type: resourceType,
    name,
    namespace,
    replicas,
  });
}

export function rollbackDeployment(name, namespace, revision) {
  return client.post("/resources/rollback", {
    resource_type: "deployment",
    name,
    namespace,
    revision: revision || undefined,
  });
}

export function deleteResource(resourceType, name, namespace) {
  return client.post("/resources/delete", {
    resource_type: resourceType,
    name,
    namespace,
  });
}

export function applyYaml(yamlContent) {
  return client.post("/resources/apply", {
    yaml_content: yamlContent,
  });
}
