import client from "./client";

export function listUsers() {
  return client.post("/users/list", {});
}

export function createUser(username, role) {
  return client.post("/users/create", { username, role });
}

export function toggleUserActive(id) {
  return client.post("/users/toggle-active", { id });
}

export function resetUserPassword(id) {
  return client.post("/users/reset-password", { id });
}
