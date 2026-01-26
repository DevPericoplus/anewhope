# Redis - Entorno DEV

## 📋 Información del Entorno

- **Entorno:** Desarrollo (dev)
- **Propósito:** Testing y desarrollo compartido
- **Configuración:** `redis.conf`
- **Servidor:** `<HOSTNAME_DEV>` (definir)
- **IP:** `<IP_DEL_SERVIDOR_DEV>` (definir)

---

## 🚀 Despliegue Inicial

### 1. Preparación del Servidor

```bash
# Conectar al servidor dev
ssh admin@<IP_DEL_SERVIDOR_DEV>

# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Redis
sudo apt install redis-server -y

# Verificar instalación
redis-server --version
```

### 2. Configurar Redis

```bash
# Crear backup de configuración original
sudo cp /etc/redis/redis.conf /etc/redis/redis.conf.backup

# Copiar configuración desde repositorio
sudo cp /path/to/repo/infrastructure/redis/dev/redis.conf /etc/redis/redis.conf

# IMPORTANTE: Editar archivo y reemplazar placeholders
sudo nano /etc/redis/redis.conf

# Reemplazar:
# - <IP_DEL_SERVIDOR_DEV> con la IP real del servidor
# - <PASSWORD_DEV> con el password de protected_values.py del entorno dev
```

### 3. Crear Directorios

```bash
# Crear directorios necesarios
sudo mkdir -p /var/lib/redis /var/log/redis

# Asignar permisos
sudo chown redis:redis /var/lib/redis /var/log/redis
sudo chmod 750 /var/lib/redis /var/log/redis

# Verificar
ls -la /var/lib/redis
ls -la /var/log/redis
```

### 4. Configurar Firewall

```bash
# Permitir acceso desde frontend dev
sudo ufw allow from <IP_FRONTEND_DEV> to any port 6379

# Permitir acceso desde backoffice dev
sudo ufw allow from <IP_BACKOFFICE_DEV> to any port 6379

# Bloquear otros accesos
sudo ufw deny 6379

# Verificar reglas
sudo ufw status
```

### 5. Iniciar Servicio

```bash
# Habilitar inicio automático
sudo systemctl enable redis-server

# Iniciar servicio
sudo systemctl start redis-server

# Verificar estado
sudo systemctl status redis-server

# Verificar logs
sudo tail -f /var/log/redis/redis-server.log
```

### 6. Verificación

```bash
# Probar conexión local
redis-cli -a <PASSWORD_DEV> ping
# Debe responder: PONG

# Verificar información
redis-cli -a <PASSWORD_DEV> INFO server

# Verificar memoria
redis-cli -a <PASSWORD_DEV> INFO memory

# Probar desde máquina remota
redis-cli -h <IP_DEL_SERVIDOR_DEV> -a <PASSWORD_DEV> ping
```

---

## 🔧 Configuración de Aplicaciones

### Variables en env.yaml (dev)

```yaml
redis_host: <IP_DEL_SERVIDOR_DEV>
redis_port: "6379"
redis_db: "0"
redis_token_expiration: "3600"
redis_lock_expiration: "10000"
redis_lock_warning_threshold: "1000"
```

### Password en protected_values.py (dev)

```python
# Redis (sesión compartida)
redis_password = "<PASSWORD_DEV>"
```

---

## 📊 Monitoreo

### Logs en Tiempo Real

```bash
# Logs del servidor
sudo tail -f /var/log/redis/redis-server.log

# Logs de sistema
sudo journalctl -u redis-server -f

# Comandos lentos
redis-cli -a <PASSWORD_DEV> SLOWLOG GET 10
```

### Métricas

```bash
# Información general
redis-cli -a <PASSWORD_DEV> INFO

# Clientes conectados
redis-cli -a <PASSWORD_DEV> CLIENT LIST

# Uso de memoria
redis-cli -a <PASSWORD_DEV> INFO memory

# Estadísticas de comandos
redis-cli -a <PASSWORD_DEV> INFO stats

# Tamaño de la base de datos
redis-cli -a <PASSWORD_DEV> DBSIZE
```

### Sesiones Activas

```bash
# Listar keys de sesión
redis-cli -a <PASSWORD_DEV> KEYS "reflex:session:*"

# Contar sesiones
redis-cli -a <PASSWORD_DEV> KEYS "reflex:session:*" | wc -l

# Ver TTL de una sesión
redis-cli -a <PASSWORD_DEV> TTL "reflex:session:TOKEN_AQUI"
```

---

## 🛠️ Mantenimiento

### Backup Manual

```bash
# Backup de datos
sudo cp /var/lib/redis/dump.rdb /backup/redis-dev-$(date +%Y%m%d).rdb
sudo cp /var/lib/redis/appendonly.aof /backup/redis-dev-$(date +%Y%m%d).aof

# Verificar tamaño
du -sh /var/lib/redis/
```

### Limpiar Sesiones Expiradas

```bash
# Redis limpia automáticamente, pero se puede forzar
redis-cli -a <PASSWORD_DEV> FLUSHDB
# CUIDADO: Esto borra TODAS las keys
```

### Reiniciar Servicio

```bash
# Reiniciar
sudo systemctl restart redis-server

# Verificar que levantó correctamente
sudo systemctl status redis-server
redis-cli -a <PASSWORD_DEV> ping
```

---

## 🚨 Troubleshooting

### Redis no inicia

```bash
# Ver logs de error
sudo journalctl -u redis-server -n 50

# Verificar configuración
sudo redis-server /etc/redis/redis.conf --test-memory 1

# Verificar permisos
ls -la /var/lib/redis
ls -la /var/log/redis
```

### No se puede conectar

```bash
# Verificar que está escuchando
sudo netstat -tlnp | grep 6379

# Verificar firewall
sudo ufw status

# Probar conexión local
redis-cli -a <PASSWORD_DEV> ping

# Ver clientes conectados
redis-cli -a <PASSWORD_DEV> CLIENT LIST
```

### Memoria llena

```bash
# Ver uso actual
redis-cli -a <PASSWORD_DEV> INFO memory

# Ver maxmemory configurado
redis-cli -a <PASSWORD_DEV> CONFIG GET maxmemory

# Aumentar límite temporalmente
redis-cli -a <PASSWORD_DEV> CONFIG SET maxmemory 1gb

# Para cambio permanente, editar redis.conf y reiniciar
```

---

## 📚 Referencias

- Configuración: `infrastructure/redis/dev/redis.conf`
- Variables: `infrastructure/environments/dev/env.yaml`
- Passwords: `infrastructure/environments/dev/protected_values.py`
- Documentación principal: `README.md`

---

**Última actualización:** 2026-01-26  
**Responsable:** Equipo DevOps
