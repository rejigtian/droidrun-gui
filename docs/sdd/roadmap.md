# DroidRun 扩展开发路线图 SDD

> 版本：v1.0 | 日期：2026-04-10 | 分支：feature/android-native-agent

---

## 背景

DroidRun 上游已升级至 v0.5.8，核心架构发生重大重构（Driver 层解耦、FastAgent 替代 CodeAct、新增 CloudDriver / MCP / TUI 等）。

在此基础上，我们计划推进两个方向：

1. **Android 原生 Agent（自治模式）** — 手机上安装 APK，直接调用云端 LLM，无需电脑
2. **Desktop GUI 适配升级** — 现有桌面应用适配 droidrun 0.5.8 新接口

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

## 项目二：Desktop GUI 适配升级

### 背景

现有 `desktop-app/` 是 Python + customtkinter GUI，通过 subprocess 调用 droidrun CLI。
上游升级后，CLI 接口、配置格式、Provider 体系均有变化，需要适配。

### 变更点梳理

| 变更项 | 旧版（0.4.x） | 新版（0.5.x） | 影响 |
|--------|-------------|-------------|------|
| LLM 配置 | 各 provider 独立参数 | Provider Registry（ZAI/Gemini/OpenAI 等）| 配置页面需重写 |
| 工具层 | `AdbTools` 单类 | `Driver` + `StateProvider` 分离 | task_runner 调用方式变化 |
| Agent 模式 | codeact / droid | fast_agent / droid（reasoning）| 模式选择 UI 需更新 |
| 设备检测 | adbutils 同步 | async_adbutils 异步 | device_checker 需改写 |
| 配置文件格式 | config.yaml v1 | config.yaml v2（含 migrations）| 配置读写逻辑更新 |
| CLI 命令 | `droidrun run` 等 | 新增 `droidrun doctor`、TUI 模式 | GUI 可集成 doctor 检测 |

### 开发计划

#### Phase A：依赖 & 配置适配（1周）
- [ ] A-1 更新 `requirements.txt`：`droidrun>=0.5.8`，移除旧 provider 包
- [ ] A-2 适配新 config.yaml 格式，更新 `src/core/` 配置读写逻辑
- [ ] A-3 设备检测改用 `async_adbutils`

#### Phase B：Provider 配置页重写（1周）
- [ ] B-1 参考上游 Provider Registry，重写配置 UI：支持 Gemini / OpenAI / Anthropic / ZAI / Ollama
- [ ] B-2 支持 OAuth 认证流程（新增 Anthropic/Gemini OAuth）
- [ ] B-3 移除旧版独立 API Key 输入，统一到 Provider 选择器

#### Phase C：任务执行适配（3天）
- [ ] C-1 `task_runner.py` 适配新 CLI 参数（fast_agent 模式、driver 选项）
- [ ] C-2 集成 `droidrun doctor` 结果展示到安装引导界面
- [ ] C-3 验证端到端任务执行流程

---

## 优先级 & 时序

```
Week 1-2  : [Android] P1 脚手架 & 工具层
Week 3-4  : [Android] P2 LLM + Agent Loop
Week 5    : [Android] P3 触发层配置  ||  [GUI] Phase A 依赖适配
Week 6    : [Android] P4 测试打磨   ||  [GUI] Phase B Provider 重写
Week 7    : [GUI] Phase C 任务执行适配 & 整体验收
```

---

## 仓库结构规划

```
rejigtian/droidrun
├── main                        ← 持续同步上游
└── feature/android-native-agent ← 当前开发分支
    └── android-agent/           ← 新增 Android 项目目录
        ├── app/
        ├── build.gradle.kts
        └── ...
```

desktop-app 升级在同一分支推进，完成后单独 PR 合入 main。
