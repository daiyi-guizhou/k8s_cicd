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
import { onMounted } from "vue";
import { useAuthStore } from "./stores/auth";
import { useClusterStore } from "./stores/cluster";
import AppSidebar from "./components/AppSidebar.vue";
import AppToast from "./components/AppToast.vue";

const auth = useAuthStore();
const clusterStore = useClusterStore();

onMounted(async () => {
  await clusterStore.fetchClusters();
});
</script>
