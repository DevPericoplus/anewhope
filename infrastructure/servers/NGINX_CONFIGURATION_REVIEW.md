# Revisión de Configuración Nginx por Entorno

**Fecha**: 2026-02-07
**Autor**: Claude
**Objetivo**: Auditar y corregir configuraciones de nginx para garantizar consistencia entre entornos

---

## 📋 Resumen Ejecutivo

### Estado Actual

| Entorno | Archivo | Estado | Problemas Críticos |
|---------|---------|--------|-------------------|
| **macbook** | `/infrastructure/servers/macbook/nginx/nginx.conf` | ⚠️ Funcional | Dominio hardcodeado |
| **dev/pre/pro** | `/infrastructure/servers/frontend/nginx/nginx.conf` | ❌ Insuficiente | Sin SSL, Sin WebSocket, Dominio hardcodeado |

### Problemas Encontrados

1. ❌ **Dominios hardcodeados** - No adaptan a `public_name` de `env.yaml`
2. ❌ **Falta WebSocket support** en dev/pre/pro - Reflex no funcionará correctamente
3. ❌ **Sin SSL/HTTPS** en dev/pre/pro - Inseguro para pre/pro
4. ❌ **Template no usado** - Existe `nginx.conf.template` pero no se usa
5. ⚠️ **Configuración no versionada por entorno** - Mismo archivo para dev/pre/pro

---

## 🔍 Análisis Detallado por Entorno

### 1. Macbook (Desarrollo Local)

**Archivo**: `/infrastructure/servers/macbook/nginx/nginx.conf`

**✅ Aspectos Correctos**:
- SSL/TLS correctamente configurado (puerto 443)
- WebSocket support completo para Reflex
- Separación frontend (puerto 443) y backoffice (puerto 8443)
- Certificados SSL autofirmados configurados
- Redirección HTTP → HTTPS

**❌ Problemas**:

1. **Dominio hardcodeado** (líneas 20, 29, 91):
   ```nginx
   server_name tfmmyllm.ai *.tfmmyllm.ai 192.168.0.101 192.168.0.39 localhost;
   ```
   **Debería ser**: Leer `public_name` desde `/infrastructure/environments/macbook/env.yaml`

2. **Rutas de certificados hardcodeadas** (líneas 33-34, 93-94):
   ```nginx
   ssl_certificate /Users/administrator/develop/anewhope/infrastructure/certificates/macbook/tfmmyllm.ai.pem;
   ssl_certificate_key /Users/administrator/develop/anewhope/infrastructure/certificates/macbook/tfmmyllm.ai-key.pem;
   ```
   **Debería ser**: Usar variable dinámica basada en `public_name`

**📊 Impacto**: Bajo (solo afecta a macbook, pero dificulta portabilidad)

---

### 2. Dev/Pre/Pro (Servidores Linux)

**Archivo**: `/infrastructure/servers/frontend/nginx/nginx.conf`

**Estado Actual** (contenido completo):
```nginx
worker_processes  1;

events {
    worker_connections  1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    sendfile      on;

    server {
        listen 80;
        server_name localhost;  # ❌ PROBLEMA 1

        location / {
            proxy_pass http://web_frontend:8005;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            # ❌ PROBLEMA 2: Sin WebSocket support
        }

        location /backoffice/ {
            proxy_pass http://web_backoffice:8006;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            # ❌ PROBLEMA 2: Sin WebSocket support
        }
    }
}
```

**❌ Problemas Críticos**:

#### Problema 1: Dominio Hardcodeado
```nginx
server_name localhost;  # ❌ Incorrecto
```

**Debería ser** (según `env.yaml`):
- **DEV**: `server_name house.loc *.house.loc;`
- **PRE**: `server_name getmylllm.com *.getmylllm.com;`
- **PRO**: `server_name getmylllm.com *.getmylllm.com;`

**Impacto**: ⚠️ **CRÍTICO** - Nginx rechazará peticiones del dominio configurado

---

#### Problema 2: Sin WebSocket Support

**Configuración actual**:
```nginx
location / {
    proxy_pass http://web_frontend:8005;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    # ❌ Faltan headers de WebSocket
}
```

**Debería incluir**:
```nginx
location / {
    proxy_pass http://web_frontend:8005;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # ✅ WebSocket support (CRÍTICO para Reflex)
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400;
}
```

**Impacto**: ⚠️ **CRÍTICO** - Reflex no puede mantener conexión WebSocket, la UI no funcionará correctamente

---

#### Problema 3: Falta Endpoint `/_event`

Reflex usa el endpoint `/_event` para comunicación WebSocket bidireccional. La configuración actual **no lo incluye**.

**Falta**:
```nginx
location /_event {
    proxy_pass http://web_frontend:8005;
    # ... (headers de WebSocket)
}

location /backoffice/_event {
    proxy_pass http://web_backoffice:8006/_event;
    # ... (headers de WebSocket)
}
```

**Impacto**: ⚠️ **CRÍTICO** - Eventos de Reflex (clicks, cambios de estado) no funcionarán

---

#### Problema 4: Sin SSL/HTTPS

La configuración actual solo soporta HTTP (puerto 80). Para pre/pro esto es **inaceptable**.

**Debería incluir**:
```nginx
# Servidor HTTPS (puerto 443)
server {
    listen 443 ssl;
    server_name getmylllm.com *.getmylllm.com;

    ssl_certificate /etc/nginx/ssl/getmylllm.com.crt;
    ssl_certificate_key /etc/nginx/ssl/getmylllm.com.key;

    # ... (configuración completa)
}

# Servidor HTTP (redirigir a HTTPS)
server {
    listen 80;
    server_name getmylllm.com *.getmylllm.com;
    return 301 https://$host$request_uri;
}
```

**Impacto**:
- **DEV**: Medio (puede funcionar sin SSL)
- **PRE/PRO**: ⚠️ **CRÍTICO** - Inseguro, datos sin cifrar

---

#### Problema 5: Faltan Endpoints de API

La configuración actual no incluye el endpoint `/api` que Reflex utiliza para operaciones REST.

**Falta**:
```nginx
location /api {
    proxy_pass http://web_frontend:8005;
    # ... (headers)
}

location /backoffice/api {
    proxy_pass http://web_backoffice:8006/api;
    # ... (headers)
}
```

---

## 🛠️ Soluciones Implementadas

### 1. Script de Generación Dinámica

**Archivo**: `/infrastructure/servers/frontend/nginx/generate_nginx_conf.py`

**Características**:
- ✅ Lee `public_name` y `private_name` desde `env.yaml`
- ✅ Genera configuración apropiada por entorno (dev/pre/pro)
- ✅ Incluye WebSocket support completo
- ✅ Incluye todos los endpoints necesarios (`/`, `/_event`, `/api`)
- ✅ Opción para incluir SSL/HTTPS
- ✅ Configuración específica por entorno (redirección HTTPS en pre/pro)

**Uso**:
```bash
# Generar para el entorno activo (lee .envglobal)
cd /Users/administrator/develop/anewhope/infrastructure/servers/frontend/nginx
python generate_nginx_conf.py

# Generar para un entorno específico
python generate_nginx_conf.py --environment dev
python generate_nginx_conf.py --environment pre --ssl
python generate_nginx_conf.py --environment pro --ssl

# Especificar archivo de salida
python generate_nginx_conf.py --output custom_nginx.conf
```

**Salida**:
```
[INFO] Obteniendo configuración del entorno...
[INFO] Entorno: dev
[INFO] Dominio público: house.loc
[INFO] Dominio privado: anewhope.house.local
[INFO] Generando nginx.conf...
[OK] nginx.conf generado exitosamente: nginx.conf

Próximos pasos:
  1. Revisar el archivo generado
  2. Si usas SSL, configurar certificados en /etc/nginx/ssl/
  3. Reiniciar nginx: docker-compose restart nginx
```

---

### 2. Configuración Recomendada (Template)

**Archivo**: `/infrastructure/servers/frontend/nginx/nginx.conf.RECOMENDADO`

Contiene una configuración completa y comentada que incluye:
- ✅ WebSocket support para Reflex
- ✅ Todos los endpoints necesarios
- ✅ Placeholders para `public_name` dinámico
- ✅ Configuración SSL comentada lista para activar
- ✅ Headers de seguridad
- ✅ Comentarios explicativos

---

## 📝 Plan de Acción Recomendado

### Fase 1: Macbook (Inmediato)

1. **Actualizar nginx.conf para usar `public_name`**:
   ```bash
   # Opción A: Generar manualmente con script
   cd /Users/administrator/develop/anewhope/infrastructure/servers/macbook/nginx
   # TODO: Crear generate_nginx_conf_macbook.py adaptado

   # Opción B: Actualizar manualmente con el valor de env.yaml
   # Editar nginx.conf y reemplazar "tfmmyllm.ai" con variable dinámica
   ```

2. **Validar configuración**:
   ```bash
   nginx -t -c /usr/local/etc/nginx/nginx.conf
   ```

3. **Reiniciar nginx**:
   ```bash
   brew services restart nginx
   ```

---

### Fase 2: Dev/Pre/Pro (Prioritario)

#### Para DEV (Testing inicial sin SSL)

1. **Generar nginx.conf con el script**:
   ```bash
   cd /Users/administrator/develop/anewhope/infrastructure/servers/frontend/nginx
   python generate_nginx_conf.py --environment dev
   ```

2. **Revisar el archivo generado**:
   ```bash
   cat nginx.conf | grep "server_name"  # Debe mostrar: house.loc *.house.loc
   cat nginx.conf | grep "Upgrade"      # Debe mostrar: proxy_set_header Upgrade
   ```

3. **Reiniciar nginx en Docker**:
   ```bash
   cd /Users/administrator/develop/anewhope/infrastructure/servers/frontend
   docker-compose restart nginx
   ```

4. **Verificar**:
   ```bash
   # Verificar que nginx levantó correctamente
   docker-compose ps nginx

   # Ver logs
   docker-compose logs -f nginx

   # Probar conexión
   curl -I http://frontend.house.loc
   ```

---

#### Para PRE/PRO (Con SSL)

**⚠️ IMPORTANTE**: Antes de desplegar en PRE/PRO, debes obtener certificados SSL válidos.

1. **Obtener certificados SSL**:

   **Opción A: Let's Encrypt (Recomendado)**
   ```bash
   # En el servidor PRE/PRO
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d getmylllm.com -d www.getmylllm.com
   ```

   **Opción B: Certificados corporativos**
   - Solicitar certificados al equipo de infraestructura
   - Colocar en `/etc/nginx/ssl/getmylllm.com.crt` y `.key`

2. **Generar nginx.conf con SSL**:
   ```bash
   cd /Users/administrator/develop/anewhope/infrastructure/servers/frontend/nginx

   # Para PRE
   python generate_nginx_conf.py --environment pre --ssl

   # Para PRO
   python generate_nginx_conf.py --environment pro --ssl
   ```

3. **Actualizar docker-compose.yml para montar certificados**:
   ```yaml
   # En docker-compose.yml
   nginx:
     image: nginx:latest
     volumes:
       - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
       - /etc/letsencrypt:/etc/nginx/ssl:ro  # Añadir esta línea
   ```

4. **Desplegar**:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

5. **Verificar HTTPS**:
   ```bash
   curl -I https://www.getmylllm.com
   curl -I https://www.getmylllm.com/backoffice/
   ```

---

### Fase 3: Automatización (Opcional, Futuro)

1. **Integrar generación en CI/CD**:
   - Añadir `generate_nginx_conf.py` al pipeline de deploy
   - Generar automáticamente antes de construir imagen Docker

2. **Crear script para macbook**:
   - Adaptar `generate_nginx_conf.py` para generar el nginx.conf de macbook
   - Incluir lógica para rutas de certificados locales

3. **Monitoreo de certificados**:
   - Configurar alertas para certificados próximos a expirar
   - Automatizar renovación con certbot

---

## 🧪 Testing y Validación

### Checklist de Validación

Para cada entorno, verificar:

- [ ] **Dominio correcto**: `curl -I http://<dominio>` retorna 200 OK (o 301 si redirige a HTTPS)
- [ ] **WebSocket funciona**: Abrir app en navegador y verificar que la UI es interactiva
- [ ] **Eventos Reflex**: Hacer click en botones, verificar que actualiza estado
- [ ] **Endpoint API**: `curl http://<dominio>/api/ping` (si existe)
- [ ] **Backoffice accesible**: `curl -I http://<dominio>/backoffice/`
- [ ] **SSL válido** (pre/pro): `curl -I https://<dominio>` sin errores de certificado
- [ ] **Redirección HTTP→HTTPS** (pre/pro): `curl -I http://<dominio>` retorna 301

### Comandos de Testing

```bash
# Verificar que nginx cargó la configuración correctamente
docker-compose exec nginx nginx -t

# Ver configuración actual
docker-compose exec nginx cat /etc/nginx/nginx.conf

# Verificar qué server_name está configurado
docker-compose exec nginx cat /etc/nginx/nginx.conf | grep server_name

# Verificar que tiene WebSocket support
docker-compose exec nginx cat /etc/nginx/nginx.conf | grep -A 5 "Upgrade"

# Ver logs de nginx en tiempo real
docker-compose logs -f nginx

# Probar conexión desde dentro del contenedor
docker-compose exec nginx curl -I http://web_frontend:8005
docker-compose exec nginx curl -I http://web_backoffice:8006
```

---

## 📚 Referencias

### Documentación del Proyecto
- **Configuración por entorno**: `/infrastructure/environments/<env>/env.yaml`
- **Variables públicas/privadas**: Sección "Domain configuration" en README.md
- **Docker Compose**: `/infrastructure/servers/frontend/docker-compose.yml`

### Archivos Relacionados
- **Configuración macbook**: `/infrastructure/servers/macbook/nginx/nginx.conf`
- **Configuración dev/pre/pro**: `/infrastructure/servers/frontend/nginx/nginx.conf`
- **Script de generación**: `/infrastructure/servers/frontend/nginx/generate_nginx_conf.py`
- **Template recomendado**: `/infrastructure/servers/frontend/nginx/nginx.conf.RECOMENDADO`

### Documentación Externa
- **Nginx Proxy**: https://nginx.org/en/docs/http/ngx_http_proxy_module.html
- **Nginx WebSocket**: https://nginx.org/en/docs/http/websocket.html
- **Reflex Deployment**: https://reflex.dev/docs/hosting/self-hosting/
- **Let's Encrypt**: https://letsencrypt.org/getting-started/

---

## ⚠️ Advertencias de Seguridad

### Para PRE/PRO (Producción)

1. **SSL/TLS es obligatorio**
   - ❌ No desplegar con solo HTTP
   - ✅ Usar certificados válidos (Let's Encrypt o corporativos)
   - ✅ Forzar redirección HTTP → HTTPS

2. **Certificados SSL**
   - ❌ No usar certificados autofirmados en producción
   - ❌ No usar certificados vencidos
   - ✅ Configurar renovación automática

3. **Headers de seguridad**
   - ✅ Incluir `Strict-Transport-Security` (HSTS)
   - ✅ Incluir `X-Frame-Options: SAMEORIGIN`
   - ✅ Incluir `X-Content-Type-Options: nosniff`

4. **Configuración de logs**
   - ✅ Configurar rotación de logs
   - ✅ No loguear información sensible
   - ✅ Monitorear errores 502/504

---

## 📊 Resumen de Cambios Necesarios

| Archivo | Acción | Prioridad | Esfuerzo |
|---------|--------|-----------|----------|
| `/servers/frontend/nginx/nginx.conf` | **Reemplazar completamente** con versión generada | 🔴 ALTA | 30 min |
| `/servers/macbook/nginx/nginx.conf` | Actualizar server_name dinámico | 🟡 MEDIA | 15 min |
| Certificados SSL para pre/pro | Obtener e instalar | 🔴 ALTA | 2-4 horas |
| Script de generación | ✅ Ya creado | - | - |
| Testing completo | Validar en cada entorno | 🔴 ALTA | 1 hora |

**Tiempo estimado total**: 4-6 horas (incluyendo obtención de certificados SSL)

---

## 🎯 Próximos Pasos (Recomendación)

1. **Inmediato** (hoy):
   - [ ] Generar nuevo nginx.conf para dev: `python generate_nginx_conf.py --environment dev`
   - [ ] Desplegar y probar en dev
   - [ ] Validar que Reflex funciona correctamente

2. **Esta semana**:
   - [ ] Obtener certificados SSL para pre/pro (Let's Encrypt)
   - [ ] Generar nginx.conf con SSL para pre
   - [ ] Desplegar y probar en pre

3. **Antes de producción**:
   - [ ] Validar exhaustivamente en pre durante 1 semana
   - [ ] Preparar rollback plan
   - [ ] Desplegar en pro en ventana de mantenimiento

---

**Fin del documento**
**Última actualización**: 2026-02-07
