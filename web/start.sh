#!/bin/bash
# Start DroidRun WebGUI (backend + frontend dev server)
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "=== DroidRun WebGUI ==="

# Backend
cd "$ROOT/backend"
if [ ! -d ".venv" ]; then
  echo "[backend] Creating virtual environment..."
  python3 -m venv .venv
fi
source .venv/bin/activate
echo "[backend] Installing dependencies..."
pip install -q -r requirements.txt

echo "[backend] Starting FastAPI on :8000"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Frontend
cd "$ROOT/frontend"
if [ ! -d "node_modules" ]; then
  echo "[frontend] Installing npm packages..."
  npm install
fi
echo "[frontend] Starting Vite dev server on :5173"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait
