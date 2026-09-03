ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

# Entorno (dev, pre, pro, silicon)
ARG ENVIRONMENT=dev

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=${ENVIRONMENT}

# Herramientas de compilación por si algún paquete no tiene wheel arm64.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential python3-dev \
    && rm -rf /var/lib/apt/lists/*

# El daemon del foro reutiliza el router de backend_core y capas compartidas,
# por lo que sus dependencias son las del backend_core (fastapi, uvicorn,
# SQLAlchemy, PyMySQL, ...).
COPY src/apps/3_backend/requirements.txt /app/requirements.txt
COPY src/apps/9_laimweb/laim_forum_daemon/entrypoint.sh /app/entrypoint.sh

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

RUN if [ "$ENVIRONMENT" = "pro" ]; then \
        rm -rf /app/src/2_shared_application/moks; \
    fi

EXPOSE 8766

RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
