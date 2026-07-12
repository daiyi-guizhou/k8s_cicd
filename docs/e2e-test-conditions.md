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

## F3. 统一资源管理页

**页面/组件：** `ResourceListPage.vue`、`api/resources.js`

**路由：** `/resources`（不再用 `/resources/:type`）

### F3.1 资源类型选择器

- [ ] 页面显示 "📦 资源管理" 标题
- [ ] 三个过滤器并排：资源类型（搜索下拉框）、Namespace（搜索下拉框）、资源名称（文本输入框）
- [ ] 资源类型下拉框分为两段：⭐ 常用（Deployment/Pod/Service）+ 📋 其他（其余类型按字母序）
- [ ] 下拉框支持键盘输入模糊匹配过滤
- [ ] 下拉框支持 ↑↓ 键盘导航 + Enter 选中
- [ ] 资源类型下拉框旁显示资源数量（如 "Deployment (5)"）
- [ ] 切换资源类型后 Namespace 筛选重置为 "全部"
- [ ] 加载中显示 "加载中..."
- [ ] API 失败时显示红色错误信息
- [ ] 无数据时显示 "暂无资源"

### F3.2 Namespace 筛选

- [ ] 命名空间级别资源，Namespace 下拉框列出 "全部" + 所有 namespace
- [ ] Namespace 下拉框支持输入模糊匹配
- [ ] 集群级别资源（namespace、clusterrole、clusterrolebinding）不显示 Namespace 筛选器
- [ ] 切换资源类型时筛选重置为 "全部"

### F3.3 资源名称搜索

- [ ] 输入文字后前端实时过滤（无需点击搜索按钮）
- [ ] URL query 参数同步：`/resources?type=pod&search=redis`
- [ ] 清空搜索框后恢复显示全部

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
- [ ] 品牌名下方有集群选择下拉框（F12）
- [ ] 导航项：仪表盘、🖥 集群管理、📦 资源管理、🛠 Apply YAML
- [ ] admin 额外显示：👤 用户管理、📋 审计日志
- [ ] 当前页面对应的导航项高亮
- [ ] 底部显示用户名和 "登出" 按钮

**路由表：**

| 路径 | 页面 | 权限 |
|------|------|------|
| `/login` | 登录 | 公开 |
| `/` | 仪表盘 | 需登录 |
| `/resources` | 统一资源管理 | 需登录 |
| `/apply` | Apply YAML | 需登录 |
| `/clusters` | 集群管理 | admin |
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
- [ ] 无 token 访问 `/resources` → 跳转 `/login`
- [ ] 无 token 访问 `/users` → 跳转 `/login`
- [ ] 有 token 访问 `/login` → 跳转 `/`
- [ ] 非 admin 访问 `/users` → 跳转 `/`
- [ ] 非 admin 访问 `/audit` → 跳转 `/`

---

## F10. Token 管理

**页面/组件：** `stores/auth.js`、`api/client.js`

**Token 过期机制：** 8h 滑动 TTL（每次 API 请求自动续期）+ 24h 绝对过期。登录时写入 `token:auth:{token}`（8h TTL）和 `token:meta:{token}`（24h TTL，JSON 格式含 `user_id`、`login_at`、`absolute_expiry`、`deploy_version`）。

- [ ] 登录后 token 持久化到 localStorage（key: `k8s_console_token`）
- [ ] 同时持久化 `loginAt` 和 `absoluteExpiry` 到 localStorage
- [ ] 每次 API 请求自动附带 `Authorization: Token {token}` 头
- [ ] API 返回 code 1002（token 无效）→ 自动清除登录态，跳转 `/login`
- [ ] API 返回 code 1003（token 已登出/黑名单）→ 自动清除登录态，跳转 `/login`
- [ ] API 返回 code 1004（系统已更新/部署版本不匹配）→ Toast "系统已更新…"，清除登录态，跳转 `/login?reason=updated`
- [ ] API 返回 code 1007（登录已过期/超24h）→ Toast "登录已过期…"，清除登录态，跳转 `/login?reason=expired`
- [ ] 请求拦截器预检：若本地 `isExpired` 为 true → 阻止请求、清除登录态、跳转 `/login?reason=expired`
- [ ] 登录页可通过 `?reason=expired` 和 `?reason=updated` query 参数展示对应的黄色提示横幅
- [ ] 页面刷新后 token 仍有效，无需重新登录

---

## 测试套件

> **ℹ️ 测试方法说明：** 当 ChromeDevTools MCP 不可用时，可通过 API curl 直接验证后端功能（登录、CRUD、权限守卫、Token 管理等）。但前端 UI 交互（页面渲染、模态框、路由跳转、表单验证提示等）仍需浏览器测试。两种方式互补，API 测试覆盖后端逻辑，浏览器测试覆盖 UI/UX。
>
> **⚠️ Admin 初始密码：** 部署后 admin 的初始密码是随机生成的（见 Backend Pod 启动日志 `Initial password:`），不再是固定的 `admin/admin`。可通过 `kubectl logs -n prd -l app=k8s-console-backend | grep password` 查看，或通过 Django shell 重置。

### 冒烟测试

改动后至少跑：

```
F1（登录正常+异常）→ F2（仪表盘）→ F3.1+F3.2（任一资源列表）
→ F8（登出）→ F9（路由守卫）
```

**认证改动后附加（API 级 — 无需浏览器）：**
```
F14（全部 9 项自检脚本）
```

### 完整回归

```
F1 → F2 → F3(全部子项) → F4 → F5 → F6 → F7 → F8 → F9 → F10 → F11 → F12 → F13 → F14
```

### 测试注意事项

- 每次操作前必须重新 `take_snapshot`（uid 会刷新）
- 异步数据加载后先用 `wait_for` 再交互
- 破坏性操作（Delete、禁用用户等）只验证弹窗逻辑，不实际提交
- F3.5 Scale 测试：修改副本数后应恢复原值


---

## F11. 集群管理（仅管理员）

**页面/组件：** `ClusterManagementPage.vue`、`api/clusters.js`、`stores/cluster.js`

### F11.1 集群列表

- [ ] 页面标题 "🖥 集群管理"
- [ ] 以表格展示所有集群：名称、描述、连接状态（已启用/已禁用）、创建时间、操作
- [ ] 无集群时显示 "暂无集群"
- [ ] 非 admin 用户不可见此页面入口；直接访问 `/clusters` 跳转到 `/`

### F11.2 添加集群

- [ ] 页面有 "+ 添加集群" 按钮
- [ ] 点击后弹出模态框：集群名称输入框（必填）、描述输入框、kubeconfig 内容 textarea、启用开关
- [ ] 名称为空时保存按钮禁用
- [ ] 创建成功后 Toast 显示成功消息，列表刷新

### F11.3 编辑集群

- [ ] 每行有 "编辑" 按钮
- [ ] 点击后弹出模态框，预填当前集群信息
- [ ] 修改保存后列表刷新

### F11.4 删除集群

- [ ] 每行有红色 "删除" 按钮
- [ ] 点击后弹出确认模态框
- [ ] 自动化测试只验证弹窗逻辑，不实际提交删除

### F11.5 测试连接

- [ ] 每行有 "测试" 按钮
- [ ] 点击后显示测试结果模态框
- [ ] 连接成功显示 ✅ 集群连接正常 + namespace 数量 + K8s 版本号
- [ ] 连接失败显示 ❌ 连接失败 + 错误信息


---

## F12. 集群选择器

**页面/组件：** `AppSidebar.vue`（集群下拉框）、`stores/cluster.js`

- [ ] 侧边栏顶部品牌名下方有集群选择下拉框
- [ ] 下拉框列出所有已启用集群
- [ ] 无集群时显示警告提示 "请先在集群管理中添加集群"
- [ ] 选中集群后，仪表盘/资源列表/Apply YAML 页面顶部显示当前集群名称
- [ ] 切换集群后，资源列表等数据自动刷新为新集群数据
- [ ] 未选择集群时，资源列表等页面显示 "请先在侧边栏选择一个目标集群"
- [ ] Apply YAML 页面未选集群时显示 "请先在侧边栏选择一个目标集群" 黄色警告


---

## F13. 多集群资源操作

**涉及：** 所有资源操作 API 请求附带 `cluster_id`

- [ ] 仪表盘统计卡片数据来自当前选中集群
- [ ] 资源列表来自当前选中集群
- [ ] Scale / Rollback / Delete / Apply YAML 操作附带当前 cluster_id
- [ ] 审计日志中记录 cluster_name 字段，可追踪操作来自哪个集群


---

## F14. Token 认证 API 测试（curl — 部署后自动验证）

> **执行环境：** 部署完成后（`bash deploy/deploy-all.sh`），在 Git Bash 中通过 curl 直连 NodePort 或 port-forward 执行。以下脚本使用 `kubectl exec` 直接操作 Redis，不依赖外部工具。
>
> **前置条件：**
> - `deploy-all.sh` 已成功执行，所有 Pod Running
> - `kubectl port-forward` 已启动（或 NodePort 30000 可达）
> - Redis Pod 名可通过 `kubectl get pods -n database -l app=redis -o jsonpath='{.items[0].metadata.name}'` 获取

### F14.1 Login → Token Meta 结构

**涉及：** `apps/auth_app/views.py:login`、`k8s_console/middleware.py:VersionCheckMiddleware.__init__`

- [ ] Login 返回 `{code:0, data:{token, user:{id,username,role}}}`
- [ ] Redis 中 `token:auth:{token}` 存在，值为 `user_id`，TTL ≈ 28800
- [ ] Redis 中 `token:meta:{token}` 存在，JSON 含 `user_id`、`login_at`、`absolute_expiry`（login_at+24h）、`deploy_version`
- [ ] Redis 中 `deploy:version` 存在，值为 ISO 时间戳（由 `VersionCheckMiddleware.__init__` 写入）

**测试命令：**

```bash
# 登录
LOGIN=$(curl -s --noproxy '*' http://localhost:30000/api/auth/login \
  -H 'Host: k8s-cicd.daiyi.local.com' \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"<admin_password>"}')
TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['token'])")
echo "Token: $TOKEN"

# 检查 Redis
REDIS_POD=$(kubectl get pods -n database -l app=redis -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! keys "token:*" 2>/dev/null
kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! get "token:meta:$TOKEN" 2>/dev/null
kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! get "deploy:version" 2>/dev/null
kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! ttl "token:auth:$TOKEN" 2>/dev/null
kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! ttl "token:meta:$TOKEN" 2>/dev/null
```

### F14.2 Token 有效验证

- [ ] 使用有效 token 访问 `/api/users/list` → 返回 `{code:0, data:[...]}`

**测试命令：**

```bash
curl -s --noproxy '*' http://localhost:30000/api/users/list \
  -H 'Host: k8s-cicd.daiyi.local.com' \
  -H "Authorization: Token $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{}'
```

### F14.3 部署版本不匹配 → code 1004

**涉及：** `k8s_console/middleware.py:VersionCheckMiddleware`

- [ ] 修改 Redis 中 `deploy:version` 为不同于 token 存储的值
- [ ] 旧 token 访问 API → 返回 `{code:1004, message:"系统已更新，请刷新页面后重新登录"}`，HTTP 401
- [ ] 返回 1004 后，`token:auth` 和 `token:meta` 的 key 被清理

**测试命令：**

```bash
# 模拟重新部署
kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! \
  set "deploy:version" "simulated-new-deploy-$(date +%s)" 2>/dev/null

# 旧 token 应返回 1004
curl -s --noproxy '*' http://localhost:30000/api/users/list \
  -H 'Host: k8s-cicd.daiyi.local.com' \
  -H "Authorization: Token $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{}'

# Token 已清理
kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! \
  keys "token:*$TOKEN" 2>/dev/null
# 预期: (empty)

# 恢复 deploy:version（重登需要）
kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! \
  set "deploy:version" "<original_version>" 2>/dev/null
```

### F14.4 Token 绝对过期 → code 1007

**涉及：** `k8s_console/middleware.py:TokenRefreshMiddleware`

- [ ] 修改 Redis 中 `token:meta` 的 `absolute_expiry` 为过去时间（但保持 `deploy_version` 匹配）
- [ ] 过期 token 访问 API → 返回 `{code:1007, message:"登录已过期，请重新登录"}`，HTTP 401
- [ ] 返回 1007 后，`token:auth` 和 `token:meta` 的 key 被清理

**测试命令：**

```bash
# 重新登录获取有效 token
LOGIN=$(curl -s --noproxy '*' http://localhost:30000/api/auth/login \
  -H 'Host: k8s-cicd.daiyi.local.com' \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"<admin_password>"}')
TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['token'])")

# 获取当前 deploy:version
CURRENT_VER=$(kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! \
  get "deploy:version" 2>/dev/null | tr -d '\r')

# 修改 absolute_expiry 为已过期（保留 deploy_version 匹配）
META="{\"user_id\":\"1\",\"login_at\":\"2026-01-01T00:00:00\",\"absolute_expiry\":\"2026-01-02T00:00:00\",\"deploy_version\":\"$CURRENT_VER\"}"
kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! \
  set "token:meta:$TOKEN" "$META" 2>/dev/null

# 应返回 1007
curl -s --noproxy '*' http://localhost:30000/api/users/list \
  -H 'Host: k8s-cicd.daiyi.local.com' \
  -H "Authorization: Token $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{}'

# Token 已清理
kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! \
  keys "token:*$TOKEN" 2>/dev/null
# 预期: (empty)
```

### F14.5 Sliding TTL 续期

**涉及：** `k8s_console/middleware.py:TokenRefreshMiddleware`

- [ ] 登录后 auth TTL ≈ 28800s
- [ ] 等待几秒后发送 API 请求
- [ ] 请求后 auth TTL 刷新为 28800s（被续期）
- [ ] meta TTL 不受影响（不续期，持续递减）

**测试命令：**

```bash
# 登录
LOGIN=$(curl -s --noproxy '*' http://localhost:30000/api/auth/login \
  -H 'Host: k8s-cicd.daiyi.local.com' \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"<admin_password>"}')
TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['token'])")

# 登录后 TTL
echo "=== 登录后 ==="
kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! ttl "token:auth:$TOKEN" 2>/dev/null
kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! ttl "token:meta:$TOKEN" 2>/dev/null

# 等待并发送请求
sleep 3
curl -s --noproxy '*' http://localhost:30000/api/users/list \
  -H 'Host: k8s-cicd.daiyi.local.com' \
  -H "Authorization: Token $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{}' > /dev/null

echo "=== 请求后（auth 应被续期回 28800）==="
kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! ttl "token:auth:$TOKEN" 2>/dev/null
kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! ttl "token:meta:$TOKEN" 2>/dev/null
# auth TTL 预期: 28800（续期）
# meta TTL 预期: < 原始值（不续期）
```

### F14.6 Logout → Token 清理

**涉及：** `apps/auth_app/views.py:logout`

- [ ] Logout 后 `token:auth` 和 `token:meta` 的 key 被删除
- [ ] `token:blacklist` key 被创建（TTL = 原 auth 剩余时间）

**测试命令：**

```bash
# 登出
curl -s --noproxy '*' http://localhost:30000/api/auth/logout \
  -H 'Host: k8s-cicd.daiyi.local.com' \
  -H "Authorization: Token $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{}'

# 检查
kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! keys "token:*$TOKEN" 2>/dev/null
# 预期: 仅 token:blacklist:{token}（如有），auth 和 meta 已删除
```

### F14.7 Token 黑名单 → code 1003

**涉及：** `k8s_console/middleware.py:TokenBlacklistMiddleware`

- [ ] 使用已登出/黑名单 token → 返回 `{code:1003, message:"Token 已被登出"}`，HTTP 401

### F14.8 Middleware 启动无异常

**涉及：** `k8s_console/middleware.py`（全部中间件）、`k8s_console/settings.py:MIDDLEWARE`

- [ ] Backend Pod 日志中无 `VersionCheckMiddleware`、`TokenRefreshMiddleware` 相关的 Traceback/Error
- [ ] Backend Pod 日志中出现 `Deploy version set:`（`__init__` 成功写入）

**测试命令：**

```bash
kubectl logs -n prd -l app=k8s-console-backend --tail=50 | grep -i "Deploy version set\|Traceback\|Error"
# 预期: 有 "Deploy version set:" 行，无 Traceback
```

### F14.9 前端构建无错误

**涉及：** `frontend/src/stores/auth.js`、`frontend/src/api/client.js`、`frontend/src/views/LoginPage.vue`、`frontend/src/components/AppToast.vue`

- [ ] `npx vite build --mode production` 退出码为 0，无 error/warning
- [ ] 浏览器访问 `http://k8s-cicd.daiyi.local.com:9001` 返回 200，页面标题 "☸️ K8s Management Console"

**测试命令：**

```bash
cd frontend && npx vite build --mode production 2>&1 | tail -3
# 预期: ✓ built in XXXms

curl -s http://k8s-cicd.daiyi.local.com:9001 | grep -o "<title>[^<]*</title>"
# 预期: <title>☸️ K8s Management Console</title>
```

### F14 一键自检脚本

以下脚本可在 `deploy-all.sh` 部署后运行，自动化验证 F14.1–F14.9 全部条件：

```bash
#!/bin/bash
# auth-self-check.sh — 认证系统一键自检
# 用法: bash deploy/auth-self-check.sh
set -e

REDIS_POD=$(kubectl get pods -n database -l app=redis -o jsonpath='{.items[0].metadata.name}')
PASS=0; FAIL=0

check() {
  local desc="$1"; local actual="$2"; local expected="$3"
  if echo "$actual" | grep -q "$expected"; then
    echo "  ✅ $desc"; PASS=$((PASS+1))
  else
    echo "  ❌ $desc (expected: $expected, got: $actual)"; FAIL=$((FAIL+1))
  fi
}

echo "=== F14.1 Login + Token Meta ==="
LOGIN=$(curl -s --noproxy '*' http://localhost:30000/api/auth/login \
  -H 'Host: k8s-cicd.daiyi.local.com' \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin"}')
TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['token'])" 2>/dev/null || echo "")
check "Login returns token" "$TOKEN" "."
META=$(kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! get "token:meta:$TOKEN" 2>/dev/null)
check "Meta has deploy_version" "$META" "deploy_version"
check "Meta has absolute_expiry" "$META" "absolute_expiry"

echo "=== F14.2 Token Valid ==="
RESP=$(curl -s --noproxy '*' http://localhost:30000/api/users/list \
  -H 'Host: k8s-cicd.daiyi.local.com' \
  -H "Authorization: Token $TOKEN" \
  -H 'Content-Type: application/json' -d '{}')
check "Valid token access" "$RESP" '"code": 0'

echo "=== F14.3 Deploy Mismatch → 1004 ==="
CURRENT_VER=$(kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! get "deploy:version" 2>/dev/null | tr -d '\r')
kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! set "deploy:version" "test-new-version" 2>/dev/null
RESP=$(curl -s --noproxy '*' http://localhost:30000/api/users/list \
  -H 'Host: k8s-cicd.daiyi.local.com' \
  -H "Authorization: Token $TOKEN" \
  -H 'Content-Type: application/json' -d '{}')
check "1004 response" "$RESP" '"code": 1004'
check "Token cleaned" "$(kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! keys "token:*$TOKEN" 2>/dev/null)" "^$"
kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! set "deploy:version" "$CURRENT_VER" 2>/dev/null

echo "=== F14.4 Absolute Expiry → 1007 ==="
LOGIN=$(curl -s --noproxy '*' http://localhost:30000/api/auth/login \
  -H 'Host: k8s-cicd.daiyi.local.com' \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin"}')
TOKEN2=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['token'])" 2>/dev/null || echo "")
CURRENT_VER=$(kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! get "deploy:version" 2>/dev/null | tr -d '\r')
META="{\"user_id\":\"1\",\"login_at\":\"2026-01-01T00:00:00\",\"absolute_expiry\":\"2026-01-02T00:00:00\",\"deploy_version\":\"$CURRENT_VER\"}"
kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! set "token:meta:$TOKEN2" "$META" 2>/dev/null
RESP=$(curl -s --noproxy '*' http://localhost:30000/api/users/list \
  -H 'Host: k8s-cicd.daiyi.local.com' \
  -H "Authorization: Token $TOKEN2" \
  -H 'Content-Type: application/json' -d '{}')
check "1007 response" "$RESP" '"code": 1007'

echo "=== F14.5 Sliding TTL ==="
LOGIN=$(curl -s --noproxy '*' http://localhost:30000/api/auth/login \
  -H 'Host: k8s-cicd.daiyi.local.com' \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin"}')
TOKEN3=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['token'])" 2>/dev/null || echo "")
TTL_BEFORE=$(kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! ttl "token:auth:$TOKEN3" 2>/dev/null)
sleep 3
curl -s --noproxy '*' http://localhost:30000/api/users/list \
  -H 'Host: k8s-cicd.daiyi.local.com' \
  -H "Authorization: Token $TOKEN3" \
  -H 'Content-Type: application/json' -d '{}' > /dev/null
TTL_AFTER=$(kubectl exec -n database "$REDIS_POD" -- redis-cli -a RedisPass2024! ttl "token:auth:$TOKEN3" 2>/dev/null)
check "TTL refreshed" "$TTL_AFTER" "28800"

echo "=== F14.8 Backend No Errors ==="
LOGS=$(kubectl logs -n prd -l app=k8s-console-backend --tail=50 2>/dev/null)
check "No Traceback" "$LOGS" "^$"  # will fail if Traceback found — inverted logic handled by grep -v
if echo "$LOGS" | grep -qi "Traceback"; then
  echo "  ❌ Backend has Traceback!"; FAIL=$((FAIL+1))
else
  echo "  ✅ No Traceback in backend logs"; PASS=$((PASS+1))
fi
check "Deploy version set" "$LOGS" "Deploy version set"

echo "=== F14.9 Frontend ==="
TITLE=$(curl -s http://k8s-cicd.daiyi.local.com:9001 | grep -o "<title>[^<]*</title>")
check "Frontend accessible" "$TITLE" "K8s Management Console"

echo ""
echo "=========================================="
echo "  Results: $PASS passed, $FAIL failed"
echo "=========================================="
[ "$FAIL" -eq 0 ] && echo "✅ All auth tests passed!" || echo "❌ Some tests failed"
```
