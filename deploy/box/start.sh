#!/bin/bash
# NutriScale OS — start on the Box (cloud computer): backend :8765 + 24x7 scheduler + Serveo HTTPS tunnel.
# Safe to re-run (stops old processes, starts new ones). Run this whenever the Box wakes up.
# First time: put NUTRISCALE_OWNER_USER=... and NUTRISCALE_OWNER_PASSWORD=... in ~/.nutriscale_owner (chmod 600)
cd "$(dirname "$0")/../.."
[ -f ~/.nutriscale_owner ] && { set -a; . ~/.nutriscale_owner; set +a; }
export NUTRISCALE_DB="$PWD/data/growth_os.db" PORT=8765
pkill -f "backend/app.py" 2>/dev/null; pkill -f "jobrunner.py --daemon" 2>/dev/null
pkill -f "box/tunnel.sh" 2>/dev/null; pkill -f "serveo.net" 2>/dev/null; sleep 1
mkdir -p logs data
nohup python3 backend/app.py >> logs/backend.log 2>&1 &
nohup python3 src/jobrunner.py --daemon >> logs/worker.log 2>&1 &
: > logs/tunnel.log; rm -f PUBLIC_URL.txt
nohup deploy/box/tunnel.sh >/dev/null 2>&1 &
sleep 2; curl -s localhost:8765/health >/dev/null && echo "✔ backend running" || echo "✘ backend did not start — check logs/backend.log"
pgrep -f "jobrunner.py --daemon" >/dev/null && echo "✔ scheduler running" || echo "✘ scheduler stopped — check logs/worker.log"
for i in $(seq 1 30); do URL=$(cat PUBLIC_URL.txt 2>/dev/null); [ -n "$URL" ] && break; sleep 1; done
[ -n "$URL" ] && echo "✔ Dashboard link (open on PC/phone): $URL" || echo "✘ no tunnel link — check logs/tunnel.log"
