<template>
  <div>
    <h2 style="margin-bottom:16px;">📋 审计日志</h2>

    <div class="card" style="margin-bottom:16px;display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end;">
      <div class="form-group" style="margin:0;">
        <label class="form-label">操作类型</label>
        <select v-model="filterAction" class="form-input">
          <option value="">全部</option>
          <option value="scale">Scale</option>
          <option value="rollback">Rollback</option>
          <option value="delete">Delete</option>
          <option value="apply">Apply</option>
          <option value="create_user">创建用户</option>
          <option value="toggle_active">启用/禁用</option>
          <option value="reset_password">重置密码</option>
          <option value="change_password">修改密码</option>
        </select>
      </div>
      <div class="form-group" style="margin:0;">
        <label class="form-label">结果</label>
        <select v-model="filterResult" class="form-input">
          <option value="">全部</option>
          <option value="success">成功</option>
          <option value="fail">失败</option>
        </select>
      </div>
      <button class="btn btn-primary" @click="fetchData(currentPage = 1)">查询</button>
    </div>

    <table class="data-table">
      <thead>
        <tr>
          <th>用户</th>
          <th>操作</th>
          <th>资源</th>
          <th>Namespace</th>
          <th>集群</th>
          <th>结果</th>
          <th>时间</th>
          <th>详情</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="log in logs" :key="log.id">
          <td>{{ log.username }}</td>
          <td><span class="tag tag-blue">{{ log.action_display }}</span></td>
          <td>{{ log.resource_type }}{{ log.resource_name ? '/' + log.resource_name : '' }}</td>
          <td>{{ log.namespace }}</td>
          <td>{{ log.cluster_name || '-' }}</td>
          <td><span :class="['tag', log.result === 'success' ? 'tag-green' : 'tag-red']">{{ log.result }}</span></td>
          <td style="font-size:12px;">{{ log.created_at }}</td>
          <td style="font-size:12px;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" :title="JSON.stringify(log.detail)">
            {{ log.error_msg || JSON.stringify(log.detail) }}
          </td>
        </tr>
      </tbody>
    </table>

    <div v-if="total > pageSize" style="display:flex;gap:8px;justify-content:center;margin-top:16px;">
      <button class="btn" :disabled="currentPage <= 1" @click="fetchData(currentPage - 1)">上一页</button>
      <span style="padding:8px;">{{ currentPage }} / {{ Math.ceil(total / pageSize) }}</span>
      <button class="btn" :disabled="currentPage >= Math.ceil(total / pageSize)" @click="fetchData(currentPage + 1)">下一页</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, inject } from "vue";
import { listAuditLogs } from "../api/audit";

const toast = inject("toast");
const logs = ref([]);
const total = ref(0);
const currentPage = ref(1);
const pageSize = 20;

const filterAction = ref("");
const filterResult = ref("");

async function fetchData(page = 1) {
  try {
    const filters = { page, page_size: pageSize };
    if (filterAction.value) filters.action = filterAction.value;
    if (filterResult.value) filters.result = filterResult.value;
    const res = await listAuditLogs(filters);
    logs.value = res.data?.items || [];
    total.value = res.data?.total || 0;
    currentPage.value = res.data?.page || page;
  } catch (e) {
    toast.show(e.message, "error");
  }
}

onMounted(() => fetchData());
</script>
