# 🐳 Despliegue de Redis con Docker para dev, pre y pro

## 📋 Resumen

Este documento describe la dockerización completa de Redis para los entornos Linux (dev, pre, pro) del servidor frontend. La solución incluye Dockerfiles, scripts de automatización y orquestación con Docker Compose.

**Fecha de creación:** 2026-01-26  
**Basado en:** Imagen oficial Redis 8.4.0 (https://hub.docker.com/_/redis)  
**Entornos:** dev, pre, pro (Linux)  
**Excluido:** macbook (instalación nativa con Homebrew)

---

## 🎯 Objetivos Cumplidos

✅ **Dockerfiles** creados para cada entorno (dev, pre, pro)  
✅ **Scripts de automatización** (`build_and_run_docker.sh`) para cada entorno  
✅ **Docker Compose** actualizado en `infrastructure/servers/frontend/`  
✅ **Variables de entorno** configurables por entorno  
✅ **Volúmenes persistentes** para datos y logs  
✅ **Healthchecks** configurados  
✅ **Límites de recursos** (CPU, memoria) configurables  
✅ **Backups automáticos** incluidos en scripts  
✅ **Seguridad** reforzada en producción  
✅ **Documentación completa** por entorno

---

## 📁 Estructura de Archivos Creados

```
infrastructure/
├── redis/
│   ├── dev/
│   │   ├── Dockerfile                      # ✅ NUEVO
│   │   ├── build_and_run_docker.sh         # ✅ NUEVO (ejecutable)
│   │   ├── redis.conf                      # ✅ Existente
│   │   └── README.md                       # ✅ Existente
│   ├── pre/
│   │   ├── Dockerfile                      # ✅ NUEVO
│   │   ├── build_and_run_docker.sh         # ✅ NUEVO (ejecutable)
│   │   ├── redis.conf                      # ✅ Existente
│   │   └── README.md                       # ✅ Existente
│   └── pro/
│       ├── Dockerfile                      # ✅ NUEVO
│       ├── build_and_run_docker.sh         # ✅ NUEVO (ejecutable)
│       ├── redis.conf                      # ✅ Existente
│       └── README.md                       # ✅ Existente
│
└── servers/
    └── frontend/
        ├── docker-compose.yml              # ✅ ACTUALIZADO
        ├── .env.example                    # ✅ NUEVO
        ├── README.md                       # ✅ NUEVO
        └── nginx/
            └── nginx.conf                  # ✅ Existente
```

---

## 🐋 Dockerfiles Creados

### Características Comunes

- **Imagen base:** `redis:8.4.0-bookworm` (Debian stable)
- **Usuario:** `redis` (no root, por seguridad)
- **Puerto:** 6379
- **Volúmenes:** `/var/lib/redis` (datos), `/var/log/redis` (logs)
- **Healthcheck:** `redis-cli ping`
- **Configuración:** Copiada desde `redis.conf` de cada entorno

### Diferencias por Entorno

| Aspecto | DEV | PRE | PRO |
|---------|-----|-----|-----|
| **Healthcheck interval** | 30s | 20s | 15s |
| **Healthcheck retries** | 3 | 3 | 5 |
| **Permisos /var/lib/redis** | 750 | 750 | 700 |
| **Permisos redis.conf** | 640 | 640 | 600 |
| **USER directive** | No | No | Sí (redis) |
| **Security labels** | No | No | Sí |

---

## 🔧 Scripts de Automatización

### Comandos Disponibles

Todos los scripts (`build_and_run_docker.sh`) soportan los siguientes comandos:

```bash
./build_and_run_docker.sh build      # Construir imagen Docker
./build_and_run_docker.sh run        # Ejecutar contenedor
./build_and_run_docker.sh stop       # Detener contenedor
./build_and_run_docker.sh restart    # Reiniciar contenedor
./build_and_run_docker.sh logs       # Ver logs en tiempo real
./build_and_run_docker.sh status     # Ver estado del servicio
./build_and_run_docker.sh shell      # Abrir shell en el contenedor
./build_and_run_docker.sh clean      # Eliminar todo (requiere confirmación)
```

### Comandos Adicionales por Entorno

#### PRE y PRO
```bash
./build_and_run_docker.sh backup     # Realizar backup de datos
```

#### PRO (Producción)
```bash
./build_and_run_docker.sh restore    # Restaurar desde backup
./build_and_run_docker.sh audit      # Ver log de auditoría
```

### Características de los Scripts

**DEV:**
- Confirmación simple para operaciones destructivas
- Volúmenes: `redis-dev-data`, `redis-dev-logs`
- Imagen: `redis-dev:8.4.0`
- Contenedor: `redis-dev`

**PRE:**
- Confirmación reforzada (`SI-CONFIRMO`)
- Backup automático antes de reiniciar/detener
- Límites de recursos: 2GB RAM, 2 CPUs
- Retención de backups: 30 días
- Volúmenes: `redis-pre-data`, `redis-pre-logs`
- Imagen: `redis-pre:8.4.0`
- Contenedor: `redis-pre`

**PRO:**
- **Requiere aprobación** para operaciones críticas (`APROBADO`)
- Backup automático antes de cualquier operación destructiva
- Log de auditoría de todas las operaciones
- Confirmación extrema para eliminación (`ELIMINAR-PRODUCCION`)
- Límites de recursos: 8GB RAM, 4 CPUs
- Retención de backups: 30 días
- Seguridad reforzada (`--security-opt no-new-privileges:true`)
- Volúmenes: `redis-pro-data`, `redis-pro-logs`
- Imagen: `redis-pro:8.4.0`
- Contenedor: `redis-pro`

---

## 🐳 Docker Compose Actualizado

### Ubicación
`infrastructure/servers/frontend/docker-compose.yml`

### Servicios Incluidos

```yaml
services:
  redis              # State manager compartido ✅ NUEVO
  nginx              # Reverse proxy (actualizado)
  web_frontend       # Aplicación pública (actualizado)
  web_backoffice     # Aplicación administrativa (actualizado)
  service_frontend   # Middleware
```

### Servicio Redis - Configuración

```yaml
redis:
  image: redis-${ENVIRONMENT}:8.4.0
  build:
    context: ../../../infrastructure/redis/${ENVIRONMENT}
  restart: always
  ports:
    - "6379:6379"
  volumes:
    - redis-data:/var/lib/redis
    - redis-logs:/var/log/redis
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 20s
    timeout: 3s
    retries: 3
  networks:
    - frontend-network
  deploy:
    resources:
      limits:
        cpus: "${REDIS_CPU_LIMIT}"
        memory: "${REDIS_MEMORY_LIMIT}"
```

### Variables de Entorno Necesarias

Ver `.env.example` en `infrastructure/servers/frontend/`

**Obligatorias:**
- `ENVIRONMENT`: `dev`, `pre` o `pro`
- `REDIS_CPU_LIMIT`: Límite de CPU (ej: `1.0`, `2.0`, `4.0`)
- `REDIS_MEMORY_LIMIT`: Límite de memoria (ej: `512m`, `2g`, `8g`)

**Opcionales:**
- `REDIS_CPU_RESERVATION`: CPU reservada
- `REDIS_MEMORY_RESERVATION`: Memoria reservada

### Integración con Otras Apps

**Frontend y Backoffice** ahora reciben variables de entorno de Redis:

```yaml
web_frontend:
  environment:
    REDIS_HOST: "redis"      # Nombre del servicio
    REDIS_PORT: "6379"
    REDIS_DB: "0"            # Compartida con backoffice
  depends_on:
    redis:
      condition: service_healthy  # Espera healthcheck
```

### Volúmenes Persistentes

```yaml
volumes:
  redis-data:
    name: redis-${ENVIRONMENT}-data
    driver: local
  redis-logs:
    name: redis-${ENVIRONMENT}-logs
    driver: local
```

### Red Interna

```yaml
networks:
  frontend-network:
    name: frontend-${ENVIRONMENT}-network
    driver: bridge
```

---

## 🚀 Guías de Uso

### Opción 1: Scripts Standalone (Un servidor)

Para desplegar **solo Redis** en un servidor:

```bash
# Ir al directorio del entorno
cd infrastructure/redis/dev/  # o pre/ o pro/

# Construir imagen
./build_and_run_docker.sh build

# Ejecutar contenedor
./build_and_run_docker.sh run

# Verificar estado
./build_and_run_docker.sh status

# Ver logs
./build_and_run_docker.sh logs
```

### Opción 2: Docker Compose (Servidor completo)

Para desplegar **todo el stack del servidor frontend**:

```bash
# Ir al directorio del servidor
cd infrastructure/servers/frontend/

# Configurar entorno
cp .env.example .env
nano .env  # Ajustar ENVIRONMENT, REDIS_MEMORY_LIMIT, etc.

# Construir todas las imágenes
docker-compose build

# Iniciar todos los servicios
docker-compose up -d

# Ver estado
docker-compose ps

# Ver logs
docker-compose logs -f redis
docker-compose logs -f web_frontend

# Detener todo
docker-compose down
```

---

## 🔐 Configuración de Seguridad

### DEV
- Protected mode: Yes
- Password: Requerido (desde `redis.conf`)
- Bind: 127.0.0.1 + IP del servidor
- Comandos peligrosos: Comentados (opcionales)

### PRE
- Protected mode: Yes (obligatorio)
- Password: Fuerte (desde `redis.conf`)
- Bind: 127.0.0.1 + IP específica
- Comandos peligrosos: **Deshabilitados** (renombrados)
- Firewall: Solo IPs autorizadas

### PRO
- Protected mode: Yes (CRÍTICO)
- Password: Muy fuerte 32+ caracteres (desde `redis.conf`)
- Bind: 127.0.0.1 + IP específica (NUNCA 0.0.0.0)
- Comandos peligrosos: **TOTALMENTE DESHABILITADOS**
- Firewall: Máximamente restrictivo
- Docker security: `--security-opt no-new-privileges:true`
- Auditoría: Log de todas las operaciones

**Nota:** Los passwords se configuran en los archivos `redis.conf` de cada entorno. Deben reemplazar el placeholder `<PASSWORD_XXX>` antes del despliegue.

---

## 💾 Persistencia y Backups

### Volúmenes Docker

Los datos se almacenan en volúmenes Docker nombrados:

```bash
# Listar volúmenes
docker volume ls | grep redis

# Inspeccionar volumen
docker volume inspect redis-dev-data

# Backup manual de volumen
docker run --rm \
  -v redis-dev-data:/data:ro \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/redis-backup-$(date +%Y%m%d).tar.gz -C /data .
```

### Backups Automáticos

**PRE y PRO** tienen backups automáticos integrados:

```bash
# Backup manual
./build_and_run_docker.sh backup

# El script crea:
# - Fuerza BGSAVE en Redis
# - Crea archivo .tar.gz comprimido
# - Guarda en ./backups/redis-{env}-backup-YYYYMMDD_HHMMSS.tar.gz
# - Limpia backups > 30 días (PRO)
```

**PRO** además:
- Backup automático antes de reiniciar
- Backup automático antes de detener
- Log de auditoría de cada backup

### Restauración

```bash
# PRO tiene comando dedicado
cd infrastructure/redis/pro/
./build_and_run_docker.sh restore

# PRE: manual
docker-compose stop redis
docker run --rm \
  -v redis-pre-data:/data \
  -v $(pwd)/backups:/backup:ro \
  alpine sh -c "cd /data && rm -rf * && tar xzf /backup/BACKUP_FILE.tar.gz"
docker-compose up -d redis
```

---

## 📊 Monitoreo

### Healthchecks

Docker Compose verifica automáticamente el estado de Redis:

```bash
# Ver estado de healthcheck
docker-compose ps redis

# Inspeccionar healthcheck
docker inspect redis-dev | jq '.[0].State.Health'
```

### Métricas de Redis

```bash
# Conectar a Redis CLI
docker-compose exec redis redis-cli

# Dentro de Redis CLI:
INFO server      # Información del servidor
INFO memory      # Uso de memoria
INFO stats       # Estadísticas
INFO persistence # Estado de persistencia
DBSIZE           # Número de keys
KEYS "reflex:session:*"  # Sesiones activas
```

### Logs

```bash
# Docker Compose
docker-compose logs -f redis
docker-compose logs --tail=100 redis

# Script standalone
./build_and_run_docker.sh logs

# Logs del sistema (dentro del contenedor)
docker-compose exec redis tail -f /var/log/redis/redis-server.log
```

---

## 🌐 Configuración por Entorno

### DEV

```bash
# .env
ENVIRONMENT=dev
REDIS_CPU_LIMIT=1.0
REDIS_MEMORY_LIMIT=512m
```

**Uso:**
- Desarrollo y pruebas locales
- Recursos mínimos
- Configuración permisiva

### PRE

```bash
# .env
ENVIRONMENT=pre
REDIS_CPU_LIMIT=2.0
REDIS_MEMORY_LIMIT=2g
```

**Uso:**
- Pruebas de pre-producción
- Configuración idéntica a producción
- Validación completa antes de PRO

### PRO

```bash
# .env
ENVIRONMENT=pro
REDIS_CPU_LIMIT=4.0
REDIS_MEMORY_LIMIT=8g
```

**Uso:**
- Sistema en vivo
- Máxima seguridad y estabilidad
- Backups automáticos obligatorios
- Monitoreo 24/7
- Alta disponibilidad recomendada

---

## 🚨 Troubleshooting

### Redis no inicia

```bash
# Ver logs
docker-compose logs redis
./build_and_run_docker.sh logs

# Verificar configuración
docker-compose config

# Verificar volúmenes
docker volume inspect redis-dev-data

# Recrear contenedor
docker-compose up -d --force-recreate redis
```

### Apps no conectan a Redis

```bash
# Verificar healthcheck
docker-compose ps redis

# Probar conectividad
docker-compose exec web_frontend ping redis

# Verificar variables de entorno
docker-compose exec web_frontend env | grep REDIS

# Verificar red Docker
docker network inspect frontend-dev-network
```

### Memoria llena

```bash
# Ver uso
docker-compose exec redis redis-cli INFO memory

# Ver keys más grandes
docker-compose exec redis redis-cli --bigkeys

# Aumentar límite (editar .env)
REDIS_MEMORY_LIMIT=4g

# Reiniciar con nuevo límite
docker-compose up -d redis
```

---

## 📚 Referencias

### Documentación del Proyecto
- **ADRs:** `src/docs/stack_of_technologies.adr`
  - ADR: Sesión Compartida Frontend/Backoffice usando Redis
  - ADR: Compatibilidad Redis 5.2.1 con Reflex 0.8.25
- **Implementación:** `docs/REDIS_IMPLEMENTATION.md`
- **Estado:** `docs/REDIS_IMPLEMENTATION_STATUS.md`
- **Guía de instalación macbook:** `infrastructure/redis/macbook/INSTALATION_GUIDE.md`
- **Guía servidor frontend:** `infrastructure/servers/frontend/README.md`

### Configuraciones por Entorno
- DEV: `infrastructure/redis/dev/README.md`
- PRE: `infrastructure/redis/pre/README.md`
- PRO: `infrastructure/redis/pro/README.md`

### Docker
- **Imagen oficial Redis:** https://hub.docker.com/_/redis
- **Docker Compose:** https://docs.docker.com/compose/
- **Dockerfile reference:** https://docs.docker.com/engine/reference/builder/

### Redis
- **Documentación oficial:** https://redis.io/docs/
- **Configuration:** https://redis.io/docs/management/config/
- **Persistence:** https://redis.io/docs/management/persistence/

---

## ✅ Checklist de Verificación

### Antes del Despliegue

- [ ] Archivo `redis.conf` revisado y placeholders reemplazados
- [ ] Password configurado en `redis.conf` (fuerte en PRE/PRO)
- [ ] Archivo `.env` creado y configurado
- [ ] Variables `ENVIRONMENT`, `REDIS_MEMORY_LIMIT`, `REDIS_CPU_LIMIT` definidas
- [ ] Volúmenes de almacenamiento verificados (espacio suficiente)
- [ ] Firewall configurado (PRE/PRO)
- [ ] Backup automático configurado (PRO)
- [ ] Monitoreo configurado (PRE/PRO)

### Después del Despliegue

- [ ] Redis responde a ping
- [ ] Healthcheck en estado "healthy"
- [ ] Frontend conecta a Redis
- [ ] Backoffice conecta a Redis
- [ ] Sesión se comparte entre frontend y backoffice
- [ ] Login/logout funciona correctamente
- [ ] Logs no muestran errores
- [ ] Persistencia funcionando (RDB + AOF)
- [ ] Backups funcionando (PRE/PRO)
- [ ] Monitoreo reportando métricas (PRE/PRO)

---

## 📊 Resumen de Archivos

**Total de archivos creados:** 10

| Archivo | Entorno | Tipo | Tamaño | Función |
|---------|---------|------|--------|---------|
| `Dockerfile` | dev | Docker | 1.1KB | Construcción de imagen |
| `build_and_run_docker.sh` | dev | Shell | 6.6KB | Automatización |
| `Dockerfile` | pre | Docker | 1.2KB | Construcción de imagen |
| `build_and_run_docker.sh` | pre | Shell | 8.0KB | Automatización + backup |
| `Dockerfile` | pro | Docker | 1.4KB | Construcción de imagen |
| `build_and_run_docker.sh` | pro | Shell | 14KB | Automatización + backup + auditoría |
| `docker-compose.yml` | frontend | YAML | 3.5KB | Orquestación de servicios |
| `.env.example` | frontend | ENV | 1.2KB | Plantilla de variables |
| `README.md` | frontend | MD | 8.4KB | Documentación de uso |
| `REDIS_DOCKER_DEPLOYMENT.md` | docs | MD | Este | Documentación general |

**Total:** ~45KB de código y documentación

---

**Fecha de creación:** 2026-01-26  
**Autor:** Equipo DevOps  
**Estado:** ✅ Completo y listo para despliegue  
**Próxima revisión:** Después del primer despliegue en DEV
