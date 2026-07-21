<template>
  <div class="log-explorer">
    <div class="page-header">
      <h2>📜 日志浏览</h2>
      <div class="status-indicators">
        <span :class="['status-dot', esHealthy ? 'healthy' : 'unhealthy']" :title="esInfo"></span>
        <span class="status-label">Elasticsearch</span>
      </div>
    </div>

    <!-- Search Bar with Index Selector -->
    <div class="card search-bar">
      <div class="search-row">
        <input
          v-model="searchQuery"
          class="form-input search-input"
          placeholder="搜索日志内容... (支持 Lucene 语法: error, status:500)"
          @keydown.enter="doSearch(1)"
        />
        <select v-model="filterIndex" class="form-input" style="width:210px;" @change="doSearch(1)">
          <option value="">全部索引 (k8s-*)</option>
          <option value="k8s-backend-*">Backend</option>
          <option value="k8s-backend-error-*">Backend Errors</option>
          <option value="k8s-mysql-*">MySQL</option>
          <option value="k8s-redis-*">Redis</option>
          <option value="k8s-nginx-*">Nginx</option>
        </select>
        <button class="btn btn-primary" @click="doSearch(1)" :disabled="loading">
          {{ loading ? '搜索中...' : '搜索' }}
        </button>
      </div>
      <div class="filter-row">
        <div class="filter-group-inline">
          <label class="filter-label-sm">Namespace</label>
          <input v-model="filterNamespace" class="form-input filter-input" placeholder="全部" />
        </div>
        <div class="filter-group-inline">
          <label class="filter-label-sm">Pod</label>
          <input v-model="filterPod" class="form-input filter-input" placeholder="全部" />
        </div>
        <div class="filter-group-inline">
          <label class="filter-label-sm">起始时间</label>
          <input v-model="startTime" type="datetime-local" class="form-input filter-input" />
        </div>
        <div class="filter-group-inline">
          <label class="filter-label-sm">结束时间</label>
          <input v-model="endTime" type="datetime-local" class="form-input filter-input" />
        </div>
      </div>
    </div>

    <!-- Error -->
    <div v-if="error" class="card" style="color:#dc2626;margin-bottom:16px;">{{ error }}</div>

    <!-- Stats Summary -->
    <div v-if="logData" class="result-meta">
      共 <strong>{{ logData.total }}</strong> 条日志，第 {{ logData.page }} / {{ totalPages }} 页
    </div>

    <!-- Log Table -->
    <div v-if="logData && logData.items.length" class="log-table-wrapper">
      <table class="data-table log-table">
        <thead>
          <tr>
            <th style="width:160px;">时间</th>
            <th style="width:120px;">Namespace</th>
            <th style="width:150px;">Pod</th>
            <th style="width:100px;">容器</th>
            <th>日志内容</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in logData.items" :key="item.id" :class="{ 'log-row-error': isErrorLog(item) }">
            <td class="log-time">{{ formatTime(item.timestamp) }}</td>
            <td><span class="tag tag-blue">{{ item.namespace || '-' }}</span></td>
            <td class="log-pod">{{ item.pod_name || '-' }}</td>
            <td>{{ item.container_name || '-' }}</td>
            <td :class="['log-message', { 'log-message-error': isErrorLog(item) }]" :title="item.log">
              <span v-if="isErrorLog(item)" class="error-badge">ERROR</span>
              {{ item.log }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else-if="logData && !logData.items.length && !loading" class="card" style="text-align:center;color:#64748b;">
      没有找到匹配的日志
    </div>

    <!-- Pagination -->
    <div v-if="logData && totalPages > 1" class="pagination">
      <button class="btn" :disabled="logData.page <= 1" @click="doSearch(logData.page - 1)">上一页</button>
      <span>{{ logData.page }} / {{ totalPages }}</span>
      <button class="btn" :disabled="logData.page >= totalPages" @click="doSearch(logData.page + 1)">下一页</button>
    </div>

    <!-- Log Stats Panel -->
    <div class="card" style="margin-top:24px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <h3 style="margin:0;">📊 日志分布</h3>
        <div style="display:flex;gap:8px;align-items:center;">
          <label class="filter-label-sm" style="margin:0;">分组:</label>
          <select v-model="statsGroupBy" class="form-input" style="width:auto;" @change="loadStats">
            <option value="namespace">按 Namespace</option>
            <option value="pod">按 Pod</option>
            <option value="level">按 级别</option>
          </select>
        </div>
      </div>
      <div v-if="statsLoading" style="color:#64748b;">加载中...</div>
      <div v-else-if="statsData && statsData.length" class="stats-grid">
        <div v-for="s in statsData" :key="s.key" class="stat-bar-item" @click="applyStatFilter(s.key)" style="cursor:pointer;">
          <div class="stat-bar-label" :title="'点击过滤: ' + s.key">{{ s.key }}</div>
          <div class="stat-bar-track">
            <div class="stat-bar-fill" :style="{width: barWidth(s.count) + '%'}"></div>
          </div>
          <div class="stat-bar-count">{{ s.count }}</div>
        </div>
      </div>
      <div v-else style="color:#64748b;">暂无数据</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { searchLogs, getLogStats, getObservabilityStatus } from "../api/observability";

const searchQuery = ref("");
const filterIndex = ref("");
const filterNamespace = ref("");
const filterPod = ref("");
const startTime = ref("");
const endTime = ref("");
const loading = ref(false);
const error = ref("");
const logData = ref(null);

const statsGroupBy = ref("namespace");
const statsData = ref(null);
const statsLoading = ref(false);

const esHealthy = ref(false);
const esInfo = ref("检测中...");

const pageSize = 50;
let esPollTimer = null;

const totalPages = computed(() => {
  if (!logData.value) return 1;
  return Math.max(1, Math.ceil(logData.value.total / pageSize));
});

function formatTime(ts) {
  if (!ts) return "-";
  try {
    const d = new Date(ts);
    return d.toLocaleString("zh-CN", { hour12: false });
  } catch {
    return ts;
  }
}

function barWidth(count) {
  if (!statsData.value || !statsData.value.length) return 0;
  const max = Math.max(...statsData.value.map(s => s.count));
  return max > 0 ? (count / max) * 100 : 0;
}

function toISO(ts) {
  if (!ts) return "";
  try {
    return new Date(ts).toISOString();
  } catch {
    return ts;
  }
}

// Check if a log entry is an error
function isErrorLog(item) {
  if (!item) return false;
  const level = (item.level || "").toUpperCase();
  const log = (item.log || "").toUpperCase();
  return (
    level === "ERROR" || level === "CRITICAL" ||
    log.includes("ERROR") || log.includes("CRITICAL") ||
    log.includes("EXCEPTION") || log.includes("TRACEBACK") ||
    log.includes("FATAL")
  );
}

// Apply stats bar click → filter search
function applyStatFilter(key) {
  if (statsGroupBy.value === "level" || statsGroupBy.value === "namespace") {
    searchQuery.value = key;
  } else if (statsGroupBy.value === "pod") {
    filterPod.value = key;
  }
  doSearch(1);
}

async function doSearch(page) {
  loading.value = true;
  error.value = "";
  logData.value = null;
  try {
    const params = {
      query: searchQuery.value,
      namespace: filterNamespace.value,
      pod: filterPod.value,
      start_time: toISO(startTime.value),
      end_time: toISO(endTime.value),
      page: page || 1,
      page_size: pageSize,
    };
    if (filterIndex.value) {
      params.index = filterIndex.value;
    }
    const res = await searchLogs(params);
    logData.value = res.data;
  } catch (e) {
    error.value = e.message || "日志查询失败";
  } finally {
    loading.value = false;
  }
}

async function loadStats() {
  statsLoading.value = true;
  try {
    const params = {
      start_time: toISO(startTime.value),
      end_time: toISO(endTime.value),
      group_by: statsGroupBy.value,
    };
    if (filterIndex.value) {
      params.index = filterIndex.value;
    }
    const res = await getLogStats(params);
    statsData.value = res.data?.buckets || [];
  } catch (e) {
    statsData.value = [];
  } finally {
    statsLoading.value = false;
  }
}

// Poll ES health every 30 seconds
async function pollEsHealth() {
  try {
    const status = await getObservabilityStatus();
    esHealthy.value = status.data?.es_healthy || false;
    esInfo.value = esHealthy.value ? "正常" : (status.data?.es_info?.error || "不可用");
  } catch {
    esHealthy.value = false;
    esInfo.value = "检测失败";
  }
}

onMounted(async () => {
  // Check ES health
  await pollEsHealth();
  // Start polling every 30s
  esPollTimer = setInterval(pollEsHealth, 30000);

  // Set default time range: last 1 hour
  const now = new Date();
  const oneHourAgo = new Date(now.getTime() - 3600000);
  endTime.value = now.toISOString().slice(0, 16);
  startTime.value = oneHourAgo.toISOString().slice(0, 16);

  // Load initial data
  await doSearch(1);
  await loadStats();
});

onUnmounted(() => {
  if (esPollTimer) {
    clearInterval(esPollTimer);
    esPollTimer = null;
  }
});
</script>

<style scoped>
.log-explorer { max-width: 100%; }
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-header h2 { margin: 0; }
.status-indicators { display: flex; align-items: center; gap: 6px; }
.status-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.status-dot.healthy { background: #16a34a; }
.status-dot.unhealthy { background: #dc2626; }
.status-label { font-size: 12px; color: #64748b; }

.search-bar { margin-bottom: 16px; }
.search-row { display: flex; gap: 8px; margin-bottom: 12px; }
.search-input { flex: 1; }
.filter-row { display: flex; gap: 12px; flex-wrap: wrap; }
.filter-group-inline { display: flex; flex-direction: column; gap: 2px; }
.filter-label-sm { font-size: 11px; color: #64748b; }
.filter-input { width: 160px; }

.result-meta {
  font-size: 13px; color: #64748b; margin-bottom: 8px;
}

.log-table-wrapper { overflow-x: auto; }
.log-table { font-size: 12px; }
.log-table th { white-space: nowrap; }
.log-time { white-space: nowrap; font-size: 11px; color: #64748b; }
.log-pod { font-family: monospace; font-size: 11px; max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.log-message {
  font-family: monospace; font-size: 11px;
  max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

/* Error highlighting */
.log-row-error {
  background: rgba(220, 38, 38, 0.06);
}
.log-row-error:hover td {
  background: rgba(220, 38, 38, 0.1) !important;
}
.log-message-error {
  color: #dc2626;
  font-weight: 500;
}
.error-badge {
  display: inline-block;
  background: #dc2626;
  color: #fff;
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 3px;
  margin-right: 4px;
  font-weight: 600;
  vertical-align: middle;
}

.pagination {
  display: flex; gap: 12px; align-items: center;
  justify-content: center; margin-top: 16px;
}
.pagination span { font-size: 13px; color: #64748b; }

.stats-grid { display: flex; flex-direction: column; gap: 8px; }
.stat-bar-item {
  display: flex; align-items: center; gap: 12px;
  padding: 2px 4px;
  border-radius: 4px;
  transition: background 0.15s;
}
.stat-bar-item:hover {
  background: #f1f5f9;
}
.stat-bar-label {
  width: 140px; font-size: 12px; overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap;
}
.stat-bar-track {
  flex: 1; height: 18px; background: #e2e8f0; border-radius: 4px; overflow: hidden;
}
.stat-bar-fill {
  height: 100%; background: #3b82f6; border-radius: 4px;
  min-width: 2px; transition: width 0.3s;
}
.stat-bar-count {
  width: 60px; text-align: right; font-size: 12px; color: #64748b; font-weight: 600;
}
</style>
