#!/bin/sh
# Reset the demo to a clean state. Touches ONLY what start_demo.sh created:
#  - stops the one backend process recorded in demo/.run/server.pid, after checking it really is LedgerFlow's server.py;
#  - removes leftover sandbox containers named lf_run_* (the prefix the LedgerFlow sandbox gives its own containers);
#  - deletes demo/.run/. Never touches .env, demo/workbook, demo/receipts, demo/out evidence, Docker itself,
#    other containers, other ports or other projects. The backend keeps state in memory, so a restart is a clean state.
set -eu
cd "$(dirname "$0")/.."
RUN=demo/.run
if [ -f "$RUN/server.pid" ]; then
  PID="$(cat "$RUN/server.pid")"
  if ps -p "$PID" -o command= 2>/dev/null | grep -q "frontend/dev-mock-api/server.py --dotenv"; then
    kill "$PID" && echo "Stopped demo backend (pid $PID)."
  else
    echo "pid $PID is not the demo backend (or already stopped): left alone."
  fi
fi
LEFT="$(docker ps -a --filter 'name=^lf_run_' --format '{{.Names}}' 2>/dev/null || true)"
if [ -n "$LEFT" ]; then
  for n in $LEFT; do case "$n" in lf_run_*) docker rm -f "$n" >/dev/null && echo "Removed leftover sandbox container $n";; esac; done
else
  echo "No leftover LedgerFlow sandbox containers."
fi
rm -rf "$RUN"
echo "Demo state reset. Start again with: sh demo/start_demo.sh"
