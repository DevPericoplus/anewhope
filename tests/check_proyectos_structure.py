#!/usr/bin/env python3
"""Script para ver la estructura de la tabla proyectos."""
import sys
from pathlib import Path

from tests.helpers import get_db_connection

conn = get_db_connection(database="myllm_projects_db")

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
