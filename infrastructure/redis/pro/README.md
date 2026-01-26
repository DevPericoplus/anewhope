# Redis - Entorno PRODUCCIÓN

## 📋 Información del Entorno

- **Entorno:** Producción (pro)
- **Propósito:** Sistema en vivo, usuarios reales
- **Configuración:** `redis.conf` (máxima seguridad y durabilidad)
- **Servidor:** `<HOSTNAME_PRO>` (definir)
- **IP:** `<IP_DEL_SERVIDOR_PRO>` (definir)

🚨 **CRÍTICO:** Cualquier cambio en producción requiere:
- Aprobación del equipo de operaciones
- Window de mantenimiento planificado
- Plan de rollback documentado
- Testing previo en PRE

---

## 🚀 Despliegue Inicial (Solo con Aprobación)

### Pre-requisitos

- [ ] Configuración probada en PRE durante al menos 1 semana
- [ ] Plan de rollback documentado
- [ ] Backup completo del sistema
- [ ] Window de mantenimiento aprobado
- [ ] Equipo de guardia disponible
- [ ] Monitoreo configurado y validado

### 1. Preparación del Servidor

```bash
# Conectar al servidor pro
ssh admin@<IP_DEL_SERVIDOR_PRO>

# Actualizar sistema (solo si es necesario, en window de mantenimiento)
sudo apt update
sudo apt list --upgradable

# Instalar Redis versión LTS estable
# IMPORTANTE: Usar misma versión que en PRE
sudo apt install redis-server=6:7.0.* -y

# Verificar versión exacta
redis-server --version
```

### 2. Optimización del Sistema Operativo

```bash
# Configurar parámetros del kernel
cat <<EOF | sudo tee -a /etc/sysctl.conf
# Redis optimizations
net.core.somaxconn = 65535
vm.overcommit_memory = 1
vm.swappiness = 1
net.ipv4.tcp_max_syn_backlog = 65535
EOF

sudo sysctl -p

# Deshabilitar Transparent Huge Pages (THP)
cat <<EOF | sudo tee /etc/systemd/system/disable-thp.service
[Unit]
Description=Disable Transparent Huge Pages (THP)
DefaultDependencies=no
After=sysinit.target local-fs.target
Before=redis-server.service

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'echo never | tee /sys/kernel/mm/transparent_hugepage/enabled > /dev/null'
ExecStart=/bin/sh -c 'echo never | tee /sys/kernel/mm/transparent_hugepage/defrag > /dev/null'

[Install]
WantedBy=basic.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable disable-thp
sudo systemctl start disable-thp

# Verificar
cat /sys/kernel/mm/transparent_hugepage/enabled  # Debe mostrar: [never]

# Configurar ulimit para usuario redis
cat <<EOF | sudo tee -a /etc/security/limits.conf
redis soft nofile 65535
redis hard nofile 65535
redis soft nproc 65535
redis hard nproc 65535
EOF

# Reboot para aplicar todos los cambios
# sudo reboot
```

### 3. Configurar Redis

```bash
# Crear backup de configuración original
sudo cp /etc/redis/redis.conf /etc/redis/redis.conf.original.$(date +%Y%m%d)

# Copiar configuración desde repositorio
sudo cp /path/to/repo/infrastructure/redis/pro/redis.conf /etc/redis/redis.conf

# CRÍTICO: Editar archivo con valores reales
sudo nano /etc/redis/redis.conf

# Reemplazar:
# - <IP_DEL_SERVIDOR_PRO> → IP real del servidor
# - <PASSWORD_PRO> → Password fuerte (openssl rand -base64 32)
# - Descomentar y personalizar comandos renombrados
# - Ajustar maxmemory según RAM del servidor (dejar 20% libre)
# - Revisar TODOS los parámetros

# Asegurar permisos estrictos
sudo chmod 600 /etc/redis/redis.conf
sudo chown redis:redis /etc/redis/redis.conf

# Validar configuración
sudo redis-server /etc/redis/redis.conf --test-memory 1
```

### 4. Crear Estructura de Directorios

```bash
# Crear directorios
sudo mkdir -p /var/lib/redis /var/log/redis /backup/redis

# Asignar permisos
sudo chown redis:redis /var/lib/redis /var/log/redis
sudo chmod 700 /var/lib/redis
sudo chmod 750 /var/log/redis

# Verificar
ls -la /var/lib/redis
ls -la /var/log/redis
```

### 5. Configurar Firewall (Máxima Seguridad)

```bash
# Permitir SOLO desde IPs específicas autorizadas
sudo ufw allow from <IP_FRONTEND_PRO> to any port 6379 comment 'Redis from frontend-pro'
sudo ufw allow from <IP_BACKOFFICE_PRO> to any port 6379 comment 'Redis from backoffice-pro'

# Si hay múltiples frontends/backoffices (load balancer), permitir su IP

# Permitir desde servidor de monitoreo
sudo ufw allow from <IP_MONITORING_PRO> to any port 6379 comment 'Redis monitoring'

# BLOQUEAR todo lo demás
sudo ufw deny 6379 comment 'Redis block default'

# Habilitar firewall si no está activo
sudo ufw enable

# Verificar reglas (debe haber muy pocas)
sudo ufw status numbered

# Verificar que no hay reglas permisivas
sudo ufw status | grep 6379
```

### 6. Configurar SELinux/AppArmor (Si aplica)

```bash
# Para Ubuntu con AppArmor
sudo aa-status | grep redis

# Si hay perfil, asegurar que está enforced
sudo aa-enforce /etc/apparmor.d/redis-server
```

### 7. Iniciar Servicio

```bash
# Habilitar inicio automático
sudo systemctl enable redis-server

# Iniciar servicio
sudo systemctl start redis-server

# Verificar estado (NO debe haber errores)
sudo systemctl status redis-server

# Verificar logs intensivamente
sudo tail -f /var/log/redis/redis-server.log
# Dejar corriendo 5 minutos, verificar que no hay warnings

# Verificar proceso
ps aux | grep redis-server
```

### 8. Verificación Exhaustiva

```bash
# 1. Conexión básica
redis-cli -a <PASSWORD_PRO> ping
# Debe: PONG

# 2. Información del servidor
redis-cli -a <PASSWORD_PRO> INFO server | grep redis_version

# 3. Verificar comandos deshabilitados (CRÍTICO)
redis-cli -a <PASSWORD_PRO> FLUSHDB
# Debe: (error) ERR unknown command 'FLUSHDB'

redis-cli -a <PASSWORD_PRO> CONFIG GET *
# Debe: (error) ERR unknown command 'CONFIG'

redis-cli -a <PASSWORD_PRO> KEYS *
# Debe: (error) ERR unknown command 'KEYS'

# 4. Usar comandos renombrados (solo admin)
redis-cli -a <PASSWORD_PRO> CONFIG_PRO_XYZ_2025 GET maxmemory
# Debe: funcionar

# 5. Verificar persistencia
redis-cli -a <PASSWORD_PRO> SET test:prod "prod-value" EX 60
redis-cli -a <PASSWORD_PRO> GET test:prod
redis-cli -a <PASSWORD_PRO> DEL test:prod

# 6. Verificar AOF
ls -lah /var/lib/redis/appendonly.aof
# Debe: existir y tener contenido

# 7. Verificar memoria
redis-cli -a <PASSWORD_PRO> INFO memory | grep -E "used_memory_human|maxmemory_human"

# 8. Verificar desde aplicación (frontend/backoffice)
# Desde servidor frontend/backoffice:
redis-cli -h <IP_DEL_SERVIDOR_PRO> -a <PASSWORD_PRO> ping

# 9. Test de latencia
redis-cli -h <IP_DEL_SERVIDOR_PRO> -a <PASSWORD_PRO> --latency

# 10. Verificar clientes conectados
redis-cli -a <PASSWORD_PRO> CLIENT LIST
```

---

## 🔧 Configuración de Aplicaciones

### Variables en env.yaml (pro)

```yaml
redis_host: <IP_DEL_SERVIDOR_PRO>
redis_port: "6379"
redis_db: "0"
redis_token_expiration: "3600"
redis_lock_expiration: "10000"
redis_lock_warning_threshold: "1000"
```

### Password en protected_values.py (pro)

```python
# Redis (sesión compartida)
# CRÍTICO: Password de 32+ caracteres
redis_password = "<PASSWORD_PRO_FUERTE>"
```

⚠️ **Password debe ser único, no reutilizado de otros entornos**

---

## 💾 Backup y Recuperación (CRÍTICO)

### Estrategia de Backup

- **Frecuencia:** Diaria incremental + Semanal completo
- **Retención:** 30 días diarios + 12 semanas semanales + 12 meses mensuales
- **Almacenamiento:** Ubicación externa + Cloud (S3/GCS)
- **Cifrado:** Backups cifrados con GPG
- **Verificación:** Testing mensual de restauración

### Configurar Backup Automático

```bash
# Crear script de backup cifrado
sudo nano /usr/local/bin/redis-backup-pro.sh
```

```bash
#!/bin/bash
# Backup cifrado de Redis para PRODUCCIÓN

DATE=$(date +%Y%m%d_%H%M%S)
DAY=$(date +%A)
BACKUP_DIR="/backup/redis/pro"
BACKUP_REMOTE="s3://company-backups/redis/pro"
RETENTION_DAYS=30
ENCRYPTION_KEY="/etc/redis/.backup_key.gpg"
LOG_FILE="/var/log/redis/backup.log"

# Función de log
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a $LOG_FILE
}

# Crear directorio de backup
mkdir -p $BACKUP_DIR

log "Iniciando backup de Redis PRO"

# Pre-backup: Forzar guardado de RDB
redis-cli -a <PASSWORD_PRO> BGSAVE
sleep 5

# Backup de RDB
log "Backing up RDB..."
cp /var/lib/redis/dump.rdb $BACKUP_DIR/dump-pro-$DATE.rdb
if [ $? -eq 0 ]; then
    log "RDB backup OK"
else
    log "ERROR: RDB backup falló"
    exit 1
fi

# Backup de AOF
log "Backing up AOF..."
cp /var/lib/redis/appendonly.aof $BACKUP_DIR/appendonly-pro-$DATE.aof
if [ $? -eq 0 ]; then
    log "AOF backup OK"
else
    log "ERROR: AOF backup falló"
    exit 1
fi

# Comprimir
log "Comprimiendo backups..."
tar czf $BACKUP_DIR/redis-pro-$DATE.tar.gz \
    $BACKUP_DIR/dump-pro-$DATE.rdb \
    $BACKUP_DIR/appendonly-pro-$DATE.aof

# Cifrar backup
log "Cifrando backup..."
gpg --encrypt --recipient backup@company.com \
    --output $BACKUP_DIR/redis-pro-$DATE.tar.gz.gpg \
    $BACKUP_DIR/redis-pro-$DATE.tar.gz

# Eliminar archivos sin cifrar
rm $BACKUP_DIR/dump-pro-$DATE.rdb
rm $BACKUP_DIR/appendonly-pro-$DATE.aof
rm $BACKUP_DIR/redis-pro-$DATE.tar.gz

# Copiar a almacenamiento remoto
log "Copiando a almacenamiento remoto..."
aws s3 cp $BACKUP_DIR/redis-pro-$DATE.tar.gz.gpg $BACKUP_REMOTE/ || log "ERROR: Upload a S3 falló"

# Backup semanal completo (domingos)
if [ "$DAY" == "Sunday" ]; then
    cp $BACKUP_DIR/redis-pro-$DATE.tar.gz.gpg $BACKUP_DIR/weekly/redis-pro-weekly-$(date +%Y%W).tar.gz.gpg
    log "Backup semanal creado"
fi

# Limpiar backups antiguos locales
find $BACKUP_DIR -name "redis-pro-*.tar.gz.gpg" -mtime +$RETENTION_DAYS -delete
log "Backups antiguos limpiados"

# Verificar integridad del backup
log "Verificando integridad..."
if gpg --decrypt $BACKUP_DIR/redis-pro-$DATE.tar.gz.gpg > /dev/null 2>&1; then
    log "Integridad verificada OK"
else
    log "ERROR: Verificación de integridad falló"
    exit 1
fi

log "Backup completado exitosamente"

# Enviar notificación (opcional)
# curl -X POST "https://monitoring.company.com/webhook" -d "Backup Redis PRO completado: $DATE"
```

```bash
# Hacer ejecutable
sudo chmod +x /usr/local/bin/redis-backup-pro.sh

# Crear clave de cifrado
sudo gpg --gen-key
# Seguir instrucciones

# Test manual
sudo /usr/local/bin/redis-backup-pro.sh

# Añadir a crontab (backup diario a las 2 AM)
sudo crontab -e
```

```cron
# Backup de Redis PRO
0 2 * * * /usr/local/bin/redis-backup-pro.sh

# Monitoreo de espacio en disco
0 * * * * df -h /var/lib/redis | grep -v Filesystem | awk '{if($5+0 > 80) print "ALERTA: Disco Redis al "$5}' | mail -s "Redis Disk Alert" ops@company.com
```

### Procedimiento de Restauración (EMERGENCIA)

```bash
# 1. DETENER APLICACIONES
# Desde servidores frontend/backoffice:
sudo systemctl stop frontend
sudo systemctl stop backoffice

# 2. Detener Redis
sudo systemctl stop redis-server

# 3. Backup del estado actual (por si acaso)
sudo cp /var/lib/redis/dump.rdb /var/lib/redis/dump.rdb.before-restore
sudo cp /var/lib/redis/appendonly.aof /var/lib/redis/appendonly.aof.before-restore

# 4. Descargar backup del almacenamiento remoto
aws s3 cp s3://company-backups/redis/pro/redis-pro-YYYYMMDD_HHMMSS.tar.gz.gpg /tmp/

# 5. Descifrar backup
gpg --decrypt /tmp/redis-pro-YYYYMMDD_HHMMSS.tar.gz.gpg > /tmp/redis-pro-YYYYMMDD_HHMMSS.tar.gz

# 6. Extraer archivos
cd /tmp
tar xzf redis-pro-YYYYMMDD_HHMMSS.tar.gz

# 7. Restaurar archivos
sudo cp /tmp/backup/redis/pro/dump-pro-*.rdb /var/lib/redis/dump.rdb
sudo cp /tmp/backup/redis/pro/appendonly-pro-*.aof /var/lib/redis/appendonly.aof

# 8. Asegurar permisos
sudo chown redis:redis /var/lib/redis/dump.rdb
sudo chown redis:redis /var/lib/redis/appendonly.aof
sudo chmod 600 /var/lib/redis/dump.rdb
sudo chmod 600 /var/lib/redis/appendonly.aof

# 9. Iniciar Redis
sudo systemctl start redis-server

# 10. Verificar datos
redis-cli -a <PASSWORD_PRO> DBSIZE
redis-cli -a <PASSWORD_PRO> INFO keyspace

# 11. INICIAR APLICACIONES
# Desde servidores frontend/backoffice:
sudo systemctl start frontend
sudo systemctl start backoffice

# 12. Verificar funcionamiento
# Probar login de usuario

# 13. Documentar incidente
echo "$(date): Restauración completada desde backup YYYYMMDD_HHMMSS" | sudo tee -a /var/log/redis/incidents.log
```

---

## 📊 Monitoreo Avanzado

### 1. Instalar Redis Exporter

```bash
# Descargar
wget https://github.com/oliver006/redis_exporter/releases/download/v1.55.0/redis_exporter-v1.55.0.linux-amd64.tar.gz
tar xvf redis_exporter-v1.55.0.linux-amd64.tar.gz
sudo mv redis_exporter-v1.55.0.linux-amd64/redis_exporter /usr/local/bin/

# Crear usuario
sudo useradd --no-create-home --shell /bin/false redis_exporter

# Crear servicio
sudo nano /etc/systemd/system/redis_exporter.service
```

```ini
[Unit]
Description=Redis Exporter for Prometheus
After=network.target redis-server.service

[Service]
Type=simple
User=redis_exporter
ExecStart=/usr/local/bin/redis_exporter \
  --redis.addr=localhost:6379 \
  --redis.password=<PASSWORD_PRO> \
  --web.listen-address=:9121
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# Iniciar
sudo systemctl daemon-reload
sudo systemctl enable redis_exporter
sudo systemctl start redis_exporter

# Verificar
curl http://localhost:9121/metrics | grep redis_up
```

### 2. Configurar Alertas Críticas

**Prometheus rules** (`/etc/prometheus/rules/redis.yml`):

```yaml
groups:
  - name: redis_alerts
    interval: 30s
    rules:
      # Redis down
      - alert: RedisDown
        expr: redis_up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Redis is DOWN"
          description: "Redis PRO no responde"

      # Memoria casi llena
      - alert: RedisMemoryHigh
        expr: (redis_memory_used_bytes / redis_memory_max_bytes) > 0.90
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Redis memory usage > 90%"

      # Sin espacio en disco
      - alert: RedisDiskFull
        expr: node_filesystem_avail_bytes{mountpoint="/var/lib/redis"} / node_filesystem_size_bytes{mountpoint="/var/lib/redis"} < 0.10
        for: 5m
        labels:
          severity: critical

      # Muchos comandos lentos
      - alert: RedisSlowCommands
        expr: rate(redis_slowlog_length[5m]) > 10
        for: 5m
        labels:
          severity: warning

      # Replicación rota (si aplica)
      - alert: RedisReplicationDown
        expr: redis_connected_slaves < 1
        for: 5m
        labels:
          severity: critical

      # Muchas conexiones rechazadas
      - alert: RedisRejectedConnections
        expr: rate(redis_rejected_connections_total[5m]) > 0
        for: 5m
        labels:
          severity: warning
```

### 3. Dashboard Grafana

Importar dashboard:
- Redis Overview: Dashboard ID 11835
- Redis Cluster: Dashboard ID 11692

Métricas clave para monitorear:
- **Uptime**
- **Connected clients**
- **Used memory**
- **Commands per second**
- **Hit rate** (cache)
- **Evicted keys**
- **Last save time**
- **Network I/O**

---

## 🔒 Seguridad Avanzada

### Auditoría de Seguridad

```bash
# Script de auditoría semanal
sudo nano /usr/local/bin/redis-security-audit.sh
```

```bash
#!/bin/bash
# Auditoría de seguridad de Redis PRO

LOG="/var/log/redis/security-audit.log"

echo "==== Redis Security Audit $(date) ====" | tee -a $LOG

# 1. Verificar bind
echo "1. Bind configuration:" | tee -a $LOG
redis-cli -a <PASSWORD_PRO> CONFIG_PRO_XYZ_2025 GET bind | tee -a $LOG

# 2. Verificar protected-mode
echo "2. Protected mode:" | tee -a $LOG
redis-cli -a <PASSWORD_PRO> CONFIG_PRO_XYZ_2025 GET protected-mode | tee -a $LOG

# 3. Verificar comandos deshabilitados
echo "3. Dangerous commands (should fail):" | tee -a $LOG
redis-cli -a <PASSWORD_PRO> FLUSHDB 2>&1 | tee -a $LOG
redis-cli -a <PASSWORD_PRO> CONFIG GET * 2>&1 | tee -a $LOG
redis-cli -a <PASSWORD_PRO> KEYS * 2>&1 | tee -a $LOG

# 4. Verificar firewall
echo "4. Firewall rules:" | tee -a $LOG
sudo ufw status numbered | grep 6379 | tee -a $LOG

# 5. Verificar permisos de archivos
echo "5. File permissions:" | tee -a $LOG
ls -l /etc/redis/redis.conf | tee -a $LOG
ls -l /var/lib/redis/ | tee -a $LOG

# 6. Verificar clientes conectados
echo "6. Connected clients:" | tee -a $LOG
redis-cli -a <PASSWORD_PRO> CLIENT LIST | wc -l | tee -a $LOG

# 7. Verificar comandos recientes (slowlog)
echo "7. Recent slow commands:" | tee -a $LOG
redis-cli -a <PASSWORD_PRO> SLOWLOG GET 5 | tee -a $LOG

echo "==== Audit Complete ====" | tee -a $LOG
```

```bash
# Ejecutar manualmente
sudo /usr/local/bin/redis-security-audit.sh

# Programar ejecución semanal
sudo crontab -e
# 0 9 * * MON /usr/local/bin/redis-security-audit.sh
```

### Procedimiento de Rotación de Password

**Frecuencia:** Cada 90 días  
**Window:** Fuera de horario de oficina

```bash
# DÍA DEL CAMBIO (ventana de mantenimiento)

# 1. Generar nuevo password fuerte
NEW_PASSWORD=$(openssl rand -base64 32)
echo "Nuevo password: $NEW_PASSWORD" | sudo tee /root/.redis_new_pass
sudo chmod 600 /root/.redis_new_pass

# 2. Actualizar configuración en Redis (sin reinicio)
redis-cli -a <PASSWORD_ANTIGUO> CONFIG_PRO_XYZ_2025 SET requirepass $NEW_PASSWORD

# 3. Verificar inmediatamente
redis-cli -a $NEW_PASSWORD ping
# Debe: PONG

# 4. Actualizar redis.conf
sudo sed -i "s/requirepass <PASSWORD_ANTIGUO>/requirepass $NEW_PASSWORD/" /etc/redis/redis.conf

# 5. Actualizar protected_values.py en repositorio
# vim infrastructure/environments/pro/protected_values.py
# redis_password = "$NEW_PASSWORD"

# 6. Commit y push cambios
git add infrastructure/environments/pro/protected_values.py
git commit -m "rotate: Update Redis PRO password"
git push

# 7. Desplegar nuevas variables en aplicaciones
# Desde servidores frontend/backoffice:
cd /path/to/app
git pull
sudo systemctl restart frontend
sudo systemctl restart backoffice

# 8. Verificar funcionamiento
# Probar login de usuarios

# 9. Documentar cambio
echo "$(date): Password rotado exitosamente" | sudo tee -a /var/log/redis/password-rotation.log

# 10. Eliminar archivo temporal
sudo rm /root/.redis_new_pass
```

---

## 🚨 Runbook de Incidentes

### Redis DOWN

**Síntoma:** Aplicaciones no pueden conectar a Redis

**Acciones:**
1. Verificar proceso: `ps aux | grep redis-server`
2. Verificar logs: `sudo tail -100 /var/log/redis/redis-server.log`
3. Verificar disco: `df -h /var/lib/redis`
4. Verificar memoria: `free -h`
5. Si proceso no existe: `sudo systemctl start redis-server`
6. Si no inicia: revisar logs, verificar configuración
7. Como último recurso: restaurar desde backup
8. Notificar al equipo inmediatamente

### Memoria Llena

**Síntoma:** Redis rechaza escrituras

**Acciones:**
1. Verificar uso: `redis-cli -a <PASSWORD_PRO> INFO memory`
2. Ver keys más grandes: `redis-cli -a <PASSWORD_PRO> --bigkeys`
3. Aumentar límite temporalmente (si hay RAM disponible):
   ```bash
   redis-cli -a <PASSWORD_PRO> CONFIG_PRO_XYZ_2025 SET maxmemory 12gb
   ```
4. Planificar upgrade de servidor o limpieza de datos
5. Documentar incidente

### Disco Lleno

**Síntoma:** Redis no puede guardar RDB/AOF

**Acciones:**
1. Verificar espacio: `df -h /var/lib/redis`
2. Limpiar logs antiguos:
   ```bash
   sudo find /var/log/redis -name "*.log.*" -mtime +30 -delete
   ```
3. Limpiar backups antiguos si están en mismo disco
4. Si es urgente, aumentar espacio en disco (EBS resize en AWS)
5. Planificar aumento permanente de capacidad

### Replicación Rota (Si aplica)

**Síntoma:** Replica no sincroniza con maestro

**Acciones:**
1. Verificar conectividad de red entre maestro y replica
2. Verificar logs en ambos servidores
3. Verificar que passwords coinciden
4. Resincronizar manualmente:
   ```bash
   # En replica:
   redis-cli -a <PASSWORD_PRO> REPLICAOF <MASTER_IP> 6379
   ```
5. Si falla, reconstruir replica desde backup

---

## 📚 Documentación de Referencia

- **Configuración:** `infrastructure/redis/pro/redis.conf`
- **Variables:** `infrastructure/environments/pro/env.yaml`
- **Passwords:** `infrastructure/environments/pro/protected_values.py` (VAULT)
- **Documentación principal:** `README.md`
- **Runbook completo:** `docs/REDIS_RUNBOOK_PRO.md` (crear)
- **Contactos de guardia:** `docs/ON_CALL.md` (crear)

---

## 📞 Escalación

**Nivel 1:** DevOps en guardia  
**Nivel 2:** Lead DevOps  
**Nivel 3:** CTO  

**Canales:**
- Slack: #incidents-pro
- PagerDuty: Redis PRO  
- Email: ops@company.com

---

**Última actualización:** 2026-01-26  
**Responsable:** Equipo DevOps  
**Revisión:** Mensual  
**Próxima auditoría:** Programar
