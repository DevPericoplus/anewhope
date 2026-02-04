#!/usr/bin/env python3
"""Script de prueba para verificar las versiones del proyecto"""

import sys
sys.path.insert(0, '/Users/administrator/develop/anewhope/src/apps/5_web_frontend')

# Importar la función
from adapters.api_client import get_project_versions, fmanagement_list_all_project_versions

print("\n" + "="*60)
print("TEST: Verificando versiones del proyecto")
print("="*60 + "\n")

# Probar con un proyecto de ejemplo (proyecto ID 1)
project_id = 1

print(f"1. Llamando a get_project_versions(project_id={project_id})...")
try:
    # Intentar sin tokens (modo demo)
    result = get_project_versions(project_id=project_id, access_token="", session_token="")
    print(f"\nRespuesta: {result}")
    print(f"\nNúmero de versiones: {len(result.get('versiones', []))}")

    if result.get('versiones'):
        print("\nDetalles de versiones encontradas:")
        for idx, ver in enumerate(result.get('versiones', [])):
            print(f"  Versión {idx+1}: {ver}")
    else:
        print("\n⚠️  No se encontraron versiones!")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("FIN DEL TEST")
print("="*60 + "\n")
