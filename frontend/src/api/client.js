import axios from "axios";
import { useAuthStore } from "../stores/auth";

const client = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

/** Show a toast message before redirecting — dispatches custom event for AppToast */
function showToast(message, type = "error") {
  window.dispatchEvent(new CustomEvent("app-toast", { detail: { message, type } }));
}

client.interceptors.request.use((config) => {
  const auth = useAuthStore();
  // Pre-check: if token is expired, block the request early
  if (auth.token && auth.isExpired) {
    auth.clearAuth();
    showToast("登录已过期，请重新登录", "error");
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

      // Generic token invalid (1002) — force logout
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
