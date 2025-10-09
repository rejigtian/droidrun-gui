# DroidRun Backend

Web backend for DroidRun agents, providing REST API and real-time event streaming via SSE and WebSocket.

## Overview

The backend provides a clean separation between DroidAgent execution and the web interface. It:

- **Zero agent code modification** - Uses existing event streaming from DroidAgent
- **Real-time updates** - SSE and WebSocket support for live event streaming
- **Session management** - Track multiple concurrent agent executions
- **Type-safe** - Pydantic models for all API requests/responses
- **Developer-friendly** - DroidAgent API remains unchanged

## Architecture

```
Frontend (Browser)
    ↓
FastAPI Server (REST + SSE/WebSocket)
    ↓
AgentRunner (wraps DroidAgent)
    ↓
EventFormatter (formats events for web)
    ↓
DroidAgent (unchanged)
```

## Installation

```bash
# Install backend dependencies
pip install -r backend/requirements.txt

# Or if using the main droidrun package
pip install droidrun[backend]
```

## Quick Start

### Start the Server

```bash
# From the droidrun directory
python -m droidrun.backend.server

# Or with custom settings
DROIDRUN_BACKEND_PORT=8080 python -m droidrun.backend.server
```

Server will start at: `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

### Basic Usage

#### 1. Start an Agent

```bash
curl -X POST http://localhost:8000/api/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Open Settings app",
    "reasoning": false,
    "max_steps": 10,
    "llms": {
      "default": {
        "provider": "GoogleGenAI",
        "model": "models/gemini-2.5-flash",
        "temperature": 0.2
      }
    }
  }'
```

Response:
```json
{
  "session_id": "uuid-here",
  "status": "running",
  "message": "Agent execution started"
}
```

#### 2. Stream Events (SSE)

```javascript
const sessionId = 'your-session-id';
const eventSource = new EventSource(`http://localhost:8000/api/agent/stream/${sessionId}`);

// Listen for different event types
eventSource.addEventListener('llm_thinking', (e) => {
  const data = JSON.parse(e.data);
  console.log('Agent thinking:', data.data.thoughts);
});

eventSource.addEventListener('screenshot', (e) => {
  const data = JSON.parse(e.data);
  const img = document.createElement('img');
  img.src = data.data.image; // data:image/png;base64,...
  document.body.appendChild(img);
});

eventSource.addEventListener('manager_plan', (e) => {
  const data = JSON.parse(e.data);
  console.log('Plan:', data.data.plan);
});

eventSource.addEventListener('finalize', (e) => {
  const data = JSON.parse(e.data);
  console.log('Completed:', data.data.success);
  eventSource.close();
});
```

#### 3. WebSocket Alternative

```javascript
const ws = new WebSocket('ws://localhost:8000/api/agent/ws/my-connection-id');

ws.onopen = () => {
  // Subscribe to session
  ws.send(JSON.stringify({
    type: 'subscribe',
    session_id: 'your-session-id'
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  if (message.type === 'event') {
    console.log('Event:', message.data);
  }
};
```

## API Endpoints

### Agent Management

#### POST `/api/agent/run`
Start a new agent execution.

**Request Body:**
```json
{
  "goal": "string (required)",
  "device": "string (optional)",
  "llms": {
    "default": {
      "provider": "GoogleGenAI",
      "model": "models/gemini-2.5-flash",
      "temperature": 0.2
    }
  },
  "vision": {
    "manager": true,
    "executor": true,
    "codeact": true
  },
  "reasoning": false,
  "max_steps": 15,
  "debug": false
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "status": "running",
  "message": "Agent execution started"
}
```

#### GET `/api/agent/status/{session_id}`
Get session status.

**Response:**
```json
{
  "session": {
    "session_id": "uuid",
    "goal": "string",
    "status": "running|completed|failed|stopped",
    "created_at": "2025-10-10T...",
    "config": {...}
  }
}
```

#### POST `/api/agent/stop/{session_id}`
Stop a running agent.

#### GET `/api/agent/sessions`
List all sessions with optional filtering.

**Query Parameters:**
- `status`: Filter by status (optional)
- `limit`: Maximum sessions to return (default: 10)

#### DELETE `/api/agent/session/{session_id}`
Delete a session.

### Event Streaming

#### GET `/api/agent/stream/{session_id}` (SSE)
Stream events via Server-Sent Events.

**Event Types:**
- `start` - Agent started
- `llm_thinking` - Agent reasoning/thinking
- `manager_plan` - Manager created plan
- `executor_action` - Executor selected action
- `code_execution` - Code being executed
- `execution_result` - Code execution result
- `screenshot` - Screenshot captured
- `ui_state` - UI state recorded
- `finalize` - Agent completed
- `status` - Status update
- `error` - Error occurred

#### WebSocket `/api/agent/ws/{connection_id}`
Bidirectional event streaming.

**Message Types:**
- `subscribe` - Subscribe to session
- `unsubscribe` - Unsubscribe from session
- `event` - Event from agent
- `ping/pong` - Keepalive

### Admin

#### POST `/api/admin/cleanup`
Cleanup old sessions.

**Query Parameters:**
- `max_age_hours`: Maximum age (default: 24)

#### GET `/api/admin/stats`
Get backend statistics.

## Event Format

All events follow this structure:

```json
{
  "event_type": "llm_thinking",
  "timestamp": "2025-10-10T12:00:00",
  "session_id": "uuid",
  "data": {
    // Event-specific data
  }
}
```

### Event Examples

**LLM Thinking:**
```json
{
  "event_type": "llm_thinking",
  "data": {
    "agent": "codeact",
    "thoughts": "I need to click the settings button",
    "code": "click(tools, 5)",
    "usage": {
      "prompt_tokens": 100,
      "completion_tokens": 50
    }
  }
}
```

**Screenshot:**
```json
{
  "event_type": "screenshot",
  "data": {
    "image": "data:image/png;base64,iVBORw0KGgo...",
    "message": "Screenshot captured"
  }
}
```

**Manager Plan:**
```json
{
  "event_type": "manager_plan",
  "data": {
    "agent": "manager",
    "plan": ["Step 1: ...", "Step 2: ..."],
    "current_subgoal": "Open the settings app",
    "thought": "I will start by finding the settings icon"
  }
}
```

## Configuration

Environment variables (prefix with `DROIDRUN_BACKEND_`):

```bash
# Server
DROIDRUN_BACKEND_HOST=0.0.0.0
DROIDRUN_BACKEND_PORT=8000
DROIDRUN_BACKEND_RELOAD=true
DROIDRUN_BACKEND_LOG_LEVEL=info

# CORS
DROIDRUN_BACKEND_CORS_ORIGINS=["*"]

# Sessions
DROIDRUN_BACKEND_MAX_SESSION_AGE_HOURS=24
DROIDRUN_BACKEND_CLEANUP_INTERVAL_HOURS=6

# Streaming
DROIDRUN_BACKEND_SSE_KEEPALIVE_SECONDS=30
DROIDRUN_BACKEND_WEBSOCKET_PING_INTERVAL=30

# Agent execution
DROIDRUN_BACKEND_MAX_CONCURRENT_AGENTS=10
```

Or create a `.env` file:

```bash
DROIDRUN_BACKEND_PORT=8080
DROIDRUN_BACKEND_DEBUG=true
```

## LLM Configuration

The backend accepts flexible LLM configurations:

### Single LLM for All Agents

```json
{
  "llms": {
    "default": {
      "provider": "GoogleGenAI",
      "model": "models/gemini-2.5-flash",
      "temperature": 0.2
    }
  }
}
```

### Per-Agent LLMs

```json
{
  "llms": {
    "manager": {
      "provider": "Anthropic",
      "model": "claude-3-opus-20240229",
      "temperature": 0.1
    },
    "executor": {
      "provider": "GoogleGenAI",
      "model": "models/gemini-2.5-flash",
      "temperature": 0.2
    },
    "codeact": {
      "provider": "OpenAI",
      "model": "gpt-4",
      "temperature": 0.0
    }
  }
}
```

### Use Config Profiles

If no LLMs specified, falls back to `config.yaml` profiles.

## Developer Usage

For developers using DroidAgent directly, **nothing changes**:

```python
# This still works exactly as before
from droidrun.agent.droid import DroidAgent

droid_agent = DroidAgent(goal="...", llms=..., tools=...)
handler = droid_agent.run()

async for event in handler.stream_events():
    print(event)  # Events flow naturally

result = await handler
```

The backend is a **separate layer** that wraps this existing functionality.

## Architecture Details

### Components

1. **server.py** - FastAPI application with REST and streaming endpoints
2. **agent_runner.py** - Wraps DroidAgent execution, manages lifecycle
3. **event_formatter.py** - Formats workflow events for web consumption
4. **session_manager.py** - Tracks active and completed sessions
5. **websocket.py** - WebSocket connection management
6. **models.py** - Pydantic models for type-safe API
7. **config.py** - Backend configuration

### Event Flow

```
DroidAgent Workflow
    ↓ (ctx.write_event_to_stream)
handler.stream_events()
    ↓ (existing functionality)
AgentRunner.stream_events()
    ↓ (thin wrapper)
EventFormatter.format_event()
    ↓ (format for web)
SSE/WebSocket Stream
    ↓ (async generator)
Frontend EventSource/WebSocket
```

## Frontend Integration

See `frontend/` directory for example React/Vue integration.

Basic JavaScript example:

```html
<!DOCTYPE html>
<html>
<body>
  <button onclick="startAgent()">Start Agent</button>
  <div id="status"></div>
  <div id="events"></div>
  <img id="screenshot" />

  <script>
    let sessionId;

    async function startAgent() {
      const response = await fetch('http://localhost:8000/api/agent/run', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          goal: 'Open Settings app',
          reasoning: false,
          llms: {
            default: {
              provider: 'GoogleGenAI',
              model: 'models/gemini-2.5-flash'
            }
          }
        })
      });

      const data = await response.json();
      sessionId = data.session_id;

      // Start listening for events
      streamEvents(sessionId);
    }

    function streamEvents(sessionId) {
      const eventSource = new EventSource(
        `http://localhost:8000/api/agent/stream/${sessionId}`
      );

      eventSource.addEventListener('llm_thinking', (e) => {
        const event = JSON.parse(e.data);
        document.getElementById('events').innerHTML +=
          `<p><strong>Thinking:</strong> ${event.data.thoughts}</p>`;
      });

      eventSource.addEventListener('screenshot', (e) => {
        const event = JSON.parse(e.data);
        document.getElementById('screenshot').src = event.data.image;
      });

      eventSource.addEventListener('finalize', (e) => {
        const event = JSON.parse(e.data);
        document.getElementById('status').innerHTML =
          `<p><strong>Status:</strong> ${event.data.success ? 'Success' : 'Failed'}</p>`;
        eventSource.close();
      });
    }
  </script>
</body>
</html>
```

## Troubleshooting

### CORS Issues

If you get CORS errors, configure allowed origins:

```bash
DROIDRUN_BACKEND_CORS_ORIGINS='["http://localhost:3000","http://localhost:5173"]'
```

### SSE Connection Drops

Increase keepalive interval:

```bash
DROIDRUN_BACKEND_SSE_KEEPALIVE_SECONDS=60
```

### Event Queue Full

Increase queue size:

```bash
DROIDRUN_BACKEND_EVENT_QUEUE_SIZE=5000
```

## License

Same as DroidRun main package.
