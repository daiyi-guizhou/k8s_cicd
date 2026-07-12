# 统一资源管理页面 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将侧边栏 14 个独立资源类型链接合并为 1 个统一的资源管理页面（`/resources`），在页面内通过下拉框选择资源类型。

**Architecture:** 纯前端重构 — 后端 API 零改动。路由从 `/resources/:type` 改为 `/resources`（使用 query 参数保持状态），侧边栏从 14 项减为 1 项，ResourceListPage 增加资源类型/Namespace/名称三个过滤器。

**Tech Stack:** Vue 3 (Composition API), Vue Router, no UI library

---

### Task 1: 修改路由 — `/resources/:type` → `/resources`

**Files:**
- Modify: `frontend/src/router/index.js:18`

- [ ] **Step 1: 改路由定义**

将 `path: "/resources/:type"` 改为 `path: "/resources"`：

```javascript
// frontend/src/router/index.js, line 18
// OLD:
//   path: "/resources/:type",
//   name: "ResourceList",
// NEW:
  {
    path: "/resources",
    name: "Resources",
    component: () => import("../views/ResourceListPage.vue"),
    meta: { requiresAuth: true },
  },
```

- [ ] **Step 2: 验证路由生效**

启动前端 dev server，访问 `http://localhost:5173/resources`（不带 type 参数），确认 ResourceListPage 组件正常渲染。

---

### Task 2: 简化侧边栏 — 14 项 → 1 项

**Files:**
- Modify: `frontend/src/components/AppSidebar.vue:31-40`

- [ ] **Step 1: 替换模板中的资源子菜单**

删除 14 个 `router-link` 资源类型循环，替换为单个链接：

```html
<!-- OLD (lines 31-40):
    <div class="sidebar-section-label">📦 资源管理</div>
    <router-link
      v-for="r in resourceTypes"
      :key="r.type"
      :to="`/resources/${r.type}`"
      class="sidebar-item sidebar-sub"
      active-class="active"
    >
      {{ r.label }}
    </router-link>
-->
<!-- NEW: -->
    <router-link to="/resources" class="sidebar-item" active-class="active">
      📦 资源管理
    </router-link>
```

- [ ] **Step 2: 删除不再需要的 resourceTypes 数组**

删除 `<script setup>` 中的 `resourceTypes` 数组定义（lines 78-93）：

```javascript
// DELETE these lines (78-93):
// const resourceTypes = [
//   { type: "namespace", label: "Namespace" },
//   { type: "deployment", label: "Deployment" },
//   { type: "pod", label: "Pod" },
//   ...
//   { type: "serviceaccount", label: "ServiceAccount" },
// ];
```

- [ ] **Step 3: 检查完整文件**

确认 AppSidebar.vue 模板中：
- `sidebar-section-label` 和 `sidebar-sub` 相关行已删除
- 只有一个 `📦 资源管理` 的 `router-link to="/resources"`

---

### Task 3: 重写 ResourceListPage — 三个过滤器 + 动态表格

**Files:**
- Modify: `frontend/src/views/ResourceListPage.vue`（完全重写）

- [ ] **Step 1: 替换模板**

```html
<template>
  <div>
    <h2 style="margin-bottom:16px;">📦 资源管理</h2>

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
```

- [ ] **Step 2: 替换 script setup**

```javascript
<script setup>
import { ref, computed, watch, onMounted, inject, nextTick } from "vue";
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
  const total = filteredNamespaces.value.length + 1; // +1 for "全部"
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
    if (CLUSTER_SCOPED.includes(currentType.value)) {
      // cluster-scoped resources ignore namespace
    }
    const res = await listResources(currentType.value, CLUSTER_SCOPED.includes(currentType.value) ? undefined : ns);
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
      opt.count = null; // null = hide count on error
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

// Watch: resource type changes → sync URL + refetch
watch(currentType, () => {
  syncQuery();
});

// Watch: namespace changes → sync URL + refetch (handled in selectNamespace)
</script>
```

- [ ] **Step 3: 替换 style**

```css
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
</style>
```

- [ ] **Step 4: 验证功能**

启动前端 dev server：
```bash
cd D:/project/k8s_cicd/k8s_cicd/frontend && npm run dev
```

验证清单：
1. 访问 `/resources`，默认选中 Deployment，表格显示 Deployment 列表
2. 资源类型下拉框：常用（Deployment、Pod、Service）在前，有 ⭐ 标记，其余按字母序
3. 在下拉框中输入 "dep" → 只显示 Deployment
4. 输入 "role" → 显示 Role、ClusterRole、ClusterRoleBinding（字母序）
5. 切换资源类型 → 表格列、操作按钮、Namespace 过滤器（集群级隐藏）动态变化
6. Namespace 下拉框：支持搜索
7. 资源名称输入框：输入文字后表格实时过滤
8. 刷新页面 → URL query 恢复状态，过滤器值不变
9. YAML / Scale / Rollback / 删除弹窗正常工作
10. 侧边栏只有 1 个 "📦 资源管理"
11. 旧路由 `/resources/deployment` 等不再可访问
