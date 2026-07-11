<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-box">
      <h3 class="modal-title" style="color:#dc2626;">🚨 删除资源</h3>
      <p style="color:#dc2626;font-size:13px;margin-bottom:16px;">此操作不可逆！请输入资源名称确认</p>
      <div class="form-group">
        <label class="form-label">资源</label>
        <div class="form-input" style="background:#f8fafc;">{{ resourceType }} / {{ name }} ({{ namespace }})</div>
      </div>
      <div class="form-group">
        <label class="form-label">输入 "<code>{{ name }}</code>" 确认删除</label>
        <input v-model="confirmText" class="form-input" :placeholder="name" />
      </div>
      <div class="modal-actions">
        <button class="btn" @click="$emit('close')">取消</button>
        <button class="btn btn-danger" :disabled="confirmText !== name" @click="$emit('confirm')">确认删除</button>
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
});

defineEmits(["close", "confirm"]);

const confirmText = ref("");

watch(() => props.visible, (v) => {
  if (v) confirmText.value = "";
});
</script>
