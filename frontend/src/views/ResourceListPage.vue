<template>
  <div>
    <h2 style="margin-bottom:16px;">📦 {{ title }}</h2>

    <div v-if="isNamespaced" style="margin-bottom:16px;display:flex;gap:8px;flex-wrap:wrap;">
      <span
        :class="['tag', ns === currentNamespace ? 'tag-blue' : '']"
        style="cursor:pointer;"
        @click="currentNamespace = ns"
        v-for="ns in namespaces"
        :key="ns"
      >{{ ns }}</span>
    </div>

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
        <tr v-for="item in items" :key="itemKey(item)">
          <td v-for="col in columns" :key="col.key">
            <template v-if="col.key === 'status'">
              <span :class="['tag', statusClass(item)]">{{ statusText(item) }}</span>
            </template>
            <template v-else>{{ getNested(item, col.key) }}</template>
          </td>
          <td class="actions-cell">
            <button class="btn" @click="viewYaml(item)" style="font-size:12px;">YAML</button>
            <button v-if="canScale" class="btn" @click="openScale(item)" style="font-size:12px;">Scale</button>
            <button v-if="resourceType === 'deployment'" class="btn" @click="openRollback(item)" style="font-size:12px;">Rollback</button>
            <button v-if="resourceType !== 'namespace'" class="btn" @click="openDelete(item)" style="font-size:12px;color:#dc2626;">删除</button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="items.length === 0 && !loading" style="color:#64748b;margin-top:16px;">暂无资源</p>

    <ScaleModal :visible="scaleVisible" :resourceType="resourceType" :name="selectedName"
      :namespace="selectedNamespace" :currentReplicas="currentReplicas"
      @close="scaleVisible = false" @confirm="doScale" />
    <DeleteModal :visible="deleteVisible" :resourceType="resourceType" :name="selectedName"
      :namespace="selectedNamespace"
      @close="deleteVisible = false" @confirm="doDelete" />
    <RollbackModal :visible="rollbackVisible" :name="selectedName" :namespace="selectedNamespace"
      @close="rollbackVisible = false" @confirm="doRollback" />
    <YamlModal :visible="yamlVisible" :resourceType="resourceType" :name="selectedName"
      :yamlContent="yamlContent"
      @close="yamlVisible = false" />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, inject } from "vue";
import { useRoute } from "vue-router";
import { listResources, getResourceYaml, scaleResource, rollbackDeployment, deleteResource } from "../api/resources";
import ScaleModal from "../components/ScaleModal.vue";
import DeleteModal from "../components/DeleteModal.vue";
import RollbackModal from "../components/RollbackModal.vue";
import YamlModal from "../components/YamlModal.vue";

const route = useRoute();
const toast = inject("toast");

const resourceType = computed(() => route.params.type);
const title = computed(() => {
  const map = {
    namespace: "Namespace", deployment: "Deployment", pod: "Pod",
    service: "Service", ingress: "Ingress", daemonset: "DaemonSet",
    statefulset: "StatefulSet", configmap: "ConfigMap", secret: "Secret",
    role: "Role", rolebinding: "RoleBinding", clusterrole: "ClusterRole",
    clusterrolebinding: "ClusterRoleBinding", serviceaccount: "ServiceAccount",
  };
  return map[resourceType.value] || resourceType.value;
});

const clusterScoped = ["namespace", "clusterrole", "clusterrolebinding"];
const isNamespaced = computed(() => !clusterScoped.includes(resourceType.value));
const canScale = computed(() => ["deployment", "statefulset"].includes(resourceType.value));

const items = ref([]);
const loading = ref(false);
const error = ref("");
const namespaces = ref(["全部"]);
const currentNamespace = ref("全部");

const scaleVisible = ref(false);
const deleteVisible = ref(false);
const rollbackVisible = ref(false);
const yamlVisible = ref(false);
const selectedName = ref("");
const selectedNamespace = ref("");
const currentReplicas = ref(0);
const yamlContent = ref("");

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
  const all = { ...base, ...(extras[resourceType.value] || {}) };
  return Object.entries(all).map(([key, val]) => ({
    key: val,
    label: key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()),
  }));
});

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
  if (resourceType.value === "pod") return getNested(item, "status.phase") || "Unknown";
  if (resourceType.value === "namespace") return getNested(item, "status.phase") || "Active";
  return "";
}

function statusClass(item) {
  const s = statusText(item);
  if (s === "Running" || s === "Active") return "tag-green";
  if (s === "Pending" || s === "Terminating") return "tag-red";
  return "tag-blue";
}

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
    const res = await getResourceYaml(resourceType.value, selectedName.value, selectedNamespace.value || undefined);
    yamlContent.value = res.data.yaml;
  } catch (e) {
    yamlContent.value = `错误: ${e.message}`;
  }
}

async function doScale(replicas) {
  try {
    await scaleResource(resourceType.value, selectedName.value, selectedNamespace.value, replicas);
    toast.show(`已将副本数调整为 ${replicas}`, "success");
    scaleVisible.value = false;
    fetchData();
  } catch (e) {
    toast.show(e.message || "Scale 失败", "error");
  }
}

async function doDelete() {
  try {
    await deleteResource(resourceType.value, selectedName.value, selectedNamespace.value || undefined);
    toast.show(`已删除 ${resourceType.value}/${selectedName.value}`, "success");
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

async function fetchData() {
  loading.value = true;
  error.value = "";
  try {
    const ns = currentNamespace.value === "全部" ? undefined : currentNamespace.value;
    const res = await listResources(resourceType.value, ns);
    items.value = res.data?.items || [];
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
    namespaces.value = ["全部", ...nsList];
  } catch (e) { /* ignore */ }
}

onMounted(() => {
  fetchNamespaces();
  fetchData();
});

watch(resourceType, () => {
  currentNamespace.value = "全部";
  fetchData();
});

watch(currentNamespace, () => fetchData());
</script>

<style scoped>
.actions-cell {
  white-space: nowrap;
}
.actions-cell .btn {
  margin-right: 4px;
}
</style>
