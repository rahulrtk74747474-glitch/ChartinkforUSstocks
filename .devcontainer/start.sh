#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
if [ -f /tmp/chartink-server.pid ] && kill -0 "$(cat /tmp/chartink-server.pid)" 2>/dev/null; then
  exit 0
fi
nohup .venv/bin/uvicorn backend.app:app --host 0.0.0.0 --port 8000 > /tmp/chartink-server.log 2>&1 &
echo $! > /tmp/chartink-server.pid
