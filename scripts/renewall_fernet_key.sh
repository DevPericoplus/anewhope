#!/bin/bash
# =============================================================================
# renewall_fernet_key.sh
# =============================================================================
# Script para renovar la clave Fernet y re-encriptar todos los valores
# cifrados con la clave antigua usando la nueva clave.
#
# IMPORTANTE: Este script es CRÍTICO para la seguridad. Asegúrate de:
#   1. Tener backup de basesecuritypass.json y users.json antes de ejecutar
#   2. Detener todos los servicios que usen cifrado antes de ejecutar
#   3. Verificar que la re-encriptación fue exitosa antes de reiniciar servicios
#
# Uso:
#   ./scripts/renewall_fernet_key.sh [--dry-run] [--backup-only]
#
# Opciones:
#   --dry-run      Simula la operación sin modificar archivos
#   --backup-only  Solo crea backups sin renovar la clave
#
# =============================================================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Rutas del proyecto
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SECURITY_DIR="$PROJECT_ROOT/src/2_shared_application/security"
MOKS_DIR="$PROJECT_ROOT/src/2_shared_application/moks"

FERNET_KEY_FILE="$SECURITY_DIR/basesecuritypass.json"
USERS_FILE="$MOKS_DIR/users.json"
CIPHER_MODULE="$SECURITY_DIR/custom_cipher_lib.py"

# Directorio de backups
BACKUP_DIR="$PROJECT_ROOT/backups/fernet_rotation"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Flags
DRY_RUN=false
BACKUP_ONLY=false

# Procesar argumentos
for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --backup-only)
            BACKUP_ONLY=true
            shift
            ;;
        --help|-h)
            echo "Uso: $0 [--dry-run] [--backup-only]"
            echo ""
            echo "Opciones:"
            echo "  --dry-run      Simula la operación sin modificar archivos"
            echo "  --backup-only  Solo crea backups sin renovar la clave"
            echo "  --help, -h     Muestra esta ayuda"
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Argumento desconocido: $arg${NC}"
            exit 1
            ;;
    esac
done

# Función para log con timestamp
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Función para verificar archivos requeridos
check_requirements() {
    log "${BLUE}Verificando requisitos...${NC}"
    
    local missing=0
    
    if [ ! -f "$FERNET_KEY_FILE" ]; then
        log "${RED}ERROR: No se encontró el archivo de clave Fernet: $FERNET_KEY_FILE${NC}"
        missing=1
    fi
    
    if [ ! -f "$USERS_FILE" ]; then
        log "${RED}ERROR: No se encontró el archivo de usuarios: $USERS_FILE${NC}"
        missing=1
    fi
    
    if [ ! -f "$CIPHER_MODULE" ]; then
        log "${RED}ERROR: No se encontró el módulo de cifrado: $CIPHER_MODULE${NC}"
        missing=1
    fi
    
    # Verificar Python y cryptography
    if ! command -v python3 &> /dev/null; then
        log "${RED}ERROR: Python3 no está instalado${NC}"
        missing=1
    fi
    
    if ! python3 -c "from cryptography.fernet import Fernet" 2>/dev/null; then
        log "${RED}ERROR: El módulo 'cryptography' no está instalado${NC}"
        log "${YELLOW}Instálalo con: pip install cryptography${NC}"
        missing=1
    fi
    
    if [ $missing -eq 1 ]; then
        exit 1
    fi
    
    log "${GREEN}✓ Todos los requisitos verificados${NC}"
}

# Función para crear backups
create_backups() {
    log "${BLUE}Creando backups...${NC}"
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup de la clave Fernet
    if [ -f "$FERNET_KEY_FILE" ]; then
        cp "$FERNET_KEY_FILE" "$BACKUP_DIR/basesecuritypass_$TIMESTAMP.json"
        log "${GREEN}✓ Backup de clave Fernet: basesecuritypass_$TIMESTAMP.json${NC}"
    fi
    
    # Backup de users.json
    if [ -f "$USERS_FILE" ]; then
        cp "$USERS_FILE" "$BACKUP_DIR/users_$TIMESTAMP.json"
        log "${GREEN}✓ Backup de usuarios: users_$TIMESTAMP.json${NC}"
    fi
    
    log "${GREEN}✓ Backups creados en: $BACKUP_DIR${NC}"
}

# Script Python embebido para la renovación
run_renewal() {
    log "${BLUE}Ejecutando renovación de clave Fernet...${NC}"
    
    if [ "$DRY_RUN" = true ]; then
        log "${YELLOW}[DRY-RUN] Simulando renovación sin modificar archivos${NC}"
    fi
    
    python3 << 'PYTHON_SCRIPT'
import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Añadir el proyecto al path
project_root = Path(__file__).resolve().parent if '__file__' in dir() else Path.cwd()
# El script se ejecuta desde el directorio del proyecto
project_root = Path(os.environ.get('PROJECT_ROOT', '.')).resolve()
sys.path.insert(0, str(project_root))

try:
    from cryptography.fernet import Fernet, InvalidToken
except ImportError:
    print("ERROR: No se pudo importar cryptography.fernet")
    sys.exit(1)

# Configuración
DRY_RUN = os.environ.get('DRY_RUN', 'false').lower() == 'true'
SECURITY_DIR = Path(os.environ.get('SECURITY_DIR', 'src/2_shared_application/security'))
MOKS_DIR = Path(os.environ.get('MOKS_DIR', 'src/2_shared_application/moks'))
FERNET_KEY_FILE = SECURITY_DIR / "basesecuritypass.json"
USERS_FILE = MOKS_DIR / "users.json"

def load_fernet_key(key_file: Path) -> tuple[str, Fernet]:
    """Carga la clave Fernet desde el archivo JSON."""
    with open(key_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    key_str = data.get('fernet_key', '')
    if not key_str:
        raise ValueError("No se encontró 'fernet_key' en el archivo")
    return key_str, Fernet(key_str.encode())

def save_fernet_key(key_file: Path, key_str: str) -> None:
    """Guarda la clave Fernet en el archivo JSON."""
    data = {"fernet_key": key_str}
    with open(key_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"✓ Nueva clave Fernet guardada en: {key_file}")

def is_fernet_encrypted(value: str, fernet: Fernet) -> bool:
    """Verifica si un valor está cifrado con Fernet."""
    if not value or not isinstance(value, str):
        return False
    try:
        fernet.decrypt(value.encode('utf-8'))
        return True
    except (InvalidToken, Exception):
        return False

def decrypt_value(fernet: Fernet, encrypted_value: str) -> str:
    """Descifra un valor usando Fernet."""
    decrypted_bytes = fernet.decrypt(encrypted_value.encode('utf-8'))
    return decrypted_bytes.decode('utf-8')

def encrypt_value(fernet: Fernet, plain_value: str) -> str:
    """Cifra un valor usando Fernet."""
    encrypted_bytes = fernet.encrypt(plain_value.encode('utf-8'))
    return encrypted_bytes.decode('utf-8')

def main():
    print("=" * 70)
    print("RENOVACIÓN DE CLAVE FERNET")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Modo: {'DRY-RUN (simulación)' if DRY_RUN else 'PRODUCCIÓN'}")
    print("=" * 70)
    
    # 1. Cargar la clave antigua
    print("\n[1/5] Cargando clave Fernet antigua...")
    try:
        old_key_str, old_fernet = load_fernet_key(FERNET_KEY_FILE)
        print(f"✓ Clave antigua cargada: {old_key_str[:15]}...")
    except Exception as e:
        print(f"ERROR: No se pudo cargar la clave antigua: {e}")
        sys.exit(1)
    
    # 2. Generar nueva clave
    print("\n[2/5] Generando nueva clave Fernet...")
    new_key_bytes = Fernet.generate_key()
    new_key_str = new_key_bytes.decode('utf-8')
    new_fernet = Fernet(new_key_bytes)
    print(f"✓ Nueva clave generada: {new_key_str[:15]}...")
    
    # 3. Cargar usuarios
    print("\n[3/5] Cargando archivo de usuarios...")
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            users = json.load(f)
        print(f"✓ {len(users)} usuarios cargados")
    except Exception as e:
        print(f"ERROR: No se pudo cargar el archivo de usuarios: {e}")
        sys.exit(1)
    
    # 4. Re-encriptar contraseñas
    print("\n[4/5] Re-encriptando contraseñas...")
    reencrypted_count = 0
    skipped_count = 0
    error_count = 0
    
    for user in users:
        user_id = user.get('user_id', 'N/A')
        user_name = user.get('user_name', 'N/A')
        password = user.get('user_password', '')
        
        if not password:
            print(f"  ⊘ Usuario {user_id} ({user_name}): Sin contraseña")
            skipped_count += 1
            continue
        
        # Verificar si está cifrado con la clave antigua
        if is_fernet_encrypted(password, old_fernet):
            try:
                # Descifrar con clave antigua
                plain_password = decrypt_value(old_fernet, password)
                # Re-encriptar con clave nueva
                new_encrypted = encrypt_value(new_fernet, plain_password)
                
                if not DRY_RUN:
                    user['user_password'] = new_encrypted
                
                print(f"  ✓ Usuario {user_id} ({user_name}): Re-encriptado")
                reencrypted_count += 1
            except Exception as e:
                print(f"  ✗ Usuario {user_id} ({user_name}): ERROR - {e}")
                error_count += 1
        else:
            print(f"  ⊘ Usuario {user_id} ({user_name}): No está cifrado con Fernet (posiblemente texto plano o hash)")
            skipped_count += 1
    
    print(f"\n  Resumen:")
    print(f"    - Re-encriptados: {reencrypted_count}")
    print(f"    - Omitidos: {skipped_count}")
    print(f"    - Errores: {error_count}")
    
    if error_count > 0:
        print(f"\n{'-' * 70}")
        print("ADVERTENCIA: Hubo errores durante la re-encriptación.")
        print("Revisa los mensajes de error arriba.")
        print(f"{'-' * 70}")
    
    # 5. Guardar cambios
    print("\n[5/5] Guardando cambios...")
    
    if DRY_RUN:
        print("  [DRY-RUN] No se guardarán cambios")
        print(f"  [DRY-RUN] Nueva clave sería: {new_key_str}")
    else:
        # Guardar nueva clave
        save_fernet_key(FERNET_KEY_FILE, new_key_str)
        
        # Guardar usuarios actualizados
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
        print(f"✓ Archivo de usuarios actualizado: {USERS_FILE}")
    
    print("\n" + "=" * 70)
    if DRY_RUN:
        print("SIMULACIÓN COMPLETADA (sin cambios)")
    else:
        print("RENOVACIÓN COMPLETADA EXITOSAMENTE")
    print("=" * 70)
    
    if not DRY_RUN:
        print("\n⚠️  ACCIONES REQUERIDAS:")
        print("   1. Reiniciar todos los servicios que usan cifrado")
        print("   2. Verificar que el login funciona correctamente")
        print("   3. Eliminar backups antiguos después de verificar")
        print("")

if __name__ == '__main__':
    main()
PYTHON_SCRIPT
}

# =============================================================================
# MAIN
# =============================================================================

log "${BLUE}========================================${NC}"
log "${BLUE}  RENOVACIÓN DE CLAVE FERNET${NC}"
log "${BLUE}========================================${NC}"

if [ "$DRY_RUN" = true ]; then
    log "${YELLOW}MODO: DRY-RUN (simulación sin cambios)${NC}"
fi

if [ "$BACKUP_ONLY" = true ]; then
    log "${YELLOW}MODO: BACKUP-ONLY${NC}"
fi

# Verificar requisitos
check_requirements

# Crear backups siempre
create_backups

if [ "$BACKUP_ONLY" = true ]; then
    log "${GREEN}Backups creados. Saliendo (--backup-only).${NC}"
    exit 0
fi

# Exportar variables para el script Python
export PROJECT_ROOT="$PROJECT_ROOT"
export SECURITY_DIR="$SECURITY_DIR"
export MOKS_DIR="$MOKS_DIR"
export DRY_RUN="$DRY_RUN"

# Ejecutar renovación
run_renewal

log "${GREEN}========================================${NC}"
log "${GREEN}  PROCESO FINALIZADO${NC}"
log "${GREEN}========================================${NC}"

if [ "$DRY_RUN" = false ]; then
    log ""
    log "${YELLOW}IMPORTANTE:${NC}"
    log "  1. Los backups están en: $BACKUP_DIR"
    log "  2. Reinicia todos los servicios antes de usar el sistema"
    log "  3. Verifica el login con un usuario de prueba"
    log ""
fi
