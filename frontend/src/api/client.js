import axios from "axios";
import { useAuthStore } from "../stores/auth";

const client = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

client.interceptors.request.use((config) => {
  const auth = useAuthStore();
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
    if (error.response) {
      const body = error.response.data;
      if (body && (body.code === 1002 || body.code === 1003)) {
        const auth = useAuthStore();
        auth.clearAuth();
        window.location.href = "/login";
      }
      const err = new Error(body?.message || error.message);
      err.code = body?.code;
      err.detail = body?.detail;
      throw err;
    }
    throw error;
  }
);

export default client;
