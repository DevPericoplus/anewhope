# Servidor Frontend - Docker Compose

## 📋 Descripción

Este `docker-compose.yml` orquesta todos los servicios necesarios para el servidor frontend en entornos Linux (dev, pre, pro):

- **Redis**: State manager compartido entre frontend y backoffice
- **Nginx**: Reverse proxy y load balancer
- **Web Frontend**: Aplicación pública (puerto 8005)
- **Web Backoffice**: Aplicación administrativa (puerto 8006)
- **Service Frontend**: Middleware de servicios (puerto 8007)

---

## 🚀 Inicio Rápido

### 1. Configurar variables de entorno

```bash
# Copiar plantilla
cp .env.example .env

# Editar según entorno
nano .env
```

**Variables clave:**
- `ENVIRONMENT`: `dev`, `pre` o `pro`
- `REDIS_MEMORY_LIMIT`: Memoria para Redis (ej: `512m`, `2g`, `8g`)
- `REDIS_CPU_LIMIT`: CPUs para Redis (ej: `1.0`, `2.0`, `4.0`)

### 2. Construir imágenes

```bash
# Construir todas las imágenes
docker-compose build

# O construir servicios específicos
docker-compose build redis
docker-compose build web_frontend
docker-compose build web_backoffice
```

### 3. Iniciar servicios

```bash
# Iniciar todos los servicios
docker-compose up -d

# Ver logs
docker-compose logs -f

# Ver logs de un servicio específico
docker-compose logs -f redis
docker-compose logs -f web_frontend
```

### 4. Verificar estado

```bash
# Ver servicios corriendo
docker-compose ps

# Ver healthcheck de Redis
docker-compose ps redis

# Probar Redis
docker-compose exec redis redis-cli ping
# Debe responder: PONG
```

---

## 📦 Servicios

### Redis

**Propósito:** State manager compartido para sesiones entre frontend y backoffice.

**Configuración:**
- **Imagen:** Construida desde `infrastructure/redis/${ENVIRONMENT}/`
- **Puerto:** 6379
- **Volúmenes:** 
  - `redis-data` → `/var/lib/redis` (persistencia)
  - `redis-logs` → `/var/log/redis` (logs)
- **Healthcheck:** `redis-cli ping` cada 20s
- **Recursos:** Configurables por entorno vía `.env`

**Comandos útiles:**
```bash
# Ver logs de Redis
docker-compose logs -f redis

# Abrir shell en Redis
docker-compose exec redis /bin/bash

# Conectar a Redis CLI
docker-compose exec redis redis-cli

# Ver estadísticas
docker-compose exec redis redis-cli INFO
docker-compose exec redis redis-cli DBSIZE

# Ver sesiones activas
docker-compose exec redis redis-cli KEYS "reflex:session:*"
```

### Web Frontend

**Propósito:** Aplicación pública para usuarios finales.

**Configuración:**
- **Puerto:** 8005
- **Variables de entorno:**
  - `REDIS_HOST=redis` (nombre del servicio)
  - `REDIS_PORT=6379`
  - `REDIS_DB=0` (compartida con backoffice)
- **Depende de:** Redis (espera healthcheck)

### Web Backoffice

**Propósito:** Aplicación administrativa.

**Configuración:**
- **Puerto:** 8006
- **Variables de entorno:**
  - `REDIS_HOST=redis`
  - `REDIS_PORT=6379`
  - `REDIS_DB=0` (⚠️ CRÍTICO: mismo DB que frontend)
- **Depende de:** Redis (espera healthcheck)

### Nginx

**Propósito:** Reverse proxy y SSL termination.

**Configuración:**
- **Puertos:** 80 (HTTP), 443 (HTTPS)
- **Configuración:** `./nginx/nginx.conf`
- **Depende de:** Redis, Web Frontend, Web Backoffice

### Service Frontend

**Propósito:** Middleware de servicios.

**Configuración:**
- **Puerto:** 8007
- **Variables de entorno:** Ver `.env.example`

---

## 🔧 Gestión de Servicios

### Iniciar y Detener

```bash
# Iniciar todos los servicios
docker-compose up -d

# Iniciar servicios específicos
docker-compose up -d redis web_frontend

# Detener todos los servicios
docker-compose down

# Detener sin eliminar volúmenes
docker-compose stop

# Reiniciar un servicio
docker-compose restart redis
```

### Logs

```bash
# Ver logs de todos los servicios
docker-compose logs -f

# Ver logs de Redis
docker-compose logs -f redis

# Ver últimas 100 líneas
docker-compose logs --tail=100 redis

# Ver logs desde una fecha
docker-compose logs --since 2026-01-26T10:00:00 redis
```

### Escalado

```bash
# Escalar frontend (múltiples instancias)
docker-compose up -d --scale web_frontend=3

# Nota: Nginx debe estar configurado para load balancing
```

### Actualizar Servicios

```bash
# Reconstruir imágenes
docker-compose build --no-cache redis

# Recrear contenedores
docker-compose up -d --force-recreate redis

# Actualizar todo
docker-compose down && docker-compose build && docker-compose up -d
```

---

## 💾 Persistencia y Backups

### Volúmenes

Los datos de Redis se almacenan en volúmenes Docker nombrados:

```bash
# Listar volúmenes
docker volume ls | grep redis

# Inspeccionar volumen
docker volume inspect redis-dev-data

# Ver ubicación en host
docker volume inspect redis-dev-data | grep Mountpoint
```

### Backup de Redis

**Opción 1: Usar script de gestión**

```bash
# Desde infrastructure/redis/{dev,pre,pro}/
./build_and_run_docker.sh backup
```

**Opción 2: Manual**

```bash
# Forzar guardado
docker-compose exec redis redis-cli BGSAVE

# Copiar archivos de persistencia
docker run --rm \
  -v redis-dev-data:/data:ro \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/redis-backup-$(date +%Y%m%d).tar.gz -C /data .
```

### Restaurar Backup

```bash
# Detener Redis
docker-compose stop redis

# Restaurar datos
docker run --rm \
  -v redis-dev-data:/data \
  -v $(pwd)/backups:/backup:ro \
  alpine sh -c "cd /data && rm -rf * && tar xzf /backup/redis-backup-YYYYMMDD.tar.gz"

# Iniciar Redis
docker-compose up -d redis
```

---

## 🌐 Configuración por Entorno

### DEV (Desarrollo)

```bash
# .env
ENVIRONMENT=dev
REDIS_MEMORY_LIMIT=512m
REDIS_CPU_LIMIT=1.0
```

**Características:**
- Recursos mínimos
- Reinicio: `unless-stopped`
- Logs: stdout
- Ideal para pruebas

### PRE (Pre-producción)

```bash
# .env
ENVIRONMENT=pre
REDIS_MEMORY_LIMIT=2g
REDIS_CPU_LIMIT=2.0
```

**Características:**
- Configuración idéntica a producción
- Recursos medios
- Reinicio: `always`
- Backups automáticos recomendados

### PRO (Producción)

```bash
# .env
ENVIRONMENT=pro
REDIS_MEMORY_LIMIT=8g
REDIS_CPU_LIMIT=4.0
ACTIVE_SYNC_DB_JSONS=0
```

**Características:**
- Máximos recursos
- Reinicio: `always`
- Healthchecks estrictos
- Backups automáticos obligatorios
- Monitoring configurado
- Alta disponibilidad recomendada

---

## 🔍 Troubleshooting

### Redis no inicia

```bash
# Ver logs
docker-compose logs redis

# Verificar configuración
docker-compose config

# Verificar volúmenes
docker volume inspect redis-dev-data

# Recrear contenedor
docker-compose up -d --force-recreate redis
```

### Frontend/Backoffice no conectan a Redis

```bash
# Verificar que Redis está healthy
docker-compose ps redis

# Probar conexión desde frontend
docker-compose exec web_frontend ping redis

# Verificar variables de entorno
docker-compose exec web_frontend env | grep REDIS

# Verificar red
docker network inspect frontend-dev-network
```

### Sesiones no se comparten

**Verificar que ambas apps usan el mismo DB:**
```bash
docker-compose exec web_frontend env | grep REDIS_DB
docker-compose exec web_backoffice env | grep REDIS_DB
# Ambos deben ser: REDIS_DB=0
```

### Memoria llena en Redis

```bash
# Ver uso de memoria
docker-compose exec redis redis-cli INFO memory

# Ver keys más grandes
docker-compose exec redis redis-cli --bigkeys

# Limpiar sesiones expiradas (Redis lo hace automáticamente)
# O forzar flush (¡CUIDADO!)
docker-compose exec redis redis-cli FLUSHDB
```

---

## 📚 Referencias

**Documentación del proyecto:**
- ADR Sesión Compartida: `src/docs/stack_of_technologies.adr`
- Implementación Redis: `docs/REDIS_IMPLEMENTATION.md`
- Estado de implementación: `docs/REDIS_IMPLEMENTATION_STATUS.md`

**Configuraciones de Redis:**
- DEV: `infrastructure/redis/dev/`
- PRE: `infrastructure/redis/pre/`
- PRO: `infrastructure/redis/pro/`

**Docker Compose:**
- https://docs.docker.com/compose/
- https://docs.docker.com/compose/compose-file/

**Redis:**
- Imagen oficial: https://hub.docker.com/_/redis
- Documentación: https://redis.io/docs/

---

## ⚙️ Variables de Entorno Completas

Consultar `.env.example` para la lista completa de variables configurables.

**Obligatorias:**
- `ENVIRONMENT`: Entorno de despliegue
- `REDIS_MEMORY_LIMIT`: Límite de memoria para Redis
- `REDIS_CPU_LIMIT`: Límite de CPU para Redis

**Opcionales:**
- `REDIS_MEMORY_RESERVATION`: Memoria reservada
- `REDIS_CPU_RESERVATION`: CPU reservada
- `ACTIVE_SYNC_DB_JSONS`: Sincronización DB/JSON
- `SYNC_DATABASE_INTERVAL_SECONDS`: Intervalo de sync
- `BROKER_BACKEND_BASE_URL`: URL del broker

---

**Última actualización:** 2026-01-26  
**Mantenido por:** Equipo DevOps
