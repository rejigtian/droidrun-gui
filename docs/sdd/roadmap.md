# DroidRun 扩展开发路线图 SDD

> 版本：v1.1 | 日期：2026-04-14 | 分支：feature/android-native-agent

---

## 背景

DroidRun 上游已升级至 v0.5.8，核心架构发生重大重构（Driver 层解耦、FastAgent 替代 CodeAct、新增 CloudDriver / MCP / TUI 等）。

在此基础上，我们计划推进两个方向：

1. **Android 原生 Agent（自治模式）** — 手机上安装 APK，直接调用云端 LLM，无需电脑
2. **Web UI（自托管 WebGUI）** — FastAPI + React 自托管 Web 界面，取代 macOS 专属桌面应用

---

## 项目一：Android 原生 Agent（自治模式）

### 目标

手机自治：用户安装一个 APK → 配置 LLM API Key → 通过通知/快捷方式下达自然语言指令 → 手机自动完成任务。全程无需电脑，无需 ADB。

### 架构设计

```
┌─────────────────────────────────────────────────────┐
│                  DroidRun Agent APK                  │
│                                                     │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────┐ │
│  │  触发层      │   │   Agent 层    │   │  工具层   │ │
│  │             │   │              │   │          │ │
│  │ - 通知监听   │──▶│ TaskQueue    │   │ A11yTools│ │
│  │ - 快捷指令   │   │ AgentLoop    │──▶│ (无障碍)  │ │
│  │ - 飞书Bot   │   │ LLM Client   │   │          │ │
│  └─────────────┘   └──────────────┘   └──────────┘ │
│                            │                        │
│                    ┌───────▼────────┐               │
│                    │  云端 LLM API   │               │
│                    │ (OpenAI/Claude │               │
│                    │  /Gemini 等)    │               │
│                    └────────────────┘               │
└─────────────────────────────────────────────────────┘
```

### 与 droidrun-portal 的关系

- 复用 droidrun-portal 的 **Accessibility Service** 读取 A11y 树
- 新建独立 Agent APK，通过 localhost HTTP（portal:8080）调用 portal 的控制接口
- 两个 APK 各司其职：portal = 工具层，agent = 决策层

### 技术选型

| 模块 | 技术方案 |
|------|---------|
| 语言 | Kotlin |
| UI | Jetpack Compose |
| Agent Loop | 协程（Coroutines）+ Flow |
| LLM 调用 | OkHttp + 直接调用 OpenAI/Anthropic HTTP API |
| A11y 读取 | 复用 droidrun-portal AccessibilityService，或独立实现 |
| 任务触发 | Android Notification Listener + Feishu Webhook |
| 配置存储 | DataStore（API Key、LLM 选择等）|

### 开发计划

#### Phase 1：脚手架 & 工具层（2周）
- [ ] P1-1 新建 Android 项目（Kotlin + Compose），接入 Gradle 构建
- [ ] P1-2 实现 `A11yToolsClient`：通过 localhost:8080 调用 portal 的 get_state / tap / swipe / input_text 接口
- [ ] P1-3 实现截图能力（调用 portal screenshot 接口）
- [ ] P1-4 本地验证：能正确读取 A11y 树并执行点击

#### Phase 2：LLM 接入 & Agent Loop（2周）
- [ ] P2-1 实现 `LLMClient`，支持 OpenAI / Anthropic / Gemini（HTTP 直连）
- [ ] P2-2 参考 FastAgent 的 XML tool-calling 协议，实现 Kotlin 版 ToolCallParser
- [ ] P2-3 实现 `AgentLoop`：get_state → LLM → parse tool call → execute → loop
- [ ] P2-4 实现 `complete(success, reason)` 终止逻辑

#### Phase 3：触发层 & 配置（1周）
- [ ] P3-1 设置页面：API Key 输入、LLM 选择
- [ ] P3-2 任务输入：前台 UI 输入 + 通知栏快捷输入
- [ ] P3-3 任务执行日志 UI（实时展示 Agent 步骤）

#### Phase 4：测试 & 打磨（1周）
- [ ] P4-1 在真机上跑通 3 个端到端任务
- [ ] P4-2 处理不同 ROM 权限差异（小米/华为/OPPO）
- [ ] P4-3 写安装/使用文档

### 关键接口定义

portal HTTP 接口（Agent APK → droidrun-portal）：

```
GET  localhost:8080/state       → { a11y_tree, phone_state }
POST localhost:8080/tap         → { x, y }
POST localhost:8080/swipe       → { x1, y1, x2, y2, duration_ms }
POST localhost:8080/input_text  → { text, clear }
POST localhost:8080/press_key   → { keycode }
GET  localhost:8080/screenshot  → PNG bytes
POST localhost:8080/start_app   → { package }
```

---

## 项目二：Web UI（自托管 WebGUI）

### 背景

原有 `desktop-app/`（Python + customtkinter）仅支持 macOS，且维护成本高。
已用 FastAPI + React 自托管 WebGUI 完整替代，可部署到云服务器或本地，任意浏览器访问。

### 架构

```
浏览器（任意平台）
      ↕ HTTP/WebSocket
FastAPI 后端（cloud / local）
      ↕ Reverse WebSocket（穿透 NAT）
droidrun-portal Android APK（手机端）
```

- Portal 主动反连后端（`/v1/providers/join`），解决手机不固定 IP 问题
- 后端通过 `WebSocketDevice(DeviceDriver)` 将 droidrun 工具调用转发为 JSON-RPC

### 关键文件

| 文件 | 说明 |
|------|------|
| `web/backend/main.py` | FastAPI 入口，CORS，静态文件，健康检查 |
| `web/backend/ws/portal_ws.py` | Portal WebSocket 端点；维护 `connected_devices` |
| `web/backend/agent/ws_device.py` | `WebSocketDevice`：工具调用 → JSON-RPC → Portal |
| `web/backend/core/task_runner.py` | 异步任务执行，注入 `WebSocketDevice` 到 `DroidAgent` |
| `web/backend/db/` | SQLite（SQLAlchemy async）：Device / Task / TaskLog |
| `web/frontend/src/` | React + TypeScript + Vite + Tailwind + React Query |

### 启动方式

```bash
cd web && ./start.sh
# 后端：uvicorn main:app --reload  （port 8000）
# 前端：npm run dev                 （port 5173，开发模式）
```

### 开发进展

- **✅ MVP 完成**（2026-04-13）：后端架构、WebSocket 桥接、数据库层、前端基础页面全部实现
- **待办**：真机端对端测试（Portal 连接 → 任务下发 → 结果展示）

---

## 优先级 & 时序

```
Week 1-2  : [Android] P1 脚手架 & 工具层          ✅ 完成（直接扩展 portal）
Week 3-4  : [Android] P2 LLM + Agent Loop         ✅ 完成
Week 5    : [Android] P3 触发层配置                ✅ 完成
Week 6    : [Android] P4 测试打磨                  ✅ 完成（文档已写，真机待验证）
            [Web] MVP 后端 + 前端                  ✅ 完成（2026-04-13）
Week 7+   : [Web] 端对端测试 & 真机验证            🔲 进行中
            合并 feature/android-native-agent → main
```

---

## 仓库结构规划

```
rejigtian/droidrun
├── main                          ← 持续同步上游
└── feature/android-native-agent  ← 当前开发分支
    ├── web/                      ← 自托管 WebGUI（FastAPI + React）
    │   ├── backend/
    │   ├── frontend/
    │   └── start.sh
    └── （Android 原生 Agent 扩展已合入 portal，无独立子目录）
```

`desktop-app/` 目录已废弃，不再维护。Web UI 替代其功能。
