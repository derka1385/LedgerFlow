#!/bin/sh
# Start the LedgerFlow demo: web app + backend with REAL Vultr inference and the REAL Docker sandbox.
# Refuses to start a mocked demo. Never prints the API key.
set -eu
cd "$(dirname "$0")/.."
PORT="${LEDGERFLOW_DEMO_PORT:-8790}"
RUN=demo/.run
mkdir -p "$RUN"
docker info >/dev/null 2>&1 || { echo "Docker is not answering. Start Docker Desktop (on this Mac it can need a second full quit/reopen), then retry."; exit 1; }
docker image inspect python:3.12-slim >/dev/null 2>&1 || { echo "Sandbox image missing. Run: docker pull python:3.12-slim"; exit 1; }
grep -q '^VULTR_INFERENCE_API_KEY=.' .env 2>/dev/null || { echo "No VULTR_INFERENCE_API_KEY in .env. Refusing to start a mocked demo."; exit 1; }
[ -f frontend/dist/index.html ] || npm --prefix frontend run build
if lsof -tiTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then echo "Port $PORT is busy. Choose another: LEDGERFLOW_DEMO_PORT=8792 sh demo/start_demo.sh"; exit 1; fi
PORT="$PORT" PYTHONUNBUFFERED=1 nohup python3 frontend/dev-mock-api/server.py --dotenv > "$RUN/server.log" 2>&1 &
echo $! > "$RUN/server.pid"
echo "$PORT" > "$RUN/port"
sleep 3
head -1 "$RUN/server.log"
if ! grep -q "inference: Vultr" "$RUN/server.log"; then
  echo "The backend did not start with real Vultr inference. Stopping it."; kill "$(cat "$RUN/server.pid")" 2>/dev/null || true; exit 1
fi
echo ""
echo "Demo running:   http://localhost:$PORT   (invites: owner-demo, accountant-demo, employee-demo)"
echo "Phone, same Wi-Fi (plain HTTP, not verified on a device): http://$(ipconfig getifaddr en0 2>/dev/null || echo YOUR-MAC-IP):$PORT"
echo "Stop and clean:  sh demo/reset_demo.sh"
