#!/usr/bin/env python3
"""Test para simular la carga de conversaciones del backoffice."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy import create_engine, text
import importlib.util

# Cargar adapter
adapter_path = Path(__file__).parent / "src/2_shared_application/adapters/conversaciones_adapter.py"
spec = importlib.util.spec_from_file_location("conversaciones_adapter", adapter_path)
adapter_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter_module)

# Crear engine
engine = create_engine("mysql+pymysql://myllm_admin:Us3r%40dminP%40ss@localhost/myllm_projects_db")

print("=== TEST: Carga de conversaciones como en el backoffice ===\n")

org_id = 1  # Organization ID de adminone

print(f"Intentando cargar conversaciones para organización {org_id}...\n")

try:
    conversaciones = adapter_module.obtener_conversaciones_organizacion(
        engine=engine,
        id_organizacion=org_id,
        solo_activas=True
    )

    print(f"✓ Conversaciones encontradas: {len(conversaciones)}\n")

    for i, conv in enumerate(conversaciones, 1):
        print(f"{i}. Conversación ID: {conv['id_conversacion']}")
        print(f"   Usuario Cliente: {conv['id_usuario_cliente']}")
        print(f"   Asunto: {conv['asunto']}")
        print(f"   Estado: {conv['estado']}")
        print(f"   Prioridad: {conv['prioridad']}")
        print(f"   Mensajes sin leer (interno): {conv.get('mensajes_sin_leer_interno', 0)}")
        print(f"   Último mensaje: {conv.get('ultimo_mensaje_texto', 'N/A')[:50]}...")
        print()

        # Cargar mensajes
        mensajes = adapter_module.obtener_mensajes_conversacion(
            engine=engine,
            id_conversacion=conv['id_conversacion']
        )
        print(f"   Total mensajes: {len(mensajes)}")
        for msg in mensajes[:3]:
            print(f"     - [{msg['tipo_emisor']}] {msg['texto_mensaje'][:40]}...")
        print()

except Exception as e:
    print(f"✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
