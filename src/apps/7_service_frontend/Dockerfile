ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

# Argumento para definir el entorno (dev, pre, pro)
# Para producción: docker build --build-arg ENVIRONMENT=pro ...
ARG ENVIRONMENT=dev

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=${ENVIRONMENT}

# Herramientas de compilación: en arm64 algunos paquetes (p.ej. hiredis) no
# tienen wheel y deben compilarse desde fuente (requieren gcc + headers).
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY src/apps/7_service_frontend/requirements.txt /app/requirements.txt
COPY src/apps/7_service_frontend/.env.example /app/.env.example
COPY src/apps/7_service_frontend/entrypoint.sh /app/entrypoint.sh

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

# SEGURIDAD: En producción, eliminar archivos JSON de moks
# Estos archivos son solo para desarrollo/pruebas sin base de datos
RUN if [ "$ENVIRONMENT" = "pro" ]; then \
        echo "PRODUCCIÓN: Eliminando archivos moks por seguridad..." && \
        rm -rf /app/src/2_shared_application/moks && \
        echo "Moks eliminados correctamente"; \
    fi

EXPOSE 8007

RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
