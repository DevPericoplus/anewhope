# Sincronización de Configuración fmanagement

Este documento describe el sistema de sincronización de archivos de configuración entre los proyectos `anewhope` y `fmanagement`.

## 📋 Archivos sincronizados

Para cada entorno (`macbook`, `dev`, `pre`, `pro`) existe un archivo `fmanagement_paths.yml` que debe mantenerse **idéntico** entre:

- **anewhope**: `infrastructure/environments/{entorno}/fmanagement_paths.yml`
- **fmanagement**: `/Users/administrator/develop/fmanagement/env/{entorno}/fmanagement_paths.yml`

## 🔧 Contenido de fmanagement_paths.yml

```yaml
# Configuración de permisos
permissions_source: mock | db_only
middleware_base_url: http://...
core_backend_base_url: http://...

# Rutas de almacenamiento
backend_core_base_storage: ~/data/files/external | /data/files/external
backend_ia_base_storage: ~/data/files/trainer | /data/files/trainer

# Configuración de transferencia
transfer_mode: local | remote

# SSH (solo si transfer_mode=remote)
trainer_ssh_host: trainer.example.com
trainer_ssh_user: rsync_user
trainer_ssh_key_path: /opt/anewhope/keys/rsync_key
trainer_ssh_port: 22
core_ssh_host: backend.example.com
core_ssh_user: rsync_user
core_ssh_key_path: /opt/anewhope/keys/rsync_key
core_ssh_port: 22
```

## ⚙️ Configuración por entorno

| Entorno | Permisos | Transferencia | Rutas | SSH |
|---------|----------|---------------|-------|-----|
| **macbook** | `mock` | `local` | `~/data/files/*` | No usado |
| **dev** | `db_only` | `remote` | `/data/files/*` | `*.house.loc` |
| **pre** | `db_only` | `remote` | `/data/files/*` | `*.anewhope.aws` |
| **pro** | `db_only` | `remote` | `/data/files/*` | `*.anewhope.aws` |

## 🔄 Flujo de trabajo

### 1. Modificar configuración

```bash
# Editar archivo en anewhope
vim infrastructure/environments/dev/fmanagement_paths.yml
```

### 2. Copiar a fmanagement

```bash
# Copiar inmediatamente
cp infrastructure/environments/dev/fmanagement_paths.yml \
   /Users/administrator/develop/fmanagement/env/dev/fmanagement_paths.yml
```

### 3. Verificar sincronización

```bash
# Verificar todos los entornos
./scripts/verify_fmanagement_sync.sh

# Verificar un entorno específico
./scripts/verify_fmanagement_sync.sh dev
```

### 4. Commit en ambos proyectos

```bash
# En anewhope
cd /Users/administrator/develop/anewhope
git add infrastructure/environments/dev/fmanagement_paths.yml
git commit -m "config: actualizar rutas de almacenamiento para dev"

# En fmanagement
cd /Users/administrator/develop/fmanagement
git add env/dev/fmanagement_paths.yml
git commit -m "config: actualizar rutas de almacenamiento para dev"
```

## ✅ Script de verificación

El script `scripts/verify_fmanagement_sync.sh` automatiza la verificación:

```bash
./scripts/verify_fmanagement_sync.sh
```

**Salida esperada:**

```
✅ SINCRONIZADO   - Archivos idénticos (correcto)
❌ DESINCRONIZADO - Archivos diferentes (corregir inmediatamente)
```

El script:
- ✅ Verifica que ambos archivos existen
- ✅ Compara contenido (ignorando comentarios de sincronización)
- ✅ Muestra diferencias si las hay
- ✅ Proporciona comando para sincronizar
- ✅ Retorna exit code 0 (sincronizado) o 1 (desincronizado)

## 🚨 Reglas críticas

1. **Sincronización bidireccional obligatoria**: Cualquier cambio debe replicarse inmediatamente
2. **Verificar antes de commit**: Siempre ejecutar `verify_fmanagement_sync.sh`
3. **Deploy en producción**: Verificar sincronización antes de deploy en `pre` o `pro`
4. **Comentarios de sincronización**: Cada archivo incluye un comentario indicando su gemelo

## 🎯 Motivo de sincronización

fmanagement se ejecuta **dockerizado** y necesita leer la configuración desde su propio entorno, pero los valores deben coincidir exactamente con anewhope para garantizar coherencia en:

- ✅ Rutas de almacenamiento
- ✅ URLs de servicios
- ✅ Configuración SSH para transferencias
- ✅ Modo de transferencia de versiones

## 📝 Ejemplos de cambios comunes

### Cambiar ruta de almacenamiento

```yaml
# Antes
backend_core_base_storage: /data/files/external

# Después
backend_core_base_storage: /mnt/storage/external
```

**Recordar**: Copiar a fmanagement y verificar.

### Cambiar modo de transferencia

```yaml
# Antes
transfer_mode: local

# Después
transfer_mode: remote
trainer_ssh_host: trainer.anewhope.aws
trainer_ssh_user: rsync_user
trainer_ssh_key_path: /opt/anewhope/keys/rsync_key
```

**Recordar**: Configurar también los valores SSH.

### Cambiar fuente de permisos

```yaml
# Antes (desarrollo con mocks)
permissions_source: mock
middleware_base_url: http://localhost:8007

# Después (producción con DB)
permissions_source: db_only
core_backend_base_url: http://backend.anewhope.aws:8003
```

## 🔗 Referencias

- **Regla en AGENTS.md**: Sección 5.2.1 "Sincronización de configuración fmanagement"
- **Script de verificación**: `scripts/verify_fmanagement_sync.sh`
- **Archivos de configuración**: `infrastructure/environments/{entorno}/fmanagement_paths.yml`
- **Proyecto fmanagement**: `/Users/administrator/develop/fmanagement/`

---

**IMPORTANTE**: Este sistema de sincronización es **crítico** para el correcto funcionamiento de fmanagement en todos los entornos. No omitir la verificación antes de commits o deploys.
