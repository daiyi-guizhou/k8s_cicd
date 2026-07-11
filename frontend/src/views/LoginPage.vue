<template>
  <div class="login-card">
    <h1 style="text-align:center;color:#fff;margin-bottom:24px;">☸️ K8s Console</h1>
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
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { login } from "../api/auth";

const username = ref("");
const password = ref("");
const error = ref("");
const loading = ref(false);
const router = useRouter();
const auth = useAuthStore();

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
</style>
