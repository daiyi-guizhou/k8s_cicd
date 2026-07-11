<template>
  <div v-if="!auth.isLoggedIn" class="app-login-shell">
    <router-view />
  </div>
  <div v-else class="app-shell">
    <AppSidebar />
    <main class="app-main">
      <router-view />
    </main>
    <AppToast />
  </div>
</template>

<script setup>
import { onMounted, watch } from "vue";
import { useAuthStore } from "./stores/auth";
import { useClusterStore } from "./stores/cluster";
import AppSidebar from "./components/AppSidebar.vue";
import AppToast from "./components/AppToast.vue";

const auth = useAuthStore();
const clusterStore = useClusterStore();

// 首次加载时尝试 fetch（刷新后 token 已在 localStorage 中）
onMounted(async () => {
  if (auth.isLoggedIn) {
    await clusterStore.fetchClusters();
  }
});

// 登录后自动 fetch 集群列表（首次登录场景）
watch(() => auth.isLoggedIn, async (loggedIn) => {
  if (loggedIn) {
    await clusterStore.fetchClusters();
  }
});
</script>
