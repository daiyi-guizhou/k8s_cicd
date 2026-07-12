# K8s Management Console — Frontend

Vue 3 单页面应用，K8s 集群管理的 Web 控制台。

## 技术栈

- Vue 3 + Vite
- Vue Router 4（页面路由）
- Pinia 2（状态管理）
- Axios（HTTP 请求）

## 页面结构

```
/                   📊 集群概览（Dashboard）
/resources          📦 统一资源管理（页面内选择 14 种资源类型）
/apply              🛠 Apply YAML 在线编辑
/users              👤 用户管理（仅 admin）
/audit              📋 审计日志（仅 admin）
/login              🔐 登录页
/clusters           🖥 集群管理（admin）
```

## 本地开发

### 前置条件

- Node.js 22+
- 后端已启动（默认 `http://localhost:8000`）

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

启动后访问 `http://localhost:3000`。

### 3. 后端 API 代理（Dev / Prd 配置）

项目通过 `.env` 文件区分开发和生产环境：

| 文件 | 环境 | 说明 |
|------|------|------|
| `.env.development` | `npm run dev` | Vite 启动时自动加载 |
| `.env.production` | `npm run build` | Vite build 时自动加载 |
| `.env.local` | 本地覆盖（不提交） | 可选，覆盖以上两个文件 |

**开发模式**（`npm run dev`）：
Vite 自动将 `/api` 请求代理到 `VITE_API_TARGET` 指定的后端地址：

```bash
# .env.development 默认值
VITE_API_TARGET=http://localhost:8000
```

如需让前端直连 K8s 部署的后端（跳过本地 Django），修改 `.env.local`：

```bash
# frontend/.env.local（本地覆盖，不提交 git）
VITE_API_TARGET=http://localhost:30000
```

**生产模式**（`npm run build`）：
无需 proxy —— K8s Ingress 按路径路由 `/api` → backend、`/` → frontend。nginx 只 serve 静态文件。

## 前后端联调

### 完整启动步骤

**1. 启动 MySQL 和 Redis**

本项目使用 K8s 集群 `database` namespace 中的 MySQL/Redis，本地开发通过 port-forward 暴露：

```bash
# 端口转发
kubectl port-forward -n database svc/mysql 3306:3306 &
kubectl port-forward -n database svc/redis 6379:6379 &
```

如果你本地已有 MySQL/Redis，确保连接参数与 `backend/k8s_console/settings_dev.py` 一致。

**2. 启动后端**（参考 `backend/README.md`）

```bash
cd backend

# 创建并激活 conda 环境
conda create -n k8s-console python=3.12 -y
conda activate k8s-console

# 安装 & 启动
pip install -r requirements.txt
python manage.py migrate --settings=k8s_console.settings_dev
python manage.py init_admin --settings=k8s_console.settings_dev
python manage.py runserver 0.0.0.0:8000 --settings=k8s_console.settings_dev
```

**3. 启动前端**

```bash
cd frontend
npm install
npm run dev
```

**4. 登录使用**

打开浏览器访问 `http://localhost:3000`，使用管理员账号登录：

| 用户名 | 密码 |
|--------|------|
| `admin` | `admin` |

> 首次部署时运行 `init_admin` 会生成随机密码，可通过 Django shell 手动重置为 `admin`。

### 联调架构

```
浏览器 (http://localhost:3000)
  │
  │  Vite dev server (port 3000)
  │  ├── /*         → 前端页面 (Vue SPA, HMR热更新)
  │  └── /api/*     → 代理到 http://localhost:8000
  │
  ▼
Django dev server (http://localhost:8000)
  │
  ├── MySQL  ← kubectl port-forward 3306 → K8s mysql.database.svc
  ├── Redis  ← kubectl port-forward 6379 → K8s redis.database.svc
  └── K8s API Server ← ~/.kube/config
```

## 页面功能说明

### 仪表盘 (Dashboard)
展示集群概况：Namespace、Deployment、Pod、Service、Ingress 的数量统计。

### 资源管理
统一页面 `/resources`，页面内通过下拉框选择 14 种资源类型。每种资源支持：
- **列表查看** — 按 namespace 过滤
- **资源名称模糊搜索** — 前端实时过滤
- **YAML 查看** — 只读弹窗 + 语法高亮 + 一键复制
- **Scale** — Deployment/StatefulSet 扩缩容（弹窗确认）
- **Rollback** — Deployment 版本回滚（可选指定 revision）
- **Delete** — 删除资源（需输入资源名确认）

> 集群级别资源（Namespace/ClusterRole/ClusterRoleBinding）自动隐藏 Namespace 列和 Namespace 筛选器。

### Apply YAML
左侧 YAML 编辑器 + 右侧 Apply 按钮和结果面板。支持在线编辑或粘贴 YAML，点击 Apply 提交到后端执行。

### 用户管理（admin only）
创建用户（随机初始密码）、启用/禁用、重置密码。

### 审计日志（admin only）
按操作类型、结果过滤，分页查看所有写操作记录。

## 操作安全设计

- **所有写操作**（scale / rollback / delete / apply / 用户管理）**均需二次确认**
- **Delete 操作**：必须输入完整的资源名称才能执行
- **Scale / Rollback / Apply**：点击确认按钮后执行
- **YAML 查看**：与 Apply 页分开，只读模式，避免误编辑
- **GET 请求不记录审计日志**，只有 POST 写操作记录

## 项目结构

```
frontend/
├── package.json
├── vite.config.js
├── index.html
├── nginx.conf                 # 生产环境 Nginx 配置
├── Dockerfile                 # 多阶段构建
└── src/
    ├── main.js                # Vue 入口
    ├── App.vue                # 根组件 (布局外壳)
    ├── styles/
    │   └── main.css           # 全局样式 + CSS变量
    ├── router/
    │   └── index.js           # Vue Router (含路由守卫)
    ├── stores/
    │   └── auth.js            # Pinia 认证状态管理
    ├── api/
    │   ├── client.js          # Axios 实例 (拦截器 + Token附加)
    │   ├── auth.js            # 登录/登出/改密
    │   ├── resources.js       # K8s 资源 CRUD
    │   ├── users.js           # 用户管理
    │   └── audit.js           # 审计日志
    ├── components/
    │   ├── AppSidebar.vue     # 左侧导航栏
    │   ├── AppToast.vue       # Toast 通知
    │   ├── ScaleModal.vue     # Scale 操作弹窗
    │   ├── DeleteModal.vue    # 删除确认弹窗（输入名称确认）
    │   ├── RollbackModal.vue  # Rollback 版本选择弹窗
    │   └── YamlModal.vue      # YAML 只读查看弹窗
    └── views/
        ├── LoginPage.vue       # 登录页
        ├── DashboardPage.vue   # 集群概览
        ├── ResourceListPage.vue # 统一资源管理（14种资源，页面内切换）
        ├── ApplyYamlPage.vue   # YAML 编辑器 + Apply
        ├── UserManagementPage.vue # 用户管理（admin）
        └── AuditLogPage.vue    # 审计日志（admin）
```

## Docker 构建

```bash
npm run build               # 构建到 dist/
docker build -t k8s-console-frontend:latest .
```
