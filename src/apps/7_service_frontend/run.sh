#!/bin/bash
# Script para activar el entorno virtual y ejecutar el middleware

# Activar el entorno virtual
source ../../../.venv314/bin/activate

# Ejecutar el middleware
python -m src.apps.7_service_frontend.main
