ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

# Argumento para definir el entorno (dev, pre, pro)
# Para producción: docker build --build-arg ENVIRONMENT=pro ...
ARG ENVIRONMENT=dev

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=${ENVIRONMENT}

# Herramientas de compilación y runtime de Reflex:
# - build-essential/python3-dev: compilar wheels sin binario arm64 (hiredis).
# - curl/unzip: Reflex los usa para descargar e instalar bun en runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential python3-dev curl unzip \
    && rm -rf /var/lib/apt/lists/*

COPY src/apps/6_web_backoffice/requirements.txt /app/requirements.txt
COPY src/apps/6_web_backoffice/entrypoint.sh /app/entrypoint.sh

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt

ARG ANEWHOPE_BUILD_SHA=unknown
COPY . /app

# Pre-generar el frontend Reflex (.web) y parchear Vite (allowedHosts) en build.
ENV PYTHONPATH=/app
RUN cd /app/src/apps/6_web_backoffice \
    && reflex init --name web_backoffice --loglevel info \
    && python patch_vite_config.py || true

# SEGURIDAD: En producción, eliminar archivos JSON de moks
RUN if [ "$ENVIRONMENT" = "pro" ]; then \
        echo "PRODUCCIÓN: Eliminando archivos moks por seguridad..." && \
        rm -rf /app/src/2_shared_application/moks && \
        echo "Moks eliminados correctamente"; \
    fi

EXPOSE 8006

RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
