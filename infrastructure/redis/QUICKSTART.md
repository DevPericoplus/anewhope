# 🚀 Guía Rápida - Despliegue de Redis por Entorno

## 📋 Resumen

Esta guía proporciona los pasos mínimos para desplegar Redis en cada entorno usando las configuraciones preparadas.

---

## 🖥️ macbook (Local) - YA CONFIGURADO

```bash
# Usando Homebrew
brew services start redis

# O con configuración específica
redis-server infrastructure/redis/macbook/redis.conf

# Verificar
redis-cli ping
```

**Documentación:** Ya funciona según `README.md` principal

---

## 🌐 dev (Desarrollo)

### Pasos Rápidos

```bash
# 1. En servidor dev
ssh admin@<IP_DEV>

# 2. Instalar Redis
sudo apt update && sudo apt install redis-server -y

# 3. Copiar configuración
sudo cp infrastructure/redis/dev/redis.conf /etc/redis/redis.conf

# 4. EDITAR: Reemplazar placeholders
sudo nano /etc/redis/redis.conf
# - Buscar: <IP_DEL_SERVIDOR_DEV>
# - Buscar: <PASSWORD_DEV>

# 5. Crear directorios
sudo mkdir -p /var/lib/redis /var/log/redis
sudo chown redis:redis /var/lib/redis /var/log/redis

# 6. Configurar firewall
sudo ufw allow from <IP_FRONTEND_DEV> to any port 6379
sudo ufw allow from <IP_BACKOFFICE_DEV> to any port 6379

# 7. Iniciar
sudo systemctl enable redis-server
sudo systemctl start redis-server

# 8. Verificar
redis-cli -a <PASSWORD_DEV> ping
```

**Tiempo estimado:** 15 minutos  
**Documentación completa:** `infrastructure/redis/dev/README.md`

---

## 🧪 pre (Pre-producción)

### Pasos Rápidos

```bash
# 1. En servidor pre
ssh admin@<IP_PRE>

# 2. Optimizar sistema
sudo nano /etc/sysctl.conf
# Añadir:
# net.core.somaxconn = 65535
# vm.overcommit_memory = 1
sudo sysctl -p

# 3. Instalar Redis
sudo apt update && sudo apt install redis-server -y

# 4. Copiar configuración
sudo cp infrastructure/redis/pre/redis.conf /etc/redis/redis.conf

# 5. EDITAR: Reemplazar placeholders
sudo nano /etc/redis/redis.conf
# - Buscar: <IP_DEL_SERVIDOR_PRE>
# - Buscar: <PASSWORD_PRE> (generar: openssl rand -base64 24)

# 6. Permisos estrictos
sudo chmod 640 /etc/redis/redis.conf
sudo chown redis:redis /etc/redis/redis.conf

# 7. Crear directorios
sudo mkdir -p /var/lib/redis /var/log/redis
sudo chown redis:redis /var/lib/redis /var/log/redis
sudo chmod 750 /var/lib/redis

# 8. Firewall estricto
sudo ufw allow from <IP_FRONTEND_PRE> to any port 6379
sudo ufw allow from <IP_BACKOFFICE_PRE> to any port 6379
sudo ufw deny 6379

# 9. Iniciar
sudo systemctl enable redis-server
sudo systemctl start redis-server

# 10. Verificar seguridad
redis-cli -a <PASSWORD_PRE> FLUSHDB  # Debe fallar
redis-cli -a <PASSWORD_PRE> ping     # Debe funcionar
```

**Tiempo estimado:** 30 minutos  
**Documentación completa:** `infrastructure/redis/pre/README.md`

---

## 🚀 pro (Producción)

### ⚠️ IMPORTANTE: Requiere Aprobación

**Pre-requisitos:**
- [ ] Configuración probada en PRE por 1+ semana
- [ ] Aprobación de operaciones
- [ ] Window de mantenimiento planificado
- [ ] Plan de rollback documentado
- [ ] Equipo de guardia disponible

### Pasos Críticos

```bash
# 1. En servidor pro (CON APROBACIÓN)
ssh admin@<IP_PRO>

# 2. Optimizar sistema COMPLETO
sudo nano /etc/sysctl.conf
# Añadir:
# net.core.somaxconn = 65535
# vm.overcommit_memory = 1
# vm.swappiness = 1
sudo sysctl -p

# Deshabilitar THP
cat <<EOF | sudo tee /etc/systemd/system/disable-thp.service
[Unit]
Description=Disable Transparent Huge Pages
After=sysinit.target

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'echo never > /sys/kernel/mm/transparent_hugepage/enabled'

[Install]
WantedBy=basic.target
EOF
sudo systemctl enable disable-thp && sudo systemctl start disable-thp

# 3. Instalar Redis (versión específica, misma que pre)
sudo apt install redis-server=6:7.0.* -y

# 4. Copiar configuración
sudo cp infrastructure/redis/pro/redis.conf /etc/redis/redis.conf

# 5. EDITAR CON EXTREMO CUIDADO
sudo nano /etc/redis/redis.conf
# - <IP_DEL_SERVIDOR_PRO> → IP real
# - <PASSWORD_PRO> → Password fuerte (openssl rand -base64 32)
# - Revisar TODOS los parámetros
# - Personalizar comandos renombrados

# 6. Permisos MÁXIMOS
sudo chmod 600 /etc/redis/redis.conf
sudo chown redis:redis /etc/redis/redis.conf

# 7. Crear estructura
sudo mkdir -p /var/lib/redis /var/log/redis /backup/redis
sudo chown redis:redis /var/lib/redis /var/log/redis
sudo chmod 700 /var/lib/redis

# 8. Firewall ESTRICTO
sudo ufw allow from <IP_FRONTEND_PRO> to any port 6379
sudo ufw allow from <IP_BACKOFFICE_PRO> to any port 6379
sudo ufw deny 6379
sudo ufw enable

# 9. Validar configuración
sudo redis-server /etc/redis/redis.conf --test-memory 1

# 10. Iniciar con monitoreo
sudo systemctl enable redis-server
sudo systemctl start redis-server
sudo tail -f /var/log/redis/redis-server.log

# 11. Verificación EXHAUSTIVA
redis-cli -a <PASSWORD_PRO> ping
redis-cli -a <PASSWORD_PRO> INFO server
redis-cli -a <PASSWORD_PRO> FLUSHDB  # Debe fallar
redis-cli -a <PASSWORD_PRO> CONFIG GET *  # Debe fallar

# 12. Configurar backup cifrado (ver pro/README.md)
sudo cp infrastructure/redis/pro/backup-script.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/redis-backup-pro.sh

# 13. Configurar monitoreo (ver pro/README.md)
# - Redis Exporter
# - Prometheus
# - Alertas

# 14. Documentar deployment
echo "$(date): Redis PRO deployed" | sudo tee -a /var/log/redis/deployments.log
```

**Tiempo estimado:** 2-3 horas (incluyendo validaciones)  
**Documentación completa:** `infrastructure/redis/pro/README.md`

---

## 🔄 Actualizar Aplicaciones

### Después de desplegar Redis en cualquier entorno:

**1. Actualizar variables en env.yaml:**

```yaml
redis_host: <IP_DEL_SERVIDOR>  # Cambiar según entorno
redis_port: "6379"
redis_db: "0"
redis_token_expiration: "3600"
redis_lock_expiration: "10000"
redis_lock_warning_threshold: "1000"
```

**2. Actualizar password en protected_values.py:**

```python
# En infrastructure/environments/<entorno>/protected_values.py
redis_password = "<PASSWORD_ENTORNO>"
```

**3. Desplegar aplicaciones:**

```bash
# Frontend
cd /path/to/frontend
git pull
source .venv_frontend313/bin/activate
pip install -r requirements.txt  # Si redis no estaba instalado
sudo systemctl restart frontend

# Backoffice
cd /path/to/backoffice
git pull
source .venv_backoffice313/bin/activate
pip install -r requirements.txt
sudo systemctl restart backoffice
```

**4. Verificar conectividad:**

```bash
# Desde servidor de aplicación
redis-cli -h <IP_REDIS> -a <PASSWORD> ping

# Verificar en logs de aplicación
sudo journalctl -u frontend -f
sudo journalctl -u backoffice -f
```

---

## ✅ Checklist de Verificación

### Para cualquier entorno:

- [ ] Redis responde a ping
- [ ] Logs no muestran errores
- [ ] Comandos peligrosos deshabilitados (pre/pro)
- [ ] Firewall configurado correctamente
- [ ] Aplicaciones pueden conectar
- [ ] Login de usuarios funciona
- [ ] Sesiones se crean en Redis
- [ ] Navegación frontend ↔ backoffice funciona
- [ ] Logout limpia sesiones

### Adicional para PRE/PRO:

- [ ] Backup automático configurado
- [ ] Monitoreo funcionando
- [ ] Alertas configuradas
- [ ] Procedimientos documentados
- [ ] Equipo entrenado

---

## 📞 Soporte

**Problemas comunes:**
- Redis no inicia → Ver logs: `sudo tail -f /var/log/redis/redis-server.log`
- No puede conectar → Verificar firewall: `sudo ufw status`
- Password incorrecto → Verificar env.yaml y protected_values.py coinciden

**Documentación completa:**
- `infrastructure/redis/<entorno>/README.md`
- `docs/REDIS_TEMPLATES_SUMMARY.md`
- `README.md` (sección Redis)

---

**Última actualización:** 2026-01-26  
**Mantenido por:** Equipo DevOps
