#!/usr/bin/env python3
"""Test para verificar la carga de conversaciones del backoffice."""

import sys
from pathlib import Path
import importlib.util

# Agregar el path base
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine

# Configuración de BD
DB_USER = "myllm_admin"
DB_PASS = "Us3r%40dminP%40ss"
DB_HOST = "localhost"

# Crear engine
engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/myllm_projects_db")

# Cargar el adaptador de conversaciones
adapter_path = Path(__file__).parent.parent / "src/2_shared_application/adapters/conversaciones_adapter.py"
spec = importlib.util.spec_from_file_location("conversaciones_adapter", adapter_path)
adapter_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter_module)

print("=== TEST: CARGA DE CONVERSACIONES BACKOFFICE ===\n")

# Simular lo que hace el backoffice
org_id = 1  # Organization ID de adminone
solo_activas = True

print(f"Parámetros:")
print(f"  - Organization ID: {org_id}")
print(f"  - Solo activas: {solo_activas}\n")

try:
    conversaciones = adapter_module.obtener_conversaciones_organizacion(
        engine=engine,
        id_organizacion=org_id,
        solo_activas=solo_activas
    )

    print(f"Conversaciones encontradas: {len(conversaciones)}\n")

    if conversaciones:
        for i, conv in enumerate(conversaciones, 1):
            print(f"{i}. Conversación ID: {conv.get('id_conversacion')}")
            print(f"   Asunto: {conv.get('asunto', 'Sin asunto')}")
            print(f"   Estado: {conv.get('estado')}")
            print(f"   Prioridad: {conv.get('prioridad')}")
            print(f"   Usuario Cliente: {conv.get('id_usuario_cliente')}")
            print(f"   Fecha: {conv.get('fecha_creacion')}")
            print(f"   Último mensaje: {conv.get('ultimo_mensaje_texto', 'Sin mensajes')[:50]}...")
            print(f"   Mensajes sin leer (interno): {conv.get('mensajes_sin_leer_interno', 0)}")
            print()
    else:
        print("❌ No se encontraron conversaciones para la organización 1")
        print("\nVerificando si hay conversaciones en la BD (sin filtros)...")

        from sqlalchemy import text
        with engine.connect() as conn:
            query = text("SELECT COUNT(*) FROM conversaciones WHERE id_organizacion = :org_id")
            total = conn.execute(query, {"org_id": org_id}).scalar()
            print(f"Total conversaciones en BD para org 1: {total}")

            if total > 0:
                query2 = text("""
                    SELECT id_conversacion, asunto, estado, prioridad
                    FROM conversaciones
                    WHERE id_organizacion = :org_id
                    ORDER BY fecha_creacion DESC
                """)
                result = conn.execute(query2, {"org_id": org_id})
                print("\nTodas las conversaciones (incluyendo inactivas):")
                for row in result:
                    print(f"  - ID {row[0]}: {row[1]} (estado: {row[2]}, prioridad: {row[3]})")

except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n=== FIN DEL TEST ===")
