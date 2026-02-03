#!/usr/bin/env python3
"""Script para listar todas las tablas en myllm_projects_db."""
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
    print("Tablas en myllm_projects_db:")
    cursor.execute("SHOW TABLES")
    for row in cursor.fetchall():
        table_name = row[list(row.keys())[0]]
        print(f"  - {table_name}")

conn.close()
