# Sistema de Sincronización de Almacenamiento

## Descripción General

El sistema de sincronización mantiene sincronizadas las carpetas `external` e `internal` entre los servidores **Backend** y **Trainer** mediante rsync.

## Arquitectura del Flujo de Datos

```
┌─────────────────────────────────────────────────────────────┐
│                    SINCRONIZACIÓN 1                          │
│  Backend External → Trainer External (unidireccional)        │
│                                                              │
│  Usuarios suben archivos → Backend (fmanagement)            │
│                           ↓                                  │
│                    Backend External/                         │
│                           ↓ (rsync cada 5 min)              │
│                    Trainer External/                         │
│                           ↓                                  │
│              Trainer procesa para entrenamientos             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    SINCRONIZACIÓN 2                          │
│  Trainer Internal → Backend Internal (unidireccional)        │
│                                                              │
│  Trainer genera: modelos, informes, GGUF, etc.              │
│                           ↓                                  │
│                    Trainer Internal/                         │
│                           ↓ (rsync cada 5 min)              │
│                    Backend Internal/                         │
│                           ↓                                  │
│     Disponible vía fmanagement para descargar               │
└─────────────────────────────────────────────────────────────┘
```

## Configuración por Entorno

### Macbook (Desarrollo Local)

**Modo**: Sincronización local (sin SSH)

**Rutas**:
- Backend External: `~/data/anewhope/files/backend_server/external/`
- Backend Internal: `~/data/anewhope/files/backend_server/internal/`
- Trainer External: `~/data/anewhope/files/trainer_server/external/`
- Trainer Internal: `~/data/anewhope/files/trainer_server/internal/`

**Comando**:
```bash
cd /Users/administrator/develop/anewhope
./infrastructure/scripts/sync_storage.sh macbook
```

**Automatización**:
```cron
*/5 * * * * cd /Users/administrator/develop/anewhope && ./infrastructure/scripts/sync_storage.sh macbook >> /Users/administrator/data/anewhope/logs/sync_storage.log 2>&1
```

**Logs**:
```bash
tail -f ~/data/anewhope/logs/sync_storage.log
```

---

### Dev/Pre/Pro (Servidores Remotos)

**Modo**: Sincronización remota via rsync over SSH

**Arquitectura de Servidores**:
- **Backend Server**: `backend.{domain}`
- **Trainer Server**: `trainer.{domain}`

**Rutas en Servidores**:
- Backend External: `/data/files/external/`
- Backend Internal: `/data/files/internal/`
- Trainer External: `/data/files/external/`
- Trainer Internal: `/data/files/internal/`

#### Configuración SSH (Autenticación por Clave Pública)

**1. Generar par de claves SSH en el servidor Backend**:
```bash
# En servidor Backend
ssh-keygen -t rsa -b 4096 -f ~/.ssh/rsync_key -C "rsync@backend"
chmod 600 ~/.ssh/rsync_key
chmod 644 ~/.ssh/rsync_key.pub
```

**2. Copiar clave pública al servidor Trainer**:
```bash
# Método 1: ssh-copy-id (recomendado)
ssh-copy-id -i ~/.ssh/rsync_key.pub rsync_user@trainer.{domain}

# Método 2: Manual
cat ~/.ssh/rsync_key.pub | ssh rsync_user@trainer.{domain} \
  'mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'
```

**3. Probar conexión SSH**:
```bash
ssh -i ~/.ssh/rsync_key rsync_user@trainer.{domain}
```

**4. Actualizar configuración en `infrastructure/environments/{entorno}/env.yaml`**:
```yaml
# Configuración de transferencia de versiones
transfer_mode: ssh
trainer_ssh_host: trainer.{domain}
trainer_ssh_user: rsync_user
trainer_ssh_key_path: ~/.ssh/rsync_key
trainer_ssh_port: "22"
```

#### Ejecución en Entornos Remotos

**En servidor Backend (dev)**:
```bash
cd /opt/anewhope
./infrastructure/scripts/sync_storage.sh dev
```

**En servidor Backend (pre)**:
```bash
cd /opt/anewhope
./infrastructure/scripts/sync_storage.sh pre
```

**En servidor Backend (pro)**:
```bash
cd /opt/anewhope
./infrastructure/scripts/sync_storage.sh pro
```

#### Automatización con Cron (Servidores Remotos)

**En servidor Backend, agregar a crontab**:
```cron
# Dev
*/5 * * * * cd /opt/anewhope && ./infrastructure/scripts/sync_storage.sh dev >> /var/log/anewhope/sync_storage.log 2>&1

# Pre
*/5 * * * * cd /opt/anewhope && ./infrastructure/scripts/sync_storage.sh pre >> /var/log/anewhope/sync_storage.log 2>&1

# Pro
*/5 * * * * cd /opt/anewhope && ./infrastructure/scripts/sync_storage.sh pro >> /var/log/anewhope/sync_storage.log 2>&1
```

#### Permisos en Servidores

**En servidor Trainer**, el usuario `rsync_user` debe tener permisos de lectura/escritura en:
```bash
/data/files/external/
/data/files/internal/
```

**Configurar permisos**:
```bash
# En servidor Trainer
sudo mkdir -p /data/files/external /data/files/internal
sudo chown -R rsync_user:rsync_group /data/files/
sudo chmod -R 755 /data/files/
```

---

## Opciones de rsync Utilizadas

| Opción | Significado | Propósito |
|--------|-------------|-----------|
| `-r` | `--recursive` | Copiar directorios recursivamente |
| `-t` | `--times` | Preservar timestamps de modificación |
| `-z` | `--compress` | Comprimir durante transferencia (útil para SSH) |
| `--update` | Solo actualizar | No sobrescribir archivos más recientes en destino |
| `--stats` | Estadísticas | Mostrar resumen de transferencia |
| `--human-readable` | Tamaños legibles | KB, MB, GB en lugar de bytes |

**Nota**: La opción `--update` asegura que solo se copien archivos:
- Que no existen en el destino
- Que son más nuevos (timestamp más reciente) que en el destino

Esto hace que rsync sea **incremental** y **eficiente**.

---

## Monitoreo y Troubleshooting

### Ver logs en tiempo real

**Macbook**:
```bash
tail -f ~/data/anewhope/logs/sync_storage.log
```

**Servidores remotos**:
```bash
tail -f /var/log/anewhope/sync_storage.log
```

### Verificar última sincronización

```bash
# Ver últimas 50 líneas del log
tail -50 ~/data/anewhope/logs/sync_storage.log

# Buscar errores
grep ERROR ~/data/anewhope/logs/sync_storage.log

# Buscar sincronizaciones exitosas hoy
grep "$(date +%Y-%m-%d)" ~/data/anewhope/logs/sync_storage.log | grep SUCCESS
```

### Ejecución manual (sin cron)

```bash
# Modo verbose para debugging
VERBOSE=1 ./infrastructure/scripts/sync_storage.sh macbook

# Sin verbose
./infrastructure/scripts/sync_storage.sh macbook
```

### Verificar cron activo

```bash
# Ver crontab del usuario actual
crontab -l

# Ver logs del cron system (macOS)
log show --predicate 'process == "cron"' --last 1h

# Ver logs del cron system (Linux)
grep CRON /var/log/syslog | tail -20
```

### Problemas comunes

#### 1. "Permission denied" en SSH

**Solución**:
- Verificar que la clave SSH tiene permisos correctos (600)
- Verificar que la clave pública está en `~/.ssh/authorized_keys` del servidor Trainer
- Verificar que el usuario `rsync_user` tiene permisos en `/data/files/`

```bash
# En Backend
chmod 600 ~/.ssh/rsync_key

# En Trainer
chmod 600 ~/.ssh/authorized_keys
chmod 755 /data/files/
```

#### 2. "Host key verification failed"

**Solución temporal** (desarrollo):
```bash
# Agregar host a known_hosts
ssh-keyscan -H trainer.{domain} >> ~/.ssh/known_hosts
```

**Nota**: El script ya incluye `-o StrictHostKeyChecking=no` para entornos de desarrollo.

#### 3. Cron no ejecuta el script

**Soluciones**:
1. Verificar que el cron está usando rutas absolutas
2. Verificar permisos de ejecución del script: `chmod +x sync_storage.sh`
3. Revisar logs del cron system

#### 4. Rsync muy lento

**Optimizaciones**:
1. Verificar ancho de banda de red
2. Agregar opciones de compresión: `-z` o `--compress-level=9`
3. Excluir archivos innecesarios: `--exclude="*.tmp"`

---

## Seguridad

### Recomendaciones

1. **Usar usuario dedicado para rsync** (`rsync_user`), no root
2. **Restringir permisos SSH** del usuario rsync:
   ```bash
   # En ~/.ssh/authorized_keys del Trainer, agregar restricciones:
   command="/usr/bin/rsync --server ...",no-port-forwarding,no-X11-forwarding,no-agent-forwarding ssh-rsa AAAA...
   ```
3. **Usar firewall** para limitar acceso SSH solo entre Backend y Trainer
4. **Monitorear logs** regularmente para detectar accesos no autorizados
5. **Rotar claves SSH** periódicamente (cada 6-12 meses)

---

## Testing

### Verificar sincronización funciona

```bash
# 1. Crear archivo de prueba en Backend External
echo "test $(date)" > ~/data/anewhope/files/backend_server/external/test_sync.txt

# 2. Ejecutar sincronización
./infrastructure/scripts/sync_storage.sh macbook

# 3. Verificar que llegó a Trainer External
cat ~/data/anewhope/files/trainer_server/external/test_sync.txt

# 4. Crear archivo de prueba en Trainer Internal
echo "test $(date)" > ~/data/anewhope/files/trainer_server/internal/test_sync_internal.txt

# 5. Ejecutar sincronización
./infrastructure/scripts/sync_storage.sh macbook

# 6. Verificar que llegó a Backend Internal
cat ~/data/anewhope/files/backend_server/internal/test_sync_internal.txt
```

---

## Referencias

- [rsync Manual](https://download.samba.org/pub/rsync/rsync.1)
- [SSH Key-based Authentication](https://www.ssh.com/academy/ssh/public-key-authentication)
- [Cron Scheduling](https://crontab.guru/)

---

**Última actualización**: 2026-02-14
**Versión**: 1.0
