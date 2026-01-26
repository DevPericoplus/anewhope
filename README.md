# Anewhope

Proyecto para gestionar infraestructura, aplicaciones y flujos de personalización de modelos LLM.

## Estructura principal

- `info.txt`: guía rápida para crear y activar el entorno virtual, además de notas de operación.
- `infrastructure/environments/<entorno>/protected_values.py`: variables sensibles por entorno.
- `README_DEPLOYMENT.md`: guía de despliegue con verificación SQL y estructura de base de datos.
- `src/`: monorepo con organización hexagonal y dominios compartidos.
  - `main.py`: punto de entrada central para orquestar servicios.
  - `config/`: configuración compartida.
  - `tests/`: pruebas comunes.
  - `1_shared_domain/`: entidades y reglas de negocio reutilizables.
    - `entities/`
    - `business_rules/`
  - `2_shared_application/`: contratos y DTOs compartidos.
    - `interfaces/`
    - `dtos/`
    - `security/`: librería de utilidades criptográficas y secretos (`custom_cipher_lib.py`, `basesecuritypass.json`).
  - `apps/`: implementaciones específicas por servicio.
    - `3_backend/`: API REST principal (gestión y orquestación).
      - `1_domain/`
      - `2_application/`
      - `3_adapters/` (incluye `controllers/` y `mappers/`)
      - `4_infrastructure/` (`persistence/`, `web/`)
    - `4_trainer/`: servicio de entrenamiento y fine-tuning.
      - `1_domain/`
      - `2_application/`
      - `3_adapters/` (`controllers/`)
      - `4_infrastructure/` (`gpu_processor/`, `web/`)
    - `5_web_frontend/`: cliente web basado en Reflex.
      - `__init__.py`
      - `frontend_reflex/` (`__init__.py`, `components/`, `pages/`)
      - `adapters/` (`api_client.py`)
- `monorepo_llm_personalizado/`: estructura de referencia en español utilizada para planificar la migración a `src/`.
- `infrastructure/`: scripts y utilidades adicionales (pendiente de completar).
- `test/`: pruebas heredadas o de exploración.

## Configuración por entorno

### Estructura de configuración

El proyecto soporta configuración personalizada por entorno usando tres niveles de archivos:

1. **`.env`** (raíz del proyecto): Selecciona el entorno activo
   ```
   environment: macbook
   ```
   o en formato shell:
   ```
   ENVIRONMENT=macbook
   ```

2. **`infrastructure/environments/<entorno>/env.yaml`**: Variables públicas y comunes
   - `storage_mode`: modo de almacenamiento (`mock`, `mock_and_db`, `db_only`)
   - `active_sync_db_jsons`: habilita/deshabilita sincronización DB/JSON (`"0"` o `"1"`)
   - `broker_backend_base_url`: URL del broker backend
   - `core_backend_base_url`: URL del backend core
   - `middleware_base_url`: URL del middleware
   - `fmanagement_base_url`: URL de la API de gestión de ficheros
   - `permissions_source`: fuente de permisos (`mock` o `db`)
   - `sync_database_interval_seconds`: intervalo de sincronización en segundos

3. **`infrastructure/environments/<entorno>/protected_values.py`**: Variables sensibles
   - Credenciales de MariaDB
   - Secrets JWT
   - Claves de encriptación
   - Tokens de servicios externos

### Entornos disponibles

- **`macbook`**: Desarrollo local en macOS 14.8.1
- **`dev`**: Máquinas virtuales VirtualBox con Oracle Linux 10
- **`pre`**: Instancias AWS con Oracle Linux 10 (preproducción)
- **`pro`**: Instancias AWS con Oracle Linux 10 (producción)

### Orden de carga

Las aplicaciones cargan la configuración en este orden:
1. `.env` → determina el entorno activo
2. `env.yaml` del entorno → variables públicas
3. `protected_values.py` del entorno → variables sensibles

### Uso en código

Todas las aplicaciones deben usar el helper centralizado para cargar configuración:

```python
from src.2_shared_application.config.env_settings import (
    get_environment_name,
    get_env_value,
    get_protected_value,
    load_protected_settings
)

# Obtener el entorno activo
env = get_environment_name()  # "macbook", "dev", "pre", "pro"

# Leer variable pública
storage_mode = get_env_value("storage_mode", "mock")

# Leer variable sensible
db_password = get_protected_value("writer_password")

# O cargar todos los valores protegidos
settings = load_protected_settings()
```

### Exportador de variables

Para generar un archivo de variables de entorno compatible con scripts shell o Docker:

```bash
# Formato shell
python infrastructure/export_env.py --environment macbook

# Formato envfile para Docker
python infrastructure/export_env.py --environment macbook --format envfile
```

## Entornos y plataformas

- `macbook`: desarrollo local en macOS 14.8.1 (equipo único que asume util01, frontend, backend, trainer).
- `dev`: virtualización en VirtualBox con Oracle Linux 10 (util01, frontend, backend, trainer).
- `pre` y `pro`: instancias en AWS con Oracle Linux 10 (util01, frontend, backend, trainer).

## Estrategia de Dockerfiles y despliegue

### Dockerfiles por aplicación

Cada aplicación en `src/apps/*` tiene su propio `Dockerfile` y un script `docker_execution.sh` 
que facilita la construcción y ejecución del contenedor:

- `src/apps/3_backend/Dockerfile` y `docker_execution.sh`
- `src/apps/5_web_frontend/Dockerfile` y `docker_execution.sh`
- `src/apps/6_web_backoffice/Dockerfile` y `docker_execution.sh`
- `src/apps/7_service_frontend/Dockerfile` y `docker_execution.sh`
- `src/apps/8_service_backend/Dockerfile` y `docker_execution.sh`

El script `docker_execution.sh` de cada aplicación:
1. Carga las variables de entorno desde `.env` y `env.yaml` del entorno activo
2. Construye la imagen Docker con `docker build`
3. Ejecuta el contenedor exponiendo el puerto fijo de la aplicación

Ejemplo de uso:
```bash
cd src/apps/7_service_frontend
bash docker_execution.sh
```

### Docker Compose por servidor

Los archivos `docker-compose.yml` están organizados por servidor en `infrastructure/servers/*` 
y agrupan los servicios que se ejecutarán juntos en cada servidor:

- `infrastructure/servers/frontend/docker-compose.yml`: `nginx`, `5_web_frontend`, 
  `6_web_backoffice`, `7_service_frontend`
- `infrastructure/servers/backend/docker-compose.yml`: `8_service_backend`, `3_backend`, 
  `fmanagement` (Go API), `mariadb`
- `infrastructure/servers/trainer/docker-compose.yml`: `4_trainer` (placeholder), 
  `keras_service` (placeholder)
- `infrastructure/servers/macbook/docker-compose.yml`: solo aplicaciones internas 
  (MariaDB y Keras nativos)

### Servidor frontend (Linux)

- `infrastructure/servers/frontend/docker-compose.yml`: `nginx`, `5_web_frontend`,
  `6_web_backoffice`, `7_service_frontend`.
- Plantilla Nginx para ansible:
  `infrastructure/servers/frontend/nginx/nginx.conf.template`.

### Servidor backend (Linux)

- `infrastructure/servers/backend/docker-compose.yml`: `8_service_backend`,
  `3_backend`, `fmanagement` (imagen externa), `mariadb`.

### Servidor trainer (Linux)

- `infrastructure/servers/trainer/docker-compose.yml`: `4_trainer` (placeholder),
  `keras_service` (placeholder).
- En macOS se instalará TensorFlow CPU en un venv ` .env_trainer` y Keras 2.15
  con TensorFlow 2.15. [Keras getting started](https://keras.io/getting_started/)

### Macbook (local)

- `infrastructure/servers/macbook/docker-compose.yml` solo contiene aplicaciones internas.
- MariaDB se usa nativa (instalada).
- Nginx se instala con Homebrew y se configura con:
  `infrastructure/servers/macbook/nginx/nginx.conf`.

#### Prerrequisitos para Nginx en macbook

**Herramientas necesarias (se verifican automáticamente):**
- **Homebrew**: Gestor de paquetes para macOS
  ```bash
  # Instalar si no está disponible
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  ```

- **OpenSSL**: Ya instalado en el sistema (OpenSSL 3.5.4)
  - Ubicación: `/opt/local/bin/openssl`
  - Usado para generar certificados SSL/TLS autofirmados

**Herramientas recomendadas para desarrollo local:**
- **mkcert**: Genera certificados locales de confianza automáticamente
  ```bash
  # Instalar con Homebrew
  brew install mkcert nss
  
  # Instalar la CA local (solo una vez)
  mkcert -install
  ```

##### Generación de certificado SSL para tfmmyllm.ai (desarrollo local)

**Prerequisito obligatorio: Instalar mkcert**

Si mkcert no está instalado en tu sistema, debes instalarlo primero:

```bash
# Instalar mkcert y nss con Homebrew
brew install mkcert nss

# Instalar la Certificate Authority (CA) local
mkcert -install
```

Este paso es **obligatorio** antes de generar certificados. El comando `mkcert -install` instalará una CA local confiable en tu sistema, permitiendo que los navegadores acepten los certificados sin advertencias de seguridad.

---

**Paso 1: Preparar el directorio de certificados**
```bash
# Crear directorio para almacenar certificados
mkdir -p infrastructure/certificates/macbook
```

**Paso 2: Configurar /etc/hosts (si no está configurado)**
```bash
# Añadir entrada al archivo hosts
echo "127.0.0.1       tfmmyllm.ai" | sudo tee -a /etc/hosts
```

**Paso 3: Generar certificado con mkcert**

**Opción A - Usar el script automatizado (recomendado):**
```bash
# Ejecutar el script de generación
cd infrastructure/certificates/macbook
./generate_certs.sh
```

El script verificará las dependencias, generará los certificados y mostrará información detallada.

**Opción B - Comando manual:**
```bash
# Navegar al directorio de certificados
cd infrastructure/certificates/macbook

# Generar certificado para tfmmyllm.ai y wildcard
mkcert -key-file tfmmyllm.ai-key.pem \
       -cert-file tfmmyllm.ai.pem \
       tfmmyllm.ai "*.tfmmyllm.ai" localhost 127.0.0.1 ::1
```

**Archivos generados:**
- `tfmmyllm.ai.pem` - Certificado público
- `tfmmyllm.ai-key.pem` - Clave privada

**Dominios incluidos en el certificado:**
- `tfmmyllm.ai` (dominio principal)
- `*.tfmmyllm.ai` (wildcard para subdominios: www, api, backoffice, etc.)
- `localhost`, `127.0.0.1`, `::1` (aliases locales)

**Paso 4: Verificar el certificado generado**
```bash
# Ver información del certificado
openssl x509 -in tfmmyllm.ai.pem -text -noout | grep -A 2 "Subject:"

# Ver fecha de expiración
openssl x509 -in tfmmyllm.ai.pem -noout -dates

# Ver todos los dominios incluidos (SANs)
openssl x509 -in tfmmyllm.ai.pem -noout -text | grep -A 1 "Subject Alternative Name"
```

**Validez del certificado:**
- mkcert genera certificados con validez predeterminada según su versión
- Versiones recientes: ~10 años (3650 días)
- La validez exacta depende de la versión instalada de mkcert

**Renovación del certificado:**

Si el certificado expira o necesitas regenerarlo:

```bash
# Opción 1: Regenerar con el mismo comando
cd infrastructure/certificates/macbook
mkcert -key-file tfmmyllm.ai-key.pem \
       -cert-file tfmmyllm.ai.pem \
       tfmmyllm.ai "*.tfmmyllm.ai" localhost 127.0.0.1 ::1

# Opción 2: Reinstalar la CA de mkcert (si hay problemas de confianza)
mkcert -uninstall
mkcert -install
# Luego regenerar el certificado con el comando anterior

# Opción 3: Verificar y actualizar mkcert
brew upgrade mkcert
mkcert -install
```

**Después de regenerar, reiniciar nginx:**
```bash
./deploy_nginx_macbook.sh
```

**Notas importantes:**
- Los certificados de mkcert son automáticamente confiables en navegadores
- No generan advertencias de seguridad en desarrollo local
- Los archivos de certificados NO deben commiterse a git (ya están en `.gitignore`)
- Para producción, usar certificados de Let's Encrypt o una CA comercial

**Configuración de nginx con SSL:**

Los certificados se almacenan en la ruta del proyecto y nginx los referencia mediante rutas absolutas:

**Ubicación de los certificados:**
```
/Users/administrator/develop/anewhope/infrastructure/certificates/macbook/
├── tfmmyllm.ai.pem           # Certificado público
└── tfmmyllm.ai-key.pem       # Clave privada
```

**Configuración en nginx:**

El archivo `infrastructure/servers/macbook/nginx/nginx.conf` referencia los certificados con rutas absolutas:

```nginx
http {
    # Configuración SSL global
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Servidor HTTP (puerto 8080) - Redirección a HTTPS
    server {
        listen 8080;
        server_name tfmmyllm.ai *.tfmmyllm.ai;
        return 301 https://$host$request_uri;
    }

    # Servidor HTTPS (puerto 443)
    server {
        listen 443 ssl;
        server_name tfmmyllm.ai *.tfmmyllm.ai;
        
        # Certificados SSL (rutas absolutas)
        ssl_certificate /Users/administrator/develop/anewhope/infrastructure/certificates/macbook/tfmmyllm.ai.pem;
        ssl_certificate_key /Users/administrator/develop/anewhope/infrastructure/certificates/macbook/tfmmyllm.ai-key.pem;
        
        # Configuración SSL adicional
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;
        
        # Proxy al frontend
        location / {
            proxy_pass http://127.0.0.1:8005;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # Proxy al backoffice
        location /backoffice/ {
            proxy_pass http://127.0.0.1:8006;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

**Características de la configuración:**

1. **Puerto 8080 (HTTP)**: Redirige automáticamente a HTTPS
2. **Puerto 443 (HTTPS)**: Conexión segura con certificados SSL
3. **Rutas absolutas**: Los certificados se referencian con la ruta completa del proyecto
4. **Wildcard support**: Acepta `tfmmyllm.ai` y subdominios (`*.tfmmyllm.ai`)
5. **Headers proxy**: Incluye `X-Forwarded-Proto` para que las aplicaciones detecten HTTPS
6. **Protocolos modernos**: TLSv1.2 y TLSv1.3 únicamente
7. **Caché de sesión SSL**: Mejora el rendimiento de las conexiones HTTPS

**Acceso después de configurar:**
- HTTP: `http://tfmmyllm.ai:8080` → Redirige a HTTPS
- HTTPS: `https://tfmmyllm.ai` (puerto 443 por defecto)
- Backoffice: `https://tfmmyllm.ai/backoffice/`

**Generación de certificados SSL con OpenSSL (alternativa no recomendada):**
```bash
# Crear directorio para certificados
mkdir -p /usr/local/etc/nginx/ssl

# Generar certificado autofirmado (válido por 365 días)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /usr/local/etc/nginx/ssl/localhost.key \
  -out /usr/local/etc/nginx/ssl/localhost.crt \
  -subj "/C=ES/ST=Madrid/L=Madrid/O=TFM MyLLM/CN=localhost"
```

**Nota sobre certificados autofirmados:**
Los certificados generados con OpenSSL mostrarán advertencias de seguridad en el navegador.
Para desarrollo local sin advertencias, se recomienda usar `mkcert`.

#### Despliegue de Nginx en macbook

Para desplegar y configurar nginx en el entorno macbook, se proporciona el script `deploy_nginx_macbook.sh`:

```bash
./deploy_nginx_macbook.sh
```

**Funcionalidades del script:**
- Verifica e instala nginx con Homebrew solo si no está instalado
- Copia la configuración desde `infrastructure/servers/macbook/nginx/nginx.conf`
- Valida la sintaxis del archivo de configuración con `nginx -t`
- Inicia nginx si está detenido o lo reinicia si ya está en ejecución
- Muestra el estado final y la URL de acceso

**Configuración de nginx:**
- **Puerto 8080 (HTTP)**: Redirige automáticamente a HTTPS
- **Puerto 443 (HTTPS)**: Conexión segura con certificados SSL
- **Frontend principal**: `https://tfmmyllm.ai/` → Proxy a `5_web_frontend` (puerto 8005)
- **Backoffice**: `https://tfmmyllm.ai/backoffice/` → Proxy a `6_web_backoffice` (puerto 8006)

**URLs de acceso:**
- Producción (HTTPS): `https://tfmmyllm.ai`
- Backoffice: `https://tfmmyllm.ai/backoffice/`
- HTTP (redirige): `http://tfmmyllm.ai:8080` → `https://tfmmyllm.ai`

**Flujo completo de despliegue:**

```bash
# 1. Instalar mkcert (si no está instalado) - OBLIGATORIO
# Verificar si mkcert está instalado
if ! command -v mkcert &> /dev/null; then
    echo "mkcert no está instalado. Instalando..."
    brew install mkcert nss
    mkcert -install
else
    echo "mkcert ya está instalado"
fi

# 2. Generar certificados SSL
brew install mkcert nss
mkcert -install

# 2. Generar certificados SSL
cd infrastructure/certificates/macbook
./generate_certs.sh
cd ../../..

# 3. Desplegar nginx con la configuración SSL
./deploy_nginx_macbook.sh

# 4. Verificar que nginx está corriendo
curl -I https://tfmmyllm.ai
```

**Verificación de certificados en nginx:**
```bash
# Ver información del certificado usado por nginx
echo | openssl s_client -connect tfmmyllm.ai:443 2>/dev/null | openssl x509 -noout -dates -subject

# Verificar que los certificados están en la ubicación correcta
ls -lh infrastructure/certificates/macbook/
```

### Solución de problemas (Troubleshooting)

#### Problema 1: Error "Not Found" (404) al acceder a https://tfmmyllm.ai

**Síntoma:**
Al acceder a `https://tfmmyllm.ai` en el navegador, aparece el mensaje "Not Found" en texto plano.

**Causa:**
El frontend de Reflex no ha cargado correctamente las rutas, o necesita ser reiniciado después de configurar nginx con HTTPS.

**Solución:**

```bash
# Paso 1: Detener el proceso actual del frontend
# Encuentra el proceso de Reflex
ps aux | grep "reflex run" | grep -v grep

# Si hay un proceso corriendo, detenerlo (Ctrl+C en la terminal o usar kill)
ps aux | grep "reflex run" | grep -v grep | awk '{print $2}' | xargs kill -9

# Paso 2: Reiniciar el frontend
cd src/apps/5_web_frontend
bash run.sh

# Paso 3: Esperar a que Reflex compile (~30 segundos)
# Verás mensajes como:
# "Compiling:  ✓ (100%)"
# "App running at: http://localhost:8005"

# Paso 4: Verificar que funciona
curl -I http://127.0.0.1:8005
# Debería devolver: HTTP/1.1 200 OK

# Paso 5: Acceder desde el navegador
# https://tfmmyllm.ai
```

**Verificación:**
- ✅ Nginx está corriendo: `brew services list | grep nginx`
- ✅ Frontend está corriendo: `lsof -i :8005`
- ✅ Puerto 443 escucha: `lsof -i :443 | grep nginx`
- ✅ Ruta funciona directamente: `curl -I http://127.0.0.1:8005`

**Nota:** Si el acceso directo al puerto 8005 devuelve 404, el problema es del frontend, no de nginx. Reinicia el frontend siguiendo los pasos anteriores.

---

#### Problema 2: Error "Connection refused" o "ERR_CONNECTION_REFUSED"

**Síntoma:**
El navegador no puede conectar a `https://tfmmyllm.ai`.

**Causa:**
Nginx no está corriendo o no está escuchando en el puerto 443.

**Solución:**

```bash
# Verificar estado de nginx
brew services list | grep nginx

# Si no está corriendo, iniciarlo
./deploy_nginx_macbook.sh

# Verificar que escucha en puerto 443
lsof -i :443 | grep nginx

# Ver logs de nginx para errores
tail -f /usr/local/var/log/nginx/error.log
```

---

#### Problema 3: Advertencia de certificado no confiable

**Síntoma:**
El navegador muestra advertencias de seguridad sobre el certificado SSL.

**Causa:**
La Certificate Authority (CA) de mkcert no está instalada en el sistema.

**Solución:**

```bash
# Reinstalar la CA de mkcert
mkcert -uninstall
mkcert -install

# Regenerar los certificados
cd infrastructure/certificates/macbook
./generate_certs.sh

# Reiniciar nginx
cd ../../..
./deploy_nginx_macbook.sh

# Reiniciar el navegador completamente
# (cierra todas las ventanas y vuelve a abrir)
```

---

#### Problema 4: Error "Address already in use" en puerto 443 o 8005

**Síntoma:**
Al iniciar nginx o el frontend aparece el error "Address already in use".

**Solución:**

```bash
# Para puerto 443 (nginx)
lsof -i :443
# Si hay un proceso que no es nginx, detenerlo:
kill -9 <PID>

# Para puerto 8005 (frontend)
lsof -i :8005
# Si hay un proceso viejo de Reflex, detenerlo:
kill -9 <PID>

# Reiniciar los servicios
./deploy_nginx_macbook.sh
cd src/apps/5_web_frontend && bash run.sh
```

---

#### Problema 5: Nginx muestra "502 Bad Gateway"

**Síntoma:**
Nginx responde pero con error "502 Bad Gateway".

**Causa:**
El frontend no está corriendo o no responde en el puerto 8005.

**Solución:**

```bash
# Verificar que el frontend está corriendo
lsof -i :8005

# Si no está corriendo, iniciarlo
cd src/apps/5_web_frontend
bash run.sh

# Verificar que responde
curl -I http://127.0.0.1:8005

# Ver logs de nginx
tail -f /usr/local/var/log/nginx/error.log
```

---

#### Problema 6: No se encuentra el dominio tfmmyllm.ai

**Síntoma:**
El navegador dice que no puede encontrar el servidor `tfmmyllm.ai`.

**Causa:**
El archivo `/etc/hosts` no tiene la entrada para el dominio.

**Solución:**

```bash
# Verificar si la entrada existe
grep tfmmyllm.ai /etc/hosts

# Si no existe, añadirla
echo "127.0.0.1       tfmmyllm.ai" | sudo tee -a /etc/hosts

# Verificar que se añadió correctamente
grep tfmmyllm.ai /etc/hosts

# Limpiar caché DNS (macOS)
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

---

#### Problema 7: Error de WebSocket "Cannot connect to server: websocket error"

**Síntoma:**
El frontend carga correctamente, pero aparece un mensaje de error: "Cannot connect to server: websocket error. Check if server is reachable at wss://tfmmyllm.ai/_event"

**Causas comunes:**

1. **El frontend no está recogiendo la configuración de `api_url`**: El frontend necesita ser reconstruido desde cero cuando se cambia la configuración en `rxconfig.py`.

2. **Cache del build del frontend**: Los assets compilados pueden tener cacheada una URL anterior.

3. **Los servicios no están sincronizados**: El frontend y el backend pueden estar corriendo en modos diferentes.

**Solución completa:**

```bash
# Paso 1: Detener todos los procesos de Reflex
ps aux | grep -E "(reflex|node.*3001|python.*8005)" | grep -v grep | awk '{print $2}' | xargs kill -9

# Paso 2: Limpiar completamente el build del frontend
cd src/apps/5_web_frontend
rm -rf .web public

# Paso 3: Activar el entorno virtual
source ../../../.venv_frontend313/bin/activate

# Paso 4: Verificar que rxconfig.py tiene la configuración correcta
# Debe contener:
# api_url="https://tfmmyllm.ai"
# env=rx.Env.PROD
# backend_port=8005

# Paso 5: Exportar el frontend desde cero
reflex export --no-zip

# Paso 6: Reiniciar Reflex en modo producción
reflex run --env prod

# Paso 7: Esperar a que compile (verás "App Running" en los logs)
# Frontend debería estar en http://0.0.0.0:3001/
# Backend debería estar en http://0.0.0.0:8005

# Paso 8: Reiniciar nginx para asegurar configuración
cd ../../..
./deploy_nginx_macbook.sh

# Paso 9: Verificar puertos
lsof -i :3001 -i :8005 | grep LISTEN

# Paso 10: Probar acceso directo
curl -I http://127.0.0.1:3001  # Frontend
curl -I http://127.0.0.1:8005/_event  # Backend WebSocket

# Paso 11: Probar a través de Nginx
curl -I https://tfmmyllm.ai  # Debería devolver 200 OK

# Paso 12: Limpiar caché del navegador
# - Abrir Developer Tools (F12)
# - Click derecho en el botón de recargar
# - Seleccionar "Empty Cache and Hard Reload"
# O simplemente usar el modo incógnito

# Paso 13: Acceder desde el navegador
# https://tfmmyllm.ai
```

**Verificación:**
- ✅ `rxconfig.py` tiene `api_url="https://tfmmyllm.ai"`
- ✅ Frontend en puerto 3001: `lsof -i :3001`
- ✅ Backend en puerto 8005: `lsof -i :8005`
- ✅ Nginx escuchando en 443: `lsof -i :443 | grep nginx`
- ✅ Nginx proxying a 3001: Ver `/usr/local/etc/nginx/nginx.conf` location `/`
- ✅ Nginx proxying `/_event` a 8005: Ver `nginx.conf` location `/_event`

**Nota importante:** En modo producción, Reflex compila los assets del frontend con el valor de `api_url` embebido. Si cambias este valor, debes limpiar el build completo (`rm -rf .web public`) y exportar de nuevo (`reflex export --no-zip`).

---

#### Comandos útiles de diagnóstico

**Script automatizado:**
```bash
./diagnose_system.sh
```

Este script verifica el estado completo del sistema: nginx, frontend, middleware, backend core, broker backend, certificados, /etc/hosts y logs recientes.

**Comandos manuales:**
```bash
# Estado completo del sistema
echo "=== Estado de Nginx ==="
brew services list | grep nginx
lsof -i :443 | grep nginx

echo "=== Estado del Frontend ==="
lsof -i :8005

echo "=== Verificar certificados ==="
ls -lh infrastructure/certificates/macbook/

echo "=== Test de conectividad ==="
curl -I https://tfmmyllm.ai 2>&1 | head -5

echo "=== Test directo al frontend ==="
curl -I http://127.0.0.1:8005

echo "=== Verificar /etc/hosts ==="
grep tfmmyllm.ai /etc/hosts
```

**Logs importantes:**
- Nginx error log: `/usr/local/var/log/nginx/error.log`
- Nginx access log: `/usr/local/var/log/nginx/access.log`
- Frontend log: `src/apps/5_web_frontend/logs/frontend_secure.log`
- Middleware log: `src/apps/7_service_frontend/logs/middleware_activiy.log`

## Diagrama de arquitectura (Mermaid)

El esquema de arquitectura está definido en `context/schemas/mermaid-ai-diagram-myllm.mmd`.
Resume la relación entre roles de usuario, servidores (frontend, backend y trainer),
el middleware (`7_service_frontend`), el backend (`3_backend`), el servicio backend
(`8_service_backend`), y los componentes compartidos (`1_shared_domain`, `2_shared_application`),
además de las dependencias con Nginx y MariaDB.

### Relación entre servicios (interpretación)

- Dos interfaces web consumen el middleware: `5_web_frontend` y `6_web_backoffice`.
- El middleware (`7_service_frontend`) enruta hacia el broker backend (`8_service_backend`),
  que reparte peticiones entre el backend core y el backend IA.
- El broker decide el destino:
  - **Operaciones de datos** (MariaDB/MySQL y sistema de ficheros): las atiende el backend core `3_backend`
    ejecutado en el servidor backend.
  - **Operaciones de IA** (uso interno y entrenamiento): las atiende `4_trainer`, que tendrá API REST y se
    ejecutará en el servidor trainer con base de datos vectorial Keras para entrenamientos.
- La capa de dominio común vive en `src/1_shared_domain/`.
- La capa de aplicación compartida vive en `src/2_shared_application/`.

### Gestión de ficheros (fmanagement)

Las operaciones sobre carpetas y ficheros se delegan desde `3_backend` a la API externa
`fmanagement` (Go). Esta API usa permisos de bajo nivel y trabaja sobre un volumen
de datos en el servidor backend.

Ruta de almacenamiento esperada en producción: `/data/files/external`.

Estructura esperada:
```
/data/files/external/
  ORG0001/
    PRJ00001/
      v001/
      v002/
```

En desarrollo existe un ejemplo en `fmanagement/example`, pero la implementación final
no debe depender de esa ruta.

#### Endpoints de fmanagement

- `GET /fmo`: operaciones sobre fichero/carpeta con `operation=view|delete|rename|create`.
  Parámetros clave: `iduser`, `basepath`, `orgpath`, `prjpath`, `versionpath`,
  `subfolders`, `filename`, `extfile`, `new_filename`, `new_extfile`.
- `POST /fmo`: subida de fichero (`operation=upload`, `multipart/form-data` con `file`).
  Parámetros clave: `iduser`, `basepath`, `orgpath`, `prjpath`, `versionpath`,
  `subfolders`, `filename`, `extfile`.
- `GET /fmo/list`: listado recursivo de directorios (estructura).
  Parámetros clave: `iduser`, `basepath`, `orgpath`, `prjpath`, `versionpath`, `subfolders`.
- `POST /fmo/newversion`: clona una versión a la siguiente (`v001` → `v002`).
  Parámetros clave: `iduser`, `basepath`, `orgpath`, `prjpath`, `versionpath`.
- `GET /fmo/diffversion`: compara dos versiones.
  Parámetros clave: `iduser`, `basepath`, `orgpath`, `prjpath`,
  `versionpath`, `compare_versionpath`.

Headers requeridos para permisos:
- `Authorization: Bearer <access_token>`
- `X-Session-Token: <session_token>`

En modo `db_only` es obligatorio incluir `identity_type_id` (query param).

## ADRs

- `src/docs/stack_of_technologies.adr`: justifica el uso de Python 3.13 y el downgrade temporal desde 3.14.

## Entornos virtuales dedicados

El proyecto usa **Python 3.13** como versión base. Para evitar conflictos de dependencias y 
garantizar aislamiento entre servicios, cada aplicación tiene su propio entorno virtual dedicado 
en la raíz del proyecto:

- **Frontend**: `.venv_frontend313` (usado por `5_web_frontend` y `2_shared_application`)
- **Middleware**: `.venv_middleware313` (usado por `7_service_frontend`, `8_service_backend`, `3_backend`)
- **Backend Core**: `.venv_backend313` (alternativa para `3_backend` en desarrollo)
- **Broker Backend**: `.venv_broker313` (alternativa para `8_service_backend` en desarrollo)

### Creación de entornos virtuales

```bash
# Frontend
python3.13 -m venv .venv_frontend313
source .venv_frontend313/bin/activate
pip install -r src/apps/5_web_frontend/requirements.txt
deactivate

# Middleware
python3.13 -m venv .venv_middleware313
source .venv_middleware313/bin/activate
pip install -r src/apps/7_service_frontend/requirements.txt
deactivate

# Backend Core
python3.13 -m venv .venv_backend313
source .venv_backend313/bin/activate
pip install -r src/apps/3_backend/requirements.txt
deactivate

# Broker Backend
python3.13 -m venv .venv_broker313
source .venv_broker313/bin/activate
pip install -r src/apps/8_service_backend/requirements.txt
deactivate
```

### Ejecución de servicios

Cada aplicación en `src/apps/*` incluye un script `run.sh` que activa automáticamente 
su entorno virtual dedicado antes de iniciar el servicio:

```bash
# Backend Core
cd src/apps/3_backend && bash run.sh

# Broker Backend
cd src/apps/8_service_backend && bash run.sh

# Middleware
cd src/apps/7_service_frontend && bash run.sh

# Frontend
cd src/apps/5_web_frontend && bash run.sh
```

## Scripts útiles

### full_test.sh

Script de ejecución de tests que valida todos los módulos del proyecto con salida detallada:

```bash
./full_test.sh
```

**Características:**
- Ejecuta tests de forma secuencial por módulo
- Muestra cada test individual con su estado (PASSED/FAILED)
- Usa entornos virtuales dedicados automáticamente:
  - `.venv_frontend313` para `2_shared_application` y `5_web_frontend`
  - `.venv_middleware313` para `7_service_frontend`, `8_service_backend` y `3_backend`
- Proporciona separadores visuales entre grupos de tests
- Salida verbose (`-v`) para máxima trazabilidad

**Módulos testeados:**
1. `src/2_shared_application/tests` (14 tests): DTOs, helpers, validaciones
2. `src/apps/5_web_frontend/tests` (23 tests): componentes web, integración middleware
3. `src/apps/7_service_frontend/tests` (8 tests): middleware, sesiones, permisos
4. `src/apps/8_service_backend/tests` (1 test): broker backend, routing
5. `src/apps/3_backend/tests` (1 test): backend core, endpoints

### clear_caches.sh

Script de limpieza de caches de Reflex y herramientas de desarrollo:

```bash
./clear_caches.sh
```

**Limpia:**
- Caches de Reflex: `.web`, `.states`
- Caches de tooling: `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.coverage`, `.hypothesis`

### diagnose_system.sh

Script de diagnóstico completo del sistema para verificar el estado de todos los servicios y configuraciones:

```bash
./diagnose_system.sh
```

**Verifica:**
- Estado de nginx y puerto 443
- Estado del frontend (puerto 8005)
- Estado del middleware (puerto 8007)
- Estado del backend core (puerto 8003)
- Estado del broker backend (puerto 8008)
- Existencia y validez de certificados SSL
- Conectividad HTTPS y HTTP
- Configuración de `/etc/hosts`
- Logs recientes de nginx

**Uso recomendado:**
Ejecutar este script cuando se presenten problemas de conectividad o después de cambios en la configuración para verificar que todo está funcionando correctamente.

## Servicio frontend en contenedor

El servicio `7_service_frontend` puede ejecutarse de forma independiente en Docker
usando el compose del servidor frontend.

```bash
docker compose -f infrastructure/servers/frontend/docker-compose.yml up --build
```

Para inyectar variables por entorno, se recomienda generar un envfile con:
`python infrastructure/export_env.py --environment <entorno> --format envfile`.

Variables relevantes (ver `src/apps/7_service_frontend/.env.example`):
- `JWT_ACCESS_SECRET`
- `JWT_SESSION_SECRET`
- `JWT_ALGORITHM`
- `BACKEND_BASE_URL`
- `SERVICE_HOST`
- `SERVICE_PORT`
- `SERVICE_RELOAD`
- `USERS_DATA_PATH`
- `ORGANIZATIONS_DATA_PATH`
- `SESSIONS_DATA_PATH` (opcional, sobrescribe `src/2_shared_application/moks/sessions.json`)
- `FERNET_KEY_PATH`
- `ACTIVITY_LOG_PATH` (opcional, sobrescribe la ruta de `middleware_activiy.log`)
- `STORAGE_MODE` (modos: `mock`, `mock_and_db`, `db_only`)
- `BROKER_BACKEND_BASE_URL` (URL del broker backend)
- `SYNC_DATABASE_INTERVAL_SECONDS` (intervalo de sincronización DB/JSON)
- `ACTIVE_SYNC_DB_JSONS` (switch de sincronización DB/JSON)

Dependencias del servicio (pip):
- `src/apps/7_service_frontend/requirements.txt`

### Modos de almacenamiento (middleware)

El middleware puede operar con tres modos configurables mediante `STORAGE_MODE`:

- `mock`: usa únicamente los ficheros JSON mockeados.
- `mock_and_db`: usa mocks y replica las escrituras hacia el broker backend.
- `db_only`: usa exclusivamente el broker backend para lectura/escritura.

Cuando el modo es `mock_and_db` o `db_only`, el middleware delega persistencia en el
broker backend (`8_service_backend`) mediante `BROKER_BACKEND_BASE_URL`.

### Base de datos de proyectos (sin mocks)

La base de datos `myllm_projects_db` **no** tiene espejo en ficheros JSON de
`src/2_shared_application/moks`. Todas las operaciones contra esta base de datos
se realizan **directamente en MariaDB**, sin fallback ni sincronización con mocks.

Notas de UX y trazabilidad (Flujos):
- El selector de proyectos **solo** muestra el nombre del proyecto; el `id` se usa
  internamente y puede registrarse en logs para trazabilidad.
- El selector de versiones **sí** muestra el `id_version` (visible para el usuario),
  ya que es el identificador usado en consultas a `versiones` y `estado`.

### Sincronización OTP (frontend y middleware)

Cuando se actualiza el OTP de un usuario, el cambio se persiste **en JSON y en
MariaDB de forma sincrónica** (modo `mock_and_db` o `db_only`). Se añade una
validación de consistencia que compara los OTP entre `users.json` y la tabla
`users`, registrando el resultado en:

- `src/apps/5_web_frontend/logs/frontend_secure.log`

### Agentes automáticos por proyecto

Al crear un proyecto, el sistema genera **4 agentes automáticos** asociados a la
organización y al proyecto, con nombres `agente_rol_organizacion_proyecto` y roles:

- `identity_type_id=10`: administrador
- `identity_type_id=11`: editor
- `identity_type_id=12`: lector
- `identity_type_id=13`: auditor

Estos agentes se almacenan en `users.json` y en la tabla `users` para asegurar
trazabilidad. El email se construye como `{nombre}@tfmmyllm.ai` y el OTP se genera
con 4 dígitos.

### Sincronización periódica DB/JSON (middleware)

Cuando `STORAGE_MODE` es `mock_and_db` o `db_only`, el middleware ejecuta una
sincronización periódica entre las tablas de MariaDB (vía broker backend) y los
ficheros JSON locales. Ante diferencias, **prevalece la base de datos** y se
reescriben los JSON para mantener coherencia.

Configuración:
- `SYNC_DATABASE_INTERVAL_SECONDS`: intervalo de sincronización en segundos
  (por defecto `300`, mínimo `30`).

Logs:
- `src/apps/7_service_frontend/logs/sync_database_and_jsons.log` registra los
  cambios detectados y las acciones aplicadas para regularizar datos.

Recomendación para producción:
- `ACTIVE_SYNC_DB_JSONS=0`
- `STORAGE_MODE="db_only"` en `.env`

### Broker backend y backend core

El broker backend (`8_service_backend`) recibe operaciones desde el middleware y
las reenvía al backend core (`3_backend`) cuando se trata de datos o filesystem.
Por ahora, el backend core usa los mocks JSON, pero su capa de infraestructura está
lista para conectar con MariaDB y la API externa `fmanagement` en futuras iteraciones.

Variables relevantes (broker):
- `CORE_BACKEND_BASE_URL`
- `BROKER_ACTIVITY_LOG_PATH` (opcional, ruta del log de actividad)

Variables relevantes (core):
- `CORE_ACTIVITY_LOG_PATH` (opcional, ruta del log de actividad)
- `USERS_DATA_PATH`, `ORGANIZATIONS_DATA_PATH`, `ROLES_DATA_PATH`,
  `BASIC_PERMISSIONS_PATH`, `LOW_LEVEL_PERMISSIONS_PATH`,
  `MANAGE_ROLES_BY_ORG_PATH` (mocks JSON)

### Ejemplos de despliegue en servidores (contenedores)

Servidor **Frontend** (web + middleware):

```bash
cd /Users/administrator/develop/anewhope
docker compose -f src/apps/5_web_frontend/docker-compose.yml up --build -d
docker compose -f src/apps/7_service_frontend/docker-compose.yml up --build -d
```

Servidor **Backend** (broker + core):

```bash
cd /Users/administrator/develop/anewhope
docker compose -f src/apps/3_backend/docker-compose.yml up --build -d
docker compose -f src/apps/8_service_backend/docker-compose.yml up --build -d
```

Ejemplo de configuración en el middleware para trabajar con el broker:

```bash
export STORAGE_MODE=db_only
export BROKER_BACKEND_BASE_URL=http://<ip-backend>:8008
```

Ejemplo de configuración en el broker para apuntar al core:

```bash
export CORE_BACKEND_BASE_URL=http://<ip-backend>:8003
```

### Sesiones y auditoría (middleware)

El middleware mantiene un registro temporal de sesiones y auditoría en
`src/2_shared_application/moks/sessions.json` (estructura `sessions` y `auth_logs`).
Se añade `jti` y `session_id` a los JWT (HS256) para validar que la sesión está activa
y no ha sido revocada, y para cerrar sesiones de forma explícita.
Estados soportados: `active`, `inactive`, `revoked`, `expired`.

Regla de seguridad: tres intentos de login fallidos consecutivos dentro de una ventana de 10 minutos
registran el bloqueo del usuario en el mock de usuarios (`blocked=true`) hasta nueva intervención.

Endpoint relevante:
- `POST /logout` invalida la sesión actual (marca `inactive`).

Directiva **security by design**: los tokens no se aceptan si no están vinculados a una sesión activa
en `sessions.json` con `session_id` y `jti` coincidentes. Al cerrar sesión se invalida la sesión y
se rechazan tokens antiguos, evitando reutilización si son filtrados.

Directiva **security by default**: cualquier token emitido queda invalidado tras logout; si el usuario
quiere acceder de nuevo, debe autenticarse con credenciales y OTP para generar una nueva sesión válida.

#### Entidades compartidas de sesión

Para reutilizar la lógica de sesión y permisos entre aplicaciones, se añaden entidades
compartidas en `src/1_shared_domain/entities/session.py` y DTOs en
`src/2_shared_application/dtos/session_dtos.py`:

- `SessionStatus`: estados de sesión (`active`, `inactive`, `revoked`, `expired`).
- `SessionTokenBinding`: JTIs asociados a la sesión.
- `Session`: entidad principal de sesión con `session_id`, usuario, estado y expiración.
- `UserSessionContext`: contexto mínimo para validar permisos en otras capas.

El acceso a persistencia se estandariza con el repositorio `SessionRepository` en
`src/2_shared_application/interfaces/session_repository.py`.

## Web frontend (Reflex)

Regla de puertos: cada aplicación usa **8000 + el primer número del nombre de la carpeta**.

- `3_backend` → **8003**
- `5_web_frontend` → **8005**
- `6_web_backoffice` → **8006** (reservado)
- `7_service_frontend` → **8007**
- `8_service_backend` → **8008** (reservado)

La aplicación web (`5_web_frontend`) usa **puerto backend fijo 8005** para el servidor interno de Reflex. Esto se configura en `src/apps/5_web_frontend/rxconfig.py` con `backend_port=8005` y no debe cambiarse para evitar conflictos con el middleware.

## TODO

- Evaluar migración a Python 3.14 cuando `pydantic-core` y Reflex certifiquen compatibilidad.
- Tests verificados con `./full_test.sh` en Python 3.13 sin warning de Pydantic (2026-01-19).

## Modelo de Dominio

El módulo `src/1_shared_domain/entities/domain_models.py` contiene las entidades centrales del sistema, diseñadas siguiendo principios de Domain-Driven Design (DDD).

### Entidades principales

#### `Organization`
Representa una organización en el sistema. Múltiples usuarios pueden pertenecer a la misma organización.

**Atributos:**
- `organization_id`: Identificador único
- `organization_name`: Nombre de la organización
- `organization_email`: Email de contacto (validado)
- `organization_tlf`: Teléfono de contacto
- `organization_address`: Dirección física
- `organization_country`: País
- `organization_state`: Estado/Provincia

**Características:**
- Validación de email en constructor y setters
- Métodos: `update_contact_info()`, `is_valid()`
- Comparación por ID (`__eq__`, `__hash__`)

#### `IdentityGlobal`
Define tipos de identidad con roles y permisos asociados. Se relaciona con `User` a través de `identity_type_id`.

**Atributos:**
- `identity_type_id`: Identificador único
- `identity_type_name`: Nombre del tipo (ej: "Admin", "Usuario")
- `identity_type_rol`: Rol asociado
- `identity_type_group_permissions`: Lista de objetos `Permissions`

**Características:**
- Gestión de permisos: `add_permission()`, `remove_permission()`, `has_permission()`
- Validaciones en todos los setters
- Comparación por ID (`__eq__`, `__hash__`)

#### `Permissions`
Representa un permiso con operaciones CRUD y acciones específicas.

**Atributos:**
- `id_permission`: Identificador único
- `permission_name`: Nombre del permiso
- `permission_description`: Descripción
- `enable`: Estado habilitado/deshabilitado
- `create`, `read`, `write`, `delete`, `execute`: Operaciones permitidas
- `log`: Indica si se registra en log
- `expired`: Fecha de expiración (`datetime | None`)

**Características:**
- Métodos: `is_expired()`, `is_active()`, `has_crud_permissions()`, `can_perform_action()`
- Validación de fecha de expiración
- Comparación por ID (`__eq__`, `__hash__`)

#### `User`
Entidad central que representa un usuario del sistema.

**Atributos:**
- `id`: Identificador único
- `organization_id`: Relación con `Organization`
- `identity_type_id`: Relación con `IdentityGlobal`
- `user_name`, `user_password`, `user_email`, `user_mobile`, `user_otp`
- `active`, `blocked`: Estados del usuario

**Invariantes:**
- Un usuario no puede estar activo y bloqueado simultáneamente
- Email debe tener formato válido
- Contraseña mínimo 8 caracteres
- OTP debe tener exactamente 4 dígitos

**Características:**
- Métodos: `activate_user()`, `deactivate_user()`, `block_user()`, `unblock_user()`, `can_perform_action()`, `generate_otp()`
- Validaciones completas en todos los setters
- Comparación por ID (`__eq__`, `__hash__`)

#### `Session`
Entidad que representa la sesión activa del usuario y su vínculo con tokens.

**Atributos:**
- `session_id`: Identificador único de sesión
- `user_id`, `organization_id`, `identity_type_id`
- `tokens`: JTIs asociados (`access_token_jti`, `session_token_jti`)
- `status`: Estado de sesión (`active`, `inactive`, `revoked`, `expired`)
- `created_at`, `last_activity`, `expires_at`

**Características:**
- Validación de estructura y expiración
- Métodos: `is_active()`, `is_expired()`, `mark_inactive()`, `mark_revoked()`

#### `UserExtended`
Extiende `User` con información de contacto adicional.

**Atributos adicionales:**
- `contact_info`: Objeto `ContactInfo` (inmutable)
- `billing_info`: Objeto `ContactInfo` para facturación

#### `UserGoogle`
Extiende `User` con autenticación OAuth de Google.

**Atributos adicionales:**
- `google_auth_info`: Objeto `GoogleAuthInfo` con tokens y datos de Google

**Características:**
- Métodos: `is_token_expired()`, `update_tokens()`
- Gestión automática de expiración de tokens

### Value Objects

#### `ContactInfo`
Value Object inmutable para información de contacto.

**Atributos:** `first_name`, `sur_name`, `country`, `state`, `zip_code`, `address`

#### `GoogleAuthInfo`
Value Object para datos de autenticación Google OAuth.

**Atributos:** `google_id`, `google_access_token`, `google_refresh_token`, `google_token_expires_at`, `google_picture_url`, `google_verified_email`

### Relaciones del modelo

```
Organization (1) ──< (N) User
IdentityGlobal (1) ──< (N) User
IdentityGlobal (1) ──< (N) Permissions
User (1) ──< (1) UserExtended
User (1) ──< (1) UserGoogle
```

### Características de diseño

- **Encapsulación:** Todos los atributos son privados con getters/setters
- **Validaciones:** Invariantes de dominio validadas en constructores y setters
- **Excepciones de dominio:** `DomainError` para errores de negocio
- **Comportamiento rico:** Métodos de dominio en lugar de simples DTOs
- **Inmutabilidad:** Value Objects como `ContactInfo` son inmutables
- **Comparación:** Entidades comparables por ID (`__eq__`, `__hash__`)

### Uso

```python
from src.1_shared_domain.entities.domain_models import (
    Organization, IdentityGlobal, Permissions, User, UserExtended, UserGoogle
)

# Crear organización
org = Organization(
    organization_id=1,
    organization_name="Mi Empresa",
    organization_email="contacto@empresa.com",
    organization_tlf="+1234567890",
    organization_address="Calle Principal 123",
    organization_country="España",
    organization_state="Madrid"
)

# Crear permisos
perm = Permissions(
    id_permission=1,
    permission_name="read_users",
    permission_description="Permite leer usuarios"
)

# Crear tipo de identidad con permisos
identity = IdentityGlobal(
    identity_type_id=1,
    identity_type_name="Admin",
    identity_type_rol="Administrator",
    identity_type_group_permissions=[perm]
)

# Crear usuario
user = User(
    user_id=1,
    organization_id=org.organization_id,
    identity_type_id=identity.identity_type_id,
    user_name="jdoe",
    password="securepass123",
    email="jdoe@empresa.com",
    mobile="+1234567890",
    otp="1234"
)
```

## Roles y permisos (mock)

- `src/2_shared_application/moks/roles.json`: define roles. El atributo
  `identity_type_group_permissions` contiene un único permiso básico (relación 1 a 1).
- `src/2_shared_application/moks/basic_permissions.json`: catálogo de permisos básicos.
- `src/2_shared_application/moks/low_level_permisions.json`: permisos de bajo nivel
  asociados 1 a 1 con `basic_permissions.json`.
- `src/2_shared_application/moks/manage_roles_by_org.json`: asigna roles a
  usuarios dentro de una organización.

En la gestión de permisos del token JWT se incluyen `user_id`, `organization_id`
e `identity_type_id` para resolver los permisos asociados.

Estructura de `manage_roles_by_org.json`:
```
{
  "id_user": 1,
  "id_organization": 1,
  "identity_type_id": 2,
  "create_date": "18/01/26-10:30",
  "modification_date": "",
  "id_modifier_user": 1,
  "active": true
}
```

El campo `identity_type_id` permite consultar los permisos del rol en
`basic_permissions.json`.

### Dominio y DTOs (roles por organización)

- **Dominio**: `ManagedRoleByOrg` y `ManageRolesByOrg` en `src/1_shared_domain/security_hierarchy.py`.
  La entidad expone `user_id`, `organization_id`, `identity_type_id` y metadatos de auditoría.
- **DTOs**: `ManageRoleByOrgDto` en `src/2_shared_application/dtos/security_dtos.py` mapea los campos
  `id_user`, `id_organization`, `identity_type_id`, `create_date`, `modification_date`,
  `id_modifier_user`, `active` hacia la entidad de dominio.

Este mapeo garantiza que el atributo `identity_type_id` del mock se preserve al cruzar capas.

### Persistencia (mock y MariaDB)

- **Mock JSON**: `src/2_shared_application/moks/manage_roles_by_org.json` es la fuente primaria para
  desarrollo y pruebas en modo `mock`.
- **MariaDB**: la tabla `user_organization_management` (definida en
  `anh_ansible_environments/env/macbook/files/init_myllm_core_db.sql`) refleja el mismo concepto con
  columnas `user_id`, `organization_id`, `identity_type_id`, `created_by_user_id`, `active`.
- **Carga**: el script de inicialización inserta desde JSON usando `JSON_TABLE()` y transforma
  `create_date` → `created_at`.

Estado verificado en BD (local): la tabla `user_organization_management` contiene 5 registros y
respeta los valores de `identity_type_id` del mock.

### Permisos básicos (dominio, DTO, mock y BD)

- **Dominio**: `BasicPermission` y `BasicPermissions` en `src/1_shared_domain/security_hierarchy.py`.
  El dominio consume `id`, `PermissionName`, `PermissionDescription` y valida su estructura.
- **DTOs**: `BasicPermissionDto` en `src/2_shared_application/dtos/security_dtos.py` mapea
  `id` → `permission_id`, `PermissionName` → `permission_name` y
  `PermissionDescription` → `permission_description`.
- **Mock JSON**: `src/2_shared_application/moks/basic_permissions.json` es la fuente principal.
  `PermissionName` se utiliza en el código para verificaciones, y `PermissionDescription`
  se usa para documentación y mensajes administrativos.
- **MariaDB**: los datos se cargan en la tabla `permissions` (script
  `anh_ansible_environments/env/macbook/files/init_myllm_core_db.sql`) mediante `JSON_TABLE()`.
  La relación entre `identity_types` y `permissions` es **1 a 1** y se controla con
  claves únicas en `identity_type_permissions`.

Estado verificado en BD (local): la tabla `permissions` contiene 13 registros y conserva los
`PermissionName`/`PermissionDescription` del mock.

### Permisos de bajo nivel (dominio, DTO, mock y BD)

- **Dominio**: `LowLevelPermission` y `LowLevelPermissions` en `src/1_shared_domain/security_hierarchy.py`.
  Cada registro utiliza `id_permissions` y flags booleanos por recurso/acción.
- **DTOs**: `LowLevelPermissionDto` en `src/2_shared_application/dtos/security_dtos.py`.
- **Mock JSON**: `src/2_shared_application/moks/low_level_permisions.json` exportado desde
  MariaDB. El `id_permissions` coincide 1 a 1 con `basic_permissions.json` y `roles.json`.
- **MariaDB**: tabla `low_level_permissions` con relación 1 a 1 con `permissions`.

Uso previsto: el token aporta `identity_type_id`; con ese ID se resuelve el permiso base,
su descripción y los flags de bajo nivel en la misma cadena de seguridad.

Ejemplo de plantilla para validar una acción concreta desde sesión/JWT:

```python
def can_rename_folder(session: SessionContext) -> bool:
    """Valida si el usuario puede renombrar carpetas."""

    permissions = router.get_permissions(session)
    return bool(permissions.get("low_level_permissions", {}).get("folder_rename"))
```

### Flujo entre APIs (permisos básicos)

- `7_service_frontend` carga permisos vía JSON o broker (`/basic-permissions`) según `STORAGE_MODE`.
- `8_service_backend` expone `GET /basic-permissions` y delega al core.
- `3_backend` expone `GET /basic-permissions` y devuelve los permisos desde el almacenamiento.

### Flujo entre APIs (permisos de bajo nivel)

- `7_service_frontend` carga permisos vía JSON o broker (`/low-level-permissions`) según `STORAGE_MODE`.
- `8_service_backend` expone `GET /low-level-permissions` y delega al core.
- `3_backend` expone `GET /low-level-permissions` y devuelve los permisos desde el almacenamiento.

## Estructura de almacenamiento (helpers)

En `src/2_shared_application/storage_access_structure.py` se definen helpers
para construir los nombres de carpetas en disco a partir de IDs numéricos:

```python
get_folder_by_id_organization(1)  # "ORG0001"
get_folder_by_id_project(1)       # "PRJ0001"
```

Estos helpers deben usarse de forma consistente en todas las capas cuando se
trabaje con rutas del storage (`/data/files/external`).

## Interfaces compartidas (aplicación)

Los contratos en `src/2_shared_application/interfaces/` desacoplan el acceso a
las entidades de dominio de la infraestructura (JSON hoy, MariaDB mañana).

- `basic_permissions_repository.py`: `BasicPermissionsRepository`
- `low_level_permissions_repository.py`: `LowLevelPermissionsRepository`
- `manage_roles_by_org_repository.py`: `ManageRolesByOrgRepository`
- `roles_repository.py`: `RolesRepository`
- `user_repository.py`: `UserRepository`
- `organization_repository.py`: `OrganizationRepository`
- `identity_global_repository.py`: `IdentityGlobalRepository`
- `permissions_repository.py`: `PermissionsRepository`
- `tenant_repository.py`: `TenantRepository`
- `dataset_repository.py`: `DatasetRepository`
- `model_version_repository.py`: `ModelVersionRepository`

### Ejemplos de implementación en adaptadores

Ejemplos simplificados (sin datos reales) para implementar repositorios desde
JSON o desde MariaDB usando DTOs. Los adaptadores viven en la capa de
infraestructura y transforman datos externos a entidades de dominio.

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from src.1_shared_domain.security_hierarchy import Roles
from src.2_shared_application.interfaces.roles_repository import RolesRepository


class RolesJsonRepository(RolesRepository):
    """Repositorio basado en JSON para roles (solo ejemplo)."""

    def __init__(self, json_path: Path) -> None:
        self._json_path = json_path

    def fetch_roles(self) -> Roles:
        records = _read_json_list(self._json_path)
        # El dominio valida estructura al construir
        return Roles.from_records(records)


def _read_json_list(json_path: Path) -> list[dict[str, object]]:
    """Lee una lista JSON de forma segura."""

    with json_path.open("r", encoding="utf-8") as file_handler:
        data = json.load(file_handler)
    if not isinstance(data, list):
        raise ValueError("El JSON debe contener una lista")
    return data
```

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.1_shared_domain.entities.domain_models import User
from src.2_shared_application.interfaces.user_repository import UserRepository


@dataclass(frozen=True)
class UserDto:
    """DTO simulado retornado por MariaDB."""

    id: int
    organization_id: int
    identity_type_id: int
    user_name: str
    user_password: str
    user_email: str
    user_mobile: str
    user_otp: str
    active: bool
    blocked: bool


class UsersMariaDbAdapter(UserRepository):
    """Repositorio simulado que mapea DTOs a entidad de dominio."""

    def __init__(self, gateway: "UserQueryGateway") -> None:
        self._gateway = gateway

    def get_by_id(self, user_id: int) -> User | None:
        dto = self._gateway.fetch_by_id(user_id)
        if dto is None:
            return None
        return _map_user(dto)

    def get_by_email(self, user_email: str) -> User | None:
        dto = self._gateway.fetch_by_email(user_email)
        if dto is None:
            return None
        return _map_user(dto)

    def get_by_name(self, user_name: str) -> User | None:
        dto = self._gateway.fetch_by_name(user_name)
        if dto is None:
            return None
        return _map_user(dto)

    def exists_by_email(self, user_email: str) -> bool:
        return self._gateway.exists_by_email(user_email)

    def exists_by_mobile(self, user_mobile: str) -> bool:
        return self._gateway.exists_by_mobile(user_mobile)

    def exists_by_name(self, user_name: str) -> bool:
        return self._gateway.exists_by_name(user_name)

    def save(self, user: User) -> User:
        dto = self._gateway.insert_user(user)
        return _map_user(dto)

    def update_password_and_otp(
        self, user_email: str, new_password: str, new_otp: str
    ) -> bool:
        return self._gateway.update_password_and_otp(
            user_email, new_password, new_otp
        )


class UserQueryGateway(Protocol):
    """Gateway simulado hacia MariaDB."""

    def fetch_by_id(self, user_id: int) -> UserDto | None:
        """Obtiene un usuario por id."""

    def fetch_by_email(self, user_email: str) -> UserDto | None:
        """Obtiene un usuario por email."""

    def fetch_by_name(self, user_name: str) -> UserDto | None:
        """Obtiene un usuario por nombre."""

    def exists_by_email(self, user_email: str) -> bool:
        """Verifica existencia por email."""

    def exists_by_mobile(self, user_mobile: str) -> bool:
        """Verifica existencia por teléfono."""

    def exists_by_name(self, user_name: str) -> bool:
        """Verifica existencia por nombre."""

    def insert_user(self, user: User) -> UserDto:
        """Inserta y retorna el DTO persistido."""

    def update_password_and_otp(
        self, user_email: str, new_password: str, new_otp: str
    ) -> bool:
        """Actualiza contraseña y OTP en base de datos."""


def _map_user(dto: UserDto) -> User:
    """Convierte un DTO en entidad de dominio."""

    return User(
        user_id=dto.id,
        organization_id=dto.organization_id,
        identity_type_id=dto.identity_type_id,
        user_name=dto.user_name,
        password=dto.user_password,
        email=dto.user_email,
        mobile=dto.user_mobile,
        otp=dto.user_otp,
        active=dto.active,
        blocked=dto.blocked,
    )
```

```python
from __future__ import annotations

import json
from pathlib import Path

from src.1_shared_domain.entities.session import Session, SessionStatus
from src.2_shared_application.interfaces.session_repository import SessionRepository


class SessionJsonRepository(SessionRepository):
    """Repositorio basado en JSON para sesiones (solo ejemplo)."""

    def __init__(self, json_path: Path) -> None:
        self._json_path = json_path

    def get_by_session_id(self, session_id: str) -> Session | None:
        records = _read_json_dict(self._json_path).get("sessions", [])
        for record in records:
            if record.get("session_id") == session_id:
                return Session.from_record(record)
        return None

    def list_by_user_id(self, user_id: int) -> tuple[Session, ...]:
        records = _read_json_dict(self._json_path).get("sessions", [])
        sessions = [
            Session.from_record(record)
            for record in records
            if int(record.get("user_id", 0)) == user_id
        ]
        return tuple(sessions)

    def save(self, session: Session) -> Session:
        payload = _read_json_dict(self._json_path)
        sessions = payload.get("sessions", [])
        sessions.append(session.to_record())
        payload["sessions"] = sessions
        _write_json_dict(self._json_path, payload)
        return session

    def update_status(
        self, session_id: str, status: SessionStatus, updated_at=None
    ) -> bool:
        payload = _read_json_dict(self._json_path)
        sessions = payload.get("sessions", [])
        for record in sessions:
            if record.get("session_id") == session_id:
                record["status"] = status.value
                return True
        return False

    def update_activity(self, session_id: str, last_activity) -> bool:
        payload = _read_json_dict(self._json_path)
        sessions = payload.get("sessions", [])
        for record in sessions:
            if record.get("session_id") == session_id:
                record["last_activity"] = last_activity
                return True
        return False


def _read_json_dict(json_path: Path) -> dict[str, object]:
    """Lee un JSON tipo dict de forma segura."""

    if not json_path.exists():
        return {}
    with json_path.open("r", encoding="utf-8") as file_handler:
        data = json.load(file_handler)
    if not isinstance(data, dict):
        raise ValueError("El JSON debe contener un objeto")
    return data


def _write_json_dict(json_path: Path, payload: dict[str, object]) -> None:
    """Escribe un JSON tipo dict de forma segura."""

    json_path.parent.mkdir(parents=True, exist_ok=True)
    with json_path.open("w", encoding="utf-8") as file_handler:
        json.dump(payload, file_handler, ensure_ascii=False, indent=2)
```

## Logging de seguridad

Las escrituras de logs de seguridad se realizan en el middleware (`7_service_frontend`).
El frontend solo envía la acción al endpoint `/security/log`.

Archivo de log (middleware):
- `src/apps/7_service_frontend/logs/middleware_secure.log`

## Logging de actividad (middleware)

El middleware registra la actividad de las APIs en un log dedicado para trazabilidad.
Este log captura acciones como autenticación, validaciones y operaciones CRUD.

Archivo de log (middleware):
- `src/apps/7_service_frontend/logs/middleware_activiy.log`

## Logging de actividad (broker y core)

Cada API registra su actividad en logs locales:

- `src/apps/8_service_backend/logs/broker_backend_activity.log`
- `src/apps/3_backend/logs/backend_core_activity.log`

### Estructura JWT (middleware)

El middleware emite dos tokens:
- **Access Token** (15 min)
- **Session Token** (45 min)

Payload mínimo común en ambos:
```
{
  "user_id": 1,
  "organization_id": 1,
  "identity_type_id": 2,
  "iat": 1700000000,
  "exp": 1700000900
}
```

## Roles y automatización (referencia)

Los roles Ansible importados se encuentran en el repositorio `anh_ansible`. Incluyen BIND, NTPD, NTPDATE, MariaDB, Nginx, Postfix, entre otros, y sirven como apoyo para el despliegue de la plataforma.
