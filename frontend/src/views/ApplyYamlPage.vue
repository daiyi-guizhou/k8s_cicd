<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
      <h2>🛠 Apply YAML</h2>
      <span v-if="clusterStore.current" style="font-size:13px;color:var(--color-text-secondary);">
        目标集群：<strong>{{ clusterStore.current.name }}</strong>
      </span>
    </div>
    <div v-if="!clusterStore.currentId" class="card" style="border-color:#fbbf24;color:#92400e;margin-bottom:16px;">
      ⚠ 请先在侧边栏选择一个目标集群
    </div>
    <div class="apply-layout">
      <div class="editor-panel">
        <textarea
          v-model="yamlContent"
          class="yaml-editor"
          placeholder="在此粘贴或编辑 YAML..."
          spellcheck="false"
        ></textarea>
      </div>
      <div class="result-panel">
        <button class="btn btn-primary" style="width:100%;margin-bottom:8px;" :disabled="!yamlContent.trim() || applying" @click="doApply">
          {{ applying ? 'Applying...' : 'Apply' }}
        </button>
        <button class="btn" style="width:100%;margin-bottom:16px;" @click="yamlContent = ''; result = null;">清空</button>
        <div v-if="result" :class="['result-box', result.success ? 'result-success' : 'result-error']">
          <div style="font-size:20px;margin-bottom:8px;">{{ result.success ? '✅' : '❌' }}</div>
          <div style="font-weight:600;">{{ result.message }}</div>
          <div v-for="r in result.results" :key="r.resource" style="font-size:12px;color:#64748b;margin-top:4px;">
            {{ r.resource }} — {{ r.action }}
          </div>
        </div>
        <p style="font-size:11px;color:#94a3b8;margin-top:8px;">💡 支持在线编辑 YAML，粘贴或直接修改后点击 Apply</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, inject } from "vue";
import { useClusterStore } from "../stores/cluster";
import { applyYaml } from "../api/resources";

const toast = inject("toast");
const clusterStore = useClusterStore();
const yamlContent = ref("");
const applying = ref(false);
const result = ref(null);

async function doApply() {
  if (!yamlContent.value.trim()) return;
  applying.value = true;
  result.value = null;
  try {
    const res = await applyYaml(yamlContent.value);
    result.value = { success: true, message: res.message, results: res.data?.results || [] };
    toast.show(res.message, "success");
  } catch (e) {
    result.value = { success: false, message: e.message || "Apply 失败", results: [] };
    toast.show(e.message || "Apply 失败", "error");
  } finally {
    applying.value = false;
  }
}
</script>

<style scoped>
.apply-layout {
  display: flex;
  gap: 16px;
  height: calc(100vh - 140px);
}
.editor-panel {
  flex: 2;
  display: flex;
}
.yaml-editor {
  flex: 1;
  background: #1e293b;
  color: #e2e8f0;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 16px;
  font-family: "Fira Code", "Cascadia Code", monospace;
  font-size: 13px;
  line-height: 1.6;
  resize: none;
  outline: none;
}
.yaml-editor::placeholder {
  color: #64748b;
}
.result-panel {
  flex: 1;
}
.result-box {
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}
.result-success {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
}
.result-error {
  background: #fef2f2;
  border: 1px solid #fecaca;
}
</style>
