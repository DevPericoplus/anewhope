#!/bin/bash
# Ejecuta el trainer en Docker con variables de entorno.

set -e

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$APP_DIR/../../.." && pwd)"
export PYTHONPATH="$ROOT_DIR"

ENVIRONMENT="$(python - <<'PY'
from src.2_shared_application.config.env_settings import get_environment_name
print(get_environment_name())
PY
)"

TMP_ENV="$(mktemp)"
python "$ROOT_DIR/infrastructure/export_env.py" \
  --environment "$ENVIRONMENT" \
  --format envfile \
  --output "$TMP_ENV"

IMAGE_NAME="anewhope-trainer"
CONTAINER_NAME="anewhope-trainer"

docker build -f "$APP_DIR/Dockerfile" -t "$IMAGE_NAME" "$ROOT_DIR"
docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
docker run -d \
  --name "$CONTAINER_NAME" \
  --env-file "$TMP_ENV" \
  --env SERVICE_HOST="0.0.0.0" \
  --env SERVICE_PORT="8004" \
  -p "8004:8004" \
  "$IMAGE_NAME"

rm -f "$TMP_ENV"
