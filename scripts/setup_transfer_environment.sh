#!/bin/bash
# ============================================================================
# setup_transfer_environment.sh
# Script para configurar el entorno de transferencia de versiones en macbook
# ============================================================================

set -e

echo "=============================================="
echo "Configuración del entorno de transferencia"
echo "=============================================="

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Función para imprimir mensajes
info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 1. Verificar rsync está instalado
echo ""
info "Verificando rsync..."
if command -v rsync &> /dev/null; then
    RSYNC_VERSION=$(rsync --version | head -n 1)
    info "rsync instalado: $RSYNC_VERSION"
else
    warn "rsync no encontrado. Instalando con Homebrew..."
    if command -v brew &> /dev/null; then
        brew install rsync
        info "rsync instalado correctamente"
    else
        error "Homebrew no encontrado. Por favor instala rsync manualmente."
        exit 1
    fi
fi

# 2. Crear estructura de carpetas para almacenamiento
echo ""
info "Creando estructura de carpetas de almacenamiento..."

# Ruta base de almacenamiento para Backend Core (servidor backend)
BACKEND_CORE_STORAGE="$HOME/data/files/external"
# Ruta base de almacenamiento para Backend IA (servidor trainer)
BACKEND_IA_STORAGE="$HOME/data/files/trainer"

# Crear directorios si no existen
mkdir -p "$BACKEND_CORE_STORAGE"
mkdir -p "$BACKEND_IA_STORAGE"

info "Carpeta Backend Core creada: $BACKEND_CORE_STORAGE"
info "Carpeta Backend IA creada: $BACKEND_IA_STORAGE"

# 3. Crear estructura de ejemplo para tests
echo ""
info "Creando estructura de ejemplo para tests..."

# Estructura de ejemplo en Backend Core
EXAMPLE_ORG="ORG0001"
EXAMPLE_PRJ="PRJ00001"
EXAMPLE_VERSION="v001"

EXAMPLE_PATH="$BACKEND_CORE_STORAGE/$EXAMPLE_ORG/$EXAMPLE_PRJ/$EXAMPLE_VERSION"
mkdir -p "$EXAMPLE_PATH/text"
mkdir -p "$EXAMPLE_PATH/images"

# Crear archivos de ejemplo
echo "Este es un archivo de texto de ejemplo para tests de transferencia." > "$EXAMPLE_PATH/text/sample.txt"
echo "Otro archivo de prueba." > "$EXAMPLE_PATH/text/readme.txt"
echo "Placeholder para imagen de prueba" > "$EXAMPLE_PATH/images/placeholder.txt"

info "Estructura de ejemplo creada en: $EXAMPLE_PATH"

# 4. Configurar SSH (opcional para modo local, pero útil para emulación remota)
echo ""
info "Configurando claves SSH para transferencia..."

SSH_KEY_PATH="$HOME/.ssh/rsync_key"

if [ -f "$SSH_KEY_PATH" ]; then
    info "Clave SSH ya existe en: $SSH_KEY_PATH"
else
    warn "Generando nueva clave SSH para rsync..."
    ssh-keygen -t ed25519 -f "$SSH_KEY_PATH" -N "" -C "rsync_transfer_key"
    info "Clave SSH generada: $SSH_KEY_PATH"
    
    # Añadir la clave pública a authorized_keys para localhost (emulación)
    cat "${SSH_KEY_PATH}.pub" >> "$HOME/.ssh/authorized_keys"
    chmod 600 "$HOME/.ssh/authorized_keys"
    info "Clave pública añadida a authorized_keys para emulación local"
fi

# 5. Verificar conexión SSH local (para emulación)
echo ""
info "Verificando conexión SSH local..."
if ssh -o StrictHostKeyChecking=no -o BatchMode=yes -i "$SSH_KEY_PATH" localhost "echo 'SSH OK'" 2>/dev/null; then
    info "Conexión SSH local verificada correctamente"
else
    warn "No se pudo verificar SSH local. Asegúrate de que:"
    warn "  1. El servicio SSH esté habilitado (Preferencias > Compartir > Sesión remota)"
    warn "  2. La clave pública esté en ~/.ssh/authorized_keys"
fi

# 6. Mostrar resumen de configuración
echo ""
echo "=============================================="
echo "Resumen de configuración"
echo "=============================================="
echo ""
echo "Rutas de almacenamiento:"
echo "  Backend Core: $BACKEND_CORE_STORAGE"
echo "  Backend IA:   $BACKEND_IA_STORAGE"
echo ""
echo "Clave SSH para rsync:"
echo "  Privada: $SSH_KEY_PATH"
echo "  Pública: ${SSH_KEY_PATH}.pub"
echo ""
echo "Variables de entorno recomendadas para .env o env.yaml:"
echo ""
echo "  BACKEND_CORE_BASE_STORAGE=$BACKEND_CORE_STORAGE"
echo "  BACKEND_IA_BASE_STORAGE=$BACKEND_IA_STORAGE"
echo "  TRANSFER_MODE=local"
echo "  TRAINER_SSH_HOST=localhost"
echo "  TRAINER_SSH_USER=$USER"
echo "  TRAINER_SSH_KEY_PATH=$SSH_KEY_PATH"
echo "  TRAINER_SSH_PORT=22"
echo ""
info "Configuración completada"
echo ""

# 7. Test rápido de transferencia local
echo "=============================================="
echo "Test de transferencia local"
echo "=============================================="
echo ""
info "Ejecutando test de copia local..."

TEST_SRC="$BACKEND_CORE_STORAGE/$EXAMPLE_ORG/$EXAMPLE_PRJ/$EXAMPLE_VERSION"
TEST_DST="$BACKEND_IA_STORAGE/$EXAMPLE_ORG/$EXAMPLE_PRJ/$EXAMPLE_VERSION"

# Limpiar destino si existe
rm -rf "$TEST_DST"

# Crear directorio padre en destino
mkdir -p "$(dirname "$TEST_DST")"

# Ejecutar copia
if cp -r "$TEST_SRC" "$TEST_DST"; then
    info "Copia local exitosa"
    info "Archivos transferidos:"
    find "$TEST_DST" -type f | while read f; do
        echo "    $f"
    done
else
    error "Error en copia local"
fi

echo ""
info "Setup completado. El entorno está listo para pruebas de transferencia."
