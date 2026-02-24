"""
Test de conversación completa entre cliente (frontend) e interno (backoffice).
Simula el flujo completo de comunicación del sistema de conversaciones.
"""

import sys
from pathlib import Path

from sqlalchemy import text
from tests.helpers import get_db_engine, load_module_from_path

engine_core = get_db_engine(database="myllm_core_db")
engine_projects = get_db_engine(database="myllm_projects_db")
conversaciones_adapter = load_module_from_path(
    "conversaciones_adapter",
    "src/2_shared_application/adapters/conversaciones_adapter.py",
)

print("=" * 80)
print("TEST: Conversación completa Cliente ↔ Interno")
print("=" * 80)

# === DATOS DE PRUEBA ===
# Buscar un usuario cliente y uno interno de la BD
with engine_core.connect() as conn:
    # Usuario cliente (primer usuario activo de la organización 1)
    result = conn.execute(text("""
        SELECT user_id, user_name FROM users
        WHERE organization_id = 1 AND active = 1
        LIMIT 1
    """)).fetchone()

    if not result:
        print("❌ ERROR: No hay usuarios activos en la organización 1")
        sys.exit(1)

    id_usuario_cliente = result[0]
    nombre_cliente = result[1]
    print(f"\n👤 Cliente: {nombre_cliente} (ID: {id_usuario_cliente})")

    # Usuario interno (buscar un usuario del backoffice)
    result = conn.execute(text("""
        SELECT user_id, user_name FROM users
        WHERE user_name LIKE '%admin%' AND active = 1
        LIMIT 1
    """)).fetchone()

    if not result:
        print("❌ ERROR: No hay usuarios internos disponibles")
        sys.exit(1)

    id_usuario_interno = result[0]
    nombre_interno = result[1]
    print(f"🛡️  Interno: {nombre_interno} (ID: {id_usuario_interno})")

    # Verificar organización
    result = conn.execute(text("""
        SELECT organization_id, organization_name FROM organizations WHERE organization_id = 1
    """)).fetchone()

    if not result:
        print("❌ ERROR: No existe la organización 1")
        sys.exit(1)

    id_organizacion = result[0]
    nombre_org = result[1]
    print(f"🏢 Organización: {nombre_org} (ID: {id_organizacion})")

print("\n" + "=" * 80)
print("PASO 1: Cliente inicia conversación")
print("=" * 80)

try:
    # Buscar conversación existente o crear una nueva
    with engine_projects.connect() as conn:
        result = conn.execute(text("""
            SELECT id_conversacion
            FROM conversaciones
            WHERE id_organizacion = :org_id
              AND id_usuario_cliente = :user_id
              AND estado IN ('abierta', 'en_curso')
            ORDER BY fecha_ultima_actualizacion DESC
            LIMIT 1
        """), {"org_id": id_organizacion, "user_id": id_usuario_cliente}).fetchone()

        if result:
            id_conversacion = result[0]
            print(f"✅ Conversación existente encontrada (ID: {id_conversacion})")
        else:
            # Crear nueva conversación
            id_conversacion = conversaciones_adapter.crear_conversacion(
                engine=engine_projects,
                id_organizacion=id_organizacion,
                id_usuario_cliente=id_usuario_cliente,
                asunto="Soporte sobre proyectos",
                prioridad="media"
            )
            print(f"✅ Nueva conversación creada (ID: {id_conversacion})")

except Exception as e:
    print(f"❌ ERROR al crear/buscar conversación: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("PASO 2: Cliente envía mensaje 1")
print("=" * 80)

mensaje_cliente_1 = "Hola, necesito ayuda con mi proyecto. ¿Cómo puedo agregar un nuevo modelo?"

try:
    id_msg1 = conversaciones_adapter.enviar_mensaje(
        engine=engine_projects,
        id_conversacion=id_conversacion,
        id_usuario_emisor=id_usuario_cliente,
        tipo_emisor="cliente",
        texto_mensaje=mensaje_cliente_1
    )
    print(f"✅ Mensaje enviado (ID: {id_msg1})")
    print(f"   📝 Texto: '{mensaje_cliente_1}'")

    # Verificar que se guardó en la BD
    with engine_projects.connect() as conn:
        result = conn.execute(text("""
            SELECT texto_mensaje, tipo_emisor, fecha_envio
            FROM mensajes_conversacion
            WHERE id_mensaje = :msg_id
        """), {"msg_id": id_msg1}).fetchone()

        if result:
            print(f"   ✓ Verificado en BD: emisor={result[1]}, fecha={result[2]}")
        else:
            print("   ⚠️  No se encontró en la BD")

except Exception as e:
    print(f"❌ ERROR al enviar mensaje: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("PASO 3: Interno se une a la conversación")
print("=" * 80)

try:
    conversaciones_adapter.unirse_a_conversacion(
        engine=engine_projects,
        id_conversacion=id_conversacion,
        id_usuario_interno=id_usuario_interno
    )
    print(f"✅ Usuario interno '{nombre_interno}' se unió a la conversación")

    # Verificar participante
    with engine_projects.connect() as conn:
        result = conn.execute(text("""
            SELECT tipo_participante, activo
            FROM participantes_conversacion
            WHERE id_conversacion = :conv_id AND id_usuario = :user_id
        """), {"conv_id": id_conversacion, "user_id": id_usuario_interno}).fetchone()

        if result:
            print(f"   ✓ Participante registrado: tipo={result[0]}, activo={result[1]}")
        else:
            print("   ⚠️  No se encontró como participante")

except Exception as e:
    print(f"❌ ERROR al unirse a conversación: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("PASO 4: Interno responde al cliente")
print("=" * 80)

mensaje_interno_1 = "¡Hola! Para agregar un nuevo modelo, debes ir a la sección 'Modelos' y hacer clic en 'Crear Nuevo Modelo'. ¿Te ayudo con algo más?"

try:
    id_msg2 = conversaciones_adapter.enviar_mensaje(
        engine=engine_projects,
        id_conversacion=id_conversacion,
        id_usuario_emisor=id_usuario_interno,
        tipo_emisor="interno",
        texto_mensaje=mensaje_interno_1
    )
    print(f"✅ Mensaje enviado (ID: {id_msg2})")
    print(f"   📝 Texto: '{mensaje_interno_1}'")

    # Verificar que se guardó
    with engine_projects.connect() as conn:
        result = conn.execute(text("""
            SELECT texto_mensaje, tipo_emisor, fecha_envio
            FROM mensajes_conversacion
            WHERE id_mensaje = :msg_id
        """), {"msg_id": id_msg2}).fetchone()

        if result:
            print(f"   ✓ Verificado en BD: emisor={result[1]}, fecha={result[2]}")
        else:
            print("   ⚠️  No se encontró en la BD")

except Exception as e:
    print(f"❌ ERROR al enviar respuesta: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("PASO 5: Cliente envía segundo mensaje")
print("=" * 80)

mensaje_cliente_2 = "Perfecto, gracias. También quiero saber cómo exportar los resultados del entrenamiento."

try:
    id_msg3 = conversaciones_adapter.enviar_mensaje(
        engine=engine_projects,
        id_conversacion=id_conversacion,
        id_usuario_emisor=id_usuario_cliente,
        tipo_emisor="cliente",
        texto_mensaje=mensaje_cliente_2
    )
    print(f"✅ Mensaje enviado (ID: {id_msg3})")
    print(f"   📝 Texto: '{mensaje_cliente_2}'")

except Exception as e:
    print(f"❌ ERROR al enviar segundo mensaje: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("PASO 6: Interno responde con información")
print("=" * 80)

mensaje_interno_2 = "Para exportar los resultados, ve a la página del proyecto, selecciona la versión entrenada y haz clic en 'Descargar Resultados'. Se generará un archivo ZIP con todos los datos."

try:
    id_msg4 = conversaciones_adapter.enviar_mensaje(
        engine=engine_projects,
        id_conversacion=id_conversacion,
        id_usuario_emisor=id_usuario_interno,
        tipo_emisor="interno",
        texto_mensaje=mensaje_interno_2
    )
    print(f"✅ Mensaje enviado (ID: {id_msg4})")
    print(f"   📝 Texto: '{mensaje_interno_2}'")

except Exception as e:
    print(f"❌ ERROR al enviar respuesta final: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("PASO 7: Verificar conversación completa")
print("=" * 80)

try:
    mensajes = conversaciones_adapter.obtener_mensajes_conversacion(
        engine=engine_projects,
        id_conversacion=id_conversacion
    )

    print(f"\n✅ Total de mensajes en la conversación: {len(mensajes)}")
    print("\nConversación completa:")
    print("-" * 80)

    for i, msg in enumerate(mensajes, 1):
        emisor_icon = "👤" if msg["tipo_emisor"] == "cliente" else "🛡️"
        emisor_nombre = nombre_cliente if msg["tipo_emisor"] == "cliente" else nombre_interno
        fecha = msg["fecha_envio"].strftime("%Y-%m-%d %H:%M:%S") if msg["fecha_envio"] else "N/A"

        print(f"\n{i}. {emisor_icon} {emisor_nombre} ({msg['tipo_emisor']}) - {fecha}")
        print(f"   {msg['texto_mensaje']}")

    print("-" * 80)

except Exception as e:
    print(f"❌ ERROR al obtener mensajes: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("PASO 8: Verificar estado de la conversación")
print("=" * 80)

try:
    with engine_projects.connect() as conn:
        result = conn.execute(text("""
            SELECT
                estado,
                prioridad,
                total_mensajes,
                mensajes_sin_leer_cliente,
                mensajes_sin_leer_interno,
                ultimo_mensaje_texto,
                ultimo_mensaje_de,
                fecha_ultima_actualizacion
            FROM conversaciones
            WHERE id_conversacion = :conv_id
        """), {"conv_id": id_conversacion}).fetchone()

        if result:
            print(f"✅ Estado de la conversación:")
            print(f"   Estado: {result[0]}")
            print(f"   Prioridad: {result[1]}")
            print(f"   Total mensajes: {result[2]}")
            print(f"   Sin leer (cliente): {result[3]}")
            print(f"   Sin leer (interno): {result[4]}")
            print(f"   Último mensaje: '{result[5][:50]}...' ({result[6]})")
            print(f"   Última actualización: {result[7]}")
        else:
            print("   ⚠️  No se encontró la conversación")

except Exception as e:
    print(f"❌ ERROR al verificar estado: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("PASO 9: Marcar mensajes como leídos")
print("=" * 80)

try:
    # Cliente marca mensajes como leídos
    conversaciones_adapter.marcar_mensajes_como_leidos(
        engine=engine_projects,
        id_conversacion=id_conversacion,
        tipo_lector="cliente"
    )
    print("✅ Mensajes marcados como leídos por cliente")

    # Interno marca mensajes como leídos
    conversaciones_adapter.marcar_mensajes_como_leidos(
        engine=engine_projects,
        id_conversacion=id_conversacion,
        tipo_lector="interno"
    )
    print("✅ Mensajes marcados como leídos por interno")

    # Verificar contadores
    with engine_projects.connect() as conn:
        result = conn.execute(text("""
            SELECT mensajes_sin_leer_cliente, mensajes_sin_leer_interno
            FROM conversaciones
            WHERE id_conversacion = :conv_id
        """), {"conv_id": id_conversacion}).fetchone()

        if result:
            print(f"   ✓ Sin leer (cliente): {result[0]}")
            print(f"   ✓ Sin leer (interno): {result[1]}")
        else:
            print("   ⚠️  No se pudo verificar")

except Exception as e:
    print(f"❌ ERROR al marcar como leídos: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("✅ TEST COMPLETADO EXITOSAMENTE")
print("=" * 80)
print(f"\nConversación ID: {id_conversacion}")
print(f"Cliente: {nombre_cliente} (ID: {id_usuario_cliente})")
print(f"Interno: {nombre_interno} (ID: {id_usuario_interno})")
print(f"Mensajes intercambiados: 4")
print("\n" + "=" * 80)
