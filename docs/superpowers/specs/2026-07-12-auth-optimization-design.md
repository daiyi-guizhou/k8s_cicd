# 认证系统优化设计

## 日期
2026-07-12

## 目标

1. 前端登录 Token 8 小时滑动过期 + 24 小时绝对过期
2. 后端重新部署时，前端检测版本变化并提示用户退出
3. 前端本地预检 Token 过期，减少无效请求

---

## 变更清单

### 后端

| # | 文件 | 变更内容 |
|---|------|----------|
| 1 | `backend/apps/auth_app/views.py` | `login`: TTL 7天→8小时；新增 `token:meta:{token}` Hash 存储登录元信息 |
| 2 | `backend/k8s_console/middleware.py` | 新增 `VersionCheckMiddleware`：启动时写 `deploy:version`，请求时校验；新增 `TokenRefreshMiddleware`：滑动续期 + 绝对过期检测 |
| 3 | `backend/k8s_console/settings.py` | 注册新中间件（在 TokenBlacklistMiddleware 之后） |
| 4 | `backend/utils/response.py` | 新增错误码 `1004`（系统已更新）、`1007`（登录已过期） |

### 前端

| # | 文件 | 变更内容 |
|---|------|----------|
| 5 | `frontend/src/stores/auth.js` | 新增 `loginAt`、`absoluteExpiry` 字段，`isExpired` getter |
| 6 | `frontend/src/api/client.js` | 请求前预检过期；响应捕获 1004/1007 → 提示 + 退出 |
| 7 | `frontend/src/views/LoginPage.vue` | 接收路由 query `?reason=expired|updated`，展示对应提示 |

---

## 详细设计

### 1. Token 过期机制（8h 滑动 + 24h 绝对）

**Redis 数据结构：**

```
# 认证 token（8h TTL，每次 API 调用续期）
token:auth:{token} → "{user_id}"

# Token 元信息（24h 绝对过期，登录时写入，不续期）
token:meta:{token} → {
    "user_id": "1",
    "login_at": "2026-07-12T08:00:00",
    "absolute_expiry": "2026-07-13T08:00:00",  # login_at + 24h
    "deploy_version": "2026-07-12T10:30:00"
}
```

**登录时（`views.py:login`）：**
- `SETEX token:auth:{token} 28800 user_id`（8h = 28800s）
- `SETEX token:meta:{token} 86400 JSON `（24h = 86400s）
- JSON 包含 `user_id`、`login_at`、`absolute_expiry`、`deploy_version`

**每次 API 请求（`TokenRefreshMiddleware`）：**
- 检查 `token:meta:{token}.absolute_expiry` 是否已过期
  - 已过期 → 返回 `{code: 1007, message: "登录已过期，请重新登录"}` → 401
- 未过期 → `EXPIRE token:auth:{token} 28800`（续期 8h）

**登出时（`views.py:logout`）：**
- 同时删除 `token:auth:{token}` 和 `token:meta:{token}`
- 黑名单保持现有逻辑不变

### 2. 部署版本检测

**启动时（`VersionCheckMiddleware.__init__`）：**
- 生成部署版本号：当前时间戳 `datetime.now().isoformat()`
- `SETNX deploy:version {version}`（只在首次部署时设置）
- 如果 key 已存在，覆盖为新版本（表示重新部署）

**每次 API 请求（`VersionCheckMiddleware.__call__`）：**
- 从 `token:meta:{token}` 获取 `deploy_version`
- 从 Redis 获取当前 `deploy:version`
- 不匹配 → 返回 `{code: 1004, message: "系统已更新，请重新登录"}` → 401
- 登录接口（`/api/auth/login`）跳过此检查

**注意：** 此中间件只对已认证请求生效（有 Token 才检查），未登录的请求直接放行。

### 3. 前端本地预检

**Auth Store 新增字段：**
- `loginAt`：登录时间戳（ISO string），持久化到 localStorage
- `absoluteExpiry`：绝对过期时间（loginAt + 24h）
- Getter `isExpired`：`Date.now() > new Date(absoluteExpiry).getTime()`

**Axios 请求拦截器增强：**
- 请求前检查 `auth.isExpired`
  - 已过期 → 直接拒绝请求，`auth.clearAuth()`，跳转 `/login?reason=expired`

**Axios 响应拦截器增强（新增 code 处理）：**
- `code === 1004`（系统已更新）：Toast "系统已更新，请刷新页面后重新登录"，`clearAuth()`，跳转 `/login?reason=updated`
- `code === 1007`（登录已过期）：Toast "登录已过期，请重新登录"，`clearAuth()`，跳转 `/login?reason=expired`

### 4. 新增错误码

```python
ERR_DEPLOY_VERSION_MISMATCH = 1004  # 系统已更新
ERR_TOKEN_EXPIRED = 1007           # Token 已过期
```

### 5. 中间件顺序

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "k8s_console.middleware.VersionCheckMiddleware",     # 新增：版本检查
    "k8s_console.middleware.TokenRefreshMiddleware",     # 新增：token 续期 + 过期检测
    "k8s_console.middleware.AuditLoggerMiddleware",
    "k8s_console.middleware.TokenBlacklistMiddleware",
]
```

`VersionCheckMiddleware` 需要排在 `TokenRefreshMiddleware` 之前但应在审计日志之前执行。实际上两者都应在认证层之前完成，所以排在 `AuditLoggerMiddleware` 之前。

---

## 边界情况

| 场景 | 处理 |
|------|------|
| Redis 不可用时的新中间件 | try/except 包裹 Redis 操作，异常时放行（不影响业务） |
| 首次部署无 `deploy:version` | `VersionCheckMiddleware` 在 key 不存在时跳过检查 |
| Token meta key 过期（>24h） | `TokenRefreshMiddleware` 检查 meta 不存在时返回 1007 |
| 登录接口被版本中间件拦截 | 白名单 `/api/auth/login` 跳过版本检查 |
| 用户开多个 tab | 一个 tab 退出后 token 变为黑名单/被清除，其他 tab 下次请求会 401 |

---

## 不涉及

- 不修改 User model
- 不修改前端路由守卫（保持现有逻辑，新增的过期检测在拦截器层完成）
- 不修改 K8s 部署配置
- 不修改 Dockerfile
