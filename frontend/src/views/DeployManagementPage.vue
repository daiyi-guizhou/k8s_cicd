<template>
  <div class="deploy-page">
    <h2>🚀 CI/CD 部署管理</h2>

    <div class="deploy-layout">
      <!-- Left: Project List -->
      <div class="deploy-left">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
          <h3 style="margin:0;">项目列表</h3>
          <button v-if="auth.isAdmin" class="btn btn-primary" @click="openCreate">+ 新增项目</button>
        </div>

        <div v-if="projectLoading" style="color:#64748b;">加载中...</div>
        <div v-else-if="projectError" style="color:#dc2626;">{{ projectError }}</div>

        <div
          v-for="p in projects"
          :key="p.app_name"
          :class="['project-item', { selected: selectedProject?.app_name === p.app_name }]"
          @click="selectProject(p)"
        >
          <div class="project-item-header">
            <strong>{{ p.app_name }}</strong>
            <span class="tag" :class="p.app_type === 'django' ? 'tag-blue' : 'tag-green'">
              {{ p.app_type === 'django' ? 'Django' : 'Vue' }}
            </span>
          </div>
          <div class="project-item-meta">
            <span>{{ p.domain }}</span>
            <span :class="['tag', p.enabled ? 'tag-green' : 'tag-red']">
              {{ p.enabled ? '已启用' : '已禁用' }}
            </span>
          </div>
        </div>
        <p v-if="projects.length === 0 && !projectLoading" style="color:#64748b;">
          暂无项目，请点击"新增项目"按钮添加。
        </p>
      </div>

      <!-- Right: Deploy Panel -->
      <div class="deploy-right">
        <div v-if="!selectedProject" class="deploy-placeholder">
          <p>← 请从左侧选择一个项目</p>
        </div>

        <template v-else>
          <!-- Project Info -->
          <div class="info-card">
            <h3>{{ selectedProject.app_name }}
              <span class="tag" :class="selectedProject.app_type === 'django' ? 'tag-blue' : 'tag-green'">
                {{ selectedProject.app_type === 'django' ? 'Django' : 'Vue' }}
              </span>
            </h3>
            <div class="info-row"><span class="info-label">域名:</span> <code>{{ selectedProject.domain }}</code>
              <span class="info-label" style="margin-left:12px;">Path:</span> <code>{{ selectedProject.ingress_path || '/' }}</code>
            </div>
            <div class="info-row"><span class="info-label">路径:</span> <code>{{ selectedProject.local_path }}</code></div>
            <div class="info-row"><span class="info-label">端口:</span> {{ selectedProject.port }} &nbsp;|&nbsp;
              <span class="info-label">副本:</span> {{ selectedProject.replicas }} &nbsp;|&nbsp;
              <span class="info-label">命名空间:</span> {{ selectedProject.namespace }}
            </div>
            <div style="margin-top:10px;display:flex;gap:8px;" v-if="auth.isAdmin">
              <button class="btn" style="font-size:12px;" @click="openEdit">✏ 编辑</button>
              <button class="btn" style="font-size:12px;color:#dc2626;" @click="openDelete">🗑 删除</button>
            </div>
          </div>

          <!-- Deploy Trigger -->
          <div v-if="auth.isAdmin" class="action-card">
            <h3 style="margin-top:0;">一键部署</h3>
            <div class="form-row">
              <div class="form-group" style="flex:1;">
                <label class="form-label">Tag <span style="color:#dc2626;">*</span></label>
                <input v-model="deployTag" class="form-input" placeholder="例如: v1.2.0" />
              </div>
              <button
                class="btn btn-primary"
                style="align-self:flex-end;height:38px;"
                :disabled="!deployTag.trim() || deploying"
                @click="doDeploy"
              >
                {{ deploying ? '部署中...' : '🚀 一键部署' }}
              </button>
            </div>
            <div v-if="deployError" style="color:#dc2626;margin-top:8px;">{{ deployError }}</div>
            <div v-if="deploySuccess" style="color:#16a34a;margin-top:8px;">{{ deploySuccess }}</div>
          </div>

          <!-- Deploy History -->
          <div class="history-card">
            <h3>部署历史</h3>
            <div v-if="historyLoading" style="color:#64748b;">加载中...</div>
            <table v-else-if="history.length > 0" class="data-table">
              <thead>
                <tr>
                  <th>Tag</th>
                  <th>状态</th>
                  <th>操作人</th>
                  <th>时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="h in history" :key="h.id">
                  <td><strong>{{ h.tag }}</strong></td>
                  <td>
                    <span :class="['tag', statusClass(h.status)]">{{ statusLabel(h.status) }}</span>
                  </td>
                  <td>{{ h.operator || '-' }}</td>
                  <td>{{ formatDate(h.created_at) }}</td>
                  <td>
                    <button
                      v-if="h.status === 'success' && auth.isAdmin"
                      class="btn"
                      style="font-size:12px;"
                      :disabled="rollbackTag === h.tag"
                      @click="doRollback(h.tag)"
                    >
                      {{ rollbackTag === h.tag ? '回滚中...' : '🔄 回滚' }}
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
            <p v-else-if="!historyLoading" style="color:#64748b;">暂无部署历史</p>
            <div v-if="historyError" style="color:#dc2626;margin-top:8px;">{{ historyError }}</div>
          </div>
        </template>
      </div>
    </div>

    <!-- Create/Edit Project Modal -->
    <div v-if="showForm" class="modal-overlay" @click.self="showForm = false">
      <div class="modal-box" style="max-width:560px;">
        <h3 style="margin-bottom:16px;">{{ editingProject ? '编辑项目' : '新增项目' }}</h3>

        <div class="form-group">
          <label class="form-label">应用名称 <span style="color:#dc2626;">*</span></label>
          <input v-model="form.app_name" class="form-input"
            placeholder="例如: my-shop" :disabled="!!editingProject" />
        </div>
        <div class="form-group">
          <label class="form-label">应用类型 <span style="color:#dc2626;">*</span></label>
          <select v-model="form.app_type" class="form-input">
            <option value="django">Django</option>
            <option value="vue">Vue</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">本地代码路径 <span style="color:#dc2626;">*</span></label>
          <input v-model="form.local_path" class="form-input" placeholder="例如: /d/projects/my-shop" />
        </div>
        <div class="form-group">
          <label class="form-label">访问域名 <span style="color:#dc2626;">*</span></label>
          <input v-model="form.domain" class="form-input" placeholder="例如: my-shop.daiyi.local.com" />
        </div>
        <div class="form-group">
          <label class="form-label">Ingress Path
            <span style="font-size:11px;color:#64748b;">（Django 默认 /api，Vue 默认 /）</span>
          </label>
          <input v-model="form.ingress_path" class="form-input" placeholder="例如: / 或 /api" />
        </div>
        <div class="form-row">
          <div class="form-group" style="flex:1;">
            <label class="form-label">容器端口</label>
            <input v-model.number="form.port" class="form-input" type="number" />
          </div>
          <div class="form-group" style="flex:1;">
            <label class="form-label">副本数</label>
            <input v-model.number="form.replicas" class="form-input" type="number" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group" style="flex:1;">
            <label class="form-label">命名空间</label>
            <input v-model="form.namespace" class="form-input" placeholder="prd" />
          </div>
          <div class="form-group" style="flex:1;">
            <label class="form-label">目标集群 <span style="color:#dc2626;">*</span></label>
            <select v-model.number="form.cluster_id" class="form-input">
              <option :value="null" disabled>-- 选择集群 --</option>
              <option v-for="c in clusterOptions" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">
            <input type="checkbox" v-model="form.enabled" style="margin-right:6px;" />
            启用
          </label>
        </div>

        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px;">
          <button class="btn" @click="showForm = false">取消</button>
          <button class="btn btn-primary"
            :disabled="!formValid || submitting"
            @click="doSubmit">
            {{ submitting ? '提交中...' : editingProject ? '更新' : '创建' }}
          </button>
        </div>
        <div v-if="formError" style="color:#dc2626;margin-top:8px;">{{ formError }}</div>
      </div>
    </div>

    <!-- Delete Confirm -->
    <div v-if="deleteTarget" class="modal-overlay" @click.self="deleteTarget = null">
      <div class="modal-box">
        <h3 style="margin-bottom:12px;">确认删除</h3>
        <p>确定要删除项目 <strong>{{ deleteTarget.app_name }}</strong> 吗？</p>
        <p style="font-size:12px;color:#64748b;">此操作仅删除控制台中的项目配置，不影响已部署的 K8s 资源。</p>
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px;">
          <button class="btn" @click="deleteTarget = null">取消</button>
          <button class="btn" style="background:#dc2626;color:#fff;" :disabled="deleting" @click="doDelete">
            {{ deleting ? '删除中...' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Rollback Confirm -->
    <div v-if="rollbackConfirmTag" class="modal-overlay" @click.self="rollbackConfirmTag = null">
      <div class="modal-box">
        <h3 style="margin-bottom:12px;">确认回滚</h3>
        <p>确定要将 <strong>{{ selectedProject?.app_name }}</strong> 回滚到 <strong>{{ rollbackConfirmTag }}</strong> 吗？</p>
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px;">
          <button class="btn" @click="rollbackConfirmTag = null">取消</button>
          <button class="btn btn-primary" :disabled="rollingBack" @click="confirmRollback">
            {{ rollingBack ? '回滚中...' : '确认回滚' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, inject } from "vue";
import {
  listProjects, createProject, updateProject, deleteProject,
  triggerDeploy, rollbackDeploy, listDeployHistory,
} from "../api/deploy";
import { getClusterList } from "../api/clusters";
import { useAuthStore } from "../stores/auth";

const toast = inject("toast", null);

/** Fallback toast using window event (in case inject not available) */
function toastShow(message, type = "success") {
  if (toast?.show) {
    toast.show(message, type);
  } else {
    window.dispatchEvent(new CustomEvent("app-toast", { detail: { message, type } }));
  }
}
const auth = useAuthStore();

// Project list
const projects = ref([]);
const projectLoading = ref(false);
const projectError = ref("");
const selectedProject = ref(null);

// Deploy
const deployTag = ref("");
const deploying = ref(false);
const deployError = ref("");
const deploySuccess = ref("");

// History
const history = ref([]);
const historyLoading = ref(false);
const historyError = ref("");

// Rollback
const rollbackTag = ref(null);
const rollbackConfirmTag = ref(null);
const rollingBack = ref(false);

// Form
const showForm = ref(false);
const editingProject = ref(null);
const form = ref({
  app_name: "", app_type: "django", local_path: "", domain: "",
  port: 8000, replicas: 1, namespace: "prd", cluster_id: null, enabled: true,
  ingress_path: "",
});
const formError = ref("");
const submitting = ref(false);

// Delete
const deleteTarget = ref(null);
const deleting = ref(false);

// Cluster options
const clusterOptions = ref([]);

const formValid = computed(() => {
  return form.value.app_name.trim() && form.value.domain.trim() &&
    form.value.local_path.trim() && form.value.cluster_id;
});

// ---- Fetch ----
async function fetchProjects() {
  projectLoading.value = true;
  projectError.value = "";
  try {
    const res = await listProjects();
    projects.value = res.data?.items || [];
  } catch (e) {
    projectError.value = e.message || "加载失败";
  } finally {
    projectLoading.value = false;
  }
}

async function fetchClusters() {
  try {
    const res = await getClusterList();
    clusterOptions.value = res.data?.items || [];
  } catch (e) { /* ignore */ }
}

function selectProject(p) {
  selectedProject.value = p;
  deployTag.value = "";
  deployError.value = "";
  deploySuccess.value = "";
  fetchHistory(p.app_name);
}

async function fetchHistory(appName) {
  historyLoading.value = true;
  historyError.value = "";
  try {
    const res = await listDeployHistory(appName);
    history.value = res.data?.items || [];
  } catch (e) {
    historyError.value = e.message || "加载失败";
  } finally {
    historyLoading.value = false;
  }
}

// ---- Deploy ----
async function doDeploy() {
  if (!deployTag.value.trim()) return;
  deploying.value = true;
  deployError.value = "";
  deploySuccess.value = "";
  try {
    const res = await triggerDeploy(selectedProject.value.app_name, deployTag.value.trim());
    toastShow(res.message || "部署成功", "success");
    deploySuccess.value = res.message;
    deployTag.value = "";
    fetchHistory(selectedProject.value.app_name);
  } catch (e) {
    deployError.value = e.message || "部署失败";
    toastShow(deployError.value, "error");
    fetchHistory(selectedProject.value.app_name);
  } finally {
    deploying.value = false;
  }
}

// ---- Rollback ----
function doRollback(tag) {
  rollbackConfirmTag.value = tag;
}

async function confirmRollback() {
  rollingBack.value = true;
  rollbackTag.value = rollbackConfirmTag.value;
  try {
    const res = await rollbackDeploy(selectedProject.value.app_name, rollbackConfirmTag.value);
    toastShow(res.message || "回滚成功", "success");
    rollbackConfirmTag.value = null;
    fetchHistory(selectedProject.value.app_name);
  } catch (e) {
    toastShow(e.message || "回滚失败", "error");
  } finally {
    rollingBack.value = false;
    rollbackTag.value = null;
  }
}

// ---- Form ----
function openCreate() {
  editingProject.value = null;
  form.value = {
    app_name: "", app_type: "django", local_path: "", domain: "",
    port: 8000, replicas: 1, namespace: "prd", cluster_id: clusterOptions.value[0]?.id || null, enabled: true,
    ingress_path: "",
  };
  formError.value = "";
  showForm.value = true;
}

function openEdit() {
  editingProject.value = selectedProject.value;
  form.value = {
    app_name: selectedProject.value.app_name,
    app_type: selectedProject.value.app_type,
    local_path: selectedProject.value.local_path,
    domain: selectedProject.value.domain,
    ingress_path: selectedProject.value.ingress_path || "",
    port: selectedProject.value.port,
    replicas: selectedProject.value.replicas,
    namespace: selectedProject.value.namespace,
    cluster_id: selectedProject.value.cluster_id,
    enabled: selectedProject.value.enabled,
  };
  formError.value = "";
  showForm.value = true;
}

async function doSubmit() {
  formError.value = "";
  submitting.value = true;
  try {
    if (editingProject.value) {
      await updateProject(form.value);
      toastShow("项目已更新", "success");
    } else {
      await createProject(form.value);
      toastShow("项目已创建", "success");
    }
    showForm.value = false;
    await fetchProjects();
  } catch (e) {
    formError.value = e.message || "操作失败";
  } finally {
    submitting.value = false;
  }
}

function openDelete() {
  deleteTarget.value = selectedProject.value;
}

async function doDelete() {
  if (!deleteTarget.value) return;
  deleting.value = true;
  try {
    await deleteProject(deleteTarget.value.app_name);
    toastShow("项目已删除", "success");
    if (selectedProject.value?.app_name === deleteTarget.value.app_name) {
      selectedProject.value = null;
      history.value = [];
    }
    deleteTarget.value = null;
    await fetchProjects();
  } catch (e) {
    toastShow(e.message || "删除失败", "error");
  } finally {
    deleting.value = false;
  }
}

// ---- Helpers ----
function statusClass(status) {
  return {
    building: "tag-blue",
    deploying: "tag-blue",
    success: "tag-green",
    failed: "tag-red",
  }[status] || "";
}

function statusLabel(status) {
  return {
    building: "构建中",
    deploying: "部署中",
    success: "成功",
    failed: "失败",
  }[status] || status;
}

function formatDate(s) {
  if (!s) return "-";
  return new Date(s).toLocaleString("zh-CN");
}

onMounted(() => {
  fetchProjects();
  fetchClusters();
});
</script>

<style scoped>
.deploy-page h2 { margin-bottom: 16px; }

.deploy-layout {
  display: flex;
  gap: 20px;
  min-height: calc(100vh - 160px);
}

.deploy-left {
  width: 300px;
  flex-shrink: 0;
  border-right: 1px solid var(--border-color, #334155);
  padding-right: 16px;
  overflow-y: auto;
}

.deploy-right {
  flex: 1;
  min-width: 0;
}

.project-item {
  padding: 10px 12px;
  border: 1px solid var(--border-color, #334155);
  border-radius: 6px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.15s;
}
.project-item:hover { border-color: #3b82f6; }
.project-item.selected {
  border-color: #3b82f6;
  background: rgba(59,130,246,0.08);
}

.project-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.project-item-meta {
  font-size: 12px;
  color: #64748b;
  display: flex;
  justify-content: space-between;
}

.deploy-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #64748b;
}

.info-card, .action-card, .history-card {
  background: var(--card-bg, #1e293b);
  border: 1px solid var(--border-color, #334155);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.info-row { margin: 6px 0; font-size: 14px; }
.info-label { color: #64748b; margin-right: 4px; }
.info-row code { background: #334155; padding: 1px 4px; border-radius: 3px; font-size: 13px; }

.form-row {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.tag-blue { background: #1e40af; color: #bfdbfe; }
.tag-green { background: #166534; color: #bbf7d0; }
.tag-red { background: #991b1b; color: #fecaca; }
.tag { font-size: 11px; padding: 2px 6px; border-radius: 4px; }
</style>
