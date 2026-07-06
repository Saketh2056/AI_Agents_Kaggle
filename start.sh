#!/bin/sh
# ------------------------------------------------------------
# StudyBuddy — one-command startup
# Starts both servers:
#   1. the agent server (Google ADK) on port 8000
#   2. the web UI       (static files) on port 3000
# Then open:  http://localhost:3000/frontend/
# Stop with Ctrl+C.
# ------------------------------------------------------------
cd "$(dirname "$0")"

# use the project's virtual environment
. .venv/bin/activate

# serve the frontend in the background; stop it when this script exits
python3 -m http.server 3000 --bind 127.0.0.1 &
FRONT_PID=$!
trap 'kill $FRONT_PID 2>/dev/null' EXIT

# run the agent server in the foreground
# (server_main.py = ADK's web server + our custom /model switch endpoint)
python3 server_main.py
