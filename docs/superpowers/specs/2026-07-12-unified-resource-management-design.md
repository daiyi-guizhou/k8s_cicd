# 统一资源管理页面 — 设计文档

**日期**: 2026-07-12
**状态**: 设计完成，待实现

---

## 1. 背景与动机

当前 K8s Console 前端有 14 种 Kubernetes 资源类型（Namespace、Deployment、Pod、Service、Ingress、DaemonSet、StatefulSet、ConfigMap、Secret、Role、RoleBinding、ClusterRole、ClusterRoleBinding、ServiceAccount），每种资源在侧边栏各占一个菜单项，每个菜单项对应一个独立的 `/resources/:type` 路由。侧边栏过长，用户需要在菜单里滚动查找。

后端 API 本身已经是统一的 —— 所有资源共用同一组 `/resources/*` 接口，仅通过 `resource_type` 参数区分。

**目标**：将 14 个独立页面合并为一个统一的资源管理页面，用户在页面内选择资源类型后再执行操作。

---

## 2. 设计方案

### 2.1 路由变更

| 变更前 | 变更后 |
|--------|--------|
| `/resources/:type`（14 个路由） | `/resources`（1 个路由） |

URL query 参数保持状态：`/resources?type=deployment&ns=default&search=api`，支持刷新和分享。

### 2.2 侧边栏变更

将 14 个资源类型子菜单项合并为 1 个 "📦 资源管理" 菜单项，链接到 `/resources`。

### 2.3 页面布局

```
┌─────────────────────────────────────────────────────┐
│ 📦 资源管理                                          │
├─────────────────────────────────────────────────────┤
│ [资源类型 ▼]  [Namespace ▼]  [资源名称搜索 🔍]  [🔄] │
├─────────────────────────────────────────────────────┤
│ Name        │ Namespace │ Replicas │ Image │ 操作   │
│ api-gateway │ default   │ 3        │ nginx │ [按钮] │
│ ...                                                  │
└─────────────────────────────────────────────────────┘
```

### 2.4 三个过滤器

#### a) 资源类型下拉框
- 常用资源（Deployment、Pod、Service）排在前面，加 ⭐ 标记
- 其余资源按字母序排列
- 每项显示资源数量统计，如 `Deployment (5)`
- 支持输入模糊搜索过滤
- 切换时自动请求对应资源列表

#### b) Namespace 下拉框
- 默认显示 "全部"
- 动态从 namespace 列表加载
- 支持输入模糊搜索
- 集群级别资源（Namespace / ClusterRole / ClusterRoleBinding 自身）时隐藏此过滤

#### c) 资源名称输入框
- 文本输入框，输入后前端对已加载列表做模糊匹配过滤
- 纯前端过滤，不触发额外 API 请求

### 2.5 动态列定义

根据选中的资源类型，表格动态显示不同列：

| 资源类型 | 额外列 |
|----------|--------|
| Deployment | Replicas, Image |
| Pod | Status (phase) |
| Service | Type, Cluster IP |
| Ingress | Hosts |
| StatefulSet | Replicas |
| 其他 | 仅 Name + Namespace |

### 2.6 操作按钮

| 按钮 | 显示条件 | 行为 |
|------|---------|------|
| YAML | 所有类型 | 打开 YAML 查看弹窗 |
| Scale | Deployment / StatefulSet | 打开 Scale 弹窗 |
| Rollback | Deployment | 打开 Rollback 弹窗 |
| 删除 | 除 Namespace 外所有类型 | 打开删除确认弹窗 |

弹窗复用现有组件：`ScaleModal`、`DeleteModal`、`RollbackModal`、`YamlModal`。

### 2.7 数量统计加载策略

资源类型下拉框中的数量统计并非实时获取所有 14 种资源的 count。采用以下策略：
- **懒加载**：页面初始加载时，仅统计默认选中资源类型（首次为 Deployment，或 URL 中指定的类型）
- **按需统计**：用户打开下拉框时，通过已有的 Dashboard 概览数据或一次性批量查询来展示计数
- **降级**：如果统计接口调用失败，只隐藏计数，不影响下拉选择功能

> **简化实现**：初始版本可以在页面挂载时一次性请求所有资源类型的 count（14 个并行请求），因为 K8s list 请求本身很快（~100-200ms），14 个并发请求总体延迟可控。后续如发现性能问题再优化为懒加载。

---

## 3. 涉及文件

### 前端（修改）

| 文件 | 改动 |
|------|------|
| `frontend/src/views/ResourceListPage.vue` | 重写为统一资源管理页面，增加资源类型下拉 + 名称搜索 |
| `frontend/src/components/AppSidebar.vue` | 移除 14 个子菜单项，替换为单个"资源管理"链接 |
| `frontend/src/router/index.js` | 路由从 `/resources/:type` 改为 `/resources` |

### 后端

**无需改动**。

---

## 4. 边界情况

| 场景 | 处理方式 |
|------|---------|
| 集群未选择 | 表格区域提示"请先选择集群" |
| 选中资源类型无数据 | 表格显示"暂无资源" |
| API 请求失败 | 表格区域显示错误信息，不影响过滤器操作 |
| 集群级别资源（Namespace 等） | Namespace 下拉框隐藏，名称搜索仍可用 |
| 浏览器刷新 | URL query 参数恢复所有过滤状态 |
| 资源类型数量统计加载失败 | 隐藏计数，下拉功能不受影响 |

---

## 5. 不改动的内容

- 弹窗组件（ScaleModal、DeleteModal、RollbackModal、YamlModal）保持不变
- 后端 API 保持不变
- ApplyYamlPage 保持不变
- 其他页面（Dashboard、用户管理、审计日志等）不变
- CSS 变量和全局样式不变

---

## 6. 验收标准

1. 侧边栏只有 1 个 "📦 资源管理" 菜单项
2. 点击进入 `/resources`，默认选中 Deployment
3. 切换资源类型下拉框，表格列和操作按钮随类型变化
4. 三个过滤器（资源类型、Namespace、名称）均正常工作
5. 搜索过滤后下拉列表正确缩小范围
6. YAML / Scale / Rollback / 删除四个弹窗功能正常
7. 页面刷新后，URL query 参数恢复过滤状态
