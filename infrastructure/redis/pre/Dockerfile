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

# Quitar los módulos que la imagen oficial trae bundled (RediSearch,
# RedisBloom, vectorset) — docker-entrypoint.sh los autocarga con
# --loadmodule por cada .so que encuentra en este directorio, sin que nada
# en redis.conf lo pida. No los usamos (Redis aquí es solo sesión/caché,
# nunca búsqueda ni bloom filters), y en x86_64 real (AWS, no la VM UTM
# arm64 de silicon/dev) RediSearch crashea al cargar: "Redis 8.4.0 crashed
# by signal: 11" dentro de getRedisConfigValue/SearchDisk_IsEnabled,
# reproducible al 100% en cada arranque. Encontrado 2026-09-21 al migrar
# pre — primera vez que esta imagen corre en x86_64 real.
RUN rm -rf /usr/local/lib/redis/modules/*

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
