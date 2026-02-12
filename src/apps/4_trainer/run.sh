#!/bin/bash
# Script para activar el entorno virtual y ejecutar el backend IA (trainer)
# NOTA: Usa Python 3.12 por compatibilidad con dependencias de IA (TensorFlow, Keras)

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

# Activar el entorno virtual del trainer (Python 3.12 - requerido por dependencias IA)
source "$ROOT_DIR/.venv_trainer312/bin/activate"

export PYTHONPATH="$ROOT_DIR"

# Configurar certificados SSL para que TensorFlow Hub pueda descargar modelos
SSL_CERT_FILE=$(python -c "import certifi; print(certifi.where())" 2>/dev/null)
if [ -n "$SSL_CERT_FILE" ]; then
    export SSL_CERT_FILE
    export REQUESTS_CA_BUNDLE="$SSL_CERT_FILE"
fi

python -m src.apps.4_trainer.main
