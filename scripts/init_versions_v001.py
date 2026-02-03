#!/usr/bin/env python3
"""Script para inicializar versiones v001 para todos los proyectos existentes.

Este script:
1. Consulta todos los proyectos existentes en myllm_projects_db
2. Crea versión v001 para cada proyecto (si no existe)
3. Crea registros en version_states (estado Abierta)
4. Crea registros en version_events (VERSION_CREADA)
5. Llama a fmanagement para crear las estructuras físicas en disco
"""

import sys
from pathlib import Path

# Añadir el root del proyecto al path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from datetime import datetime
import json
import urllib.request

# Importar configuración
sys.path.insert(0, str(ROOT_DIR / "src" / "2_shared_application"))
from config.env_settings import get_all_config

print("=" * 80)
print("INICIALIZACIÓN DE VERSIONES V001")
print("=" * 80)
print()

# ============================================================================
# PASO 1: Conectar a la base de datos
# ============================================================================

print("PASO 1: Conectando a la base de datos myllm_projects_db...")
settings = get_all_config()

host = settings.get("projects_db_host", "localhost")
port = int(settings.get("projects_db_port", "3306"))
user = settings.get("writer_user", "myllmwriter")
password = quote_plus(settings.get("writer_password", ""))
database = settings.get("projects_database", "myllm_projects_db")

dsn = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
engine = create_engine(dsn)

print(f"✅ Conectado a {host}:{port}/{database}")
print()

# ============================================================================
# PASO 2: Consultar proyectos existentes
# ============================================================================

print("PASO 2: Consultando proyectos existentes...")

query_projects = text("""
    SELECT 
        id_proyecto,
        id_organizacion,
        nombre_proyecto,
        created_by_user_id
    FROM proyectos
    WHERE activo = 1
    ORDER BY id_organizacion, id_proyecto
""")

with engine.connect() as conn:
    result = conn.execute(query_projects)
    projects = [dict(row._mapping) for row in result]

print(f"✅ Encontrados {len(projects)} proyectos activos")
for proj in projects:
    print(f"   - Proyecto {proj['id_proyecto']}: {proj['nombre_proyecto']} (Org {proj['id_organizacion']})")
print()

# ============================================================================
# PASO 3: Verificar tablas version_states y version_events existen
# ============================================================================

print("PASO 3: Verificando tablas version_states y version_events...")

check_tables = text("""
    SELECT TABLE_NAME 
    FROM information_schema.TABLES 
    WHERE TABLE_SCHEMA = :database 
    AND TABLE_NAME IN ('version_states', 'version_events', 'versiones')
""")

with engine.connect() as conn:
    result = conn.execute(check_tables, {"database": database})
    existing_tables = [row[0] for row in result]

if 'versiones' not in existing_tables:
    print("❌ ERROR: La tabla 'versiones' no existe. Ejecuta primero el DDL de versiones.")
    sys.exit(1)

if 'version_states' not in existing_tables:
    print("⚠️ ADVERTENCIA: La tabla 'version_states' no existe. Ejecutando DDL...")
    ddl_path = ROOT_DIR / "infrastructure" / "database" / "ddl_version_states.sql"
    if ddl_path.exists():
        with open(ddl_path, "r") as f:
            ddl = f.read()
        with engine.connect() as conn:
            # Ejecutar cada statement por separado
            for statement in ddl.split(";"):
                statement = statement.strip()
                if statement and not statement.startswith("--"):
                    try:
                        conn.execute(text(statement))
                        conn.commit()
                    except Exception as e:
                        # Ignorar errores de INSERT (si no hay versiones aún)
                        if "INSERT" not in statement:
                            raise
        print("✅ Tabla version_states creada")
    else:
        print(f"❌ ERROR: No se encuentra {ddl_path}")
        sys.exit(1)

if 'version_events' not in existing_tables:
    print("⚠️ ADVERTENCIA: La tabla 'version_events' no existe. Ejecutando DDL...")
    ddl_path = ROOT_DIR / "infrastructure" / "database" / "ddl_version_events.sql"
    if ddl_path.exists():
        with open(ddl_path, "r") as f:
            ddl = f.read()
        with engine.connect() as conn:
            for statement in ddl.split(";"):
                statement = statement.strip()
                if statement and not statement.startswith("--"):
                    try:
                        conn.execute(text(statement))
                        conn.commit()
                    except Exception as e:
                        # Ignorar errores de INSERT de ejemplo
                        if "INSERT" not in statement:
                            raise
        print("✅ Tabla version_events creada")
    else:
        print(f"❌ ERROR: No se encuentra {ddl_path}")
        sys.exit(1)

print("✅ Todas las tablas necesarias existen")
print()

# ============================================================================
# PASO 4: Crear versiones v001 para cada proyecto
# ============================================================================

print("PASO 4: Creando versiones v001 para cada proyecto...")

insert_version = text("""
    INSERT INTO versiones 
        (id_organizacion, id_proyecto, id_version, nombre_version, descripcion_version, 
         version_bloqueada, version_entrenada, created_by_user_id, version_activa)
    VALUES 
        (:id_organizacion, :id_proyecto, 1, 'v001', 'Versión inicial creada automáticamente', 
         0, 0, :created_by_user_id, 1)
    ON DUPLICATE KEY UPDATE
        nombre_version = VALUES(nombre_version)
""")

versions_created = 0
versions_existing = 0

with engine.connect() as conn:
    for proj in projects:
        try:
            result = conn.execute(insert_version, {
                "id_organizacion": proj["id_organizacion"],
                "id_proyecto": proj["id_proyecto"],
                "created_by_user_id": proj["created_by_user_id"] or 1,
            })
            conn.commit()
            
            if result.rowcount > 0:
                versions_created += 1
                print(f"   ✅ Versión v001 creada para proyecto {proj['id_proyecto']}")
            else:
                versions_existing += 1
                print(f"   ⏭️ Versión v001 ya existía para proyecto {proj['id_proyecto']}")
        except Exception as e:
            print(f"   ❌ Error creando versión para proyecto {proj['id_proyecto']}: {e}")

print(f"✅ Versiones creadas: {versions_created}, ya existentes: {versions_existing}")
print()

# ============================================================================
# PASO 5: Crear registros en version_states
# ============================================================================

print("PASO 5: Creando registros en version_states...")

insert_state = text("""
    INSERT INTO version_states 
        (id_organizacion, id_proyecto, id_version, state, protected, size_bytes, 
         final_c, final_i, updated_by_user_id)
    VALUES 
        (:id_organizacion, :id_proyecto, 1, 'Abierta', 0, 0, 0, 0, :user_id)
    ON DUPLICATE KEY UPDATE
        state = VALUES(state)
""")

states_created = 0

with engine.connect() as conn:
    for proj in projects:
        try:
            result = conn.execute(insert_state, {
                "id_organizacion": proj["id_organizacion"],
                "id_proyecto": proj["id_proyecto"],
                "user_id": proj["created_by_user_id"] or 1,
            })
            conn.commit()
            
            if result.rowcount > 0:
                states_created += 1
                print(f"   ✅ Estado creado para proyecto {proj['id_proyecto']}")
        except Exception as e:
            print(f"   ❌ Error creando estado para proyecto {proj['id_proyecto']}: {e}")

print(f"✅ Estados creados: {states_created}")
print()

# ============================================================================
# PASO 6: Crear registros en version_events
# ============================================================================

print("PASO 6: Creando registros en version_events...")

insert_event = text("""
    INSERT INTO version_events 
        (id_organizacion, id_proyecto, id_version, evento, mensaje, 
         user_id, user_name, old_state, new_state)
    VALUES 
        (:id_organizacion, :id_proyecto, 1, 'VERSION_CREADA', 
         'Versión v001 creada automáticamente por script de inicialización', 
         :user_id, :user_name, NULL, 'Abierta')
""")

# Obtener nombres de usuarios
query_users = text("""
    SELECT user_id, user_name 
    FROM users 
    WHERE user_id IN :user_ids
""")

user_ids = [proj["created_by_user_id"] or 1 for proj in projects]
user_map = {}

with engine.connect() as conn:
    try:
        result = conn.execute(query_users, {"user_ids": tuple(set(user_ids))})
        user_map = {row.user_id: row.user_name for row in result}
    except Exception as e:
        print(f"   ⚠️ No se pudo consultar tabla 'users': {e}")
        print(f"   ⚠️ Usando 'system' como nombre de usuario")

events_created = 0

with engine.connect() as conn:
    for proj in projects:
        user_id = proj["created_by_user_id"] or 1
        user_name = user_map.get(user_id, "system")
        
        try:
            result = conn.execute(insert_event, {
                "id_organizacion": proj["id_organizacion"],
                "id_proyecto": proj["id_proyecto"],
                "user_id": user_id,
                "user_name": user_name,
            })
            conn.commit()
            
            events_created += 1
            print(f"   ✅ Evento creado para proyecto {proj['id_proyecto']}")
        except Exception as e:
            # Puede que el evento ya exista
            print(f"   ⏭️ Evento para proyecto {proj['id_proyecto']}: {e}")

print(f"✅ Eventos creados: {events_created}")
print()

# ============================================================================
# PASO 7: Llamar a fmanagement para crear estructuras físicas
# ============================================================================

print("PASO 7: Creando estructuras físicas en disco (fmanagement)...")

fmanagement_url = settings.get("fmanagement_url", "http://localhost:9090")

# Importar helper de storage para obtener paths
sys.path.insert(0, str(ROOT_DIR / "src" / "2_shared_application"))
from storage_access_structure import get_folder_by_id_organization, get_folder_by_id_project

structures_created = 0

for proj in projects:
    org_id = proj["id_organizacion"]
    proj_id = proj["id_proyecto"]
    
    # Obtener paths según las reglas del proyecto
    org_folder = get_folder_by_id_organization(org_id)
    proj_folder = get_folder_by_id_project(proj_id)
    version_path = f"{org_folder}/{proj_folder}/v001"
    
    # Crear estructura básica con fmanagement
    payload = {
        "operation": "create_version",
        "base_path": f"{org_folder}/{proj_folder}",
        "version_name": "v001",
        "clone_from": None,  # Nueva versión sin clonar
    }
    
    try:
        req = urllib.request.Request(
            f"{fmanagement_url}/api/v1/operations",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Client-App": "init_script",
            },
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
            
            if result.get("success"):
                structures_created += 1
                print(f"   ✅ Estructura creada en disco para {version_path}")
            else:
                print(f"   ❌ Error en fmanagement para {version_path}: {result.get('error')}")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"   ❌ HTTP {e.code} para {version_path}: {error_body}")
    except Exception as e:
        print(f"   ⚠️ Error creando estructura para {version_path}: {e}")
        print(f"   ⚠️ La versión existe en BD pero puede faltar en disco")

print(f"✅ Estructuras físicas creadas: {structures_created}")
print()

# ============================================================================
# RESUMEN FINAL
# ============================================================================

print("=" * 80)
print("RESUMEN DE INICIALIZACIÓN")
print("=" * 80)
print(f"Proyectos procesados: {len(projects)}")
print(f"Versiones v001 creadas: {versions_created}")
print(f"Versiones v001 ya existentes: {versions_existing}")
print(f"Estados creados: {states_created}")
print(f"Eventos creados: {events_created}")
print(f"Estructuras físicas creadas: {structures_created}")
print()

if structures_created < len(projects):
    print("⚠️ ADVERTENCIA: Algunas estructuras físicas no se crearon.")
    print("   Verifica que fmanagement esté corriendo en", fmanagement_url)
    print("   y que el endpoint /api/v1/operations esté disponible.")
    print()

print("✅ Inicialización completada. Las versiones v001 están listas para usar.")
print()

# ============================================================================
# VERIFICACIÓN FINAL
# ============================================================================

print("VERIFICACIÓN FINAL: Consultando versiones creadas...")

query_verification = text("""
    SELECT 
        v.id_proyecto,
        v.id_version,
        v.nombre_version,
        vs.state,
        vs.protected,
        COUNT(ve.id) as eventos_count
    FROM versiones v
    LEFT JOIN version_states vs 
        ON v.id_proyecto = vs.id_proyecto AND v.id_version = vs.id_version
    LEFT JOIN version_events ve 
        ON v.id_proyecto = ve.id_proyecto AND v.id_version = ve.id_version
    WHERE v.id_version = 1
    GROUP BY v.id_proyecto, v.id_version, v.nombre_version, vs.state, vs.protected
    ORDER BY v.id_proyecto
""")

with engine.connect() as conn:
    result = conn.execute(query_verification)
    print()
    print(f"{'Proyecto':<10} {'Versión':<10} {'Estado':<15} {'Protected':<10} {'Eventos':<10}")
    print("-" * 65)
    for row in result:
        print(f"{row.id_proyecto:<10} {row.nombre_version:<10} {row.state or 'N/A':<15} {row.protected or 'N/A':<10} {row.eventos_count:<10}")

print()
print("=" * 80)
print("✅ SCRIPT COMPLETADO")
print("=" * 80)
