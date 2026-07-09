#!/usr/bin/env bash
# Variables comunes del daemon del foro LAIM Web
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv_backend313"
PID_FILE="$APP_DIR/logs/laim_forum_daemon.pid"
LOG_FILE="$APP_DIR/logs/laim_forum_daemon.log"

FORUM_API_HOST="${LAIM_FORUM_API_HOST:-127.0.0.1}"
FORUM_API_PORT="${LAIM_FORUM_API_PORT:-8766}"
