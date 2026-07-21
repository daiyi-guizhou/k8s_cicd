import client from "./client";

// --- Logs (Elasticsearch) ---

export function searchLogs(params = {}) {
  return client.post("/observability/logs/search", params);
}

export function getLogStats(params = {}) {
  return client.post("/observability/logs/stats", params);
}

// --- Metrics (Prometheus) ---

export function queryMetric(params = {}) {
  return client.get("/observability/metrics/query", { params });
}

export function queryMetricRange(params = {}) {
  return client.get("/observability/metrics/range", { params });
}

export function getMetricLabels(params = {}) {
  return client.get("/observability/metrics/labels", { params });
}

// --- Health ---

export function getObservabilityStatus() {
  return client.get("/observability/status");
}
