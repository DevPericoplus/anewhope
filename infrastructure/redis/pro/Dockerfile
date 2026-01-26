# Dockerfile para Redis en entorno de PRODUCCIÓN (pro)
# Basado en la imagen oficial de Redis 8.4.0
# https://hub.docker.com/_/redis
# CRÍTICO: Máxima seguridad y estabilidad

FROM redis:8.4.0-bookworm

# Metadata
LABEL maintainer="DevOps Team <ops@company.com>"
LABEL environment="production"
LABEL service="redis"
LABEL version="8.4.0"
LABEL security="high"

# Crear directorios necesarios con permisos máximamente restrictivos
RUN mkdir -p /var/lib/redis /var/log/redis && \
    chown -R redis:redis /var/lib/redis /var/log/redis && \
    chmod 700 /var/lib/redis && \
    chmod 750 /var/log/redis

# Copiar configuración personalizada
COPY redis.conf /usr/local/etc/redis/redis.conf

# Ajustar permisos de la configuración (máxima seguridad)
RUN chown redis:redis /usr/local/etc/redis/redis.conf && \
    chmod 600 /usr/local/etc/redis/redis.conf

# Volúmenes para persistencia y logs
# CRÍTICO: Estos volúmenes deben tener backups automáticos en producción
VOLUME ["/var/lib/redis", "/var/log/redis"]

# Puerto de Redis
EXPOSE 6379

# Ejecutar Redis con la configuración personalizada
# Nota: Redis se ejecuta como usuario 'redis' (no root) - CRÍTICO para seguridad
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]

# Healthcheck estricto para producción
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=5 \
    CMD redis-cli ping || exit 1

# Security: Deshabilitar root login (Redis ya se ejecuta como 'redis')
USER redis
