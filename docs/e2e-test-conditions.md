# 功能与验收条件 · K8s 管理控制台

> 本文档是 E2E 测试的唯一执行依据。由 `chrome-devtools-e2e-testing` skill 驱动读取和维护。
>
> **维护规则：** 代码功能变更时同步更新此文件。增删改功能 → 增删改对应条目。

---

## F1. 登录

**页面/组件：** `LoginPage.vue`、`stores/auth.js`、`api/auth.js`

**正常流程：**

- [ ] 未登录用户访问任何受保护页面，自动跳转到 `/login`
- [ ] 页面显示 "☸️ K8s Console" 标题、用户名输入框、密码输入框、"登录" 按钮
- [ ] 输入正确用户名密码（admin/admin），点击登录后跳转到仪表盘 `/`
- [ ] 登录成功后，侧边栏可见，Token 存入 localStorage (`k8s_console_token`)

**异常情况：**

- [ ] 用户名为空或密码为空 → 显示 "请输入用户名和密码"
- [ ] 用户名或密码错误 → 显示后端返回的错误消息
- [ ] 后端不可达 → 显示网络错误提示，停留在登录页

**边界条件：**

- [ ] 已登录用户访问 `/login` → 自动跳转到 `/`
- [ ] Token 过期或无效时发起 API 请求 → 自动清除登录态，跳转到 `/login`

---

## F2. 仪表盘

**页面/组件：** `DashboardPage.vue`

- [ ] 登录后默认进入仪表盘，显示 "📊 集群概览" 标题
- [ ] 显示 5 张统计卡片：Namespace、Deployment、Pod、Service、Ingress
- [ ] 每张卡片显示具体数字（不是 "..." 或 "错误"）
- [ ] API 异常时页面显示错误提示而非白屏

---

## F3. 资源列表

**页面/组件：** `ResourceListPage.vue`、`api/resources.js`

### F3.1 通用

- [ ] 页面标题 "📦 {资源类型中文名}"
- [ ] 数据以表格展示，列随资源类型变化
- [ ] 无数据时显示 "暂无资源"
- [ ] 加载中显示 "加载中..."
- [ ] API 失败时显示红色错误信息

### F3.2 Namespace 筛选

- [ ] 命名空间级别资源，顶部显示 namespace 筛选标签（"全部" + 各 namespace 名）
- [ ] 点击某 namespace 标签 → 列表只显示该 namespace 资源
- [ ] 当前选中标签有视觉高亮
- [ ] 集群级别资源（namespace、clusterrole、clusterrolebinding）不显示筛选标签
- [ ] 切换资源类型时筛选重置为 "全部"

### F3.3 各资源类型表格列

- [ ] **Deployment:** Name, Namespace, Replicas, Image, 操作
- [ ] **Pod:** Name, Namespace, Status, 操作 — Status 用颜色标签：Running(绿)/Pending(红)/其他
- [ ] **Service:** Name, Namespace, Type, Cluster IP, 操作
- [ ] **Ingress:** Name, Namespace, Hosts, 操作
- [ ] **Namespace:** Name, Status, 操作（无 Namespace 列）
- [ ] **StatefulSet:** Name, Namespace, Replicas, 操作
- [ ] **DaemonSet / ConfigMap / Secret / Role / RoleBinding / ClusterRole / ClusterRoleBinding / ServiceAccount:** Name, Namespace, 操作

### F3.4 YAML 查看

- [ ] 每行有 "YAML" 按钮
- [ ] 点击后弹出模态框，显示该资源 YAML 内容（语法高亮）
- [ ] 加载期间显示 "加载中..."
- [ ] 加载失败时弹窗内显示错误
- [ ] 弹窗可关闭（关闭按钮 / 点击遮罩层）

### F3.5 Scale（仅 Deployment、StatefulSet）

- [ ] 列表行出现 "Scale" 按钮
- [ ] 点击后弹出模态框：显示资源标识、当前副本数、目标副本数输入框
- [ ] 输入框预填当前副本数
- [ ] 成功：弹窗关闭，Toast 显示 "已将副本数调整为 {n}"，列表刷新
- [ ] 失败：Toast 显示错误，弹窗保持打开

### F3.6 Rollback（仅 Deployment）

- [ ] 列表行出现 "Rollback" 按钮
- [ ] 点击后弹出模态框，可选择回滚 revision
- [ ] 成功：Toast 显示 "回滚成功"，列表刷新
- [ ] 失败：Toast 显示错误

### F3.7 Delete（除 Namespace 外）

- [ ] 列表行出现红色 "删除" 按钮
- [ ] 点击后弹出确认模态框："🚨 删除资源" 标题、确认输入框、"确认删除" 按钮
- [ ] 未输入正确名称时 "确认删除" 禁用
- [ ] 输入正确名称后 "确认删除" 可用
- [ ] 自动化测试只验证弹窗逻辑，不实际提交删除

---

## F4. Apply YAML

**页面/组件：** `ApplyYamlPage.vue`、`api/resources.js`

- [ ] 页面标题 "🛠 Apply YAML"
- [ ] 左侧 YAML 编辑区（textarea，深色背景，等宽字体）
- [ ] 编辑器有空状态 placeholder 提示
- [ ] 编辑器为空时 "Apply" 按钮禁用
- [ ] 填入 YAML → 点击 Apply → 右侧显示结果面板（成功 ✅ / 失败 ❌）
- [ ] 成功时显示各资源 action 详情
- [ ] 点击 "清空" → 编辑器和结果面板清空
- [ ] YAML 语法错误或 API 失败 → 结果面板显示失败信息

---

## F5. 用户管理（仅管理员）

**页面/组件：** `UserManagementPage.vue`、`api/users.js`

- [ ] 页面标题 "👤 用户管理"
- [ ] 上部创建表单：用户名输入框、角色下拉（普通用户/管理员）、"创建" 按钮
- [ ] 下部用户表格：用户名、角色、状态、创建时间、操作
- [ ] 创建成功 → 显示初始密码，列表刷新
- [ ] 角色列标签区分：admin（蓝色）/ user（默认色）
- [ ] 状态列标签区分：启用（绿色）/ 禁用（红色）
- [ ] 操作按钮：禁用/启用、重置密码
- [ ] 非 admin 用户看不到此页面入口；直接访问 `/users` 跳转到 `/`

---

## F6. 审计日志（仅管理员）

**页面/组件：** `AuditLogPage.vue`、`api/audit.js`

- [ ] 页面标题 "📋 审计日志"
- [ ] 包括操作类型和结果的筛选下拉
- [ ] 日志以表格展示（含操作时间、用户、操作类型、资源类型等列）
- [ ] 数据超过一页时分页控件可用
- [ ] 非 admin 用户看不到此页面入口；直接访问 `/audit` 跳转到 `/`

---

## F7. 侧边栏导航

**页面/组件：** `AppSidebar.vue`、`router/index.js`

- [ ] 侧边栏固定在左侧，深色背景
- [ ] 顶部品牌名 "☸️ K8s Console"
- [ ] 导航项：仪表盘、资源管理分组（14 种资源）、Apply YAML
- [ ] admin 额外显示：用户管理、审计日志
- [ ] 当前页面对应的导航项高亮
- [ ] 底部显示用户名和 "登出" 按钮

**路由表：**

| 路径 | 页面 | 权限 |
|------|------|------|
| `/login` | 登录 | 公开 |
| `/` | 仪表盘 | 需登录 |
| `/resources/:type` | 资源列表 | 需登录 |
| `/apply` | Apply YAML | 需登录 |
| `/users` | 用户管理 | admin |
| `/audit` | 审计日志 | admin |

---

## F8. 登出

**页面/组件：** `AppSidebar.vue`（登出按钮）、`stores/auth.js`、`api/auth.js`

- [ ] 点击 "登出" → 调用 logout API → 清除 localStorage 中的 token 和 user
- [ ] 登出后跳转到 `/login`
- [ ] 登出后不能通过 URL 直接访问受保护页面
- [ ] logout API 调用失败时仍清除本地登录态并跳转登录页

---

## F9. 路由守卫

**页面/组件：** `router/index.js`（beforeEach）

- [ ] 无 token 访问 `/` → 跳转 `/login`
- [ ] 无 token 访问 `/resources/deployment` → 跳转 `/login`
- [ ] 无 token 访问 `/users` → 跳转 `/login`
- [ ] 有 token 访问 `/login` → 跳转 `/`
- [ ] 非 admin 访问 `/users` → 跳转 `/`
- [ ] 非 admin 访问 `/audit` → 跳转 `/`

---

## F10. Token 管理

**页面/组件：** `stores/auth.js`、`api/client.js`

- [ ] 登录后 token 持久化到 localStorage（key: `k8s_console_token`）
- [ ] 每次 API 请求自动附带 `Authorization: Token {token}` 头
- [ ] API 返回 code 1002 或 1003 → 自动清除登录态，跳转 `/login`
- [ ] 页面刷新后 token 仍有效，无需重新登录

---

## 测试套件

### 冒烟测试

改动后至少跑：

```
F1（登录正常+异常）→ F2（仪表盘）→ F3.1+F3.2（任一资源列表）
→ F8（登出）→ F9（路由守卫）
```

### 完整回归

```
F1 → F2 → F3(全部子项) → F4 → F5 → F6 → F7 → F8 → F9 → F10
```

### 测试注意事项

- 每次操作前必须重新 `take_snapshot`（uid 会刷新）
- 异步数据加载后先用 `wait_for` 再交互
- 破坏性操作（Delete、禁用用户等）只验证弹窗逻辑，不实际提交
- F3.5 Scale 测试：修改副本数后应恢复原值
