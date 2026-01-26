# 📦 Guía de Instalación de Redis en macOS

## 🎯 Objetivo

Esta guía proporciona instrucciones paso a paso para instalar y configurar Redis desde cero en un macbook, listo para ser usado como backend de sesión compartida entre aplicaciones Reflex (frontend y backoffice).

---

## 📋 Pre-requisitos

### Sistema Operativo
- **macOS:** 10.15 (Catalina) o superior
- **Arquitectura:** Intel (x86_64) o Apple Silicon (ARM64)

### Software Requerido

1. **Homebrew** (gestor de paquetes para macOS)
   ```bash
   # Verificar si está instalado
   brew --version
   
   # Si no está instalado, instalarlo
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. **Python 3.13** (para scripts de monitoreo)
   ```bash
   # Verificar versión
   python3 --version
   
   # Debe ser Python 3.13.x
   ```

3. **Terminal** con permisos de administrador
   ```bash
   # Verificar que puedes ejecutar comandos con sudo
   sudo -v
   ```

---

## 🚀 Paso 1: Instalar Redis

### Opción A: Instalación Manual

```bash
# Actualizar Homebrew
brew update

# Instalar Redis
brew install redis

# Verificar instalación
redis-server --version
# Output esperado: Redis server v=8.4.0 (o superior)
```

### Opción B: Usar Script Automatizado

```bash
# Desde el directorio raíz del proyecto
cd /Users/administrator/develop/anewhope

# Ejecutar script de instalación
./scripts/manage_redis.sh install

# El script detectará si Redis ya está instalado y lo instalará si es necesario
```

**Output esperado:**
```
📦 Instalando Redis...
Instalando con Homebrew...
==> Downloading redis...
==> Installing redis...
✅ Redis instalado
Redis server v=8.4.0
```

---

## ⚙️ Paso 2: Configurar Redis

### 2.1. Ubicar Archivos de Configuración

Homebrew instala Redis con su configuración por defecto en:
```bash
/usr/local/etc/redis.conf  # Intel
# o
/opt/homebrew/etc/redis.conf  # Apple Silicon
```

**Nuestro proyecto usa una configuración personalizada:**
```
infrastructure/redis/macbook/redis.conf
```

### 2.2. Revisar Configuración Personalizada

Abrir y revisar el archivo de configuración del proyecto:

```bash
cat infrastructure/redis/macbook/redis.conf
```

**Parámetros clave configurados:**

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `bind` | `127.0.0.1` | Solo conexiones locales (seguridad) |
| `port` | `6379` | Puerto estándar de Redis |
| `protected-mode` | `no` | Desactivado (OK para localhost) |
| `dir` | `/usr/local/var/db/redis/` | Directorio de datos |
| `logfile` | `/usr/local/var/log/redis.log` | Archivo de logs |
| `loglevel` | `notice` | Nivel de detalle de logs |
| `appendonly` | `yes` | Persistencia AOF activada |
| `maxmemory` | `256mb` | Límite de memoria |
| `maxmemory-policy` | `allkeys-lru` | Política de eviction |

### 2.3. Crear Directorios Necesarios

```bash
# Crear directorios si no existen
sudo mkdir -p /usr/local/var/db/redis
sudo mkdir -p /usr/local/var/log

# Asignar permisos (usuario actual)
sudo chown -R $(whoami) /usr/local/var/db/redis
sudo chown -R $(whoami) /usr/local/var/log

# Verificar
ls -la /usr/local/var/db/redis
ls -la /usr/local/var/log
```

**Para Apple Silicon (ARM64):**
```bash
sudo mkdir -p /opt/homebrew/var/db/redis
sudo mkdir -p /opt/homebrew/var/log
sudo chown -R $(whoami) /opt/homebrew/var/db/redis
sudo chown -R $(whoami) /opt/homebrew/var/log
```

---

## 🔐 Paso 3: Configurar Password y Variables de Entorno

### 3.1. Configurar Password en protected_values.py

El password de Redis se gestiona desde la aplicación, no desde el archivo `redis.conf`.

**Verificar que existe en todos los entornos:**

```bash
# Macbook (desarrollo local)
cat infrastructure/environments/macbook/protected_values.py | grep redis_password
# Output: redis_password = "PassRedis2025"

# Dev
cat infrastructure/environments/dev/protected_values.py | grep redis_password

# Pre
cat infrastructure/environments/pre/protected_values.py | grep redis_password

# Pro
cat infrastructure/environments/pro/protected_values.py | grep redis_password
```

**Si no existe, añadirlo:**

```python
# En infrastructure/environments/macbook/protected_values.py
# (y en cada entorno con su password correspondiente)

# Redis (sesión compartida)
redis_password = "PassRedis2025"
```

### 3.2. Configurar Variables Públicas en env.yaml

**Verificar que existen:**

```bash
cat infrastructure/environments/macbook/env.yaml | grep redis
```

**Output esperado:**
```yaml
redis_host: localhost
redis_port: "6379"
redis_db: "0"
redis_token_expiration: "3600"
redis_lock_expiration: "10000"
redis_lock_warning_threshold: "1000"
```

**Si no existen, añadirlas:**

```yaml
# En infrastructure/environments/macbook/env.yaml

# Redis para sesión compartida
redis_host: localhost
redis_port: "6379"
redis_db: "0"
redis_token_expiration: "3600"      # 1 hora
redis_lock_expiration: "10000"      # 10 segundos
redis_lock_warning_threshold: "1000" # 1 segundo
```

---

## 🎬 Paso 4: Iniciar Redis

### Opción A: Como Servicio (Recomendado)

Redis se iniciará automáticamente en cada boot del sistema.

```bash
# Iniciar servicio
brew services start redis

# Verificar que está corriendo
brew services list | grep redis
# Output: redis  started  administrator  ~/Library/LaunchAgents/homebrew.mxcl.redis.plist
```

### Opción B: Manualmente con Configuración Personalizada

Redis se ejecutará solo mientras la terminal esté abierta.

```bash
# Desde el directorio raíz del proyecto
redis-server infrastructure/redis/macbook/redis.conf

# Mantener terminal abierta. Redis se detendrá al cerrarla.
```

### Opción C: Usar Script de Gestión

```bash
# Iniciar
./scripts/manage_redis.sh start

# Output:
# 🚀 Iniciando Redis...
# ✅ Redis iniciado
# PONG
```

---

## ✅ Paso 5: Verificar Instalación

### 5.1. Verificación Básica

```bash
# Test de conectividad
redis-cli ping
# Output esperado: PONG

# Versión de Redis
redis-server --version
# Output: Redis server v=8.4.0

# Estado del servicio
./scripts/manage_redis.sh status
```

**Output esperado del status:**
```
📊 Estado de Redis:

redis          started         administrator ~/Library/LaunchAgents/homebrew.mxcl.redis.plist

✅ Redis está respondiendo

redis_version:8.4.0
connected_clients:1
(integer) 0
```

### 5.2. Verificación de Configuración

```bash
# Conectar a Redis CLI
redis-cli

# Dentro de Redis CLI:
127.0.0.1:6379> INFO server
# Debe mostrar información del servidor

127.0.0.1:6379> CONFIG GET bind
# Debe mostrar: 1) "bind" 2) "127.0.0.1"

127.0.0.1:6379> CONFIG GET port
# Debe mostrar: 1) "port" 2) "6379"

127.0.0.1:6379> CONFIG GET maxmemory
# Debe mostrar el límite de memoria configurado

127.0.0.1:6379> CONFIG GET appendonly
# Debe mostrar: 1) "appendonly" 2) "yes"

# Salir
127.0.0.1:6379> EXIT
```

### 5.3. Test de Escritura/Lectura

```bash
# Escribir una key
redis-cli SET test:key "Hello Redis"
# Output: OK

# Leer la key
redis-cli GET test:key
# Output: "Hello Redis"

# Eliminar la key
redis-cli DEL test:key
# Output: (integer) 1

# Verificar que se eliminó
redis-cli GET test:key
# Output: (nil)
```

### 5.4. Verificar Persistencia

```bash
# Crear una key con TTL de 60 segundos
redis-cli SETEX test:ttl 60 "Expires in 60 seconds"

# Verificar TTL restante
redis-cli TTL test:ttl
# Output: número de segundos restantes (ej: 57)

# Forzar guardado en disco
redis-cli BGSAVE
# Output: Background saving started

# Verificar archivos de persistencia
ls -lh /usr/local/var/db/redis/
# Debe mostrar: dump.rdb y appendonly.aof
```

---

## 🔧 Paso 6: Instalar Dependencias Python

Para que las aplicaciones Reflex puedan conectarse a Redis:

```bash
# Activar entorno virtual del frontend
cd /Users/administrator/develop/anewhope
source src/apps/5_web_frontend/.venv_frontend313/bin/activate

# Instalar dependencias de Redis
pip install redis==5.2.1 hiredis==2.3.2

# Verificar instalación
pip show redis
# Output: Name: redis, Version: 5.2.1

# Desactivar entorno
deactivate

# Repetir para backoffice
source src/apps/6_web_backoffice/.venv_backoffice313/bin/activate
pip install redis==5.2.1 hiredis==2.3.2
deactivate
```

**Verificar que está en requirements.txt:**

```bash
# Frontend
grep redis src/apps/5_web_frontend/requirements.txt
# Output: redis==5.2.1
#         hiredis==2.3.2

# Backoffice
grep redis src/apps/6_web_backoffice/requirements.txt
# Output: redis==5.2.1
#         hiredis==2.3.2
```

---

## 🔗 Paso 7: Configurar Integración con Reflex

### 7.1. Verificar rxconfig.py del Frontend

```bash
cat src/apps/5_web_frontend/rxconfig.py
```

**Debe contener:**

```python
import reflex as rx
import sys
import importlib.util
from pathlib import Path

# Cargar configuración dinámica
env_settings_path = Path(__file__).resolve().parent.parent.parent / "2_shared_application" / "config" / "env_settings.py"
spec = importlib.util.spec_from_file_location("env_settings", env_settings_path)
env_settings = importlib.util.module_from_spec(spec)
sys.modules["env_settings"] = env_settings
spec.loader.exec_module(env_settings)

# Obtener variables de Redis
REDIS_HOST = env_settings.get_env_value("redis_host", "localhost")
REDIS_PORT = int(env_settings.get_env_value("redis_port", "6379"))
REDIS_PASSWORD = env_settings.get_protected_value("redis_password", None)
REDIS_DB = int(env_settings.get_env_value("redis_db", "0"))

# Construir redis_url
if REDIS_PASSWORD:
    redis_url = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
else:
    redis_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# Configuración de Reflex
config = rx.Config(
    app_name="web_frontend",
    db_url="sqlite:///reflex.db",
    redis_url=redis_url,  # ← Redis como state manager
    env=rx.Env.PROD,
    backend_port=8005,
    api_url="https://tfmmyllm.ai",
    backend_host="0.0.0.0",
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
)
```

### 7.2. Verificar rxconfig.py del Backoffice

```bash
cat src/apps/6_web_backoffice/rxconfig.py
```

**Debe ser similar al frontend, pero con:**
- `app_name="web_backoffice"`
- `backend_port=8006`
- `api_url="https://tfmmyllm.ai/backoffice"`
- **Mismo `redis_db="0"`** (CRÍTICO para compartir estado)

---

## 🧪 Paso 8: Probar Integración Completa

### 8.1. Iniciar Frontend

```bash
cd src/apps/5_web_frontend
source .venv_frontend313/bin/activate
reflex run --loglevel debug

# Buscar en logs:
# "Connected to Redis at localhost:6379"
# "State manager: Redis"
```

**Verificar en otra terminal:**
```bash
redis-cli KEYS "reflex:*"
# Debe mostrar keys de Reflex si la conexión es exitosa
```

### 8.2. Iniciar Backoffice (en otra terminal)

```bash
cd src/apps/6_web_backoffice
source .venv_backoffice313/bin/activate
reflex run --loglevel debug --backend-port 8006

# Debe conectar al mismo Redis
```

### 8.3. Test de Sesión Compartida

1. **Abrir frontend:** `https://tfmmyllm.ai`
2. **Login con usuario de prueba**
3. **Verificar sesión en Redis:**
   ```bash
   ./scripts/manage_redis.sh sessions
   ```
   
   **Output esperado:**
   ```
   📋 Sesiones activas en Redis:
   
   🔑 reflex:session:TOKEN_AQUI
      ⏱️  Expira en 3598 segundos
   
   Total: 1 sesiones activas
   ```

4. **Navegar a backoffice:** Click en botón "Backoffice"
5. **Verificar que el usuario sigue logueado** (sesión compartida)
6. **Logout desde backoffice**
7. **Verificar que la sesión se eliminó de Redis:**
   ```bash
   ./scripts/manage_redis.sh sessions
   # Total: 0 sesiones activas
   ```

---

## 📊 Paso 9: Configurar Monitoreo (Opcional)

### 9.1. Script de Monitoreo de Sesiones

```bash
# Ver sesiones activas (una vez)
./scripts/monitor_redis_sessions.py

# Monitoreo continuo (actualización cada 5 segundos)
./scripts/monitor_redis_sessions.py --continuous

# Presionar Ctrl+C para salir
```

### 9.2. Monitoreo en Tiempo Real

```bash
# Ver todos los comandos ejecutados en Redis
./scripts/manage_redis.sh monitor

# Output en tiempo real:
# 1706289123.456789 [0 127.0.0.1:52341] "SET" "reflex:session:abc123" "..."
# 1706289124.567890 [0 127.0.0.1:52341] "GET" "reflex:session:abc123"
```

### 9.3. Comandos Útiles de Diagnóstico

```bash
# Información del servidor
redis-cli INFO server

# Estadísticas de memoria
redis-cli INFO memory

# Estadísticas de comandos
redis-cli INFO stats

# Clientes conectados
redis-cli CLIENT LIST

# Comandos lentos (slowlog)
redis-cli SLOWLOG GET 10

# Tamaño de la base de datos
redis-cli DBSIZE
```

---

## 🛠️ Gestión del Servicio

### Comandos Comunes

```bash
# Iniciar Redis
./scripts/manage_redis.sh start
# o: brew services start redis

# Detener Redis
./scripts/manage_redis.sh stop
# o: brew services stop redis

# Reiniciar Redis
./scripts/manage_redis.sh restart
# o: brew services restart redis

# Ver estado
./scripts/manage_redis.sh status
# o: brew services list | grep redis

# Abrir CLI
./scripts/manage_redis.sh cli
# o: redis-cli

# Ver sesiones activas
./scripts/manage_redis.sh sessions

# Monitorear en tiempo real
./scripts/manage_redis.sh monitor

# Limpiar base de datos (¡CUIDADO!)
./scripts/manage_redis.sh flush
```

### Inicio Automático en el Boot

Si Redis se instaló como servicio con Homebrew:

```bash
# Redis se iniciará automáticamente en cada boot
# Para verificar:
brew services list | grep redis

# Para desactivar inicio automático:
brew services stop redis

# Para reactivar:
brew services start redis
```

---

## 🚨 Troubleshooting

### Redis no inicia

**Síntoma:** `brew services start redis` no funciona

**Solución:**
```bash
# Ver logs de error
tail -100 /usr/local/var/log/redis.log

# Verificar que el puerto no está ocupado
lsof -i :6379

# Si está ocupado, matar el proceso
kill -9 $(lsof -t -i:6379)

# Intentar iniciar nuevamente
brew services restart redis
```

### Redis no responde a ping

**Síntoma:** `redis-cli ping` no responde

**Solución:**
```bash
# Verificar que el proceso está corriendo
ps aux | grep redis-server

# Si no está corriendo, iniciarlo
brew services start redis

# Verificar conectividad
redis-cli -h 127.0.0.1 -p 6379 ping

# Ver logs
tail -f /usr/local/var/log/redis.log
```

### Aplicación no puede conectar a Redis

**Síntoma:** Error en logs de Reflex: "Cannot connect to Redis"

**Solución:**
```bash
# Verificar que Redis está corriendo
redis-cli ping

# Verificar variables de entorno
cat infrastructure/environments/macbook/env.yaml | grep redis
cat infrastructure/environments/macbook/protected_values.py | grep redis

# Verificar que redis está en requirements.txt
grep redis src/apps/5_web_frontend/requirements.txt

# Reinstalar dependencia
cd src/apps/5_web_frontend
source .venv_frontend313/bin/activate
pip install --force-reinstall redis==5.2.1 hiredis==2.3.2
```

### Sesiones no se comparten entre frontend y backoffice

**Síntoma:** Usuario debe loguearse dos veces

**Solución:**
```bash
# CRÍTICO: Verificar que ambas apps usan la MISMA base de datos
grep "redis_db" src/apps/5_web_frontend/rxconfig.py
grep "redis_db" src/apps/6_web_backoffice/rxconfig.py
# Ambos deben mostrar: redis_db = 0

# Verificar que SharedSessionState está siendo usado
grep "SharedSessionState" src/apps/5_web_frontend/web_frontend/web_frontend.py
grep "SharedSessionState" src/apps/6_web_backoffice/web_backoffice/web_frontend.py

# Reiniciar ambas aplicaciones
```

### Memoria llena

**Síntoma:** Redis rechaza escrituras: "OOM command not allowed"

**Solución:**
```bash
# Ver uso de memoria
redis-cli INFO memory | grep used_memory_human

# Ver límite configurado
redis-cli CONFIG GET maxmemory

# Aumentar límite temporalmente (hasta reinicio)
redis-cli CONFIG SET maxmemory 512mb

# Para cambio permanente, editar redis.conf:
nano infrastructure/redis/macbook/redis.conf
# Cambiar: maxmemory 512mb

# Reiniciar Redis
brew services restart redis
```

### Disco lleno (persistencia)

**Síntoma:** Redis no puede guardar RDB/AOF

**Solución:**
```bash
# Ver espacio en disco
df -h /usr/local/var/db/redis

# Ver tamaño de archivos de Redis
du -sh /usr/local/var/db/redis/*

# Limpiar archivos antiguos (¡CUIDADO!)
rm /usr/local/var/db/redis/dump.rdb.old
rm /usr/local/var/db/redis/appendonly.aof.old

# Limpiar logs antiguos
rm /usr/local/var/log/redis.log.*
```

---

## 🔄 Desinstalación (Si es necesario)

```bash
# Detener servicio
brew services stop redis

# Desinstalar Redis
brew uninstall redis

# Eliminar datos (opcional)
rm -rf /usr/local/var/db/redis
rm -rf /usr/local/var/log/redis.log

# Eliminar configuración de Homebrew
rm ~/Library/LaunchAgents/homebrew.mxcl.redis.plist
```

---

## 📚 Referencias

### Documentación Oficial
- **Redis Official:** https://redis.io/docs/
- **Redis Commands:** https://redis.io/commands/
- **Redis Configuration:** https://redis.io/docs/management/config/

### Documentación del Proyecto
- **Configuración macbook:** `infrastructure/redis/macbook/redis.conf`
- **Variables de entorno:** `infrastructure/environments/macbook/env.yaml`
- **Passwords:** `infrastructure/environments/macbook/protected_values.py`
- **Script de gestión:** `scripts/manage_redis.sh`
- **Documentación principal:** `README.md` (sección Redis)
- **Estado de implementación:** `docs/REDIS_IMPLEMENTATION_STATUS.md`

### Otros Entornos
- **Desarrollo (dev):** `infrastructure/redis/dev/README.md`
- **Pre-producción (pre):** `infrastructure/redis/pre/README.md`
- **Producción (pro):** `infrastructure/redis/pro/README.md`
- **Guía rápida:** `infrastructure/redis/QUICKSTART.md`

---

## ✅ Checklist de Verificación Final

Antes de considerar la instalación completa, verificar:

- [ ] Redis instalado con Homebrew
- [ ] Redis se inicia correctamente (`redis-cli ping` → PONG)
- [ ] Servicio configurado para inicio automático
- [ ] Directorios de datos y logs creados
- [ ] Archivo de configuración personalizado aplicado
- [ ] Variables en `env.yaml` configuradas
- [ ] Password en `protected_values.py` configurado
- [ ] Dependencias Python instaladas (`redis==5.2.1`)
- [ ] Frontend conecta a Redis correctamente
- [ ] Backoffice conecta a Redis correctamente
- [ ] Sesión se comparte entre frontend y backoffice
- [ ] Login/logout funciona correctamente
- [ ] Script de gestión funciona (`manage_redis.sh`)
- [ ] Monitoreo de sesiones funciona
- [ ] Persistencia AOF activada (archivos en `/usr/local/var/db/redis/`)

---

**Fecha de creación:** 2026-01-26  
**Versión de Redis:** 8.4.0  
**Sistema operativo:** macOS 13.6+  
**Python:** 3.13  
**Estado:** ✅ Documentación completa y verificada
