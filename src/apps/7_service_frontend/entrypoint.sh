#!/bin/bash
# Entrypoint para ejecutar el middleware en contenedor
#
# En el contenedor, el Dockerfile copia el repo a /app (WORKDIR) y este script
# a /app/entrypoint.sh, por lo que la raíz del proyecto es el directorio del
# propio script (/app).
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -d "$ROOT_DIR/src/apps/7_service_frontend" ]; then
    ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
fi
export PYTHONPATH="$ROOT_DIR"
cd "$ROOT_DIR"

# Mail Gateway: vault → .env (base64) → ficheros 0600 dentro del contenedor.
MAIL_CREDS_FILE="${LAIM_MAIL_CREDENTIALS_FILE:-/run/mail-gateway/credentials.json}"
MAIL_TOKEN_FILE="${LAIM_MAIL_TOKEN_FILE:-/run/mail-gateway/token.json}"
MAIL_DIR="$(dirname "$MAIL_CREDS_FILE")"
mkdir -p "$MAIL_DIR"
if [ -n "${LAIM_MAIL_GATEWAY_CREDENTIALS_B64:-}" ]; then
  printf '%s' "$LAIM_MAIL_GATEWAY_CREDENTIALS_B64" | base64 -d > "$MAIL_CREDS_FILE"
  chmod 600 "$MAIL_CREDS_FILE"
fi
if [ -n "${LAIM_MAIL_GATEWAY_TOKEN_B64:-}" ]; then
  printf '%s' "$LAIM_MAIL_GATEWAY_TOKEN_B64" | base64 -d > "$MAIL_TOKEN_FILE"
  chmod 600 "$MAIL_TOKEN_FILE"
fi

python -m src.apps.7_service_frontend.main
