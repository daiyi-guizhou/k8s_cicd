import client from "./client";

// Project CRUD
export function listProjects() {
  return client.post("/deploy/projects", {});
}

export function createProject(data) {
  return client.post("/deploy/project/create", data);
}

export function updateProject(data) {
  return client.post("/deploy/project/update", data);
}

export function deleteProject(appName) {
  return client.post("/deploy/project/delete", { app_name: appName });
}

// Deploy
export function triggerDeploy(appName, tag) {
  return client.post("/deploy/trigger", { app_name: appName, tag });
}

export function rollbackDeploy(appName, tag) {
  return client.post("/deploy/rollback", { app_name: appName, tag });
}

// History
export function listDeployHistory(appName) {
  return client.post("/deploy/history", { app_name: appName });
}
