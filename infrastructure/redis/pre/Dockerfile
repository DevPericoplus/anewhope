# Dockerfile para Redis en entorno de pre-producción (pre)
# Basado en la imagen oficial de Redis 8.4.0
# https://hub.docker.com/_/redis
# IMPORTANTE: Esta configuración debe ser idéntica a producción

ARG REDIS_VERSION=8.4.0
FROM redis:${REDIS_VERSION}-bookworm

# Metadata
LABEL maintainer="DevOps Team <ops@company.com>"
LABEL environment="pre-production"
LABEL service="redis"
LABEL version="${REDIS_VERSION}"

# Crear directorios necesarios con permisos estrictos
RUN mkdir -p /var/lib/redis /var/log/redis && \
    chown -R redis:redis /var/lib/redis /var/log/redis && \
    chmod 750 /var/lib/redis /var/log/redis

# Copiar configuración personalizada
COPY redis.conf /usr/local/etc/redis/redis.conf

# Ajustar permisos de la configuración (más restrictivos)
RUN chown redis:redis /usr/local/etc/redis/redis.conf && \
    chmod 640 /usr/local/etc/redis/redis.conf

# Volúmenes para persistencia y logs
VOLUME ["/var/lib/redis", "/var/log/redis"]

# Puerto de Redis
EXPOSE 6379

# Ejecutar Redis con la configuración personalizada
# Nota: Redis se ejecuta como usuario 'redis' (no root) por seguridad
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]

# Healthcheck más estricto que dev
HEALTHCHECK --interval=20s --timeout=3s --start-period=10s --retries=3 \
    CMD redis-cli ping || exit 1
