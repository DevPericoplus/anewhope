ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

# Argumento para definir el entorno (dev, pre, pro, silicon)
ARG ENVIRONMENT=dev

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=${ENVIRONMENT}

# Dependencias de sistema que Reflex/Vite necesitan en runtime
# (bun/node se descargan por Reflex; curl/unzip/bash son requeridos).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        unzip \
        bash \
        build-essential \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY src/apps/9_laimweb/requirements.txt /app/requirements.txt
COPY src/apps/9_laimweb/entrypoint.sh /app/entrypoint.sh

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

# Pre-generar el frontend Reflex (.web) y parchear Vite (allowedHosts) en build.
ENV PYTHONPATH=/app
RUN cd /app/src/apps/9_laimweb \
    && reflex init --name laim_web --loglevel info \
    && python patch_vite_config.py || true

# SEGURIDAD: En producción, eliminar archivos JSON de moks
RUN if [ "$ENVIRONMENT" = "pro" ]; then \
        echo "PRODUCCIÓN: Eliminando archivos moks por seguridad..." && \
        rm -rf /app/src/2_shared_application/moks && \
        echo "Moks eliminados correctamente"; \
    fi

# Puertos: 8010 (backend Reflex), 3110 (frontend Vite)
EXPOSE 8010 3110

RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
