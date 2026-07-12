import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "../stores/auth";

const routes = [
  {
    path: "/login",
    name: "Login",
    component: () => import("../views/LoginPage.vue"),
    meta: { requiresAuth: false },
  },
  {
    path: "/",
    name: "Dashboard",
    component: () => import("../views/DashboardPage.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/resources",
    name: "Resources",
    component: () => import("../views/ResourceListPage.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/apply",
    name: "ApplyYaml",
    component: () => import("../views/ApplyYamlPage.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/clusters",
    name: "ClusterManagement",
    component: () => import("../views/ClusterManagementPage.vue"),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    path: "/users",
    name: "UserManagement",
    component: () => import("../views/UserManagementPage.vue"),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    path: "/audit",
    name: "AuditLog",
    component: () => import("../views/AuditLogPage.vue"),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, from, next) => {
  const auth = useAuthStore();
  if (to.meta.requiresAuth !== false && !auth.token) {
    next("/login");
  } else if (to.path === "/login" && auth.token) {
    next("/");
  } else if (to.meta.requiresAdmin && auth.user?.role !== "admin") {
    next("/");
  } else {
    next();
  }
});

export default router;
