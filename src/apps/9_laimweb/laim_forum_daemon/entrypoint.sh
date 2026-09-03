#!/bin/bash
# Entrypoint del daemon del foro LAIM (API 8766) en contenedor.
# Corre junto al backend (acceso a MariaDB laim_core_db y storage del foro).
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -d "$ROOT_DIR/src/apps/9_laimweb/laim_forum_daemon" ]; then
    ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
fi
export PYTHONPATH="$ROOT_DIR"

# Escucha en 0.0.0.0 dentro del contenedor (el puerto se publica por compose).
export LAIM_FORUM_API_HOST="${LAIM_FORUM_API_HOST:-0.0.0.0}"
export LAIM_FORUM_API_PORT="${LAIM_FORUM_API_PORT:-${SERVICE_PORT:-8766}}"

cd "$ROOT_DIR"
exec python src/apps/9_laimweb/laim_forum_daemon/main.py
