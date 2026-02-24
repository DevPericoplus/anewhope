#!/usr/bin/env python3
"""Test para verificar la integración del calendario con la tabla cambios."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine
import importlib.util
from datetime import datetime

# Cargar adapter
adapter_path = Path(__file__).parent.parent / "src/2_shared_application/adapters/cambios_adapter.py"
spec = importlib.util.spec_from_file_location("cambios_adapter", adapter_path)
adapter_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter_module)

# Crear engine
engine = create_engine("mysql+pymysql://myllm_admin:Us3r%40dminP%40ss@localhost/myllm_projects_db")

print("=== TEST: Integración de Calendario con Cambios ===\n")

# 1. Obtener tipos de cambio únicos
print("1. Tipos de cambio existentes:")
tipos = adapter_module.obtener_tipos_cambio_unicos(engine)
for tipo in tipos:
    print(f"   - {tipo}")
print()

# 2. Obtener organizaciones para usuario interno (user_id=1 = adminone)
print("2. Organizaciones asignadas al usuario adminone (id=1):")
organizaciones = adapter_module.obtener_organizaciones_internas_usuario(
    engine=engine,
    id_usuario=1
)
print(f"   Total: {len(organizaciones)}")
for org in organizaciones:
    print(f"   - {org['nombre']} (ID: {org['id']})")
print()

if not organizaciones:
    print("⚠️  No hay organizaciones asignadas. Verificar asignaciones_organizaciones_internas.")
    sys.exit(0)

org_id = organizaciones[0]['id']
org_nombre = organizaciones[0]['nombre']

# 3. Obtener proyectos de la organización
print(f"3. Proyectos de la organización '{org_nombre}':")
proyectos = adapter_module.obtener_proyectos_organizacion(
    engine=engine,
    id_organizacion=org_id
)
print(f"   Total: {len(proyectos)}")
for p in proyectos:
    print(f"   - {p['nombre']} (ID: {p['id']})")
print()

# 4. Obtener cambios del mes actual
print(f"4. Cambios del mes actual para organización '{org_nombre}':")
now = datetime.now()
cambios = adapter_module.obtener_cambios_por_organizacion(
    engine=engine,
    id_organizacion=org_id,
    mes=now.month,
    anio=now.year
)
print(f"   Total de cambios: {len(cambios)}")
for cambio in cambios[:5]:  # Mostrar solo los primeros 5
    print(f"   - {cambio.fecha_cambio}: {cambio.tipo_cambio}")
    print(f"     Descripción: {cambio.descripcion[:60]}...")
    print(f"     Color: {cambio.get_color()}")
print()

# 5. Obtener eventos agrupados por día
print(f"5. Eventos agrupados por día (mes actual):")
eventos_dia = adapter_module.obtener_cambios_agrupados_por_dia(
    engine=engine,
    id_organizacion=org_id,
    mes=now.month,
    anio=now.year
)
print(f"   Días con eventos: {len(eventos_dia)}")
for evento in eventos_dia[:5]:  # Mostrar solo los primeros 5
    print(f"   - {evento['date']}: {evento['count']} evento(s)")
    print(f"     Color: {evento['color']}")
    print(f"     Mixto: {evento['has_mixed']}")
    print(f"     Tooltip: {evento['tooltip'][:80]}...")
print()

print("✓ Test completado exitosamente!")
