#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=laim_forum_common.sh
source "$SCRIPT_DIR/laim_forum_common.sh"

if [ ! -d "$VENV_DIR" ]; then
  echo "Error: no se encontró el entorno virtual en $VENV_DIR"
  exit 1
fi

if [ -f "$PID_FILE" ]; then
  OLD_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Daemon del foro LAIM ya en ejecución (PID $OLD_PID)"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

mkdir -p "$(dirname "$LOG_FILE")"
export PYTHONPATH="$ROOT_DIR"

# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

echo "Iniciando daemon del foro LAIM (${FORUM_API_HOST}:${FORUM_API_PORT})..."
nohup python "$APP_DIR/laim_forum_daemon/main.py" >>"$LOG_FILE" 2>&1 &
echo $! >"$PID_FILE"
sleep 1

if kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "Daemon del foro LAIM iniciado (PID $(cat "$PID_FILE"))"
else
  echo "Error: el daemon del foro no arrancó. Ver $LOG_FILE"
  rm -f "$PID_FILE"
  exit 1
fi
