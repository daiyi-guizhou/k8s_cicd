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
import { useAuthStore } from "./stores/auth";
import AppSidebar from "./components/AppSidebar.vue";
import AppToast from "./components/AppToast.vue";

const auth = useAuthStore();
</script>
