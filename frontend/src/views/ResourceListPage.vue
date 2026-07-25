<template>
  <div>
    <h2 style="margin-bottom:16px;">📦 资源管理</h2>

    <!-- 监控与日志快捷入口：集中跳转 Prometheus / Alertmanager / Grafana / Kibana -->
    <div class="quick-links">
      <span class="ql-label">🔗 监控与日志：</span>
      <a class="ql-link" href="http://grafana.monitoring.local:9001/" target="_blank" rel="noopener">📊 Grafana</a>
      <a class="ql-link" href="http://prometheus.monitoring.local:9091/" target="_blank" rel="noopener">🔥 Prometheus</a>
      <a class="ql-link" href="http://alertmanager.monitoring.local:9091/" target="_blank" rel="noopener">🔔 Alertmanager</a>
      <a class="ql-link" href="http://kibana.logging.local:9001/" target="_blank" rel="noopener">🔍 Kibana</a>
    </div>

    <!-- Toolbar: 3 filters -->
    <div class="toolbar">
      <!-- Resource type combobox -->
      <div class="filter-group">
        <label class="filter-label">资源类型</label>
        <div class="combobox" ref="typeComboRef">
          <input
            v-model="typeSearch"
            class="form-input combobox-input"
            placeholder="搜索资源类型..."
            @focus="showTypeDropdown = true"
            @blur="hideTypeDropdown"
            @keydown.down.prevent="moveTypeHighlight(1)"
            @keydown.up.prevent="moveTypeHighlight(-1)"
            @keydown.enter.prevent="selectHighlightedType"
          />
          <div v-if="showTypeDropdown" class="combobox-dropdown">
            <div v-if="filteredCommonTypes.length" class="dropdown-section-label">⭐ 常用</div>
            <div
              v-for="(rt, idx) in filteredCommonTypes"
              :key="rt.type"
              :class="['dropdown-item', { highlighted: typeHighlightIndex === idx }]"
              @mousedown.prevent="selectResourceType(rt)"
            >{{ rt.label }} <span class="dropdown-count">({{ rt.count ?? '...' }})</span></div>
            <div v-if="filteredOtherTypes.length" class="dropdown-section-label">📋 其他</div>
            <div
              v-for="(rt, idx) in filteredOtherTypes"
              :key="rt.type"
              :class="['dropdown-item', { highlighted: typeHighlightIndex === filteredCommonTypes.length + idx }]"
              @mousedown.prevent="selectResourceType(rt)"
            >{{ rt.label }} <span class="dropdown-count">({{ rt.count ?? '...' }})</span></div>
            <div v-if="filteredCommonTypes.length === 0 && filteredOtherTypes.length === 0" class="dropdown-item" style="color:#94a3b8;">
              无匹配资源类型
            </div>
          </div>
        </div>
      </div>

      <!-- Namespace combobox (hidden for cluster-scoped) -->
      <div v-if="isNamespaced" class="filter-group">
        <label class="filter-label">Namespace</label>
        <div class="combobox" ref="nsComboRef">
          <input
            v-model="nsSearch"
            class="form-input combobox-input"
            placeholder="搜索 namespace..."
            @focus="showNsDropdown = true"
            @blur="hideNsDropdown"
            @keydown.down.prevent="moveNsHighlight(1)"
            @keydown.up.prevent="moveNsHighlight(-1)"
            @keydown.enter.prevent="selectHighlightedNs"
          />
          <div v-if="showNsDropdown" class="combobox-dropdown">
            <div
              :class="['dropdown-item', { highlighted: nsHighlightIndex === 0 }]"
              @mousedown.prevent="selectNamespace('全部', 0)"
            >全部</div>
            <div
              v-for="(ns, idx) in filteredNamespaces"
              :key="ns"
              :class="['dropdown-item', { highlighted: nsHighlightIndex === idx + 1 }]"
              @mousedown.prevent="selectNamespace(ns, idx + 1)"
            >{{ ns }}</div>
          </div>
        </div>
      </div>

      <!-- Resource name filter -->
      <div class="filter-group">
        <label class="filter-label">资源名称</label>
        <input
          v-model="nameSearch"
          class="form-input"
          placeholder="输入名称过滤..."
          style="min-width:180px;"
          @input="onNameSearchChange"
        />
      </div>

      <button class="btn" style="margin-left:auto;align-self:flex-end;" @click="fetchData">🔄 刷新</button>
    </div>

    <!-- Data table -->
    <div v-if="loading" style="color:#64748b;">加载中...</div>
    <div v-else-if="error" class="card" style="color:#dc2626;">{{ error }}</div>
    <table v-else class="data-table">
      <thead>
        <tr>
          <th v-for="col in columns" :key="col.key">{{ col.label }}</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in filteredItems" :key="itemKey(item)">
          <td v-for="col in columns" :key="col.key">
            <template v-if="col.key === 'status'">
              <span :class="['tag', statusClass(item)]">{{ statusText(item) }}</span>
            </template>
            <template v-else>{{ getNested(item, col.key) }}</template>
          </td>
          <td class="actions-cell">
            <button class="btn" @click="viewYaml(item)" style="font-size:12px;">YAML</button>
            <button v-if="canScale" class="btn" @click="openScale(item)" style="font-size:12px;">Scale</button>
            <button v-if="currentType === 'deployment'" class="btn" @click="openRollback(item)" style="font-size:12px;">Rollback</button>
            <button v-if="currentType !== 'namespace'" class="btn" @click="openDelete(item)" style="font-size:12px;color:#dc2626;">删除</button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="items.length === 0 && !loading" style="color:#64748b;margin-top:16px;">暂无资源</p>

    <!-- Modals -->
    <ScaleModal :visible="scaleVisible" :resourceType="currentType" :name="selectedName"
      :namespace="selectedNamespace" :currentReplicas="currentReplicas"
      @close="scaleVisible = false" @confirm="doScale" />
    <DeleteModal :visible="deleteVisible" :resourceType="currentType" :name="selectedName"
      :namespace="selectedNamespace"
      @close="deleteVisible = false" @confirm="doDelete" />
    <RollbackModal :visible="rollbackVisible" :name="selectedName" :namespace="selectedNamespace"
      @close="rollbackVisible = false" @confirm="doRollback" />
    <YamlModal :visible="yamlVisible" :resourceType="currentType" :name="selectedName"
      :yamlContent="yamlContent"
      @close="yamlVisible = false" />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, inject } from "vue";
import { useRoute, useRouter } from "vue-router";
import { listResources, getResourceYaml, scaleResource, rollbackDeployment, deleteResource } from "../api/resources";
import ScaleModal from "../components/ScaleModal.vue";
import DeleteModal from "../components/DeleteModal.vue";
import RollbackModal from "../components/RollbackModal.vue";
import YamlModal from "../components/YamlModal.vue";

const route = useRoute();
const router = useRouter();
const toast = inject("toast");

// ── Resource type definitions ──
const COMMON_TYPES = ["deployment", "pod", "service"];

const LABEL_MAP = {
  namespace: "Namespace", deployment: "Deployment", pod: "Pod",
  service: "Service", ingress: "Ingress", daemonset: "DaemonSet",
  statefulset: "StatefulSet", configmap: "ConfigMap", secret: "Secret",
  role: "Role", rolebinding: "RoleBinding", clusterrole: "ClusterRole",
  clusterrolebinding: "ClusterRoleBinding", serviceaccount: "ServiceAccount",
};

const CLUSTER_SCOPED = ["namespace", "clusterrole", "clusterrolebinding"];

// Build ordered type list: common first, rest alphabetically
const ALL_TYPES = Object.keys(LABEL_MAP);
const orderedTypes = [
  ...COMMON_TYPES.filter(t => ALL_TYPES.includes(t)),
  ...ALL_TYPES.filter(t => !COMMON_TYPES.includes(t)).sort(),
];

const resourceTypeOptions = orderedTypes.map(t => ({
  type: t,
  label: LABEL_MAP[t] || t,
  count: null,
  common: COMMON_TYPES.includes(t),
}));

// ── Reactive state ──
const currentType = ref(route.query.type || "deployment");
const currentNamespace = ref(route.query.ns || "全部");
const nameSearch = ref(route.query.search || "");

const typeSearch = ref("");
const showTypeDropdown = ref(false);
const typeHighlightIndex = ref(0);
const typeComboRef = ref(null);

const nsSearch = ref("");
const showNsDropdown = ref(false);
const nsHighlightIndex = ref(0);
const nsComboRef = ref(null);

const items = ref([]);
const loading = ref(false);
const error = ref("");
const namespaces = ref([]);

// Modal state
const scaleVisible = ref(false);
const deleteVisible = ref(false);
const rollbackVisible = ref(false);
const yamlVisible = ref(false);
const selectedName = ref("");
const selectedNamespace = ref("");
const currentReplicas = ref(0);
const yamlContent = ref("");

// ── Computed ──
const isNamespaced = computed(() => !CLUSTER_SCOPED.includes(currentType.value));
const canScale = computed(() => ["deployment", "statefulset"].includes(currentType.value));

const filteredCommonTypes = computed(() => {
  const s = typeSearch.value.toLowerCase();
  return resourceTypeOptions
    .filter(rt => rt.common && (!s || rt.label.toLowerCase().includes(s) || rt.type.toLowerCase().includes(s)));
});

const filteredOtherTypes = computed(() => {
  const s = typeSearch.value.toLowerCase();
  return resourceTypeOptions
    .filter(rt => !rt.common && (!s || rt.label.toLowerCase().includes(s) || rt.type.toLowerCase().includes(s)));
});

const filteredNamespaces = computed(() => {
  const s = nsSearch.value.toLowerCase();
  if (!s) return namespaces.value;
  return namespaces.value.filter(ns => ns.toLowerCase().includes(s));
});

// Frontend fuzzy filter by name
const filteredItems = computed(() => {
  const s = nameSearch.value.toLowerCase().trim();
  if (!s) return items.value;
  return items.value.filter(item => {
    const name = getNested(item, "metadata.name")?.toLowerCase() || "";
    return name.includes(s);
  });
});

const columns = computed(() => {
  const base = { name: "metadata.name" };
  if (isNamespaced.value) base.namespace = "metadata.namespace";
  const extras = {
    deployment: { replicas: "status.replicas", image: "spec.template.spec.containers[0].image" },
    pod: { status: "status.phase" },
    service: { type: "spec.type", cluster_ip: "spec.cluster_ip" },
    ingress: { hosts: "spec.rules[0].host" },
    statefulset: { replicas: "status.replicas" },
  };
  const all = { ...base, ...(extras[currentType.value] || {}) };
  return Object.entries(all).map(([key, val]) => ({
    key: val,
    label: key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()),
  }));
});

// ── Helpers ──
function getNested(obj, path) {
  if (!obj) return "";
  const parts = path.replace(/\[(\d+)\]/g, ".$1").split(".");
  let val = obj;
  for (const p of parts) {
    if (val == null) return "";
    val = val[p];
  }
  if (Array.isArray(val)) val = val.join(", ");
  return val ?? "";
}

function itemKey(item) {
  const name = getNested(item, "metadata.name");
  const ns = getNested(item, "metadata.namespace");
  return `${ns || ""}/${name}`;
}

function statusText(item) {
  if (currentType.value === "pod") return getNested(item, "status.phase") || "Unknown";
  if (currentType.value === "namespace") return getNested(item, "status.phase") || "Active";
  return "";
}

function statusClass(item) {
  const s = statusText(item);
  if (s === "Running" || s === "Active") return "tag-green";
  if (s === "Pending" || s === "Terminating") return "tag-red";
  return "tag-blue";
}

// ── Resource type dropdown ──
function hideTypeDropdown() {
  setTimeout(() => { showTypeDropdown.value = false; }, 150);
}

function moveTypeHighlight(dir) {
  const total = filteredCommonTypes.value.length + filteredOtherTypes.value.length;
  typeHighlightIndex.value = Math.max(0, Math.min(total - 1, typeHighlightIndex.value + dir));
}

function selectHighlightedType() {
  const common = filteredCommonTypes.value;
  const other = filteredOtherTypes.value;
  if (typeHighlightIndex.value < common.length) {
    selectResourceType(common[typeHighlightIndex.value]);
  } else {
    selectResourceType(other[typeHighlightIndex.value - common.length]);
  }
}

function selectResourceType(rt) {
  currentType.value = rt.type;
  typeSearch.value = "";
  showTypeDropdown.value = false;
  typeHighlightIndex.value = 0;
  currentNamespace.value = "全部";
  syncQuery();
  fetchData();
}

// ── Namespace dropdown ──
function hideNsDropdown() {
  setTimeout(() => { showNsDropdown.value = false; }, 150);
}

function moveNsHighlight(dir) {
  const total = filteredNamespaces.value.length + 1;
  nsHighlightIndex.value = Math.max(0, Math.min(total - 1, nsHighlightIndex.value + dir));
}

function selectHighlightedNs() {
  if (nsHighlightIndex.value === 0) {
    selectNamespace("全部", 0);
  } else {
    const ns = filteredNamespaces.value[nsHighlightIndex.value - 1];
    if (ns) selectNamespace(ns, nsHighlightIndex.value);
  }
}

function selectNamespace(ns, idx) {
  currentNamespace.value = ns;
  nsSearch.value = "";
  showNsDropdown.value = false;
  nsHighlightIndex.value = idx;
  syncQuery();
  fetchData();
}

// ── Name search (debounced) ──
let nameSearchTimer = null;
function onNameSearchChange() {
  clearTimeout(nameSearchTimer);
  nameSearchTimer = setTimeout(() => {
    syncQuery();
  }, 300);
}

// ── URL query sync ──
function syncQuery() {
  const q = {};
  if (currentType.value && currentType.value !== "deployment") q.type = currentType.value;
  if (currentNamespace.value && currentNamespace.value !== "全部") q.ns = currentNamespace.value;
  if (nameSearch.value) q.search = nameSearch.value;
  router.replace({ query: q });
}

// ── Data fetching ──
async function fetchData() {
  loading.value = true;
  error.value = "";
  try {
    const ns = currentNamespace.value === "全部" ? undefined : currentNamespace.value;
    const isClusterScoped = CLUSTER_SCOPED.includes(currentType.value);
    const res = await listResources(currentType.value, isClusterScoped ? undefined : ns);
    items.value = res.data?.items || [];
    // Update count for current type
    const opt = resourceTypeOptions.find(o => o.type === currentType.value);
    if (opt) opt.count = res.data?.count ?? items.value.length;
  } catch (e) {
    error.value = e.message || "加载失败";
    items.value = [];
  } finally {
    loading.value = false;
  }
}

async function fetchNamespaces() {
  try {
    const res = await listResources("namespace");
    const nsList = (res.data?.items || []).map(i => i.metadata?.name).filter(Boolean);
    namespaces.value = nsList;
  } catch (e) { /* ignore */ }
}

// Load counts for all resource types in parallel (for dropdown display)
async function fetchAllCounts() {
  const promises = resourceTypeOptions.map(async (opt) => {
    try {
      const res = await listResources(opt.type, undefined);
      opt.count = res.data?.count ?? 0;
    } catch (e) {
      opt.count = null;
    }
  });
  await Promise.allSettled(promises);
}

// ── Actions ──
function openScale(item) {
  selectedName.value = getNested(item, "metadata.name");
  selectedNamespace.value = getNested(item, "metadata.namespace");
  currentReplicas.value = getNested(item, "status.replicas") || 0;
  scaleVisible.value = true;
}

function openDelete(item) {
  selectedName.value = getNested(item, "metadata.name");
  selectedNamespace.value = getNested(item, "metadata.namespace") || "";
  deleteVisible.value = true;
}

function openRollback(item) {
  selectedName.value = getNested(item, "metadata.name");
  selectedNamespace.value = getNested(item, "metadata.namespace");
  rollbackVisible.value = true;
}

async function viewYaml(item) {
  selectedName.value = getNested(item, "metadata.name");
  selectedNamespace.value = getNested(item, "metadata.namespace") || "";
  yamlContent.value = "加载中...";
  yamlVisible.value = true;
  try {
    const res = await getResourceYaml(currentType.value, selectedName.value, selectedNamespace.value || undefined);
    yamlContent.value = res.data.yaml;
  } catch (e) {
    yamlContent.value = `错误: ${e.message}`;
  }
}

async function doScale(replicas) {
  try {
    await scaleResource(currentType.value, selectedName.value, selectedNamespace.value, replicas);
    toast.show(`已将副本数调整为 ${replicas}`, "success");
    scaleVisible.value = false;
    fetchData();
  } catch (e) {
    toast.show(e.message || "Scale 失败", "error");
  }
}

async function doDelete() {
  try {
    await deleteResource(currentType.value, selectedName.value, selectedNamespace.value || undefined);
    toast.show(`已删除 ${currentType.value}/${selectedName.value}`, "success");
    deleteVisible.value = false;
    fetchData();
  } catch (e) {
    toast.show(e.message || "删除失败", "error");
  }
}

async function doRollback(revision) {
  try {
    await rollbackDeployment(selectedName.value, selectedNamespace.value, revision);
    toast.show("回滚成功", "success");
    rollbackVisible.value = false;
    fetchData();
  } catch (e) {
    toast.show(e.message || "回滚失败", "error");
  }
}

// ── Lifecycle ──
onMounted(() => {
  // Restore from URL query if present
  if (route.query.type) currentType.value = route.query.type;
  if (route.query.ns) currentNamespace.value = route.query.ns;
  if (route.query.search) nameSearch.value = route.query.search;

  fetchNamespaces();
  fetchAllCounts();
  fetchData();
});

watch(currentType, () => {
  syncQuery();
});
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 16px;
  flex-wrap: wrap;
  padding: 12px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.filter-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  padding-left: 2px;
}

.combobox {
  position: relative;
}

.combobox-input {
  min-width: 200px;
}

.combobox-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  z-index: 10;
  margin-top: 4px;
  max-height: 320px;
  overflow-y: auto;
}

.dropdown-section-label {
  padding: 6px 12px 2px;
  font-size: 11px;
  color: #94a3b8;
  text-transform: uppercase;
}

.dropdown-item {
  padding: 6px 12px;
  font-size: 13px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.dropdown-item:hover,
.dropdown-item.highlighted {
  background: #eff6ff;
}

.dropdown-count {
  color: var(--color-text-secondary);
  font-size: 12px;
}

.actions-cell {
  white-space: nowrap;
}
.actions-cell .btn {
  margin-right: 4px;
}

/* 监控与日志快捷入口 */
.quick-links {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  padding: 10px 12px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
}
.ql-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
}
.ql-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 500;
  text-decoration: none;
  color: #1d4ed8;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 6px;
  transition: background 0.15s, border-color 0.15s;
}
.ql-link:hover {
  background: #dbeafe;
  border-color: #93c5fd;
}
</style>
