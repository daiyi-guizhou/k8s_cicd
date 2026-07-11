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
