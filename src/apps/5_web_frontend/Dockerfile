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

COPY src/apps/5_web_frontend/requirements.txt /app/requirements.txt
COPY src/apps/5_web_frontend/entrypoint.sh /app/entrypoint.sh

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

# Pre-generar el frontend Reflex (.web) y parchear Vite (allowedHosts) durante
# el build, para que el arranque del contenedor no reescriba la config en
# caliente (evita el error "host not allowed" y reinicios del dev server).
ENV PYTHONPATH=/app
RUN cd /app/src/apps/5_web_frontend \
    && reflex init --name web_frontend --loglevel info \
    && python patch_vite_config.py || true

# SEGURIDAD: En producción, eliminar archivos JSON de moks
RUN if [ "$ENVIRONMENT" = "pro" ]; then \
        echo "PRODUCCIÓN: Eliminando archivos moks por seguridad..." && \
        rm -rf /app/src/2_shared_application/moks && \
        echo "Moks eliminados correctamente"; \
    fi

EXPOSE 8005

RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
