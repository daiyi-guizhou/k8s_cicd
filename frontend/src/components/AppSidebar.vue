<template>
  <aside class="sidebar">
    <div class="sidebar-brand">☸️ K8s Console</div>

    <router-link to="/" class="sidebar-item" active-class="active" exact>
      📊 仪表盘
    </router-link>

    <div class="sidebar-section-label">📦 资源管理</div>
    <router-link
      v-for="r in resourceTypes"
      :key="r.type"
      :to="`/resources/${r.type}`"
      class="sidebar-item sidebar-sub"
      active-class="active"
    >
      {{ r.label }}
    </router-link>

    <div class="sidebar-divider"></div>

    <router-link to="/apply" class="sidebar-item" active-class="active">
      🛠 Apply YAML
    </router-link>
    <router-link to="/users" v-if="auth.isAdmin" class="sidebar-item" active-class="active">
      👤 用户管理
    </router-link>
    <router-link to="/audit" v-if="auth.isAdmin" class="sidebar-item" active-class="active">
      📋 审计日志
    </router-link>

    <div class="sidebar-footer">
      <span class="sidebar-user">{{ auth.user?.username }}</span>
      <button class="btn" style="width:100%;margin-top:8px;" @click="doLogout">登出</button>
    </div>
  </aside>
</template>

<script setup>
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { logout } from "../api/auth";

const auth = useAuthStore();
const router = useRouter();

const resourceTypes = [
  { type: "namespace", label: "Namespace" },
  { type: "deployment", label: "Deployment" },
  { type: "pod", label: "Pod" },
  { type: "service", label: "Service" },
  { type: "ingress", label: "Ingress" },
  { type: "daemonset", label: "DaemonSet" },
  { type: "statefulset", label: "StatefulSet" },
  { type: "configmap", label: "ConfigMap" },
  { type: "secret", label: "Secret" },
  { type: "role", label: "Role" },
  { type: "rolebinding", label: "RoleBinding" },
  { type: "clusterrole", label: "ClusterRole" },
  { type: "clusterrolebinding", label: "ClusterRoleBinding" },
  { type: "serviceaccount", label: "ServiceAccount" },
];

async function doLogout() {
  try { await logout(); } catch (e) { /* ignore */ }
  auth.clearAuth();
  router.push("/login");
}
</script>

<style scoped>
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: var(--sidebar-width);
  background: #1e293b;
  color: #cbd5e1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  z-index: 100;
}

.sidebar-brand {
  padding: 16px;
  font-size: 16px;
  font-weight: 700;
  color: #fff;
}

.sidebar-section-label {
  padding: 12px 16px 4px;
  font-size: 11px;
  text-transform: uppercase;
  color: #64748b;
  letter-spacing: 0.5px;
}

.sidebar-item {
  padding: 10px 16px;
  color: #94a3b8;
  text-decoration: none;
  font-size: 13px;
  display: block;
  transition: all 0.15s;
  border-left: 3px solid transparent;
}
.sidebar-item:hover {
  background: #334155;
  color: #e2e8f0;
}
.sidebar-item.active {
  background: #334155;
  color: #fff;
  border-left-color: #3b82f6;
}

.sidebar-sub {
  padding-left: 28px;
  font-size: 12px;
}

.sidebar-divider {
  margin: 8px 16px;
  border-top: 1px solid #334155;
}

.sidebar-footer {
  margin-top: auto;
  padding: 16px;
  border-top: 1px solid #334155;
}
.sidebar-user {
  font-size: 13px;
  color: #e2e8f0;
  display: block;
  text-align: center;
}
</style>
