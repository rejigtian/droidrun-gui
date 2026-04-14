# DroidRun WebGUI

自托管 Web 界面，通过浏览器控制 Android/iOS 设备，无需桌面客户端。

## 架构

```
浏览器  ──HTTP──►  FastAPI 服务端 (:8000)
                       │
                       │  WebSocket (反向连接)
                       │
               droidrun-portal (手机 App)
```

Portal App 主动连接到服务端，手机无需固定 IP，也无需 ADB。服务端向 Portal 发送 JSON-RPC 指令（如 `performTap`、`getText` 等），Portal 执行后返回结果。

## 环境要求

| 依赖 | 版本 |
|------|------|
| Python | 3.11 – 3.13 |
| Node.js | 18+ |
| droidrun-portal | Android APK，安装于目标手机 |

## 快速启动（开发模式）

```bash
cd web
./start.sh
```

启动后：
- 后端 API：`http://localhost:8000`
- 前端页面：`http://localhost:5173`

脚本会自动：
1. 创建 Python 虚拟环境并安装后端依赖
2. 安装前端 npm 包
3. 同时启动两个服务

## 连接手机设备

1. 打开前端页面 → **Devices** → **Add Device**
2. 填写设备名称，点击 **Generate Token**，复制生成的 token
3. 在手机的 **droidrun-portal** App 中：
   - Server URL：`ws://<你的电脑IP>:8000/v1/providers/join`
   - Token：粘贴上一步复制的 token
4. 点击 **Connect**
5. 回到浏览器 Devices 页面，设备状态变为 **online**

> 手机与电脑需在同一局域网，或服务端部署在公网。

## 配置 LLM API Key

打开前端页面 → **Settings**，填写对应提供商的 API Key：

| 提供商 | 环境变量（备选） |
|--------|----------------|
| Google Gemini | `GOOGLE_API_KEY` |
| OpenAI | `OPENAI_API_KEY` |
| Anthropic | `ANTHROPIC_API_KEY` |
| DeepSeek | `DEEPSEEK_API_KEY` |
| ZhipuAI | `ZHIPUAI_API_KEY` |
| Ollama | 无需 Key，填写 base URL |

Key 保存在 `web/backend/data/settings.json`（已加入 `.gitignore`，不会提交到 git）。

## 下发任务

1. 前端页面 → **New Task**
2. 选择在线设备
3. 选择 LLM 提供商和模型
4. 输入自然语言指令，如：`打开设置，进入 WLAN，连接到 HomeNetwork`
5. 点击 **Run**
6. 任务列表页面实时查看执行日志

## 生产部署

### 构建前端

```bash
cd web/frontend
npm install
npm run build          # 输出到 web/frontend/dist/
```

### 启动后端（生产模式）

```bash
cd web/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

生产模式下，FastAPI 会直接伺服 `frontend/dist/` 的静态文件，只需访问 `http://<服务器IP>:8000`。

### 使用 HTTPS（推荐公网部署）

在 Nginx 或 Caddy 前置反代，将 HTTPS 流量转发到 :8000，Portal 的 Server URL 改为：

```
wss://your-domain.com/v1/providers/join
```

### 使用 systemd 保持后台运行

```ini
[Unit]
Description=DroidRun WebGUI
After=network.target

[Service]
WorkingDirectory=/path/to/droidrun/web/backend
ExecStart=/path/to/droidrun/web/backend/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

## 目录结构

```
web/
├── start.sh                  # 一键启动脚本（开发）
├── backend/
│   ├── main.py               # FastAPI 入口，CORS，静态文件
│   ├── requirements.txt
│   ├── settings.example.json # 配置文件模板（复制为 data/settings.json）
│   ├── agent/
│   │   └── ws_device.py      # WebSocketDevice：桥接 droidrun 工具调用 ↔ JSON-RPC
│   ├── core/
│   │   ├── settings_manager.py  # settings.json 读写
│   │   └── task_runner.py       # 异步任务执行，注入 WebSocketDevice 到 DroidAgent
│   ├── db/
│   │   ├── database.py       # SQLAlchemy async + aiosqlite
│   │   └── models.py         # Device、Task、TaskLog 表
│   ├── routers/
│   │   ├── devices.py        # GET /api/devices，POST /api/tokens
│   │   ├── tasks.py          # GET/POST /api/tasks，SSE 日志流
│   │   └── settings.py       # GET/PUT /api/settings（API Key 脱敏返回）
│   └── ws/
│       └── portal_ws.py      # WebSocket /v1/providers/join，Bearer token 认证
└── frontend/
    └── src/
        ├── pages/
        │   ├── Devices.tsx   # 设备管理页
        │   ├── Tasks.tsx     # 任务列表页
        │   ├── NewTask.tsx   # 下发任务页
        │   └── Settings.tsx  # LLM 配置页
        └── api.ts            # 后端 API 调用封装
```

## 常见问题

**设备连不上**
- 确认 Portal App 的 Server URL 格式：`ws://IP:8000/v1/providers/join`（注意是 `ws://` 不是 `http://`）
- 检查防火墙是否放行 8000 端口

**任务执行失败**
- Settings 页面确认已填写对应 LLM 的 API Key
- 查看 Tasks 页面的实时日志定位错误

**前端访问 5173 但后端 8000 报 CORS 错误**
- 开发模式正常，前端通过 Vite proxy 转发到后端
- 生产模式需确保前端已构建（`npm run build`）并由 FastAPI 直接伺服
