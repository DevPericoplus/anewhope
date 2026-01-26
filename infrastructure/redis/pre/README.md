# Redis - Entorno PRE

## 📋 Información del Entorno

- **Entorno:** Pre-producción (pre)
- **Propósito:** Testing de producción, validación final
- **Configuración:** `redis.conf` (idéntica a producción)
- **Servidor:** `<HOSTNAME_PRE>` (definir)
- **IP:** `<IP_DEL_SERVIDOR_PRE>` (definir)

⚠️ **IMPORTANTE:** Este entorno debe ser idéntico a producción para pruebas reales.

---

## 🚀 Despliegue Inicial

### 1. Preparación del Servidor

```bash
# Conectar al servidor pre
ssh admin@<IP_DEL_SERVIDOR_PRE>

# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Redis (usar versión LTS estable)
sudo apt install redis-server -y

# Verificar versión (debe ser >= 6.2)
redis-server --version
```

### 2. Optimizar Sistema Operativo

```bash
# Configurar parámetros del kernel
echo "net.core.somaxconn = 65535" | sudo tee -a /etc/sysctl.conf
echo "vm.overcommit_memory = 1" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# Deshabilitar Transparent Huge Pages
echo never | sudo tee /sys/kernel/mm/transparent_hugepage/enabled
echo never | sudo tee /sys/kernel/mm/transparent_hugepage/defrag

# Hacerlo permanente
sudo nano /etc/rc.local
# Añadir:
# echo never > /sys/kernel/mm/transparent_hugepage/enabled
# echo never > /sys/kernel/mm/transparent_hugepage/defrag

# Configurar ulimit para usuario redis
echo "redis soft nofile 65535" | sudo tee -a /etc/security/limits.conf
echo "redis hard nofile 65535" | sudo tee -a /etc/security/limits.conf
```

### 3. Configurar Redis

```bash
# Crear backup de configuración original
sudo cp /etc/redis/redis.conf /etc/redis/redis.conf.backup.$(date +%Y%m%d)

# Copiar configuración desde repositorio
sudo cp /path/to/repo/infrastructure/redis/pre/redis.conf /etc/redis/redis.conf

# IMPORTANTE: Editar archivo y reemplazar placeholders
sudo nano /etc/redis/redis.conf

# Reemplazar:
# - <IP_DEL_SERVIDOR_PRE> con la IP real del servidor
# - <PASSWORD_PRE> con password fuerte (generar con: openssl rand -base64 24)
# - Descomentar comandos renombrados para seguridad

# Asegurar permisos del archivo
sudo chmod 640 /etc/redis/redis.conf
sudo chown redis:redis /etc/redis/redis.conf
```

### 4. Crear Directorios

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

### 5. Configurar Firewall (Estricto)

```bash
# Permitir SOLO desde frontend pre
sudo ufw allow from <IP_FRONTEND_PRE> to any port 6379 comment 'Redis from frontend-pre'

# Permitir SOLO desde backoffice pre
sudo ufw allow from <IP_BACKOFFICE_PRE> to any port 6379 comment 'Redis from backoffice-pre'

# Permitir desde servidor de monitoreo (opcional)
# sudo ufw allow from <IP_MONITORING> to any port 6379 comment 'Redis monitoring'

# Bloquear todo lo demás
sudo ufw deny 6379 comment 'Redis block default'

# Verificar reglas
sudo ufw status numbered
```

### 6. Iniciar Servicio

```bash
# Habilitar inicio automático
sudo systemctl enable redis-server

# Iniciar servicio
sudo systemctl start redis-server

# Verificar estado
sudo systemctl status redis-server

# Verificar logs (no debe haber errores)
sudo tail -f /var/log/redis/redis-server.log
```

### 7. Verificación Completa

```bash
# 1. Probar conexión local
redis-cli -a <PASSWORD_PRE> ping
# Debe responder: PONG

# 2. Verificar información del servidor
redis-cli -a <PASSWORD_PRE> INFO server

# 3. Verificar que comandos peligrosos están deshabilitados
redis-cli -a <PASSWORD_PRE> FLUSHDB
# Debe dar error: unknown command

redis-cli -a <PASSWORD_PRE> CONFIG GET *
# Debe dar error: unknown command

# 4. Verificar memoria
redis-cli -a <PASSWORD_PRE> INFO memory

# 5. Probar desde máquina remota (frontend/backoffice)
redis-cli -h <IP_DEL_SERVIDOR_PRE> -a <PASSWORD_PRE> ping

# 6. Verificar persistencia
redis-cli -a <PASSWORD_PRE> SET test:key "test-value"
redis-cli -a <PASSWORD_PRE> GET test:key
redis-cli -a <PASSWORD_PRE> DEL test:key

# 7. Verificar que AOF está activo
ls -la /var/lib/redis/appendonly.aof
```

---

## 🔧 Configuración de Aplicaciones

### Variables en env.yaml (pre)

```yaml
redis_host: <IP_DEL_SERVIDOR_PRE>
redis_port: "6379"
redis_db: "0"
redis_token_expiration: "3600"
redis_lock_expiration: "10000"
redis_lock_warning_threshold: "1000"
```

### Password en protected_values.py (pre)

```python
# Redis (sesión compartida)
# IMPORTANTE: Generar password fuerte único para pre
redis_password = "<PASSWORD_PRE>"
```

⚠️ **Usar password diferente a dev y pro**

---

## 💾 Backup y Recuperación

### Configurar Backup Automático

```bash
# Crear script de backup
sudo nano /usr/local/bin/redis-backup.sh
```

```bash
#!/bin/bash
# Backup de Redis para entorno PRE

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/redis/pre"
RETENTION_DAYS=30

# Crear directorio de backup
mkdir -p $BACKUP_DIR

# Backup de RDB
cp /var/lib/redis/dump.rdb $BACKUP_DIR/dump-pre-$DATE.rdb

# Backup de AOF
cp /var/lib/redis/appendonly.aof $BACKUP_DIR/appendonly-pre-$DATE.aof

# Comprimir
gzip $BACKUP_DIR/dump-pre-$DATE.rdb
gzip $BACKUP_DIR/appendonly-pre-$DATE.aof

# Limpiar backups antiguos
find $BACKUP_DIR -name "*.rdb.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.aof.gz" -mtime +$RETENTION_DAYS -delete

# Log
echo "$(date): Backup completado" >> /var/log/redis/backup.log
```

```bash
# Hacer ejecutable
sudo chmod +x /usr/local/bin/redis-backup.sh

# Añadir a crontab (backup diario a las 3 AM)
sudo crontab -e
# Añadir:
# 0 3 * * * /usr/local/bin/redis-backup.sh
```

### Restaurar desde Backup

```bash
# Detener Redis
sudo systemctl stop redis-server

# Restaurar archivo RDB
sudo gunzip -c /backup/redis/pre/dump-pre-YYYYMMDD.rdb.gz > /var/lib/redis/dump.rdb

# Restaurar archivo AOF
sudo gunzip -c /backup/redis/pre/appendonly-pre-YYYYMMDD.aof.gz > /var/lib/redis/appendonly.aof

# Asegurar permisos
sudo chown redis:redis /var/lib/redis/dump.rdb
sudo chown redis:redis /var/lib/redis/appendonly.aof

# Iniciar Redis
sudo systemctl start redis-server

# Verificar
redis-cli -a <PASSWORD_PRE> DBSIZE
```

---

## 📊 Monitoreo y Alertas

### Instalar Redis Exporter (Prometheus)

```bash
# Descargar Redis Exporter
wget https://github.com/oliver006/redis_exporter/releases/download/v1.55.0/redis_exporter-v1.55.0.linux-amd64.tar.gz

# Extraer
tar xvf redis_exporter-v1.55.0.linux-amd64.tar.gz

# Copiar binario
sudo cp redis_exporter-v1.55.0.linux-amd64/redis_exporter /usr/local/bin/

# Crear servicio
sudo nano /etc/systemd/system/redis_exporter.service
```

```ini
[Unit]
Description=Redis Exporter
After=network.target

[Service]
Type=simple
User=redis
ExecStart=/usr/local/bin/redis_exporter \
  --redis.addr=localhost:6379 \
  --redis.password=<PASSWORD_PRE>
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Habilitar y iniciar
sudo systemctl daemon-reload
sudo systemctl enable redis_exporter
sudo systemctl start redis_exporter

# Verificar métricas
curl http://localhost:9121/metrics
```

### Métricas Clave a Monitorear

- **Memoria:** Uso actual vs. límite (maxmemory)
- **Comandos:** Throughput de comandos por segundo
- **Latencia:** Tiempo de respuesta de comandos
- **Conexiones:** Clientes conectados
- **Persistencia:** Último guardado exitoso (RDB/AOF)
- **Replicación:** Estado (si aplica)

---

## 🔒 Seguridad

### Auditoría de Seguridad

```bash
# Verificar bind
redis-cli -a <PASSWORD_PRE> CONFIG GET bind

# Verificar protected-mode
redis-cli -a <PASSWORD_PRE> CONFIG GET protected-mode

# Verificar que comandos están renombrados
redis-cli -a <PASSWORD_PRE> FLUSHDB  # Debe fallar
redis-cli -a <PASSWORD_PRE> CONFIG GET *  # Debe fallar

# Verificar firewall
sudo ufw status verbose

# Verificar logs de acceso
sudo grep "Accepted" /var/log/redis/redis-server.log
```

### Rotación de Password (cada 90 días)

```bash
# 1. Generar nuevo password
NEW_PASSWORD=$(openssl rand -base64 24)
echo "Nuevo password: $NEW_PASSWORD"

# 2. Actualizar redis.conf
sudo nano /etc/redis/redis.conf
# Cambiar: requirepass <PASSWORD_NUEVO>

# 3. Actualizar protected_values.py en repositorio

# 4. Recargar configuración (sin downtime)
redis-cli -a <PASSWORD_ANTIGUO> CONFIG SET requirepass $NEW_PASSWORD

# 5. Reiniciar servicio (en ventana de mantenimiento)
sudo systemctl restart redis-server

# 6. Verificar con nuevo password
redis-cli -a $NEW_PASSWORD ping

# 7. Desplegar aplicaciones con nuevo password
```

---

## 🧪 Testing de Carga

### Benchmark básico

```bash
# Test de escritura/lectura
redis-benchmark -h <IP_DEL_SERVIDOR_PRE> -a <PASSWORD_PRE> -t set,get -n 100000 -q

# Test con pipeline
redis-benchmark -h <IP_DEL_SERVIDOR_PRE> -a <PASSWORD_PRE> -t set,get -n 100000 -P 16 -q

# Test específico de sesiones
redis-benchmark -h <IP_DEL_SERVIDOR_PRE> -a <PASSWORD_PRE> -t set,get,del -n 50000 --csv
```

---

## 🚨 Procedimientos de Emergencia

### Redis no responde

```bash
# 1. Verificar proceso
ps aux | grep redis-server

# 2. Verificar logs
sudo tail -100 /var/log/redis/redis-server.log

# 3. Verificar memoria del sistema
free -h
df -h /var/lib/redis

# 4. Reiniciar servicio
sudo systemctl restart redis-server

# 5. Notificar al equipo
```

### Memoria llena

```bash
# 1. Verificar uso
redis-cli -a <PASSWORD_PRE> INFO memory | grep used_memory_human

# 2. Ver keys más grandes
redis-cli -a <PASSWORD_PRE> --bigkeys

# 3. Aumentar límite temporalmente
redis-cli -a <PASSWORD_PRE> CONFIG_PRE_2025 SET maxmemory 4gb

# 4. Planificar aumento permanente
```

---

## 📚 Referencias

- Configuración: `infrastructure/redis/pre/redis.conf`
- Variables: `infrastructure/environments/pre/env.yaml`
- Passwords: `infrastructure/environments/pre/protected_values.py`
- Documentación principal: `README.md`
- Runbook de incidentes: `docs/REDIS_RUNBOOK.md` (crear)

---

**Última actualización:** 2026-01-26  
**Responsable:** Equipo DevOps  
**Siguiente revisión:** Antes de pasar a producción
