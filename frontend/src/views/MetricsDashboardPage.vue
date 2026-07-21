<template>
  <div class="metrics-page">
    <div class="page-header">
      <h2>📈 集群指标</h2>
      <div class="status-indicators">
        <span :class="['status-dot', promHealthy ? 'healthy' : 'unhealthy']" :title="promInfo"></span>
        <span class="status-label">Prometheus</span>
      </div>
    </div>

    <!-- Quick Metric Cards -->
    <div class="metrics-grid">
      <div class="card metric-card" v-for="m in quickMetrics" :key="m.label">
        <div class="metric-label">{{ m.label }}</div>
        <div class="metric-value" :class="{ 'metric-error': m.error }">
          {{ m.loading ? '...' : (m.error ? '错误' : m.value) }}
        </div>
        <div class="metric-unit">{{ m.unit }}</div>
      </div>
    </div>

    <!-- Node CPU Chart -->
    <div class="card chart-card">
      <h3>节点 CPU 使用率</h3>
      <div v-if="cpuData.length" class="chart-bars">
        <div v-for="d in cpuData" :key="d.name" class="chart-bar-item">
          <div class="chart-bar-label">{{ d.name }}</div>
          <div class="chart-bar-track">
            <div class="chart-bar-fill" :style="{width: d.value + '%'}"></div>
          </div>
          <div class="chart-bar-val">{{ d.value.toFixed(1) }}%</div>
        </div>
      </div>
      <div v-else-if="cpuLoading" style="color:#64748b;">加载中...</div>
      <div v-else style="color:#64748b;">暂无数据</div>
    </div>

    <!-- Node Memory Chart -->
    <div class="card chart-card">
      <h3>节点 内存使用率</h3>
      <div v-if="memData.length" class="chart-bars">
        <div v-for="d in memData" :key="d.name" class="chart-bar-item">
          <div class="chart-bar-label">{{ d.name }}</div>
          <div class="chart-bar-track">
            <div class="chart-bar-fill mem-fill" :style="{width: d.value + '%'}"></div>
          </div>
          <div class="chart-bar-val">{{ d.value.toFixed(1) }}%</div>
        </div>
      </div>
      <div v-else-if="memLoading" style="color:#64748b;">加载中...</div>
      <div v-else style="color:#64748b;">暂无数据</div>
    </div>

    <!-- Pod Count -->
    <div class="card chart-card">
      <h3>Pod 数量 (按 Namespace)</h3>
      <div v-if="podData.length" class="chart-bars">
        <div v-for="d in podData" :key="d.name" class="chart-bar-item">
          <div class="chart-bar-label">{{ d.name }}</div>
          <div class="chart-bar-track">
            <div class="chart-bar-fill pod-fill" :style="{width: barWidthPct(d.value, podData) + '%'}"></div>
          </div>
          <div class="chart-bar-val">{{ d.value }}</div>
        </div>
      </div>
      <div v-else-if="podLoading" style="color:#64748b;">加载中...</div>
      <div v-else style="color:#64748b;">暂无数据</div>
    </div>

    <!-- Error Rate -->
    <div class="card chart-card">
      <h3>错误率 (最近 5 分钟)</h3>
      <div v-if="errorRateData.length" class="chart-bars">
        <div v-for="d in errorRateData" :key="d.name" class="chart-bar-item">
          <div class="chart-bar-label">{{ d.name }}</div>
          <div class="chart-bar-track">
            <div class="chart-bar-fill error-fill" :style="{width: barWidthPct(d.value, errorRateData) + '%'}"></div>
          </div>
          <div class="chart-bar-val">{{ d.value.toFixed(2) }}/s</div>
        </div>
      </div>
      <div v-else-if="errorRateLoading" style="color:#64748b;">加载中...</div>
      <div v-else style="color:#64748b;">暂无数据</div>
    </div>

    <!-- Custom Query -->
    <div class="card">
      <h3 style="margin-bottom:12px;">自定义 PromQL 查询</h3>
      <div class="query-row">
        <input
          v-model="customQuery"
          class="form-input"
          placeholder="输入 PromQL 查询，例如：up, rate(node_cpu_seconds_total[5m])"
          style="flex:1;font-family:monospace;"
          @keydown.enter="runCustomQuery"
        />
        <button class="btn btn-primary" @click="runCustomQuery" :disabled="customLoading">
          {{ customLoading ? '查询中...' : '查询' }}
        </button>
      </div>
      <div v-if="customError" style="color:#dc2626;margin-top:8px;">{{ customError }}</div>
      <div v-if="customResult" style="margin-top:12px;">
        <table class="data-table" v-if="customResult.length">
          <thead>
            <tr>
              <th>Metric</th>
              <th>Labels</th>
              <th>Value</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(r, idx) in customResult" :key="idx">
              <td><code>{{ r.metric?.__name__ || '-' }}</code></td>
              <td style="font-size:11px;">{{ formatLabels(r.metric) }}</td>
              <td><strong>{{ r.value?.[1] || '-' }}</strong></td>
            </tr>
          </tbody>
        </table>
        <div v-else style="color:#64748b;">查询无结果</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import { queryMetric, getObservabilityStatus } from "../api/observability";

const promHealthy = ref(false);
const promInfo = ref("检测中...");

// Quick metric cards
const quickMetrics = ref([
  { label: "集群节点数", value: "...", unit: "", loading: true, error: false, key: "nodes" },
  { label: "运行中 Pod", value: "...", unit: "", loading: true, error: false, key: "pods" },
  { label: "CPU 核心", value: "...", unit: "", loading: true, error: false, key: "cpu" },
  { label: "内存总量", value: "...", unit: "GB", loading: true, error: false, key: "memory" },
  { label: "DB 连接数", value: "...", unit: "", loading: true, error: false, key: "db_connections" },
]);

// Node CPU data
const cpuData = ref([]);
const cpuLoading = ref(true);
const memData = ref([]);
const memLoading = ref(true);
const podData = ref([]);
const podLoading = ref(true);

// Error rate data
const errorRateData = ref([]);
const errorRateLoading = ref(true);

// Custom query
const customQuery = ref("");
const customResult = ref(null);
const customError = ref("");
const customLoading = ref(false);

// Auto-refresh interval IDs
let quickMetricsTimer = null;
let cpuTimer = null;
let memTimer = null;

function barWidthPct(value, data) {
  if (!data.length) return 0;
  const max = Math.max(...data.map(d => d.value));
  return max > 0 ? (value / max) * 100 : 0;
}

function formatLabels(metric) {
  if (!metric) return "-";
  const entries = Object.entries(metric).filter(([k]) => k !== "__name__");
  return entries.map(([k, v]) => `${k}="${v}"`).join(", ");
}

async function fetchMetric(queryStr) {
  try {
    const res = await queryMetric({ query: queryStr });
    return res.data?.result || [];
  } catch {
    return [];
  }
}

async function loadQuickMetrics() {
  // Nodes count
  const nodes = await fetchMetric("count(kube_node_info)");
  updateQuickCard("nodes", nodes, val => val, " 个");

  // Running pods
  const pods = await fetchMetric('sum(kube_pod_status_phase{phase="Running"})');
  updateQuickCard("pods", pods, val => val, " 个");

  // CPU cores
  const cpu = await fetchMetric('count(count(node_cpu_seconds_total{mode="idle"}) by (cpu,instance))');
  updateQuickCard("cpu", cpu, val => val, " 核");

  // Total memory
  const mem = await fetchMetric("sum(node_memory_MemTotal_bytes) / 1024 / 1024 / 1024");
  updateQuickCard("memory", mem, val => Number(val).toFixed(1), " GB");

  // DB connections
  const db = await fetchMetric("django_db_connections_total");
  updateQuickCard("db_connections", db, val => val || "0", " 个");
}

function updateQuickCard(key, results, formatter, unit) {
  const idx = quickMetrics.value.findIndex(m => m.key === key);
  if (idx < 0) return;
  if (!results || !results.length) {
    quickMetrics.value[idx].value = "N/A";
    quickMetrics.value[idx].error = true;
  } else {
    const val = results[0]?.value?.[1];
    quickMetrics.value[idx].value = formatter ? formatter(val) : (val || "0");
    quickMetrics.value[idx].error = false;
  }
  quickMetrics.value[idx].loading = false;
  quickMetrics.value[idx].unit = unit;
}

async function loadCPUData() {
  cpuLoading.value = true;
  const results = await fetchMetric(
    '100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'
  );
  cpuData.value = results.map(r => ({
    name: r.metric?.instance || "unknown",
    value: parseFloat(r.value?.[1] || 0),
  }));
  cpuLoading.value = false;
}

async function loadMemoryData() {
  memLoading.value = true;
  const results = await fetchMetric(
    "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100"
  );
  memData.value = results.map(r => ({
    name: r.metric?.instance || "unknown",
    value: parseFloat(r.value?.[1] || 0),
  }));
  memLoading.value = false;
}

async function loadPodData() {
  podLoading.value = true;
  const results = await fetchMetric("count by (namespace) (kube_pod_info)");
  podData.value = results.map(r => ({
    name: r.metric?.namespace || "unknown",
    value: parseInt(r.value?.[1] || 0),
  }));
  podLoading.value = false;
}

async function loadErrorRate() {
  errorRateLoading.value = true;
  const results = await fetchMetric(
    'rate(django_log_errors_total[5m])'
  );
  errorRateData.value = results.map(r => {
    const ns = r.metric?.namespace || "";
    const pod = r.metric?.pod || "";
    const label = ns && pod ? `${ns}/${pod}` : (ns || pod || "unknown");
    return {
      name: label,
      value: parseFloat(r.value?.[1] || 0),
    };
  });
  errorRateLoading.value = false;
}

async function runCustomQuery() {
  if (!customQuery.value.trim()) return;
  customLoading.value = true;
  customError.value = "";
  customResult.value = null;
  try {
    const res = await queryMetric({ query: customQuery.value });
    customResult.value = res.data?.result || [];
  } catch (e) {
    customError.value = e.message || "查询失败";
  } finally {
    customLoading.value = false;
  }
}

onMounted(async () => {
  // Check prometheus health
  try {
    const status = await getObservabilityStatus();
    promHealthy.value = status.data?.prometheus_healthy || false;
    promInfo.value = promHealthy.value
      ? `${status.data?.prom_info?.targets_up || 0}/${status.data?.prom_info?.targets_total || 0} up`
      : (status.data?.prom_info?.error || "不可用");
  } catch {
    promHealthy.value = false;
    promInfo.value = "检测失败";
  }

  // Load all data initially
  await Promise.allSettled([
    loadQuickMetrics(),
    loadCPUData(),
    loadMemoryData(),
    loadPodData(),
    loadErrorRate(),
  ]);

  // Set up auto-refresh intervals (15s each)
  quickMetricsTimer = setInterval(loadQuickMetrics, 15000);
  cpuTimer = setInterval(loadCPUData, 15000);
  memTimer = setInterval(loadMemoryData, 15000);
});

onUnmounted(() => {
  if (quickMetricsTimer) clearInterval(quickMetricsTimer);
  if (cpuTimer) clearInterval(cpuTimer);
  if (memTimer) clearInterval(memTimer);
});
</script>

<style scoped>
.metrics-page { max-width: 100%; }
.page-header {
  display: flex; justify-content: space-between;
  align-items: center; margin-bottom: 16px;
}
.page-header h2 { margin: 0; }
.status-indicators { display: flex; align-items: center; gap: 6px; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.status-dot.healthy { background: #16a34a; }
.status-dot.unhealthy { background: #dc2626; }
.status-label { font-size: 12px; color: #64748b; }

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px; margin-bottom: 20px;
}
.metric-card { text-align: center; padding: 20px 16px; }
.metric-label { font-size: 12px; color: #64748b; margin-bottom: 8px; }
.metric-value { font-size: 28px; font-weight: 700; color: #1e293b; }
.metric-value.metric-error { font-size: 18px; color: #dc2626; }
.metric-unit { font-size: 12px; color: #94a3b8; margin-top: 4px; }

.chart-card { margin-bottom: 16px; }
.chart-card h3 { margin-bottom: 12px; }

.chart-bars { display: flex; flex-direction: column; gap: 8px; }
.chart-bar-item { display: flex; align-items: center; gap: 12px; }
.chart-bar-label {
  width: 180px; font-size: 11px; overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap; font-family: monospace;
}
.chart-bar-track {
  flex: 1; height: 24px; background: #e2e8f0; border-radius: 4px; overflow: hidden;
}
.chart-bar-fill {
  height: 100%; background: #3b82f6; border-radius: 4px;
  min-width: 2px; transition: width 0.3s;
}
.chart-bar-fill.mem-fill { background: #8b5cf6; }
.chart-bar-fill.pod-fill { background: #10b981; }
.chart-bar-fill.error-fill { background: #ef4444; }
.chart-bar-val {
  width: 70px; text-align: right; font-size: 12px;
  color: #64748b; font-weight: 600; font-family: monospace;
}

.query-row { display: flex; gap: 8px; }
</style>