<template>
  <div class="toast-container">
    <div
      v-for="toast in toasts"
      :key="toast.id"
      :class="['toast', `toast-${toast.type}`]"
    >
      {{ toast.message }}
    </div>
  </div>
</template>

<script setup>
import { ref, provide, onMounted, onUnmounted } from "vue";

const toasts = ref([]);
let nextId = 0;

function show(message, type = "success", duration = 3000) {
  const id = nextId++;
  toasts.value.push({ id, message, type });
  setTimeout(() => {
    toasts.value = toasts.value.filter((t) => t.id !== id);
  }, duration);
}

/** Listen for external toast events (from Axios interceptors outside Vue tree) */
function onExternalToast(e) {
  const { message, type } = e.detail || {};
  if (message) {
    show(message, type || "error", 5000);
  }
}

onMounted(() => {
  window.addEventListener("app-toast", onExternalToast);
});

onUnmounted(() => {
  window.removeEventListener("app-toast", onExternalToast);
});

provide("toast", { show });
</script>
