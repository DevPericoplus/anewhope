#!/bin/bash
# Script para activar el entorno virtual y ejecutar el broker backend

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

# Cargar variables de entorno desde .env si existe
if [ -f "$ROOT_DIR/.env" ]; then
    set -a
    source "$ROOT_DIR/.env"
    set +a
fi

# Cargar variables de entorno específicas del entorno (macbook por defecto)
ENV_NAME="${ENVIRONMENT:-macbook}"
ENV_YAML="$ROOT_DIR/infrastructure/environments/$ENV_NAME/env.yaml"
if [ -f "$ENV_YAML" ]; then
    # Parsear YAML simple (clave: valor) y exportar como variables de entorno
    while IFS=': ' read -r key value; do
        # Ignorar líneas vacías y comentarios
        [[ -z "$key" || "$key" == \#* ]] && continue
        # Eliminar comillas del valor
        value=$(echo "$value" | sed 's/^["'"'"']//;s/["'"'"']$//')
        # Exportar en mayúsculas (compatible con bash 3.2 de macOS)
        key_upper=$(echo "$key" | tr '[:lower:]' '[:upper:]')
        export "$key_upper"="$value"
    done < "$ENV_YAML"
fi

# Activar el entorno virtual del broker (Python 3.13)
source "$ROOT_DIR/.venv_broker313/bin/activate"

export PYTHONPATH="$ROOT_DIR"
python -m src.apps.8_service_backend.main
