#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=laim_forum_common.sh
source "$SCRIPT_DIR/laim_forum_common.sh"

if [ ! -f "$PID_FILE" ]; then
  echo "Daemon del foro LAIM no está en ejecución."
  exit 0
fi

PID="$(cat "$PID_FILE" 2>/dev/null || true)"
if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
  kill "$PID" 2>/dev/null || true
  sleep 1
  if kill -0 "$PID" 2>/dev/null; then
    kill -9 "$PID" 2>/dev/null || true
  fi
  echo "Daemon del foro LAIM detenido (PID $PID)"
else
  echo "PID obsoleto en $PID_FILE"
fi
rm -f "$PID_FILE"
