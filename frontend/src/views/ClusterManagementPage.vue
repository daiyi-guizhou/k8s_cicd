<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
      <h2>🖥 集群管理</h2>
      <button class="btn btn-primary" @click="openCreate">+ 添加集群</button>
    </div>

    <div v-if="loading" style="color:#64748b;">加载中...</div>
    <div v-else-if="error" class="card" style="color:#dc2626;">{{ error }}</div>

    <table v-else-if="clusters.length > 0" class="data-table">
      <thead>
        <tr>
          <th>名称</th>
          <th>描述</th>
          <th>Kubeconfig</th>
          <th>状态</th>
          <th>创建时间</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="c in clusters" :key="c.id">
          <td>
            <strong>{{ c.name }}</strong>
            <span v-if="c.id === clusterStore.currentId" class="tag tag-green" style="margin-left:6px;">当前</span>
          </td>
          <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{{ c.description || '-' }}</td>
          <td>
            <span v-if="c.kubeconfig_content" class="tag tag-blue">自定义</span>
            <span v-else class="tag">默认</span>
          </td>
          <td>
            <span :class="['tag', c.enabled ? 'tag-green' : 'tag-red']">{{ c.enabled ? '启用' : '禁用' }}</span>
          </td>
          <td>{{ formatDate(c.created_at) }}</td>
          <td class="actions-cell">
            <button class="btn" @click="testConnection(c)" :disabled="testingId === c.id" style="font-size:12px;">
              {{ testingId === c.id ? '测试中...' : '测试' }}
            </button>
            <button class="btn" @click="openEdit(c)" style="font-size:12px;">编辑</button>
            <button class="btn" @click="openDelete(c)" style="font-size:12px;color:#dc2626;">删除</button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else style="color:#64748b;margin-top:16px;">暂无集群，请点击"添加集群"按钮添加。</p>

    <!-- Create / Edit Modal -->
    <div v-if="showForm" class="modal-overlay" @click.self="showForm = false">
      <div class="modal-box" style="max-width:640px;">
        <h3 style="margin-bottom:16px;">{{ editingCluster ? '编辑集群' : '添加集群' }}</h3>

        <div class="form-group">
          <label class="form-label">集群名称 <span style="color:#dc2626;">*</span></label>
          <input v-model="form.name" class="form-input" placeholder="例如：生产集群、开发集群" />
        </div>

        <div class="form-group">
          <label class="form-label">描述</label>
          <input v-model="form.description" class="form-input" placeholder="可选描述" />
        </div>

        <div class="form-group">
          <label class="form-label">
            Kubeconfig 内容
            <span style="font-size:11px;color:#94a3b8;">（留空使用服务器默认配置）</span>
          </label>
          <textarea v-model="form.kubeconfig_content" class="form-textarea"
            placeholder="粘贴完整的 kubeconfig YAML..."
            rows="10" spellcheck="false"></textarea>
        </div>

        <div class="form-group">
          <label class="form-label">
            <input type="checkbox" v-model="form.enabled" style="margin-right:6px;" />
            启用
          </label>
        </div>

        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px;">
          <button class="btn" @click="showForm = false">取消</button>
          <button class="btn btn-primary" :disabled="!form.name.trim() || submitting" @click="doSubmit">
            {{ submitting ? '提交中...' : '保存' }}
          </button>
        </div>
        <div v-if="formError" style="color:#dc2626;margin-top:8px;">{{ formError }}</div>
      </div>
    </div>

    <!-- Delete Confirm Modal -->
    <div v-if="deleteTarget" class="modal-overlay" @click.self="deleteTarget = null">
      <div class="modal-box">
        <h3 style="margin-bottom:12px;">确认删除</h3>
        <p>确定要删除集群 <strong>{{ deleteTarget.name }}</strong> 吗？</p>
        <p style="font-size:12px;color:#64748b;">仅删除控制台中的集群配置，不会影响集群本身。</p>
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px;">
          <button class="btn" @click="deleteTarget = null">取消</button>
          <button class="btn" style="background:#dc2626;color:#fff;" :disabled="deleting" @click="doDelete">
            {{ deleting ? '删除中...' : '确认删除' }}
          </button>
        </div>
        <div v-if="deleteError" style="color:#dc2626;margin-top:8px;">{{ deleteError }}</div>
      </div>
    </div>

    <!-- Test result -->
    <div v-if="testResult" class="modal-overlay" @click.self="testResult = null">
      <div class="modal-box">
        <h3 style="margin-bottom:12px;">连接测试</h3>
        <div v-if="testResult.success" style="color:#16a34a;">
          ✅ {{ testResult.message }}
          <div style="margin-top:4px;font-size:12px;color:#64748b;">
            Namespace 数量: {{ testResult.nsCount }} | 版本: {{ testResult.version }}
          </div>
        </div>
        <div v-else style="color:#dc2626;">
          ❌ {{ testResult.message }}
        </div>
        <div style="text-align:right;margin-top:12px;">
          <button class="btn" @click="testResult = null">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, inject } from "vue";
import { useClusterStore } from "../stores/cluster";
import { createCluster, updateCluster, deleteCluster, testCluster } from "../api/clusters";

const clusterStore = useClusterStore();
const toast = inject("toast");

const clusters = ref([]);
const loading = ref(false);
const error = ref("");

// Form state
const showForm = ref(false);
const editingCluster = ref(null);
const form = ref({ name: "", description: "", kubeconfig_content: "", enabled: true });
const formError = ref("");
const submitting = ref(false);

// Delete state
const deleteTarget = ref(null);
const deleteError = ref("");
const deleting = ref(false);

// Test state
const testingId = ref(null);
const testResult = ref(null);

async function fetchData() {
  loading.value = true;
  error.value = "";
  try {
    await clusterStore.fetchClusters();
    clusters.value = clusterStore.clusters;
  } catch (e) {
    error.value = e.message || "加载失败";
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editingCluster.value = null;
  form.value = { name: "", description: "", kubeconfig_content: "", enabled: true };
  formError.value = "";
  showForm.value = true;
}

function openEdit(c) {
  editingCluster.value = c;
  form.value = {
    name: c.name,
    description: c.description || "",
    kubeconfig_content: c.kubeconfig_content || "",
    enabled: c.enabled,
  };
  formError.value = "";
  showForm.value = true;
}

async function doSubmit() {
  formError.value = "";
  submitting.value = true;
  try {
    if (editingCluster.value) {
      await updateCluster(editingCluster.value.id, {
        name: form.value.name,
        description: form.value.description,
        kubeconfig_content: form.value.kubeconfig_content,
        enabled: form.value.enabled,
      });
      toast.show("集群已更新", "success");
    } else {
      await createCluster(form.value.name, form.value.description, form.value.kubeconfig_content);
      toast.show("集群已创建", "success");
    }
    showForm.value = false;
    await fetchData();
  } catch (e) {
    formError.value = e.message || "操作失败";
  } finally {
    submitting.value = false;
  }
}

function openDelete(c) {
  deleteTarget.value = c;
  deleteError.value = "";
}

async function doDelete() {
  if (!deleteTarget.value) return;
  deleting.value = true;
  deleteError.value = "";
  try {
    await deleteCluster(deleteTarget.value.id);
    toast.show("集群已删除", "success");
    deleteTarget.value = null;
    await fetchData();
  } catch (e) {
    deleteError.value = e.message || "删除失败";
  } finally {
    deleting.value = false;
  }
}

async function testConnection(c) {
  testingId.value = c.id;
  try {
    const res = await testCluster(c.id);
    testResult.value = {
      success: true,
      message: res.message,
      nsCount: res.data?.namespace_count || 0,
      version: res.data?.server_version || "未知",
    };
  } catch (e) {
    testResult.value = { success: false, message: e.detail || e.message || "连接失败" };
  } finally {
    testingId.value = null;
  }
}

function formatDate(s) {
  if (!s) return "-";
  return new Date(s).toLocaleString("zh-CN");
}

onMounted(fetchData);
</script>

<style scoped>
.actions-cell {
  white-space: nowrap;
}
.actions-cell .btn {
  margin-right: 4px;
}
</style>
