#!/bin/bash
################################################################################
# Script de Sincronización de Almacenamiento
# ============================================================================
# Propósito: Sincronizar bidireccionalente las carpetas external e internal
#            entre los servidores Backend y Trainer usando rsync.
#
# Modo de operación:
#   - Sincronización 1: backend external → trainer external (unidireccional)
#   - Sincronización 2: trainer internal → backend internal (unidireccional)
#
# Características:
#   - Recursivo (-r)
#   - Incremental (solo copia archivos nuevos o modificados)
#   - Preserva timestamps (-t)
#   - Compresión durante transferencia (-z)
#   - Verbose para logs (-v)
#   - No elimina archivos del destino
#
# Uso:
#   ./sync_storage.sh [entorno]
#
# Ejemplos:
#   ./sync_storage.sh macbook    # Sincronización local en desarrollo
#   ./sync_storage.sh dev        # Sincronización remota via SSH en dev
#   ./sync_storage.sh pre        # Sincronización remota via SSH en pre
#   ./sync_storage.sh pro        # Sincronización remota via SSH en pro
#
# Configuración:
#   Las rutas y configuración SSH se leen de los archivos YAML en:
#   infrastructure/environments/{entorno}/env.yaml
#
# Automatización:
#   Este script puede ser ejecutado por cron cada 5 minutos:
#   */5 * * * * /path/to/sync_storage.sh macbook >> /var/log/sync_storage.log 2>&1
#
# Adaptación para entornos remotos (dev/pre/pro):
#   En servidores separados, este script se ejecutará:
#   - En servidor Backend: sincroniza external hacia Trainer
#   - En servidor Trainer: sincroniza internal hacia Backend
#   Ambos usando rsync over SSH con autenticación por clave pública.
################################################################################

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_PREFIX="[SYNC-STORAGE]"

# Parámetro de entorno (default: macbook)
ENVIRONMENT="${1:-macbook}"

# Timestamp para logs
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# ============================================================================
# FUNCIONES DE UTILIDAD
# ============================================================================

log_info() {
    echo "$TIMESTAMP $LOG_PREFIX [INFO] $*"
}

log_error() {
    echo "$TIMESTAMP $LOG_PREFIX [ERROR] $*" >&2
}

log_success() {
    echo "$TIMESTAMP $LOG_PREFIX [SUCCESS] $*"
}

# Función para leer configuración del archivo YAML
# Nota: Esta es una implementación simplificada que funciona para la estructura actual
read_yaml_value() {
    local yaml_file="$1"
    local key="$2"

    if [[ ! -f "$yaml_file" ]]; then
        log_error "Archivo de configuración no encontrado: $yaml_file"
        return 1
    fi

    # Leer valor eliminando comentarios y espacios
    grep "^${key}:" "$yaml_file" | sed "s/^${key}:[[:space:]]*//" | sed 's/#.*//' | tr -d '"' | tr -d "'"
}

# ============================================================================
# CARGA DE CONFIGURACIÓN POR ENTORNO
# ============================================================================

ENV_FILE="$PROJECT_ROOT/infrastructure/environments/$ENVIRONMENT/env.yaml"

if [[ ! -f "$ENV_FILE" ]]; then
    log_error "Archivo de configuración no encontrado para entorno: $ENVIRONMENT"
    log_error "Ruta esperada: $ENV_FILE"
    exit 1
fi

log_info "Cargando configuración del entorno: $ENVIRONMENT"

# ============================================================================
# CONFIGURACIÓN ESPECÍFICA POR ENTORNO
# ============================================================================

case "$ENVIRONMENT" in
    macbook)
        # En macbook, sincronización local sin SSH
        TRANSFER_MODE="local"

        # Rutas locales expandiendo ~
        BACKEND_EXTERNAL="$HOME/data/anewhope/files/backend_server/external"
        BACKEND_INTERNAL="$HOME/data/anewhope/files/backend_server/internal"
        TRAINER_EXTERNAL="$HOME/data/anewhope/files/trainer_server/external"
        TRAINER_INTERNAL="$HOME/data/anewhope/files/trainer_server/internal"

        # Crear directorios si no existen
        mkdir -p "$BACKEND_EXTERNAL" "$BACKEND_INTERNAL" "$TRAINER_EXTERNAL" "$TRAINER_INTERNAL"

        log_info "Modo: Sincronización local (macbook)"
        ;;

    dev|pre|pro)
        # En entornos remotos, sincronización via SSH
        TRANSFER_MODE="ssh"

        # Leer configuración SSH del YAML
        TRAINER_SSH_HOST=$(read_yaml_value "$ENV_FILE" "trainer_ssh_host")
        TRAINER_SSH_USER=$(read_yaml_value "$ENV_FILE" "trainer_ssh_user")
        TRAINER_SSH_KEY=$(read_yaml_value "$ENV_FILE" "trainer_ssh_key_path")
        TRAINER_SSH_PORT=$(read_yaml_value "$ENV_FILE" "trainer_ssh_port")

        # Expandir ~ en la ruta de la clave SSH
        TRAINER_SSH_KEY="${TRAINER_SSH_KEY/#\~/$HOME}"

        # Rutas en servidores remotos (sin ~ porque son absolutas)
        BACKEND_EXTERNAL="/data/files/external"
        BACKEND_INTERNAL="/data/files/internal"
        TRAINER_EXTERNAL="/data/files/external"
        TRAINER_INTERNAL="/data/files/internal"

        # Validar que la clave SSH existe
        if [[ ! -f "$TRAINER_SSH_KEY" ]]; then
            log_error "Clave SSH no encontrada: $TRAINER_SSH_KEY"
            exit 1
        fi

        log_info "Modo: Sincronización remota via SSH ($ENVIRONMENT)"
        log_info "Trainer SSH: $TRAINER_SSH_USER@$TRAINER_SSH_HOST:$TRAINER_SSH_PORT"
        ;;

    *)
        log_error "Entorno no reconocido: $ENVIRONMENT"
        log_error "Entornos válidos: macbook, dev, pre, pro"
        exit 1
        ;;
esac

# ============================================================================
# OPCIONES DE RSYNC
# ============================================================================

# Opciones comunes de rsync:
# -r, --recursive: Copiar directorios recursivamente
# -t, --times: Preservar timestamps de modificación
# -z, --compress: Comprimir datos durante transferencia (útil para SSH)
# -v, --verbose: Modo verbose para logs
# --update: Solo copiar archivos más nuevos o que no existen en destino
# --stats: Mostrar estadísticas al final

RSYNC_OPTS=(
    -rtz                    # Recursivo, preservar timestamps, comprimir
    --update                # Solo actualizar archivos nuevos/modificados
    --stats                 # Mostrar estadísticas
    --human-readable        # Tamaños legibles (KB, MB, GB)
)

# Opciones adicionales para modo verbose (útil en desarrollo)
if [[ "${VERBOSE:-0}" == "1" ]]; then
    RSYNC_OPTS+=(-v --progress)
fi

# ============================================================================
# FUNCIONES DE SINCRONIZACIÓN
# ============================================================================

sync_local() {
    local source="$1"
    local destination="$2"
    local description="$3"

    log_info "Sincronizando: $description"
    log_info "  Origen: $source"
    log_info "  Destino: $destination"

    # Validar que origen existe
    if [[ ! -d "$source" ]]; then
        log_error "Directorio origen no existe: $source"
        return 1
    fi

    # Crear destino si no existe
    mkdir -p "$destination"

    # Ejecutar rsync local (agregar / al final para copiar contenido, no el directorio)
    if rsync "${RSYNC_OPTS[@]}" "${source}/" "${destination}/"; then
        log_success "Sincronización completada: $description"
        return 0
    else
        log_error "Error en sincronización: $description"
        return 1
    fi
}

sync_remote() {
    local source="$1"
    local destination="$2"
    local description="$3"
    local direction="$4"  # "push" o "pull"

    log_info "Sincronizando (SSH): $description"

    # Construir comando SSH para rsync
    SSH_CMD="ssh -i $TRAINER_SSH_KEY -p $TRAINER_SSH_PORT -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

    # Agregar opción SSH a rsync
    local rsync_ssh_opts=("${RSYNC_OPTS[@]}" -e "$SSH_CMD")

    if [[ "$direction" == "push" ]]; then
        # Backend → Trainer (push)
        log_info "  Origen (local): $source"
        log_info "  Destino (remoto): $TRAINER_SSH_USER@$TRAINER_SSH_HOST:$destination"

        if rsync "${rsync_ssh_opts[@]}" "${source}/" "${TRAINER_SSH_USER}@${TRAINER_SSH_HOST}:${destination}/"; then
            log_success "Push completado: $description"
            return 0
        else
            log_error "Error en push: $description"
            return 1
        fi

    elif [[ "$direction" == "pull" ]]; then
        # Trainer → Backend (pull)
        log_info "  Origen (remoto): $TRAINER_SSH_USER@$TRAINER_SSH_HOST:$source"
        log_info "  Destino (local): $destination"

        # Crear destino si no existe
        mkdir -p "$destination"

        if rsync "${rsync_ssh_opts[@]}" "${TRAINER_SSH_USER}@${TRAINER_SSH_HOST}:${source}/" "${destination}/"; then
            log_success "Pull completado: $description"
            return 0
        else
            log_error "Error en pull: $description"
            return 1
        fi
    else
        log_error "Dirección no válida: $direction (debe ser 'push' o 'pull')"
        return 1
    fi
}

# ============================================================================
# EJECUCIÓN PRINCIPAL
# ============================================================================

log_info "========================================="
log_info "Iniciando sincronización de almacenamiento"
log_info "Entorno: $ENVIRONMENT"
log_info "Modo: $TRANSFER_MODE"
log_info "========================================="

SYNC_SUCCESS=0
SYNC_ERRORS=0

# ----------------------------------------------------------------------------
# SINCRONIZACIÓN 1: Backend External → Trainer External
# ----------------------------------------------------------------------------
# Propósito: Los archivos que los usuarios suben al backend (via fmanagement)
#            se replican al trainer para que pueda procesarlos en entrenamientos.
# ----------------------------------------------------------------------------

log_info ""
log_info "--- SYNC 1: Backend External → Trainer External ---"

if [[ "$TRANSFER_MODE" == "local" ]]; then
    if sync_local "$BACKEND_EXTERNAL" "$TRAINER_EXTERNAL" "Backend External → Trainer External"; then
        ((SYNC_SUCCESS++))
    else
        ((SYNC_ERRORS++))
    fi
else
    # En entornos remotos, este script se ejecuta en el servidor Backend
    if sync_remote "$BACKEND_EXTERNAL" "$TRAINER_EXTERNAL" "Backend External → Trainer External" "push"; then
        ((SYNC_SUCCESS++))
    else
        ((SYNC_ERRORS++))
    fi
fi

# ----------------------------------------------------------------------------
# SINCRONIZACIÓN 2: Trainer Internal → Backend Internal
# ----------------------------------------------------------------------------
# Propósito: Los resultados generados por el trainer (modelos, informes, etc.)
#            se replican al backend para que estén disponibles vía fmanagement.
# ----------------------------------------------------------------------------

log_info ""
log_info "--- SYNC 2: Trainer Internal → Backend Internal ---"

if [[ "$TRANSFER_MODE" == "local" ]]; then
    if sync_local "$TRAINER_INTERNAL" "$BACKEND_INTERNAL" "Trainer Internal → Backend Internal"; then
        ((SYNC_SUCCESS++))
    else
        ((SYNC_ERRORS++))
    fi
else
    # En entornos remotos, este script se ejecuta en el servidor Backend
    if sync_remote "$TRAINER_INTERNAL" "$BACKEND_INTERNAL" "Trainer Internal → Backend Internal" "pull"; then
        ((SYNC_SUCCESS++))
    else
        ((SYNC_ERRORS++))
    fi
fi

# ============================================================================
# RESUMEN
# ============================================================================

log_info ""
log_info "========================================="
log_info "Sincronización finalizada"
log_info "Exitosas: $SYNC_SUCCESS"
log_info "Errores: $SYNC_ERRORS"
log_info "========================================="

if [[ $SYNC_ERRORS -gt 0 ]]; then
    exit 1
else
    exit 0
fi
