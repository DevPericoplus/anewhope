#!/usr/bin/env python3
"""
Crea la tabla estado_version e inserta los registros iniciales.
"""
import pymysql
import importlib.util
from pathlib import Path

# Cargar configuración
protected_path = Path(__file__).parent / "infrastructure" / "environments" / "macbook" / "protected_values.py"
spec = importlib.util.spec_from_file_location("protected_values", protected_path)
protected = importlib.util.module_from_spec(spec)
spec.loader.exec_module(protected)

# Conectar a la base de datos de proyectos
conn = pymysql.connect(
    host=protected.mariadb_host,
    port=protected.mariadb_port,
    user=protected.mariadb_admin_user,
    password=protected.mariadb_admin_password,
    database=protected.mariadb_ai_database,
    cursorclass=pymysql.cursors.DictCursor
)

try:
    with conn.cursor() as cursor:
        # Leer el DDL
        ddl_path = Path(__file__).parent / "infrastructure" / "database" / "ddl_estado_version.sql"
        with open(ddl_path, 'r') as f:
            sql_script = f.read()

        # Ejecutar cada statement separando por punto y coma
        statements = []
        current_statement = []

        for line in sql_script.split('\n'):
            line = line.strip()
            if line and not line.startswith('--'):
                current_statement.append(line)
                if line.endswith(';'):
                    statements.append(' '.join(current_statement))
                    current_statement = []

        for statement in statements:
            if statement.strip():
                try:
                    cursor.execute(statement)
                except Exception as e:
                    print(f'⚠ Error en statement: {str(e)[:100]}')
                    continue

        conn.commit()

        # Verificar creación
        cursor.execute('SELECT COUNT(*) as count FROM estado_version')
        result = cursor.fetchone()
        print(f'✓ Tabla estado_version creada exitosamente')
        print(f'✓ Registros insertados: {result["count"]}')

        # Mostrar algunos registros
        cursor.execute('SELECT * FROM estado_version ORDER BY id_organizacion, id_proyecto, id_version LIMIT 10')
        records = cursor.fetchall()
        print(f'\nPrimeros registros:')
        for r in records:
            print(f'  Org {r["id_organizacion"]} / Proyecto {r["id_proyecto"]} / Versión {r["id_version"]} -> '
                  f'Estado: {r["state"]} (protected={r["protected"]}, final_c={r["final_c"]}, final_i={r["final_i"]})')

finally:
    conn.close()
