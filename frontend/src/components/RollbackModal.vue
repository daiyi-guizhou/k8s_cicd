<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-box">
      <h3 class="modal-title">Rollback 操作</h3>
      <p style="color:#64748b;font-size:13px;margin-bottom:16px;">⚠️ 此操作将回滚 Deployment 到指定版本</p>
      <div class="form-group">
        <label class="form-label">Deployment</label>
        <div class="form-input" style="background:#f8fafc;">{{ name }} ({{ namespace }})</div>
      </div>
      <div class="form-group">
        <label class="form-label">回滚版本 (留空回滚到上一个版本)</label>
        <input v-model.number="revision" type="number" class="form-input" min="1" placeholder="留空 = 上一个版本" />
      </div>
      <div class="modal-actions">
        <button class="btn" @click="$emit('close')">取消</button>
        <button class="btn btn-primary" @click="$emit('confirm', revision || undefined)">确认 Rollback</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from "vue";

const props = defineProps({
  visible: Boolean,
  name: String,
  namespace: String,
});

defineEmits(["close", "confirm"]);

const revision = ref(null);

watch(() => props.visible, (v) => {
  if (v) revision.value = null;
});
</script>
