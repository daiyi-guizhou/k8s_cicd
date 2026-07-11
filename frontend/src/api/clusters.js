import client from "./client";

export function getClusterList() {
  return client.post("/clusters/list", {});
}

export function createCluster(name, description, kubeconfigContent) {
  return client.post("/clusters/create", {
    name,
    description,
    kubeconfig_content: kubeconfigContent,
  });
}

export function updateCluster(id, data) {
  return client.post("/clusters/update", { id, ...data });
}

export function deleteCluster(id) {
  return client.post("/clusters/delete", { id });
}

export function testCluster(id) {
  return client.post("/clusters/test", { id });
}
