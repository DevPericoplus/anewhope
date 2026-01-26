# Dockerfile para Redis en entorno de desarrollo (dev)
# Basado en la imagen oficial de Redis 8.4.0
# https://hub.docker.com/_/redis

FROM redis:8.4.0-bookworm

# Metadata
LABEL maintainer="DevOps Team <ops@company.com>"
LABEL environment="development"
LABEL service="redis"
LABEL version="8.4.0"

# Crear directorios necesarios
RUN mkdir -p /var/lib/redis /var/log/redis && \
    chown -R redis:redis /var/lib/redis /var/log/redis && \
    chmod 750 /var/lib/redis /var/log/redis

# Copiar configuración personalizada
COPY redis.conf /usr/local/etc/redis/redis.conf

# Ajustar permisos de la configuración
RUN chown redis:redis /usr/local/etc/redis/redis.conf && \
    chmod 640 /usr/local/etc/redis/redis.conf

# Volúmenes para persistencia y logs
VOLUME ["/var/lib/redis", "/var/log/redis"]

# Puerto de Redis
EXPOSE 6379

# Ejecutar Redis con la configuración personalizada
# Nota: Redis se ejecuta como usuario 'redis' (no root)
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD redis-cli ping || exit 1
