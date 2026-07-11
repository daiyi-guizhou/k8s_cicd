<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
      <h2>📊 集群概览</h2>
      <span v-if="clusterStore.current" style="font-size:13px;color:var(--color-text-secondary);">
        当前集群：<strong>{{ clusterStore.current.name }}</strong>
      </span>
    </div>
    <div class="dashboard-grid">
      <div class="card stat-card" v-for="stat in stats" :key="stat.label">
        <div class="stat-value">{{ stat.value }}</div>
        <div class="stat-label">{{ stat.label }}</div>
      </div>
    </div>
    <div v-if="error" class="card" style="margin-top:16px;color:#dc2626;">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useClusterStore } from "../stores/cluster";
import { listResources } from "../api/resources";

const clusterStore = useClusterStore();

const stats = ref([
  { label: "Namespace", value: "..." },
  { label: "Deployment", value: "..." },
  { label: "Pod", value: "..." },
  { label: "Service", value: "..." },
  { label: "Ingress", value: "..." },
]);
const error = ref("");

onMounted(async () => {
  if (!clusterStore.currentId) return;
  const types = [
    { key: "namespace", label: "Namespace" },
    { key: "deployment", label: "Deployment" },
    { key: "pod", label: "Pod" },
    { key: "service", label: "Service" },
    { key: "ingress", label: "Ingress" },
  ];
  const results = [];
  for (const t of types) {
    try {
      const res = await listResources(t.key);
      results.push({ label: t.label, value: res.data?.count ?? 0 });
    } catch (e) {
      results.push({ label: t.label, value: "错误" });
    }
  }
  stats.value = results;
});
</script>

<style scoped>
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
}
.stat-card {
  text-align: center;
  padding: 24px 16px;
}
.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--color-primary);
}
.stat-label {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-top: 4px;
}
</style>
