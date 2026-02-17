#!/bin/bash
#
# Script para sincronizar sistema de versiones con fmanagement
#
# Este script copia el archivo versions.yml y el módulo version_reader.py
# al proyecto fmanagement ubicado en ~/develop/fmanagement/
#

set -e

ANEWHOPE_ROOT="/Users/administrator/develop/anewhope"
FMANAGEMENT_ROOT="/Users/administrator/develop/fmanagement"

echo "=========================================="
echo "Sincronización de Versiones con fmanagement"
echo "=========================================="
echo ""

# Verificar que existe el directorio de fmanagement
if [ ! -d "$FMANAGEMENT_ROOT" ]; then
    echo "❌ Error: Directorio fmanagement no encontrado en $FMANAGEMENT_ROOT"
    exit 1
fi

# Copiar versions.yml
echo "1. Copiando versions.yml..."
cp "$ANEWHOPE_ROOT/versions.yml" "$FMANAGEMENT_ROOT/versions.yml"
echo "   ✅ versions.yml copiado"

# Crear directorio src/utils en fmanagement si no existe
echo ""
echo "2. Preparando directorio de utilidades..."
mkdir -p "$FMANAGEMENT_ROOT/src/utils"
touch "$FMANAGEMENT_ROOT/src/__init__.py"
touch "$FMANAGEMENT_ROOT/src/utils/__init__.py"
echo "   ✅ Estructura de directorios creada"

# Copiar version_reader.py
echo ""
echo "3. Copiando version_reader.py..."
cp "$ANEWHOPE_ROOT/src/2_shared_application/utils/version_reader.py" \
   "$FMANAGEMENT_ROOT/src/utils/version_reader.py"
echo "   ✅ version_reader.py copiado"

# Verificar que PyYAML está instalado en fmanagement
echo ""
echo "4. Verificando dependencias..."
if [ -f "$FMANAGEMENT_ROOT/requirements.txt" ]; then
    if ! grep -q "pyyaml" "$FMANAGEMENT_ROOT/requirements.txt"; then
        echo "   ⚠️  PyYAML no encontrado en requirements.txt"
        echo "   Agregando PyYAML..."
        echo "pyyaml==6.0.2" >> "$FMANAGEMENT_ROOT/requirements.txt"
        echo "   ✅ PyYAML agregado a requirements.txt"
    else
        echo "   ✅ PyYAML ya está en requirements.txt"
    fi
else
    echo "   ⚠️  requirements.txt no encontrado en fmanagement"
fi

# Crear script de ejemplo para usar versiones en fmanagement
echo ""
echo "5. Creando script de ejemplo..."
cat > "$FMANAGEMENT_ROOT/check_version.py" << 'PYTHON_EOF'
#!/usr/bin/env python3
"""
Script de ejemplo para verificar la versión de fmanagement.

Uso:
    python check_version.py
"""

from src.utils.version_reader import get_version, get_version_info

if __name__ == "__main__":
    version = get_version("fmanagement")
    info = get_version_info("fmanagement")

    print("=" * 50)
    print("fmanagement - Version Information")
    print("=" * 50)
    print(f"Version: {version}")
    print(f"Major:   {info['major']}")
    print(f"Minor:   {info['minor']}")
    print(f"Patch:   {info['patch']}")
    print("=" * 50)
PYTHON_EOF

chmod +x "$FMANAGEMENT_ROOT/check_version.py"
echo "   ✅ check_version.py creado"

echo ""
echo "=========================================="
echo "✅ Sincronización completada"
echo "=========================================="
echo ""
echo "Para usar en fmanagement:"
echo "  1. cd $FMANAGEMENT_ROOT"
echo "  2. python check_version.py"
echo ""
echo "O en tu código Python:"
echo '  from src.utils.version_reader import get_version'
echo '  version = get_version("fmanagement")'
echo ""
