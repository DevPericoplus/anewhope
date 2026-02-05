"""
Script para instalar el sistema de conversaciones en la base de datos.

Ejecuta el DDL y opcionalmente crea datos de ejemplo.

Uso:
    python install_conversaciones_db.py
    python install_conversaciones_db.py --with-examples
"""

import sys
import argparse
from sqlalchemy import create_engine, text
from pathlib import Path


def get_db_connection_string():
    """Obtiene la cadena de conexión de la base de datos."""
    # Ajustar según tu configuración
    return "mysql+pymysql://root@localhost/myllm_projects_db"


def ejecutar_ddl(engine, ddl_path: Path):
    """Ejecuta el archivo DDL."""
    print(f"📄 Leyendo DDL desde: {ddl_path}")

    with open(ddl_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # Dividir por delimitadores y ejecutar cada bloque
    print("⚙️  Ejecutando DDL...")

    with engine.connect() as conn:
        # Ejecutar statement por statement
        statements = []
        current_statement = []
        in_delimiter_block = False

        for line in sql_content.split('\n'):
            line_stripped = line.strip()

            # Detectar DELIMITER
            if line_stripped.startswith('DELIMITER'):
                in_delimiter_block = not in_delimiter_block
                if not in_delimiter_block and current_statement:
                    # Fin del bloque DELIMITER
                    stmt = '\n'.join(current_statement)
                    if stmt.strip():
                        statements.append(stmt)
                    current_statement = []
                continue

            # Dentro de bloque DELIMITER
            if in_delimiter_block:
                current_statement.append(line)
                if line_stripped.endswith('//'):
                    stmt = '\n'.join(current_statement)
                    if stmt.strip():
                        statements.append(stmt.replace('//', ';'))
                    current_statement = []
                continue

            # Fuera de bloque DELIMITER
            if line_stripped and not line_stripped.startswith('--'):
                current_statement.append(line)
                if line_stripped.endswith(';'):
                    stmt = '\n'.join(current_statement)
                    if stmt.strip():
                        statements.append(stmt)
                    current_statement = []

        # Ejecutar cada statement
        for i, stmt in enumerate(statements, 1):
            try:
                # Limpiar comentarios
                cleaned_stmt = '\n'.join([
                    line for line in stmt.split('\n')
                    if not line.strip().startswith('--')
                ])

                if cleaned_stmt.strip():
                    conn.execute(text(cleaned_stmt))
                    conn.commit()
                    print(f"  ✓ Statement {i}/{len(statements)} ejecutado")
            except Exception as e:
                print(f"  ⚠️  Error en statement {i}: {str(e)[:100]}")
                # Continuar con el siguiente statement

    print("✅ DDL ejecutado completamente")


def crear_datos_ejemplo(engine):
    """Crea datos de ejemplo para probar el sistema."""
    print("\n📦 Creando datos de ejemplo...")

    with engine.connect() as conn:
        # Verificar si existen usuarios y organizaciones
        result = conn.execute(text("""
            SELECT COUNT(*) as count FROM myllm_projects_db.users
            WHERE identity_type_id IN (
                SELECT id_permissions FROM myllm_projects_db.low_level_permissions
                WHERE training_create = TRUE
            )
        """))
        usuarios_internos = result.fetchone()[0]

        if usuarios_internos == 0:
            print("  ⚠️  No hay usuarios internos disponibles. Crea primero usuarios con training_create=TRUE")
            return

        # Crear conversación de ejemplo
        try:
            # Obtener primer usuario interno y primera organización
            result_user = conn.execute(text("""
                SELECT u.id FROM myllm_projects_db.users u
                JOIN myllm_projects_db.identity_type it ON u.identity_type_id = it.id_permissions
                JOIN myllm_projects_db.low_level_permissions llp ON it.id_permissions = llp.id
                WHERE llp.training_create = TRUE
                LIMIT 1
            """))
            user_interno = result_user.fetchone()

            result_org = conn.execute(text("""
                SELECT id FROM myllm_projects_db.organizaciones LIMIT 1
            """))
            org = result_org.fetchone()

            result_cliente = conn.execute(text("""
                SELECT id FROM myllm_projects_db.users
                WHERE identity_type_id NOT IN (
                    SELECT id_permissions FROM myllm_projects_db.low_level_permissions
                    WHERE training_create = TRUE
                )
                LIMIT 1
            """))
            user_cliente = result_cliente.fetchone()

            if not user_interno or not org or not user_cliente:
                print("  ⚠️  Faltan datos necesarios (usuarios o organizaciones)")
                return

            print(f"  ℹ️  Usuario interno: {user_interno[0]}")
            print(f"  ℹ️  Organización: {org[0]}")
            print(f"  ℹ️  Usuario cliente: {user_cliente[0]}")

            # Crear asignación de ejemplo
            conn.execute(text("""
                INSERT IGNORE INTO myllm_projects_db.asignaciones_organizaciones_internas
                    (id_usuario_interno, id_organizacion, id_rol, asignado_por, notas)
                VALUES
                    (:user_interno, :org_id, 1, :user_interno, 'Asignación de ejemplo')
            """), {
                "user_interno": user_interno[0],
                "org_id": org[0]
            })

            # Crear conversación de ejemplo
            result_conv = conn.execute(text("""
                INSERT INTO myllm_projects_db.conversaciones
                    (id_organizacion, id_usuario_cliente, asunto, prioridad)
                VALUES
                    (:org_id, :user_cliente, 'Consulta de ejemplo', 'media')
            """), {
                "org_id": org[0],
                "user_cliente": user_cliente[0]
            })
            id_conversacion = result_conv.lastrowid

            # Añadir participante cliente
            conn.execute(text("""
                INSERT INTO myllm_projects_db.participantes_conversacion
                    (id_conversacion, id_usuario, tipo_participante)
                VALUES
                    (:id_conv, :user_cliente, 'cliente')
            """), {
                "id_conv": id_conversacion,
                "user_cliente": user_cliente[0]
            })

            # Crear mensajes de ejemplo
            conn.execute(text("""
                INSERT INTO myllm_projects_db.mensajes_conversacion
                    (id_conversacion, id_usuario_emisor, tipo_emisor, texto_mensaje)
                VALUES
                    (:id_conv, :user_cliente, 'cliente', 'Hola, necesito ayuda con mi proyecto')
            """), {
                "id_conv": id_conversacion,
                "user_cliente": user_cliente[0]
            })

            conn.commit()
            print(f"  ✓ Conversación de ejemplo creada (ID: {id_conversacion})")

        except Exception as e:
            print(f"  ⚠️  Error creando datos de ejemplo: {str(e)}")


def main():
    parser = argparse.ArgumentParser(
        description='Instalar sistema de conversaciones en la base de datos'
    )
    parser.add_argument(
        '--with-examples',
        action='store_true',
        help='Crear datos de ejemplo después de la instalación'
    )
    parser.add_argument(
        '--connection',
        type=str,
        help='Cadena de conexión personalizada (default: mysql+pymysql://root@localhost/myllm_projects_db)'
    )

    args = parser.parse_args()

    print("=" * 70)
    print("🚀 INSTALACIÓN SISTEMA DE CONVERSACIONES")
    print("=" * 70)

    # Obtener connection string
    conn_string = args.connection or get_db_connection_string()
    print(f"\n🔌 Conectando a: {conn_string.split('@')[1]}")

    try:
        engine = create_engine(conn_string, echo=False)

        # Test conexión
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("  ✓ Conexión exitosa\n")

        # Ejecutar DDL
        ddl_path = Path(__file__).parent / "infrastructure" / "database" / "migrations" / "007_conversaciones_sistema.sql"

        if not ddl_path.exists():
            print(f"❌ Error: No se encuentra el archivo DDL en {ddl_path}")
            sys.exit(1)

        ejecutar_ddl(engine, ddl_path)

        # Crear datos de ejemplo si se solicita
        if args.with_examples:
            crear_datos_ejemplo(engine)

        print("\n" + "=" * 70)
        print("✅ INSTALACIÓN COMPLETADA EXITOSAMENTE")
        print("=" * 70)
        print("\n📚 Próximos pasos:")
        print("  1. Verificar las tablas creadas en la base de datos")
        print("  2. Asignar usuarios internos a organizaciones")
        print("  3. Integrar el componente de notificaciones")
        print("\n💡 Consulta la documentación en docs/ para más información")

    except Exception as e:
        print(f"\n❌ Error durante la instalación: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
