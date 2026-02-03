#!/usr/bin/env python3
"""Script para ver la estructura de la tabla proyectos."""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import importlib.util
protected_values_path = project_root / "infrastructure" / "environments" / "macbook" / "protected_values.py"
spec = importlib.util.spec_from_file_location("protected_values", protected_values_path)
protected_values = importlib.util.module_from_spec(spec)
spec.loader.exec_module(protected_values)

import pymysql

conn = pymysql.connect(
    host=protected_values.mariadb_host,
    port=int(protected_values.mariadb_port),
    user=protected_values.mariadb_writer_user,
    password=protected_values.mariadb_writer_password,
    database="myllm_projects_db",
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
)

with conn.cursor() as cursor:
    # Ver estructura de tabla proyectos
    print("=" * 80)
    print("ESTRUCTURA DE LA TABLA proyectos")
    print("=" * 80)
    cursor.execute("DESCRIBE proyectos")
    for row in cursor.fetchall():
        print(f"{row['Field']:30} {row['Type']:20} {row['Null']:5} {row['Key']:5} {row['Default']}")

    print("\n" + "=" * 80)
    print("DATOS DE LA TABLA proyectos")
    print("=" * 80)
    cursor.execute("SELECT * FROM proyectos LIMIT 3")
    for row in cursor.fetchall():
        print(row)

    print("\n" + "=" * 80)
    print("ESTRUCTURA DE LA TABLA versiones")
    print("=" * 80)
    cursor.execute("DESCRIBE versiones")
    for row in cursor.fetchall():
        print(f"{row['Field']:30} {row['Type']:20} {row['Null']:5} {row['Key']:5} {row['Default']}")

conn.close()
