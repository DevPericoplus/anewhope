# NOTA: Usa Python 3.12 por compatibilidad con TensorFlow/Keras
FROM python:3.12-slim

WORKDIR /app

# Argumento para definir el entorno (dev, pre, pro)
# Para producción: docker build --build-arg ENVIRONMENT=pro ...
ARG ENVIRONMENT=dev

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=${ENVIRONMENT}

COPY src/apps/4_trainer/requirements.txt /app/requirements.txt
COPY src/apps/4_trainer/entrypoint.sh /app/entrypoint.sh

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

# SEGURIDAD: En producción, eliminar archivos JSON de moks
RUN if [ "$ENVIRONMENT" = "pro" ]; then \
        echo "PRODUCCIÓN: Eliminando archivos moks por seguridad..." && \
        rm -rf /app/src/2_shared_application/moks && \
        echo "Moks eliminados correctamente"; \
    fi

EXPOSE 8004

RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
