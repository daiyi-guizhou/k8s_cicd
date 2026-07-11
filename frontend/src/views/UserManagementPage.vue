<template>
  <div>
    <h2 style="margin-bottom:16px;">👤 用户管理</h2>

    <div class="card" style="margin-bottom:20px;">
      <h3 style="margin-bottom:12px;">创建用户</h3>
      <form @submit.prevent="doCreate" style="display:flex;gap:8px;align-items:flex-end;">
        <div class="form-group" style="margin:0;flex:1;">
          <label class="form-label">用户名</label>
          <input v-model="newUsername" class="form-input" required />
        </div>
        <div class="form-group" style="margin:0;">
          <label class="form-label">角色</label>
          <select v-model="newRole" class="form-input">
            <option value="user">普通用户</option>
            <option value="admin">管理员</option>
          </select>
        </div>
        <button type="submit" class="btn btn-primary" :disabled="creating">{{ creating ? '创建中...' : '创建' }}</button>
      </form>
      <p v-if="createdUser" style="margin-top:12px;color:#16a34a;">
        ✅ 用户 <strong>{{ createdUser.username }}</strong> 创建成功，初始密码: <code>{{ createdUser.password }}</code>
      </p>
    </div>

    <table class="data-table">
      <thead>
        <tr>
          <th>用户名</th>
          <th>角色</th>
          <th>状态</th>
          <th>创建时间</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="u in users" :key="u.id">
          <td>{{ u.username }}</td>
          <td><span :class="['tag', u.role === 'admin' ? 'tag-blue' : '']">{{ u.role }}</span></td>
          <td><span :class="['tag', u.is_active ? 'tag-green' : 'tag-red']">{{ u.is_active ? '启用' : '禁用' }}</span></td>
          <td style="font-size:12px;">{{ u.created_at }}</td>
          <td>
            <button class="btn" style="font-size:12px;" @click="doToggle(u)">{{ u.is_active ? '禁用' : '启用' }}</button>
            <button class="btn" style="font-size:12px;" @click="doReset(u)">重置密码</button>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-if="resetResult" class="card" style="margin-top:16px;background:#fefce8;">
      <p>🔑 用户 <strong>{{ resetResult.username }}</strong> 密码已重置为: <code>{{ resetResult.password }}</code></p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, inject } from "vue";
import { listUsers, createUser, toggleUserActive, resetUserPassword } from "../api/users";

const toast = inject("toast");
const users = ref([]);
const newUsername = ref("");
const newRole = ref("user");
const creating = ref(false);
const createdUser = ref(null);
const resetResult = ref(null);

async function fetchUsers() {
  try {
    const res = await listUsers();
    users.value = res.data || [];
  } catch (e) {
    toast.show(e.message, "error");
  }
}

async function doCreate() {
  creating.value = true;
  createdUser.value = null;
  try {
    const res = await createUser(newUsername.value, newRole.value);
    createdUser.value = res.data;
    newUsername.value = "";
    toast.show(res.message, "success");
    fetchUsers();
  } catch (e) {
    toast.show(e.message, "error");
  } finally {
    creating.value = false;
  }
}

async function doToggle(user) {
  try {
    const res = await toggleUserActive(user.id);
    toast.show(res.message, "success");
    fetchUsers();
  } catch (e) {
    toast.show(e.message, "error");
  }
}

async function doReset(user) {
  try {
    const res = await resetUserPassword(user.id);
    resetResult.value = res.data;
    toast.show(res.message, "success");
  } catch (e) {
    toast.show(e.message, "error");
  }
}

onMounted(fetchUsers);
</script>
