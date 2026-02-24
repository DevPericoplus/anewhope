# Configuración de Acceso Externo a Nginx

Esta guía explica cómo permitir el acceso a nginx desde otros equipos en la red local.

## 🚀 Inicio Rápido

### 1. Ejecutar el script de configuración de firewall

```bash
cd /Users/administrator/develop/anewhope
sudo ./scripts/configure_firewall_nginx.sh
```

Este script:
- ✅ Verifica que nginx esté corriendo
- ✅ Confirma que los puertos estén activos (443, 8080, 8443)
- ✅ Configura el firewall de macOS para permitir nginx
- ✅ Muestra las URLs para acceso externo
- ✅ Proporciona comandos de verificación

### 2. Verificar acceso

```bash
./tests/test_external_access.sh
```

Este script:
- ✅ Detecta tu IP local
- ✅ Verifica que nginx esté corriendo
- ✅ Prueba conectividad en los 3 puertos
- ✅ Muestra las URLs para compartir

## 📝 URLs de Acceso

Una vez configurado, desde cualquier equipo en tu red local podrás acceder con:

| Servicio | URL | Puerto |
|----------|-----|--------|
| **Frontend** | `https://192.168.0.101` | 443 |
| **Backoffice** | `https://192.168.0.101:8443` | 8443 |
| **HTTP** (redirige) | `http://192.168.0.101:8080` | 8080 |

⚠️ **Nota**: Sustituye `192.168.0.101` por tu IP local real (el script te la mostrará).

## 🔍 Monitoreo

Para ver las conexiones entrantes en tiempo real:

```bash
tail -f /usr/local/var/log/nginx/access.log
```

Cuando un equipo externo se conecte, verás su IP en lugar de `127.0.0.1`.

## ⚙️ Solución de Problemas

### Problema: No se puede conectar desde otro equipo

**Solución 1: Desactivar firewall temporalmente (solo para pruebas)**
```bash
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate off
```

Prueba la conexión. Si funciona, el problema es el firewall.

**Solución 2: Verificar que nginx escuche en todas las interfaces**
```bash
lsof -nP -iTCP -sTCP:LISTEN | grep nginx
```

Deberías ver `*:443`, `*:8080`, `*:8443` (no `127.0.0.1:443`).

**Solución 3: Verificar configuración de nginx**
```bash
nginx -t
cat /usr/local/etc/nginx/nginx.conf | grep "listen"
```

Debe mostrar `listen 0.0.0.0:443 ssl;` (no solo `listen 443 ssl;`)

**Solución 4: Reactivar firewall después de probar**
```bash
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on
```

### Problema: Advertencia de certificado SSL

Esto es **normal** cuando accedes por IP. Los certificados están generados para `tfmmyllm.ai`.

**Opciones:**
1. **Aceptar el riesgo** en el navegador (recomendado para desarrollo)
2. **Usar `/etc/hosts`** en cada equipo cliente (mapear IP → tfmmyllm.ai)
3. **Regenerar certificados** incluyendo la IP:
   ```bash
   cd infrastructure/certificates/macbook
   mkcert -key-file tfmmyllm.ai-key.pem \
          -cert-file tfmmyllm.ai.pem \
          tfmmyllm.ai "*.tfmmyllm.ai" localhost 127.0.0.1 ::1 192.168.0.101
   nginx -s reload
   ```

## 🔒 Configuración de /etc/hosts en Equipos Clientes

Si quieres usar `https://tfmmyllm.ai` desde otros equipos:

### Windows
1. Abrir como Administrador: `C:\Windows\System32\drivers\etc\hosts`
2. Añadir: `192.168.0.101    tfmmyllm.ai`

### macOS/Linux
```bash
sudo nano /etc/hosts
# Añadir: 192.168.0.101    tfmmyllm.ai
```

Después podrás usar:
- `https://tfmmyllm.ai` (Frontend)
- `https://tfmmyllm.ai:8443` (Backoffice)

## 📊 Archivos Modificados

- `infrastructure/servers/macbook/nginx/nginx.conf`
  - Añadido `0.0.0.0` en directivas `listen`
  - Añadido `192.168.0.101` en `server_name`
  - Cambio de redirecciones de `tfmmyllm.ai` a `$host`

## 🛠️ Comandos Útiles

```bash
# Ver estado de nginx
ps aux | grep nginx

# Reiniciar nginx
nginx -s reload

# Ver logs de errores
tail -f /usr/local/var/log/nginx/error.log

# Ver lista de firewall
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --listapps | grep nginx

# Probar desde terminal
curl -k https://192.168.0.101
```

## 📞 Soporte

Si después de ejecutar estos scripts no funciona, verifica:
1. ✅ Firewall está configurado/desactivado
2. ✅ Nginx escucha en `0.0.0.0` (todas las interfaces)
3. ✅ Los puertos no están bloqueados por el router
4. ✅ Ambos equipos están en la misma red local

---

**Última actualización**: 2026-02-02
