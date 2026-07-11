import client from "./client";

export function listAuditLogs(filters = {}) {
  return client.post("/audit/list", filters);
}
