import client from "./client";

export function login(username, password) {
  return client.post("/auth/login", { username, password });
}

export function logout() {
  return client.post("/auth/logout");
}

export function changePassword(oldPassword, newPassword) {
  return client.post("/auth/change-password", {
    old_password: oldPassword,
    new_password: newPassword,
  });
}
