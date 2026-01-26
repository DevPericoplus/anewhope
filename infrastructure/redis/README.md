# Configuración de Redis por Entorno

Este directorio contiene las configuraciones de Redis específicas para cada entorno.

## 📂 Estructura

```
infrastructure/redis/
├── macbook/
│   └── redis.conf          # Configuración para desarrollo local (macOS)
├── dev/
│   └── redis.conf          # Configuración para entorno de desarrollo (pendiente)
├── pre/
│   └── redis.conf          # Configuración para entorno de pre-producción (pendiente)
├── pro/
│   └── redis.conf          # Configuración para entorno de producción (pendiente)
├── redis_requirements.txt   # Dependencias Python para Redis
└── README.md               # Este archivo
```

---

## 🖥️ macbook/ - Desarrollo Local

**Archivo:** `macbook/redis.conf`

**Configuración:**
- **Puerto:** 6379
- **Bind:** 127.0.0.1 (solo localhost)
- **Password:** PassRedis2025 (definido en `infrastructure/environments/macbook/protected_values.py`)
- **Persistencia:** AOF (Append Only File) habilitada
- **Modo protegido:** Activado

**Uso:**
```bash
# Iniciar Redis con configuración específica
redis-server infrastructure/redis/macbook/redis.conf

# O usar Homebrew (usa configuración por defecto)
brew services start redis

# Gestionar con script
./scripts/manage_redis.sh start
```

---

## 🌐 dev/ - Desarrollo

**Estado:** ✅ **Configuración lista para despliegue**

**Archivos:**
- `dev/redis.conf` - Configuración completa
- `dev/README.md` - Guía de despliegue

**Configuración:**
- Bind: Localhost + IP del servidor dev
- Puerto: 6379
- Password: Definido en `protected_values.py` (dev)
- Persistencia: RDB + AOF
- Maxmemory: 512MB
- Protected mode: Yes
- Comandos peligrosos: Comentados (opcional activar)

**Para desplegar:** Seguir guía en `dev/README.md`

---

## 🧪 pre/ - Pre-producción

**Estado:** ✅ **Configuración lista para despliegue**

**Archivos:**
- `pre/redis.conf` - Configuración idéntica a producción
- `pre/README.md` - Guía completa de despliegue

**Configuración:**
- Bind: Localhost + IP del servidor pre
- Puerto: 6379
- Password: Fuerte, definido en `protected_values.py` (pre)
- Persistencia: RDB + AOF (configuración conservadora)
- Maxmemory: 2GB
- Protected mode: Yes (obligatorio)
- Comandos peligrosos: **DESHABILITADOS**
- Monitoreo: Redis Exporter + Prometheus
- Backup: Automático diario + semanal

**Para desplegar:** Seguir guía en `pre/README.md`

---

## 🚀 pro/ - Producción

**Estado:** ✅ **Configuración lista para despliegue** (requiere aprobación)

**Archivos:**
- `pro/redis.conf` - Configuración máxima seguridad
- `pro/README.md` - Runbook completo de producción

**Configuración:**
- Bind: Localhost + IP del servidor pro (NUNCA 0.0.0.0)
- Puerto: 6379
- Password: Muy fuerte (32+ caracteres), definido en `protected_values.py` (pro)
- Persistencia: RDB + AOF + AOF-use-rdb-preamble
- Maxmemory: 8GB (ajustar según servidor)
- Protected mode: Yes (CRÍTICO)
- Comandos peligrosos: **TOTALMENTE DESHABILITADOS**
- TLS/SSL: Recomendado (configuración incluida)
- Monitoreo: Redis Exporter + Prometheus + Alertas
- Backup: Cifrado diario + semanal + mensual + almacenamiento remoto
- Alta disponibilidad: Opcional (Redis Sentinel)
- I/O threads: 4 (optimización)
- Lazy freeing: Configurado
- Auditoría de seguridad: Semanal

**Para desplegar:** 
1. Revisar checklist en `pro/README.md`
2. Obtener aprobación de operaciones
3. Planificar window de mantenimiento
4. Seguir procedimiento paso a paso

---

## 📋 Parámetros Comunes

Todos los entornos comparten estas variables (definidas en `env.yaml`):

```yaml
redis_host: <hostname_por_entorno>
redis_port: "6379"
redis_db: "0"                          # Base de datos 0 compartida entre frontend/backoffice
redis_token_expiration: "3600"         # 1 hora
redis_lock_expiration: "10000"         # 10 segundos
redis_lock_warning_threshold: "1000"   # 1 segundo
```

**Passwords:** Definidos en `infrastructure/environments/{entorno}/protected_values.py`

---

## 🔒 Seguridad

### Password Management
- **NO** commitear passwords en git
- Cada entorno tiene su propio `protected_values.py` con `redis_password`
- Usar passwords fuertes en pre y pro
- Rotar passwords periódicamente en producción

### Network Security
- **macbook:** Solo localhost (127.0.0.1)
- **dev/pre/pro:** Configurar bind específico o usar firewall
- **pro:** Considerar TLS/SSL para conexiones Redis

---

## 📦 Dependencias Python

**Archivo:** `redis_requirements.txt`

```txt
# Redis client compatible con Reflex 0.8.25
redis==5.2.1
# Parser optimizado en C
hiredis==2.3.2
```

**Instalación:**
```bash
# Frontend
cd src/apps/5_web_frontend
pip install -r ../../infrastructure/redis/redis_requirements.txt

# Backoffice
cd src/apps/6_web_backoffice
pip install -r ../../infrastructure/redis/redis_requirements.txt
```

---

## 🔧 Gestión

### Scripts Disponibles

**Gestión general:**
```bash
./scripts/manage_redis.sh install   # Instalar Redis
./scripts/manage_redis.sh start     # Iniciar servicio
./scripts/manage_redis.sh stop      # Detener servicio
./scripts/manage_redis.sh status    # Ver estado
./scripts/manage_redis.sh sessions  # Listar sesiones activas
```

**Monitoreo de sesiones:**
```bash
./scripts/monitor_redis_sessions.py              # Ver snapshot
./scripts/monitor_redis_sessions.py --continuous # Monitoreo continuo
```

**Verificación de integración:**
```bash
./scripts/verify_redis_integration.sh            # Verificar configuración
```

---

## 📚 Referencias

- **Documentación principal:** `README.md`
- **Implementación Redis:** `docs/REDIS_IMPLEMENTATION.md`
- **Estado de integración:** `docs/REDIS_IMPLEMENTATION_STATUS.md`
- **Tests:** `docs/REDIS_TESTS_STATUS.md`
- **Guía de testing:** `docs/INTEGRATION_COMPLETED.md`

---

**Última actualización:** 2026-01-26  
**Mantenido por:** Equipo de desarrollo anewhope
