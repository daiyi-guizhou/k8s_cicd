<template>
  <div class="login-card">
    <h1 style="text-align:center;color:#fff;margin-bottom:24px;">☸️ K8s Console</h1>
    <div v-if="reasonMessage" class="login-info-banner">{{ reasonMessage }}</div>
    <form @submit.prevent="doLogin" class="card" style="width:380px;">
      <h2 style="margin-bottom:20px;">登录</h2>
      <div class="form-group">
        <label class="form-label">用户名</label>
        <input v-model="username" class="form-input" autofocus />
      </div>
      <div class="form-group">
        <label class="form-label">密码</label>
        <input v-model="password" type="password" class="form-input" />
      </div>
      <p v-if="error" style="color:#dc2626;font-size:13px;margin-bottom:12px;">{{ error }}</p>
      <button type="submit" class="btn btn-primary" style="width:100%;" :disabled="loading">
        {{ loading ? '登录中...' : '登录' }}
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { login } from "../api/auth";

const username = ref("");
const password = ref("");
const error = ref("");
const loading = ref(false);
const router = useRouter();
const route = useRoute();
const auth = useAuthStore();

const REASON_MESSAGES = {
  expired: "⚠️ 您的登录会话已过期（超过24小时），请重新登录",
  updated: "⚠️ 系统已更新，请刷新页面后重新登录",
};

const reasonMessage = ref("");

onMounted(() => {
  const reason = route.query.reason;
  if (reason && REASON_MESSAGES[reason]) {
    reasonMessage.value = REASON_MESSAGES[reason];
  }
});

async function doLogin() {
  error.value = "";
  if (!username.value || !password.value) {
    error.value = "请输入用户名和密码";
    return;
  }
  loading.value = true;
  try {
    const res = await login(username.value, password.value);
    auth.setAuth(res.data.token, res.data.user);
    router.push("/");
  } catch (e) {
    error.value = e.message || "登录失败";
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-card {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.login-info-banner {
  background: #fef3c7;
  color: #92400e;
  padding: 10px 16px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 14px;
  text-align: center;
  max-width: 380px;
}
</style>
