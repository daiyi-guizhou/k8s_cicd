<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-box" style="min-width:640px;max-width:800px;">
      <h3 class="modal-title">YAML — {{ resourceType }}/{{ name }}</h3>
      <pre class="yaml-viewer"><code>{{ yamlContent || '加载中...' }}</code></pre>
      <div class="modal-actions">
        <button class="btn" @click="copyYaml">📋 复制</button>
        <button class="btn" @click="$emit('close')">关闭</button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  visible: Boolean,
  resourceType: String,
  name: String,
  yamlContent: String,
});

defineEmits(["close"]);

function copyYaml() {
  const content = document.querySelector(".yaml-viewer code")?.textContent || "";
  navigator.clipboard.writeText(content);
}
</script>

<style scoped>
.yaml-viewer {
  background: #1e293b;
  color: #e2e8f0;
  padding: 16px;
  border-radius: 8px;
  overflow: auto;
  max-height: 50vh;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre;
  font-family: "Fira Code", "Cascadia Code", monospace;
}
</style>
