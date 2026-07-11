# K8s Management Console — Frontend

Vue 3 单页面应用，K8s 集群管理的 Web 控制台。

## 技术栈

- Vue 3 + Vite
- Vue Router 4（页面路由）
- Pinia 2（状态管理）
- Axios（HTTP 请求）
- CodeMirror 6（YAML 编辑器）

## 页面结构

```
/                   📊 集群概览（Dashboard）
/resources/:type    📦 资源列表（13 种资源类型）
/apply              🛠 Apply YAML 在线编辑
/users              👤 用户管理（仅 admin）
/audit              📋 审计日志（仅 admin）
/login              🔐 登录页
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

### 3. 后端 API 代理

开发模式下，Vite 自动将 `/api` 请求代理到后端 `http://localhost:8000`。

如需修改后端地址，编辑 `vite.config.js`：

```js
server: {
  proxy: {
    "/api": {
      target: "http://localhost:8000",  // 修改为你的后端地址
      changeOrigin: true,
    },
  },
},
```

## 前后端联调

### 完整启动步骤

1. **启动 MySQL 和 Redis**（本地或 Docker）

```bash
# 如果用 Docker:
docker run -d --name mysql -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD=RootPass2024! \
  -e MYSQL_DATABASE=appdb \
  -e MYSQL_USER=appuser \
  -e MYSQL_PASSWORD=UserPass2024! \
  mysql:8.0

docker run -d --name redis -p 6379:6379 \
  -e REDIS_PASSWORD=RedisPass2024! \
  redis:7-alpine redis-server --requirepass RedisPass2024!
```

2. **启动后端**（参考 `backend/README.md`）

```bash
cd backend
pip install -r requirements.txt
python manage.py migrate --settings=k8s_console.settings_dev
python manage.py init_admin --settings=k8s_console.settings_dev
python manage.py runserver 0.0.0.0:8000 --settings=k8s_console.settings_dev
```

3. **启动前端**

```bash
cd frontend
npm install
npm run dev
```

4. **打开浏览器访问** `http://localhost:3000`

5. **使用 init_admin 输出的密码登录**

## 构建部署

```bash
npm run build
```

产出在 `dist/` 目录，由 Nginx 托管。

## Docker 构建

```bash
docker build -t k8s-console-frontend:latest .
```
