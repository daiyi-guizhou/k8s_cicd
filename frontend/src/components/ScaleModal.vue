<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-box">
      <h3 class="modal-title">Scale 操作</h3>
      <p style="color:#64748b;font-size:13px;margin-bottom:16px;">⚠️ 此操作将修改副本数，请确认</p>
      <div class="form-group">
        <label class="form-label">资源</label>
        <div class="form-input" style="background:#f8fafc;">{{ resourceType }} / {{ name }} ({{ namespace }})</div>
      </div>
      <div class="form-group">
        <label class="form-label">当前副本数</label>
        <div class="form-input" style="background:#f8fafc;">{{ currentReplicas ?? '未知' }}</div>
      </div>
      <div class="form-group">
        <label class="form-label">目标副本数</label>
        <input v-model.number="replicas" type="number" class="form-input" min="0" />
      </div>
      <div class="modal-actions">
        <button class="btn" @click="$emit('close')">取消</button>
        <button class="btn btn-primary" :disabled="replicas === null" @click="$emit('confirm', replicas)">确认 Scale</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from "vue";

const props = defineProps({
  visible: Boolean,
  resourceType: String,
  name: String,
  namespace: String,
  currentReplicas: Number,
});

defineEmits(["close", "confirm"]);

const replicas = ref(null);

watch(() => props.visible, (v) => {
  if (v) replicas.value = props.currentReplicas;
});
</script>
