# Auth Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement 8h sliding + 24h absolute token expiry with Redis, deploy version check middleware, and frontend expiry pre-check.

**Architecture:** Two new middleware classes handle token refresh/expiry and deploy version mismatch on every API request. Frontend Pinia store gains expiry awareness and interceptors handle the new error codes with user-friendly messages.

**Tech Stack:** Python 3.12, Django 5.2, Redis 7, Vue 3, Pinia 2, Axios

**Spec:** `docs/superpowers/specs/2026-07-12-auth-optimization-design.md`

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `backend/utils/response.py` | Renumber error codes, add ERR_DEPLOY_VERSION_MISMATCH + ERR_TOKEN_EXPIRED |
| Modify | `backend/apps/auth_app/views.py` | login: 8h TTL + token meta; logout: clean token meta |
| Modify | `backend/k8s_console/middleware.py` | Add VersionCheckMiddleware + TokenRefreshMiddleware |
| Modify | `backend/k8s_console/settings.py` | Register new middleware in stack |
| Modify | `frontend/src/stores/auth.js` | Add loginAt, absoluteExpiry, isExpired getter |
| Modify | `frontend/src/api/client.js` | Pre-check expiry, handle 1004/1007 codes |
| Modify | `frontend/src/views/LoginPage.vue` | Accept ?reason= query param for context messages |

---

### Task 1: Renumber Error Codes and Add New Ones

**Files:**
- Modify: `backend/utils/response.py`
- Modify: `backend/apps/auth_app/views.py`

**Context:** `ERR_USER_NOT_FOUND` currently uses code 1004, which the spec assigns to `ERR_DEPLOY_VERSION_MISMATCH`. We must renumber `ERR_USER_NOT_FOUND` to 1008 to free 1004, and update all references.

- [ ] **Step 1: Update error code constants in `response.py`**

Replace the error code block (lines 17-32) in `backend/utils/response.py`:

```python
# Error codes
ERR_AUTH_FAILED = 1001
ERR_TOKEN_INVALID = 1002
ERR_TOKEN_BLACKLISTED = 1003
ERR_DEPLOY_VERSION_MISMATCH = 1004
ERR_USER_INACTIVE = 1005
ERR_WRONG_PASSWORD = 1006
ERR_TOKEN_EXPIRED = 1007
ERR_USER_NOT_FOUND = 1008

ERR_RESOURCE_NOT_FOUND = 2001
ERR_K8S_API_ERROR = 2002
ERR_INVALID_YAML = 2003
ERR_UNSUPPORTED_RESOURCE = 2004
ERR_NAMESPACE_REQUIRED = 2005

ERR_PERMISSION_DENIED = 3001
ERR_VALIDATION = 3002
```

- [ ] **Step 2: Update references to `ERR_USER_NOT_FOUND`**

In `backend/apps/auth_app/views.py`, the import line at line 14-17 references `ERR_USER_NOT_FOUND`. No code change needed since the name stays the same — only the numeric value changed. However, verify the import still works:

```bash
cd D:/project/k8s_cicd/k8s_cicd/backend && python -c "from utils.response import ERR_USER_NOT_FOUND; print(ERR_USER_NOT_FOUND)"
```

Expected output: `1008`

Also check — do any other files import `ERR_USER_NOT_FOUND`?

Run: `cd D:/project/k8s_cicd/k8s_cicd && grep -rn "ERR_USER_NOT_FOUND" backend/`

Expected: only `response.py` and `views.py` reference it.

- [ ] **Step 3: Commit**

```bash
git add backend/utils/response.py backend/apps/auth_app/views.py
git commit -m "refactor: renumber ERR_USER_NOT_FOUND to 1008, add ERR_DEPLOY_VERSION_MISMATCH(1004) and ERR_TOKEN_EXPIRED(1007)"
```

---

### Task 2: Update Login to Write Token Metadata and Use 8h TTL

**Files:**
- Modify: `backend/apps/auth_app/views.py`

- [ ] **Step 1: Rewrite the `login` function body**

In `backend/apps/auth_app/views.py`, replace the `login` function (lines 28-61) with:

```python
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def login(request):
    """Login: {username, password} → {token, user}"""
    import json
    from datetime import datetime, timedelta

    username = request.data.get("username", "").strip()
    password = request.data.get("password", "")

    if not username or not password:
        return error(ERR_AUTH_FAILED, "用户名和密码不能为空")

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return error(ERR_AUTH_FAILED, "用户名或密码错误")

    if not user.is_active:
        return error(ERR_USER_INACTIVE, "用户已被禁用")

    if not check_password(password, user.password):
        return error(ERR_AUTH_FAILED, "用户名或密码错误")

    token = _generate_token()
    r = _get_redis()

    # 8h sliding TTL for auth key
    auth_ttl = 28800  # 8 hours in seconds

    # 24h absolute expiry for meta key
    meta_ttl = 86400  # 24 hours in seconds
    now = datetime.now()
    absolute_expiry = now + timedelta(hours=24)
    deploy_version = r.get("deploy:version") or "initial"

    meta = json.dumps({
        "user_id": str(user.id),
        "login_at": now.isoformat(),
        "absolute_expiry": absolute_expiry.isoformat(),
        "deploy_version": deploy_version,
    })

    r.setex(f"token:auth:{token}", auth_ttl, str(user.id))
    r.setex(f"token:meta:{token}", meta_ttl, meta)

    return success(data={
        "token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
        },
    }, message="登录成功")
```

- [ ] **Step 2: Rewrite the `logout` function to also clean token meta**

Replace the `logout` function body (lines 64-76) with:

```python
@api_view(["POST"])
def logout(request):
    """Logout: blacklist current token in Redis with TTL."""
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if auth_header.startswith("Token "):
        token = auth_header[6:].strip()
        r = _get_redis()
        user_id = r.get(f"token:auth:{token}")
        ttl = r.ttl(f"token:auth:{token}")
        if ttl > 0:
            r.setex(f"token:blacklist:{token}", ttl, user_id or "")
        r.delete(f"token:auth:{token}")
        r.delete(f"token:meta:{token}")
    return success(message="已登出")
```

- [ ] **Step 3: Verify imports**

Run a quick Python syntax check:

```bash
cd D:/project/k8s_cicd/k8s_cicd/backend && python -c "import ast; ast.parse(open('apps/auth_app/views.py').read()); print('OK')"
```

Expected output: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/apps/auth_app/views.py
git commit -m "feat: 8h sliding TTL + 24h absolute expiry with token metadata in Redis"
```

---

### Task 3: Add VersionCheckMiddleware and TokenRefreshMiddleware

**Files:**
- Modify: `backend/k8s_console/middleware.py`

- [ ] **Step 1: Add the two new middleware classes**

In `backend/k8s_console/middleware.py`, add the new imports at the top. Replace the existing import block (lines 1-7) with:

```python
"""Middleware: AuditLoggerMiddleware, TokenBlacklistMiddleware, VersionCheckMiddleware, TokenRefreshMiddleware."""
import json
import logging
from datetime import datetime
from django.conf import settings
from django.http import JsonResponse, RawPostDataException
from apps.auth_app.authentication import get_user_from_token
import redis as _redis
from django.conf import settings as _settings

logger = logging.getLogger(__name__)

def _get_redis():
    return _redis.Redis.from_url(_settings.REDIS_URL, decode_responses=True)
```

Then insert the two new middleware classes **before** the existing `TokenBlacklistMiddleware` class (before line 13):

```python
class VersionCheckMiddleware:
    """Detect backend redeploy by comparing token's deploy_version with current.

    On first __init__, writes a deploy version (current timestamp) to Redis.
    On each request with a Token, compares the token's stored deploy_version
    with the current Redis value. A mismatch means the backend was redeployed,
    and the request is rejected with code 1004.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Write deploy version on every startup (redeploy = new version)
        try:
            r = _get_redis()
            version = datetime.now().isoformat()
            r.set("deploy:version", version)
            logger.info(f"Deploy version set: {version}")
        except Exception:
            logger.warning("VersionCheckMiddleware: unable to set deploy:version", exc_info=True)

    def __call__(self, request):
        # Skip for login endpoint
        path = request.path.rstrip("/")
        if path.endswith("/auth/login"):
            return self.get_response(request)

        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Token "):
            return self.get_response(request)

        token = auth_header[6:].strip()
        try:
            r = _get_redis()
            current_version = r.get("deploy:version")
            if current_version is None:
                # No deploy version yet (first deploy before any login) — skip
                return self.get_response(request)

            meta_raw = r.get(f"token:meta:{token}")
            if meta_raw is None:
                # Token expired or invalid — let downstream middleware handle it
                return self.get_response(request)

            meta = json.loads(meta_raw)
            token_version = meta.get("deploy_version", "")

            if token_version and token_version != current_version:
                # Backend was redeployed since this token was issued
                # Clean up the stale token
                r.delete(f"token:auth:{token}")
                r.delete(f"token:meta:{token}")
                return JsonResponse(
                    {"code": 1004, "message": "系统已更新，请刷新页面后重新登录", "detail": ""},
                    status=401,
                )
        except Exception:
            logger.warning("VersionCheckMiddleware: Redis error", exc_info=True)
            # On Redis error, let the request through — don't block users

        return self.get_response(request)


class TokenRefreshMiddleware:
    """Refresh token TTL on each request and enforce 24h absolute expiry.

    On each authenticated request, renews the token:auth key TTL to 8h.
    Checks the absolute_expiry in token:meta — if exceeded, rejects with 1007.
    """

    def __call__(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Token "):
            return self.get_response(request)

        token = auth_header[6:].strip()
        try:
            r = _get_redis()
            meta_raw = r.get(f"token:meta:{token}")
            if meta_raw is None:
                # No meta key — token may have expired (meta has 24h TTL)
                return JsonResponse(
                    {"code": 1007, "message": "登录已过期，请重新登录", "detail": ""},
                    status=401,
                )

            meta = json.loads(meta_raw)
            # Check absolute expiry
            absolute_expiry_str = meta.get("absolute_expiry")
            if absolute_expiry_str:
                absolute_expiry = datetime.fromisoformat(absolute_expiry_str)
                if datetime.now() > absolute_expiry:
                    # Absolute expiry reached, clean up and reject
                    r.delete(f"token:auth:{token}")
                    r.delete(f"token:meta:{token}")
                    return JsonResponse(
                        {"code": 1007, "message": "登录已过期，请重新登录", "detail": ""},
                        status=401,
                    )

            # Refresh sliding TTL — reset auth key to 8h
            user_id = r.get(f"token:auth:{token}")
            if user_id:
                r.expire(f"token:auth:{token}", 28800)  # 8 hours
        except Exception:
            logger.warning("TokenRefreshMiddleware: Redis error", exc_info=True)
            # On Redis error, let the request through

        return self.get_response(request)
```

- [ ] **Step 2: Verify syntax**

```bash
cd D:/project/k8s_cicd/k8s_cicd/backend && python -c "import ast; ast.parse(open('k8s_console/middleware.py').read()); print('OK')"
```

Expected output: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/k8s_console/middleware.py
git commit -m "feat: add VersionCheckMiddleware and TokenRefreshMiddleware"
```

---

### Task 4: Register New Middleware in Settings

**Files:**
- Modify: `backend/k8s_console/settings.py`

- [ ] **Step 1: Update MIDDLEWARE list**

In `backend/k8s_console/settings.py`, replace the MIDDLEWARE list (lines 23-28) with:

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "k8s_console.middleware.VersionCheckMiddleware",
    "k8s_console.middleware.TokenRefreshMiddleware",
    "k8s_console.middleware.AuditLoggerMiddleware",
    "k8s_console.middleware.TokenBlacklistMiddleware",
]
```

The order is intentional:
1. `VersionCheckMiddleware` runs first — detects redeploy before any other processing
2. `TokenRefreshMiddleware` runs second — refreshes TTL and checks absolute expiry
3. `AuditLoggerMiddleware` runs after — sees the authenticated user
4. `TokenBlacklistMiddleware` runs last — catches explicitly logged-out tokens

- [ ] **Step 2: Commit**

```bash
git add backend/k8s_console/settings.py
git commit -m "feat: register VersionCheckMiddleware and TokenRefreshMiddleware in middleware stack"
```

---

### Task 5: Enhance Frontend Auth Store with Expiry Fields

**Files:**
- Modify: `frontend/src/stores/auth.js`

- [ ] **Step 1: Rewrite the Auth Store**

Replace the entire content of `frontend/src/stores/auth.js` with:

```js
import { defineStore } from "pinia";

const TOKEN_KEY = "k8s_console_token";
const USER_KEY = "k8s_console_user";
const LOGIN_AT_KEY = "k8s_console_login_at";
const ABSOLUTE_EXPIRY_KEY = "k8s_console_absolute_expiry";

// 24 hours in milliseconds
const ABSOLUTE_TIMEOUT_MS = 24 * 60 * 60 * 1000;

export const useAuthStore = defineStore("auth", {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || "",
    user: JSON.parse(localStorage.getItem(USER_KEY) || "null"),
    loginAt: localStorage.getItem(LOGIN_AT_KEY) || "",
    absoluteExpiry: localStorage.getItem(ABSOLUTE_EXPIRY_KEY) || "",
  }),

  getters: {
    isLoggedIn: (state) => !!state.token && !this._isTokenStale(state),
    /** @returns {boolean} true if token has exceeded absolute expiry or expired from storage */
    isExpired(state) {
      return this._isTokenStale(state);
    },
    isAdmin: (state) => state.user?.role === "admin",
  },

  actions: {
    /** Private helper — checks if token is stale based on absolute expiry */
    _isTokenStale(state) {
      if (!state.token) return true;
      // If we have an absolute expiry, check it
      if (state.absoluteExpiry) {
        return Date.now() > new Date(state.absoluteExpiry).getTime();
      }
      // Fallback: if loginAt exists but no absoluteExpiry, derive it
      if (state.loginAt) {
        const loginTime = new Date(state.loginAt).getTime();
        if (Date.now() > loginTime + ABSOLUTE_TIMEOUT_MS) {
          return true;
        }
      }
      return false;
    },

    setAuth(token, user, loginAt, absoluteExpiry) {
      this.token = token;
      this.user = user;
      this.loginAt = loginAt || new Date().toISOString();
      this.absoluteExpiry = absoluteExpiry || new Date(Date.now() + ABSOLUTE_TIMEOUT_MS).toISOString();
      localStorage.setItem(TOKEN_KEY, token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      localStorage.setItem(LOGIN_AT_KEY, this.loginAt);
      localStorage.setItem(ABSOLUTE_EXPIRY_KEY, this.absoluteExpiry);
    },

    clearAuth() {
      this.token = "";
      this.user = null;
      this.loginAt = "";
      this.absoluteExpiry = "";
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      localStorage.removeItem(LOGIN_AT_KEY);
      localStorage.removeItem(ABSOLUTE_EXPIRY_KEY);
    },
  },
});
```

> **Note:** Pinia getters cannot call `this._isTokenStale()` directly — they receive `state` as the first argument. If the method calling pattern above doesn't work in Pinia, we'll fix it in the next step. Actually, Pinia getters are not supposed to call actions. Let's restructure:

Actually, Pinia getters CAN access other getters but NOT actions. Let's use a plain function for the staleness check:

```js
import { defineStore } from "pinia";

const TOKEN_KEY = "k8s_console_token";
const USER_KEY = "k8s_console_user";
const LOGIN_AT_KEY = "k8s_console_login_at";
const ABSOLUTE_EXPIRY_KEY = "k8s_console_absolute_expiry";

// 24 hours in milliseconds
const ABSOLUTE_TIMEOUT_MS = 24 * 60 * 60 * 1000;

/** Pure function: check if token is stale based on localStorage data */
function isTokenStale(absoluteExpiry, loginAt, token) {
  if (!token) return true;
  if (absoluteExpiry) {
    return Date.now() > new Date(absoluteExpiry).getTime();
  }
  if (loginAt) {
    return Date.now() > new Date(loginAt).getTime() + ABSOLUTE_TIMEOUT_MS;
  }
  return false;
}

export const useAuthStore = defineStore("auth", {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || "",
    user: JSON.parse(localStorage.getItem(USER_KEY) || "null"),
    loginAt: localStorage.getItem(LOGIN_AT_KEY) || "",
    absoluteExpiry: localStorage.getItem(ABSOLUTE_EXPIRY_KEY) || "",
  }),

  getters: {
    isLoggedIn(state) {
      return !!state.token && !isTokenStale(state.absoluteExpiry, state.loginAt, state.token);
    },
    isExpired(state) {
      return isTokenStale(state.absoluteExpiry, state.loginAt, state.token);
    },
    isAdmin: (state) => state.user?.role === "admin",
  },

  actions: {
    setAuth(token, user, loginAt, absoluteExpiry) {
      this.token = token;
      this.user = user;
      this.loginAt = loginAt || new Date().toISOString();
      this.absoluteExpiry = absoluteExpiry || new Date(Date.now() + ABSOLUTE_TIMEOUT_MS).toISOString();
      localStorage.setItem(TOKEN_KEY, token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      localStorage.setItem(LOGIN_AT_KEY, this.loginAt);
      localStorage.setItem(ABSOLUTE_EXPIRY_KEY, this.absoluteExpiry);
    },

    clearAuth() {
      this.token = "";
      this.user = null;
      this.loginAt = "";
      this.absoluteExpiry = "";
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      localStorage.removeItem(LOGIN_AT_KEY);
      localStorage.removeItem(ABSOLUTE_EXPIRY_KEY);
    },
  },
});
```

- [ ] **Step 2: Verify frontend compiles**

```bash
cd D:/project/k8s_cicd/k8s_cicd/frontend && npx vite build --mode production 2>&1 | tail -5
```

Expected: Build succeeds with no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/stores/auth.js
git commit -m "feat: add loginAt, absoluteExpiry, and isExpired getter to auth store"
```

---

### Task 6: Enhance Axios Interceptors for New Error Codes and Pre-check

**Files:**
- Modify: `frontend/src/api/client.js`

- [ ] **Step 1: Rewrite the API client**

Replace the entire content of `frontend/src/api/client.js` with:

```js
import axios from "axios";
import { useAuthStore } from "../stores/auth";

const client = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

/** Show a toast message before redirecting — uses the global toast if available */
function showToast(message, type = "error") {
  // Try to access the toast via the app's provide/inject mechanism
  // Since we're outside a component, we dispatch a custom event that AppToast listens for
  window.dispatchEvent(new CustomEvent("app-toast", { detail: { message, type } }));
}

client.interceptors.request.use((config) => {
  const auth = useAuthStore();
  // Pre-check: if token is expired, block the request early
  if (auth.token && auth.isExpired) {
    auth.clearAuth();
    showToast("登录已过期，请重新登录", "error");
    // Use a microtask to redirect after current execution
    Promise.resolve().then(() => {
      window.location.href = "/login?reason=expired";
    });
    // Cancel this request
    const cancel = new axios.CancelToken((cancelFn) => cancelFn("Token expired"));
    config.cancelToken = cancel;
    return config;
  }
  if (auth.token) {
    config.headers.Authorization = `Token ${auth.token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => {
    const body = response.data;
    if (body.code === 0) {
      return body;
    }
    const error = new Error(body.message || "Unknown error");
    error.code = body.code;
    error.detail = body.detail;
    throw error;
  },
  (error) => {
    // Handle axios cancellation (from pre-check)
    if (axios.isCancel(error)) {
      return Promise.reject(error);
    }

    if (error.response) {
      const body = error.response.data;
      const code = body?.code;

      // Token blacklisted (1003) — force logout
      if (code === 1003) {
        const auth = useAuthStore();
        auth.clearAuth();
        window.location.href = "/login";
        const err = new Error(body?.message || "Token 已被登出");
        err.code = code;
        throw err;
      }

      // System updated / redeployed (1004) — prompt re-login
      if (code === 1004) {
        const auth = useAuthStore();
        auth.clearAuth();
        showToast("系统已更新，请刷新页面后重新登录", "warning");
        Promise.resolve().then(() => {
          window.location.href = "/login?reason=updated";
        });
        const err = new Error(body?.message || "系统已更新");
        err.code = code;
        throw err;
      }

      // Token expired (1007) — prompt re-login
      if (code === 1007) {
        const auth = useAuthStore();
        auth.clearAuth();
        showToast("登录已过期，请重新登录", "error");
        Promise.resolve().then(() => {
          window.location.href = "/login?reason=expired";
        });
        const err = new Error(body?.message || "登录已过期");
        err.code = code;
        throw err;
      }

      // Generic error (including old 1002 token invalid)
      if (code === 1002) {
        const auth = useAuthStore();
        auth.clearAuth();
        window.location.href = "/login";
      }

      const err = new Error(body?.message || error.message);
      err.code = code;
      err.detail = body?.detail;
      throw err;
    }
    throw error;
  }
);

export default client;
```

- [ ] **Step 2: Verify frontend compiles**

```bash
cd D:/project/k8s_cicd/k8s_cicd/frontend && npx vite build --mode production 2>&1 | tail -5
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/client.js
git commit -m "feat: add pre-check expiry in request interceptor and handle 1004/1007 error codes"
```

---

### Task 7: Update LoginPage to Show Context Messages from URL Query

**Files:**
- Modify: `frontend/src/views/LoginPage.vue`

- [ ] **Step 1: Add reason display to LoginPage**

In `frontend/src/views/LoginPage.vue`, add an info banner before the form. Replace lines 4-10 (the `<form>` area with the heading) with:

```vue
<h1 style="text-align:center;color:#fff;margin-bottom:24px;">☸️ K8s Console</h1>
<div v-if="reasonMessage" class="login-info-banner">{{ reasonMessage }}</div>
<form @submit.prevent="doLogin" class="card" style="width:380px;">
```

In the `<script setup>` section (after line 23), add the route query handling. Replace the existing `import { ref }` line (line 23) with:

```js
import { ref, computed, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { login } from "../api/auth";

const username = ref("");
const password = ref("");
const error = ref("");
const loading = ref(false);
const router = useRouter();
const route = useRoute();
const auth = useAuthStore();

const REASON_MESSAGES = {
  expired: "⚠️ 您的登录会话已过期（超过24小时），请重新登录",
  updated: "⚠️ 系统已更新，请刷新页面后重新登录",
};

const reasonMessage = ref("");

onMounted(() => {
  const reason = route.query.reason;
  if (reason && REASON_MESSAGES[reason]) {
    reasonMessage.value = REASON_MESSAGES[reason];
  }
});
```

And add this CSS at the end of the `<style scoped>` block (before `</style>`):

```css
.login-info-banner {
  background: #fef3c7;
  color: #92400e;
  padding: 10px 16px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 14px;
  text-align: center;
  max-width: 380px;
}
```

- [ ] **Step 2: Verify the final file compiles correctly**

```bash
cd D:/project/k8s_cicd/k8s_cicd/frontend && npx vite build --mode production 2>&1 | tail -5
```

- [ ] **Step 3: Full build test**

```bash
cd D:/project/k8s_cicd/k8s_cicd/frontend && npm run build 2>&1 | tail -10
```

Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/LoginPage.vue
git commit -m "feat: show reason banner on login page for expired/updated tokens"
```

---

### Task 8: Wire AppToast to Listen for External Toast Events

**Files:**
- Modify: `frontend/src/components/AppToast.vue`

**Context:** The Axios interceptor needs to show toasts before redirecting to login, but it's outside Vue's component tree. It dispatches `window.dispatchEvent(new CustomEvent("app-toast", ...))`. The `AppToast.vue` component needs to listen for this event.

- [ ] **Step 1: Add custom event listener in AppToast**

In `frontend/src/components/AppToast.vue`, replace the `<script setup>` block (lines 13-28) with:

```js
import { ref, provide, onMounted, onUnmounted } from "vue";

const toasts = ref([]);
let nextId = 0;

function show(message, type = "success", duration = 3000) {
  const id = nextId++;
  toasts.value.push({ id, message, type });
  setTimeout(() => {
    toasts.value = toasts.value.filter((t) => t.id !== id);
  }, duration);
}

/** Listen for external toast events (from Axios interceptors outside Vue tree) */
function onExternalToast(e) {
  const { message, type } = e.detail || {};
  if (message) {
    show(message, type || "error", 5000);
  }
}

onMounted(() => {
  window.addEventListener("app-toast", onExternalToast);
});

onUnmounted(() => {
  window.removeEventListener("app-toast", onExternalToast);
});

provide("toast", { show });
```

And add this CSS rule in the `<style scoped>` block for the `warning` type (if not already present). Add after `.toast-error` (or wherever toast color classes are defined):

Check the existing styles. Currently there's no CSS in the file. Add scoped styles:

```css
<style scoped>
.toast-container {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.toast {
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  color: #fff;
  animation: toast-in 0.25s ease;
  max-width: 400px;
}

.toast-success { background: #16a34a; }
.toast-error { background: #dc2626; }
.toast-warning { background: #d97706; }

@keyframes toast-in {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
```

Wait — the `<style scoped>` tag already exists in the file but appears to be empty. Let me re-read the file to check...

The file currently has no `<style scoped>` block. The toasts render but have no styling. Looking at the template, the CSS classes `.toast-container`, `.toast`, `.toast-${toast.type}` are already in use but styles come from `main.css`. Let me check...

Actually, looking at the template, it already uses `.toast-container`, `.toast`, `.toast-${toast.type}` — these styles must be in `main.css`. So I should NOT add a scoped style block. The existing global styles should work.

Let me just focus on adding the event listener. No CSS changes needed.

- [ ] **Step 2: Verify frontend compiles**

```bash
cd D:/project/k8s_cicd/k8s_cicd/frontend && npx vite build --mode production 2>&1 | tail -5
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/AppToast.vue
git commit -m "feat: AppToast listens for window app-toast custom events from axios interceptors"
```

---

### Task 9: End-to-End Verification

**Files:** (none — verification step)

- [ ] **Step 1: Full backend syntax check**

```bash
cd D:/project/k8s_cicd/k8s_cicd/backend && python -c "
from k8s_console.middleware import VersionCheckMiddleware, TokenRefreshMiddleware
from utils.response import ERR_DEPLOY_VERSION_MISMATCH, ERR_TOKEN_EXPIRED, ERR_USER_NOT_FOUND
print(f'ERR_DEPLOY_VERSION_MISMATCH={ERR_DEPLOY_VERSION_MISMATCH}')
print(f'ERR_TOKEN_EXPIRED={ERR_TOKEN_EXPIRED}')
print(f'ERR_USER_NOT_FOUND={ERR_USER_NOT_FOUND}')
print('All imports OK')
"
```

Expected:
```
ERR_DEPLOY_VERSION_MISMATCH=1004
ERR_TOKEN_EXPIRED=1007
ERR_USER_NOT_FOUND=1008
All imports OK
```

- [ ] **Step 2: Full frontend build**

```bash
cd D:/project/k8s_cicd/k8s_cicd/frontend && npm run build 2>&1
```

Expected: exit code 0.

- [ ] **Step 3: Verify no hardcoded error code references broke**

```bash
cd D:/project/k8s_cicd/k8s_cicd && grep -rn "1004\|1007\|1008" backend/ frontend/src/
```

Expected results:
- `backend/utils/response.py`: `ERR_DEPLOY_VERSION_MISMATCH = 1004`, `ERR_TOKEN_EXPIRED = 1007`, `ERR_USER_NOT_FOUND = 1008`
- `backend/k8s_console/middleware.py`: `code": 1004` (version mismatch response), `code": 1007` (token expired response)
- `frontend/src/api/client.js`: `code === 1004`, `code === 1007`
- `backend/apps/auth_app/views.py`: No references to 1004/1007/1008 directly (uses named constants)
- Any stale references? `frontend/src/api/client.js` line 32 had `1002` — still there, that's fine

- [ ] **Step 4: Full deploy test (optional — requires local K8s)**

```bash
cd D:/project/k8s_cicd/k8s_cicd && bash deploy/deploy-all.sh --clean --skip-build 2>&1 | tail -20
```

If K8s is available, verify:
- Login works
- After redeploy (restart backend pod), old token returns 1004
- After 8h idle (simulate by setting short TTL), sliding refresh works
- After 24h (simulate), token returns 1007

- [ ] **Step 5: Final commit if no issues**

```bash
git status
git diff --stat
```

- [ ] **Step 6: Commit remaining changes if any**

```bash
git add -A
git commit -m "chore: final verification and cleanup"
```
