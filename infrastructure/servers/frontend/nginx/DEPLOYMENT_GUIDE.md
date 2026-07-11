# Guía de Despliegue de Nginx con SSL por Entorno

**Última actualización**: 2026-02-07

---

## 📋 Resumen

Esta guía explica cómo desplegar nginx con SSL en cada entorno (DEV, PRE, PRO).

### Archivos Generados

| Entorno | Archivo nginx.conf | Tipo de Certificados | Método |
|---------|-------------------|---------------------|---------|
| **DEV** | `nginx.conf.dev` | Autofirmados | Script local |
| **PRE** | `nginx.conf.pre` | Let's Encrypt | Certbot en AWS |
| **PRO** | `nginx.conf.pro` | Let's Encrypt | Certbot en AWS |

---

## 🔧 Entorno DEV (VirtualBox - Red Local)

### Características
- **Dominio**: `house.loc`
- **Ubicación**: VirtualBox en servidor de red local
- **Certificados**: Autofirmados (generados localmente)
- **Navegadores**: Mostrarán advertencia de seguridad (normal para certificados autofirmados)

### Paso 1: Generar Certificados SSL Autofirmados

```bash
# En tu máquina local (macbook)
cd /Users/administrator/develop/anewhope/infrastructure/certificates/dev

# Ejecutar el script de generación
bash generate_self_signed_certs.sh
```

**Salida esperada**:
```
✓ Certificados generados exitosamente:
  house.loc.crt
  house.loc.key
```

### Paso 2: Copiar Certificados al Servidor DEV

```bash
# Opción A: Si tienes acceso SSH al servidor frontend de DEV
scp house.loc.crt user@frontend.house.loc:/tmp/
scp house.loc.key user@frontend.house.loc:/tmp/

# Conectar al servidor y mover certificados
ssh user@frontend.house.loc
sudo mkdir -p /etc/nginx/ssl
sudo mv /tmp/house.loc.crt /etc/nginx/ssl/
sudo mv /tmp/house.loc.key /etc/nginx/ssl/
sudo chmod 644 /etc/nginx/ssl/house.loc.crt
sudo chmod 600 /etc/nginx/ssl/house.loc.key
```

```bash
# Opción B: Si usas montajes de red/carpetas compartidas
# Copiar manualmente los certificados a:
#   /etc/nginx/ssl/house.loc.crt
#   /etc/nginx/ssl/house.loc.key
```

### Paso 3: Desplegar nginx.conf para DEV

```bash
# En tu máquina local
cd /Users/administrator/develop/anewhope/infrastructure/servers/frontend/nginx

# Copiar la configuración generada al servidor DEV
scp nginx.conf.dev user@frontend.house.loc:/tmp/nginx.conf

# En el servidor DEV
ssh user@frontend.house.loc
cd /ruta/a/docker-compose/anewhope/infrastructure/servers/frontend
sudo cp /tmp/nginx.conf nginx/nginx.conf

# Verificar la configuración
docker-compose exec nginx nginx -t
```

**Salida esperada**:
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### Paso 4: Reiniciar Nginx

```bash
# En el servidor DEV
docker-compose restart nginx

# Verificar que levantó correctamente
docker-compose ps nginx
docker-compose logs nginx | tail -20
```

### Paso 5: Verificar HTTPS

```bash
# Desde el servidor DEV
curl -Ik https://house.loc
curl -Ik https://frontend.house.loc

# Desde tu navegador
# Ir a: https://house.loc
# Aceptar la advertencia de seguridad (certificado autofirmado)
```

### Solución de Problemas (DEV)

**Problema**: "This site can't provide a secure connection"
```bash
# Verificar que los certificados existen
ls -l /etc/nginx/ssl/house.loc.*

# Verificar permisos
sudo chmod 644 /etc/nginx/ssl/house.loc.crt
sudo chmod 600 /etc/nginx/ssl/house.loc.key

# Ver logs de nginx
docker-compose logs nginx | grep -i ssl
```

**Problema**: "NET::ERR_CERT_AUTHORITY_INVALID"
- Es normal para certificados autofirmados
- Click en "Advanced" → "Proceed to house.loc"
- O importa el certificado en el almacén de confianza del sistema

---

## 🌐 Entorno PRE (AWS - IP Pública)

### Características
- **Dominio**: `getmylllm.com`
- **Ubicación**: AWS EC2 con IP pública
- **Certificados**: Let's Encrypt (válidos, gratuitos, renovación automática)
- **Navegadores**: Sin advertencias (certificados válidos)

### Requisitos Previos

1. **DNS configurado**: `getmylllm.com` debe apuntar a la IP pública de AWS
2. **Firewall/Security Group**: Puertos 80 y 443 abiertos
3. **Nginx corriendo**: Al menos en puerto 80

**Verificar DNS**:
```bash
# En tu máquina local
dig +short getmylllm.com
# Debe mostrar la IP pública del servidor PRE en AWS
```

**Verificar puertos abiertos**:
```bash
# En el servidor PRE
sudo netstat -tlnp | grep -E ':(80|443)'
```

### Paso 1: Conectar al Servidor PRE

```bash
# Desde tu máquina local
ssh -i /ruta/a/clave.pem user@<IP_PUBLICA_PRE>

# O si ya tienes el dominio configurado
ssh -i /ruta/a/clave.pem user@frontend.anewhope.aws
```

### Paso 2: Copiar Scripts al Servidor

```bash
# Desde tu máquina local
cd /Users/administrator/develop/anewhope/infrastructure/certificates/pre

scp setup_letsencrypt.sh user@<IP_PUBLICA_PRE>:/tmp/

# Conectar al servidor
ssh user@<IP_PUBLICA_PRE>
```

### Paso 3: Obtener Certificados Let's Encrypt

```bash
# En el servidor PRE
cd /tmp
sudo bash setup_letsencrypt.sh
```

**El script te preguntará**:
1. **Email del administrador**: Para notificaciones de renovación
2. **Método de validación**: Recomendado: Opción 1 (Nginx)

**Proceso automático**:
- Instala certbot (si no está instalado)
- Obtiene certificados de Let's Encrypt
- Configura renovación automática
- Crea symlinks en `/etc/nginx/ssl/`

**Salida esperada**:
```
✓ Certificados obtenidos exitosamente
✓ Symlinks creados:
  /etc/nginx/ssl/getmylllm.com.crt -> /etc/letsencrypt/live/getmylllm.com/fullchain.pem
  /etc/nginx/ssl/getmylllm.com.key -> /etc/letsencrypt/live/getmylllm.com/privkey.pem
```

### Paso 4: Desplegar nginx.conf para PRE

```bash
# Desde tu máquina local
cd /Users/administrator/develop/anewhope/infrastructure/servers/frontend/nginx

scp nginx.conf.pre user@<IP_PUBLICA_PRE>:/tmp/nginx.conf

# En el servidor PRE
ssh user@<IP_PUBLICA_PRE>
cd /opt/anewhope/infrastructure/servers/frontend  # Ajustar ruta
sudo cp /tmp/nginx.conf nginx/nginx.conf

# Verificar la configuración
docker-compose exec nginx nginx -t
```

### Paso 5: Actualizar docker-compose.yml

Descomentar la línea de Let's Encrypt en `docker-compose.yml`:

```yaml
nginx:
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    - /etc/nginx/ssl:/etc/nginx/ssl:ro
    - /etc/letsencrypt:/etc/letsencrypt:ro  # ← Descomentar esta línea
```

### Paso 6: Reiniciar Nginx

```bash
# En el servidor PRE
docker-compose down
docker-compose up -d

# Verificar logs
docker-compose logs -f nginx
```

### Paso 7: Verificar HTTPS

```bash
# Desde el servidor PRE
curl -Ik https://getmylllm.com
curl -Ik https://www.getmylllm.com

# Desde tu navegador
# Ir a: https://www.getmylllm.com
# NO debe mostrar advertencias de seguridad
```

### Paso 8: Verificar Renovación Automática

```bash
# En el servidor PRE
sudo certbot renew --dry-run
```

**Salida esperada**:
```
Congratulations, all simulated renewals succeeded
```

### Solución de Problemas (PRE)

**Problema**: "Failed to obtain certificate"
```bash
# Verificar DNS
dig +short getmylllm.com
# Debe mostrar la IP del servidor

# Verificar que nginx está corriendo en puerto 80
curl -I http://getmylllm.com

# Ver logs de certbot
sudo tail -100 /var/log/letsencrypt/letsencrypt.log
```

**Problema**: "Connection refused on port 443"
```bash
# Verificar que nginx escucha en 443
docker-compose exec nginx netstat -tlnp | grep 443

# Verificar security group en AWS
# Debe permitir tráfico entrante en puerto 443
```

**Problema**: "Certificate has expired"
```bash
# Forzar renovación
sudo certbot renew --force-renewal

# Verificar cron job de renovación
sudo crontab -l | grep certbot
```

---

## 🚀 Entorno PRO (AWS - Producción)

### Características
- **Dominio**: `getmylllm.com` (mismo que PRE)
- **Ubicación**: AWS EC2 con IP pública
- **Certificados**: Let's Encrypt (válidos, gratuitos)
- **Proceso**: Idéntico a PRE

### Procedimiento

**Seguir exactamente los mismos pasos que PRE**, pero usando:
- `nginx.conf.pro` en lugar de `nginx.conf.pre`
- Script: `/infrastructure/certificates/pro/setup_letsencrypt.sh`

**Recomendaciones adicionales para PRO**:

1. **Backup antes de cambios**:
   ```bash
   # Backup de configuración actual
   cp nginx/nginx.conf nginx/nginx.conf.backup.$(date +%Y%m%d)
   ```

2. **Ventana de mantenimiento**:
   - Planificar el despliegue en horario de bajo tráfico
   - Notificar a usuarios si es necesario

3. **Monitoreo post-despliegue**:
   ```bash
   # Monitorear logs durante 10 minutos
   docker-compose logs -f nginx

   # Verificar métricas de acceso
   docker-compose exec nginx tail -f /var/log/nginx/access.log
   ```

4. **Plan de rollback**:
   ```bash
   # Si algo sale mal, restaurar backup
   cp nginx/nginx.conf.backup.YYYYMMDD nginx/nginx.conf
   docker-compose restart nginx
   ```

5. **Monitoreo de certificados**:
   - Configurar alertas para certificados próximos a expirar (30 días)
   - Verificar renovación automática funciona: `sudo certbot renew --dry-run`

---

## 📊 Checklist de Validación Post-Despliegue

### Para DEV

- [ ] Certificados autofirmados generados
- [ ] Certificados copiados a `/etc/nginx/ssl/`
- [ ] nginx.conf.dev desplegado
- [ ] Nginx reiniciado sin errores
- [ ] `curl -Ik https://house.loc` retorna 200 OK
- [ ] Navegador muestra la aplicación (aceptando advertencia)
- [ ] WebSocket funciona (UI interactiva)
- [ ] Backoffice accesible en `/backoffice/`

### Para PRE/PRO

- [ ] DNS configurado correctamente
- [ ] Puertos 80 y 443 abiertos en firewall
- [ ] Certbot instalado
- [ ] Certificados Let's Encrypt obtenidos
- [ ] Renovación automática configurada
- [ ] `certbot renew --dry-run` exitoso
- [ ] nginx.conf.pre/pro desplegado
- [ ] docker-compose.yml actualizado (volumen letsencrypt)
- [ ] Nginx reiniciado sin errores
- [ ] `curl -Ik https://www.getmylllm.com` retorna 200 OK
- [ ] Navegador muestra la aplicación SIN advertencias
- [ ] WebSocket funciona (UI interactiva)
- [ ] Backoffice accesible en `/backoffice/`
- [ ] HTTP redirige a HTTPS automáticamente

---

## 🔍 Comandos Útiles de Diagnóstico

```bash
# Ver configuración actual de nginx
docker-compose exec nginx cat /etc/nginx/nginx.conf

# Ver qué server_name está configurado
docker-compose exec nginx grep -E "server_name|ssl_certificate" /etc/nginx/nginx.conf

# Verificar sintaxis de nginx
docker-compose exec nginx nginx -t

# Ver certificados instalados
ls -l /etc/nginx/ssl/
openssl x509 -in /etc/nginx/ssl/*.crt -text -noout | grep -E "(Subject:|Not Before|Not After)"

# Ver logs en tiempo real
docker-compose logs -f nginx

# Ver solo errores
docker-compose logs nginx | grep -i error

# Ver conexiones activas
docker-compose exec nginx netstat -an | grep -E ':(80|443)'

# Probar WebSocket desde dentro del contenedor
docker-compose exec nginx curl -I \
  -H "Upgrade: websocket" \
  -H "Connection: Upgrade" \
  http://web_frontend:8005/_event
```

---

## 📚 Referencias

### Documentación
- **Let's Encrypt**: https://letsencrypt.org/getting-started/
- **Certbot**: https://certbot.eff.org/
- **Nginx SSL**: https://nginx.org/en/docs/http/configuring_https_servers.html
- **Reflex Deployment**: https://reflex.dev/docs/hosting/self-hosting/

### Archivos del Proyecto
- **Configuraciones nginx**: `/infrastructure/servers/frontend/nginx/nginx.conf.{dev,pre,pro}`
- **Scripts de certificados DEV**: `/infrastructure/certificates/dev/generate_self_signed_certs.sh`
- **Scripts de certificados PRE/PRO**: `/infrastructure/certificates/{pre,pro}/setup_letsencrypt.sh`
- **Docker Compose**: `/infrastructure/servers/frontend/docker-compose.yml`
- **Variables de entorno**: `/infrastructure/environments/{dev,pre,pro}/env.yaml`

---

## ⚠️ Notas Importantes

### Seguridad

1. **Nunca commitear claves privadas** (`.key` files) al repositorio Git
2. **Permisos de certificados**:
   - `.crt` (público): `644` (lectura para todos)
   - `.key` (privado): `600` (solo root)
3. **Renovación de certificados**: Verificar cada 2 meses que la renovación automática funciona
4. **Backup de certificados**: Incluir `/etc/letsencrypt/` en backups regulares

### Diferencias entre Entornos

| Aspecto | DEV | PRE | PRO |
|---------|-----|-----|-----|
| Certificados | Autofirmados | Let's Encrypt | Let's Encrypt |
| Validez | 365 días | 90 días (auto-renueva) | 90 días (auto-renueva) |
| Advertencia navegador | ⚠️ Sí | ✅ No | ✅ No |
| Renovación | Manual | Automática | Automática |
| Ubicación certs | `/etc/nginx/ssl/` | `/etc/letsencrypt/live/` | `/etc/letsencrypt/live/` |

---

**Fin de la guía**
**Última actualización**: 2026-02-07
