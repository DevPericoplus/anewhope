#!/usr/bin/env python3
"""Script para verificar el estado de las conversaciones."""

from sqlalchemy import create_engine, text

# Configuración de base de datos
DB_USER = "myllm_admin"
DB_PASS = "Us3r%40dminP%40ss"  # URL-encoded
DB_HOST = "localhost"

engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/myllm_projects_db")

print("=== CONVERSACIONES EN LA BASE DE DATOS ===\n")

with engine.connect() as conn:
    # Ver todas las conversaciones
    query = text("""
        SELECT id_conversacion, id_organizacion, id_usuario_cliente,
               asunto, estado, prioridad, fecha_creacion, fecha_ultima_actualizacion
        FROM conversaciones
        ORDER BY fecha_creacion DESC
        LIMIT 10
    """)
    result = conn.execute(query)

    print("ID | Org | Usuario | Asunto | Estado | Prioridad | Fecha Creación")
    print("-" * 80)
    for row in result:
        print(f"{row.id_conversacion} | {row.id_organizacion} | {row.id_usuario_cliente} | "
              f"{row.asunto[:20]} | {row.estado} | {row.prioridad} | {row.fecha_creacion}")

print("\n=== MENSAJES POR CONVERSACIÓN ===\n")

with engine.connect() as conn:
    # Contar mensajes por conversación
    query = text("""
        SELECT c.id_conversacion, c.asunto, c.estado, COUNT(m.id_mensaje) as num_mensajes
        FROM conversaciones c
        LEFT JOIN mensajes_conversacion m ON c.id_conversacion = m.id_conversacion
        GROUP BY c.id_conversacion
        ORDER BY c.fecha_creacion DESC
        LIMIT 10
    """)
    result = conn.execute(query)

    print("ID | Asunto | Estado | Num Mensajes")
    print("-" * 60)
    for row in result:
        print(f"{row.id_conversacion} | {row.asunto[:30]} | {row.estado} | {row.num_mensajes}")

print("\n=== ESTADOS VÁLIDOS SEGÚN obtener_conversaciones_organizacion ===")
print("Estados considerados 'activas': abierta, en_curso")
print("\nSi las conversaciones tienen estado diferente, no se mostrarán en el backoffice.")
