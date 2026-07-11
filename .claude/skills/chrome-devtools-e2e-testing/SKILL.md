---
name: chrome-devtools-e2e-testing
description: 用于需要执行自动化浏览器测试、验证前端行为、端到端测试 UI 流程、或为此 Django+Vue 项目配置 ChromeDevTools MCP 的场景。触发词包括 "e2e 测试"、"浏览器测试"、"UI 测试"、"自动化测试"、"ChromeDevTools"、"测试前端"、"验证界面"、"冒烟测试"。
---

# ChromeDevTools MCP 端到端测试

## 概述

通过 ChromeDevTools MCP 驱动真实浏览器，对此 K8s 管理控制台 (Django + Vue 3) 执行端到端测试。

## 核心规则

**本文档定义的是"怎么维护测试"的流程，功能点和验收条件记录在 `docs/e2e-test-conditions.md` 中。**

```
你（Claude）的职责：
  1. 每次涉及前端功能变更时 → 更新 docs/e2e-test-conditions.md
  2. 每次被要求执行测试时  → 读取 docs/e2e-test-conditions.md，按其中的验收条件执行
  3. 发现实际行为与条件不符 → 报告差异，不静默修改条件
```

## 文件关系

```
.claude/skills/chrome-devtools-e2e-testing/SKILL.md    ← 本文件：流程与规范
docs/e2e-test-conditions.md                            ← 功能与验收条件（你维护它）
```

- SKILL.md 告诉你**什么时候**去读/写 `docs/e2e-test-conditions.md`
- `docs/e2e-test-conditions.md` 告诉你**测什么**

## 何时更新功能与验收条件

以下情况必须更新 `docs/e2e-test-conditions.md`：

| 触发条件 | 操作 |
|---------|------|
| 新增页面或组件 | 追加新功能条目和验收条件 |
| 修改现有 UI 行为 | 更新对应条目的描述 |
| 修改文案、提示语 | 同步更新条件中的预期文案 |
| 新增 API 端点 | 追加对应功能条目 |
| 删除功能 | 移除对应条目 |
| 修改路由或权限 | 更新路由守卫和权限相关条件 |

**原则：代码改了什么，条件文件就跟进什么。两者同步是强制要求，不能只改代码不更新条件。**

## 如何执行测试

当被要求执行测试时：

### 1. 准备工作

- 确认前后端服务在运行：
  ```bash
  # 后端
  cd backend && conda activate k8s-console
  python manage.py runserver 0.0.0.0:8000 --settings=k8s_console.settings_dev

  # 前端
  cd frontend && npm run dev
  ```
- 确认 MySQL/Redis 端口转发就绪
- 确认 ChromeDevTools MCP 可用

### 2. 读取条件文件

打开 `docs/e2e-test-conditions.md`，获取当前的验收条件列表。

### 3. 执行验证

按条件条目逐项验证。使用 ChromeDevTools MCP 工具：

| 工具 | 用途 |
|------|------|
| `navigate_page` | 导航到 URL |
| `take_snapshot` | 获取页面结构快照（文本 + uid） |
| `click` | 点击元素 |
| `fill` | 填入文本 |
| `wait_for` | 等待异步内容渲染 |
| `evaluate_script` | 执行 JS（检查 localStorage、URL 等） |

**关键约束：**

- 每次操作前必须重新 `take_snapshot`（uid 每次快照后刷新）
- 异步内容先 `wait_for` 再交互
- 弹窗关闭方式：点击遮罩层 → 关闭按钮 → JS 关闭
- 破坏性操作（Delete、禁用等）仅验证交互逻辑，不实际提交

### 4. 报告结果

按条件逐项报告结果，格式：

```
F1 登录
  ✅ 未登录自动跳转 /login
  ✅ 正确账号登录后跳转 /
  ❌ 空密码提交未显示错误提示 —— 实际：按钮无响应，期望：显示 "请输入用户名和密码"
```

## 测试环境信息

| 配置项 | 值 |
|-------|-----|
| 前端地址 | `http://localhost:3000` |
| 后端地址 | `http://localhost:8000` |
| 测试账号 | `admin` / `admin` |
| 前端技术栈 | Vue 3 + Vite + Vue Router 4 + Pinia 2 + Axios |
| 后端技术栈 | Django 5.2 + DRF 3.16 + MySQL 8.0 + Redis 7 |

### MCP 配置

首次使用需在 `~/.claude/mcp.json` 中添加：

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "@anthropic/chrome-devtools-mcp"]
    }
  }
}
```

## 项目 UI 结构速查

```
http://localhost:3000/
├── /login                          LoginPage.vue
├── /                               DashboardPage.vue
├── /resources/:type                ResourceListPage.vue
│   ├── ScaleModal.vue              (deployment / statefulset)
│   ├── DeleteModal.vue             (除 namespace 外)
│   ├── RollbackModal.vue           (仅 deployment)
│   └── YamlModal.vue               (所有类型)
├── /apply                          ApplyYamlPage.vue
├── /users                          UserManagementPage.vue (admin)
└── /audit                          AuditLogPage.vue (admin)
```

## 关联 Skill

- **superpowers:verification-before-completion** — 完成后跑相关测试场景验证
- **superpowers:systematic-debugging** — 测试失败时先做根因分析
