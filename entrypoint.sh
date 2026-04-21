#!/bin/bash
set -e

echo "========================================"
echo "🚀 MEMULAI DOCKER SCRAPER VNC ENVIRONMENT"
echo "========================================"

# 1. Jalankan Xvfb (Virtual Screen ukuran 1280x720)
echo "[1/5] Starting Xvfb on :99..."
Xvfb :99 -screen 0 1280x720x24 &
sleep 2

# 2. Jalankan Window Manager (Fluxbox) agar Chrome punya bingkai
echo "[2/5] Starting Fluxbox..."
fluxbox -display :99 &
sleep 1

# 3. Jalankan VNC Server untuk merekam layar Xvfb
echo "[3/5] Starting x11vnc..."
x11vnc -display :99 -nopw -forever -shared -quiet &
sleep 1

# 4. Jalankan Websockify (Jembatan noVNC) di port 6080
echo "[4/5] Starting Websockify (noVNC)..."
websockify --web /usr/share/novnc 6080 localhost:5900 &
sleep 1

# 5. Jalankan API Server Python
echo "[5/5] Starting FastAPI Server on port 8000..."
exec uvicorn api:app --host 0.0.0.0 --port 8000