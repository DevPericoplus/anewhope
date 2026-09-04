"""
Tests de integración para conversaciones_adapter.

Estos tests verifican que las funciones del adapter trabajen correctamente
con las bases de datos myllm_core_db y myllm_projects_db.
"""

import pytest
from sqlalchemy import create_engine, text
from datetime import datetime

from tests.helpers import load_module_from_path, load_protected_values, get_db_engine

conversaciones_adapter = load_module_from_path(
    "conversaciones_adapter",
    "src/2_shared_application/adapters/conversaciones_adapter.py",
)


@pytest.fixture(scope="module")
def engine_core():
    """Engine para myllm_core_db (users, organizations)"""
    return get_db_engine(database="myllm_core_db")


@pytest.fixture(scope="module")
def engine_projects():
    """Engine para myllm_projects_db (conversaciones, tickets)"""
    return get_db_engine(database="myllm_projects_db")


@pytest.fixture(scope="function")
def setup_test_data(engine_core, engine_projects):
    """Prepara datos de prueba y limpia después."""
    # Setup: Crear datos de prueba
    test_data = {}

    with engine_core.connect() as conn:
        result = conn.execute(text("SELECT user_id FROM users LIMIT 1"))
        test_data['user_id'] = result.fetchone()[0]

        result = conn.execute(text("SELECT organization_id FROM organizations LIMIT 1"))
        test_data['org_id'] = result.fetchone()[0]

    with engine_projects.connect() as conn:
        result = conn.execute(text("SELECT id FROM tickets LIMIT 1"))
        row = result.fetchone()
        test_data['ticket_id'] = row[0] if row else None

    yield test_data

    # Teardown: Limpiar datos de prueba
    with engine_projects.connect() as conn:
        # Borrar conversaciones de prueba creadas en los tests
        conn.execute(text("""
            DELETE FROM conversaciones
            WHERE asunto LIKE 'TEST:%'
        """))
        conn.commit()


TEST_ASIGNACION_ROL = 5


def _ensure_test_asignacion(
    engine_projects,
    user_id: int,
    org_id: int,
    id_rol: int = TEST_ASIGNACION_ROL,
) -> int:
    """Reutiliza o crea una asignación de prueba (evita unique_asignacion)."""
    with engine_projects.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT id FROM asignaciones_organizaciones_internas
                WHERE id_usuario_interno = :user_id
                  AND id_organizacion = :org_id
                  AND id_rol = :id_rol
                """
            ),
            {"user_id": user_id, "org_id": org_id, "id_rol": id_rol},
        ).fetchone()
        if row:
            return int(row[0])
    return conversaciones_adapter.crear_asignacion_interna(
        engine=engine_projects,
        id_usuario_interno=user_id,
        id_organizacion=org_id,
        id_rol=id_rol,
        asignado_por=user_id,
        notas="TEST: Asignación de prueba",
    )


class TestAsignacionesInternas:
    """Tests para asignaciones de usuarios internos a organizaciones."""

    def test_crear_asignacion_interna(self, engine_projects, setup_test_data):
        """Verifica que se puede crear una asignación interna."""
        user_id = setup_test_data['user_id']
        org_id = setup_test_data['org_id']

        id_asignacion = _ensure_test_asignacion(
            engine_projects, user_id, org_id, id_rol=5
        )

        assert id_asignacion > 0, "Debería retornar un ID válido"

        # Verificar que se creó correctamente
        with engine_projects.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM asignaciones_organizaciones_internas WHERE id = :id"),
                {"id": id_asignacion}
            )
            row = result.fetchone()

            assert row is not None
            assert row[1] == user_id  # id_usuario_interno
            assert row[2] == org_id   # id_organizacion
            assert row[3] == TEST_ASIGNACION_ROL
            assert row[5] == True     # activo

        # Cleanup
        with engine_projects.connect() as conn:
            conn.execute(
                text("DELETE FROM asignaciones_organizaciones_internas WHERE id = :id"),
                {"id": id_asignacion}
            )
            conn.commit()

    def test_obtener_organizaciones_asignadas(self, engine_projects, setup_test_data):
        """Verifica que se pueden obtener las organizaciones asignadas."""
        user_id = setup_test_data['user_id']
        org_id = setup_test_data['org_id']

        # Crear asignación temporal
        id_asignacion = _ensure_test_asignacion(engine_projects, user_id, org_id)

        # Obtener asignaciones
        organizaciones = conversaciones_adapter.obtener_organizaciones_asignadas(
            engine=engine_projects,
            id_usuario_interno=user_id
        )

        assert len(organizaciones) > 0, "Debería tener al menos una organización asignada"
        assert any(o['id'] == org_id for o in organizaciones)

        # Cleanup
        with engine_projects.connect() as conn:
            conn.execute(
                text("DELETE FROM asignaciones_organizaciones_internas WHERE id = :id"),
                {"id": id_asignacion}
            )
            conn.commit()

    def test_desactivar_asignacion(self, engine_projects, setup_test_data):
        """Verifica que se puede desactivar una asignación."""
        user_id = setup_test_data['user_id']
        org_id = setup_test_data['org_id']

        # Crear asignación
        id_asignacion = _ensure_test_asignacion(engine_projects, user_id, org_id)

        # Desactivar
        result = conversaciones_adapter.desactivar_asignacion_interna(
            engine=engine_projects,
            id_asignacion=id_asignacion,
            desactivado_por=user_id
        )

        assert result == True

        # Verificar que está desactivada
        with engine_projects.connect() as conn:
            result = conn.execute(
                text("SELECT activo FROM asignaciones_organizaciones_internas WHERE id = :id"),
                {"id": id_asignacion}
            )
            row = result.fetchone()
            assert row[0] == False  # activo = False

        # Cleanup
        with engine_projects.connect() as conn:
            conn.execute(
                text("DELETE FROM asignaciones_organizaciones_internas WHERE id = :id"),
                {"id": id_asignacion}
            )
            conn.commit()


class TestConversaciones:
    """Tests para gestión de conversaciones."""

    def test_crear_conversacion(self, engine_projects, setup_test_data):
        """Verifica que se puede crear una conversación."""
        user_id = setup_test_data['user_id']
        org_id = setup_test_data['org_id']

        id_conv = conversaciones_adapter.crear_conversacion(
            engine=engine_projects,
            id_organizacion=org_id,
            id_usuario_cliente=user_id,
            asunto="TEST: Conversación de prueba",
            prioridad="alta"
        )

        assert id_conv > 0

        # Verificar que se creó
        with engine_projects.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM conversaciones WHERE id_conversacion = :id"),
                {"id": id_conv}
            )
            row = result.fetchone()

            assert row is not None
            assert row[1] == org_id
            assert row[2] == user_id
            assert row[4] == "TEST: Conversación de prueba"
            assert row[6] == "alta"

    def test_crear_conversacion_con_ticket(self, engine_projects, setup_test_data):
        """Verifica que se puede crear conversación con ticket principal."""
        user_id = setup_test_data['user_id']
        org_id = setup_test_data['org_id']
        ticket_id = setup_test_data['ticket_id']

        if not ticket_id:
            pytest.skip("No hay tickets en la base de datos")

        id_conv = conversaciones_adapter.crear_conversacion(
            engine=engine_projects,
            id_organizacion=org_id,
            id_usuario_cliente=user_id,
            asunto="TEST: Conversación con ticket",
            id_ticket_principal=ticket_id
        )

        assert id_conv > 0

        # Verificar relación con ticket
        with engine_projects.connect() as conn:
            result = conn.execute(
                text("""SELECT * FROM conversaciones_tickets_relacionados
                        WHERE id_conversacion = :id AND id_ticket = :ticket_id"""),
                {"id": id_conv, "ticket_id": ticket_id}
            )
            row = result.fetchone()
            assert row is not None
            assert row[3] == "principal"  # tipo_relacion

    def test_obtener_conversaciones_cliente(self, engine_projects, setup_test_data):
        """Verifica que se pueden obtener conversaciones de un cliente."""
        user_id = setup_test_data['user_id']
        org_id = setup_test_data['org_id']

        # Crear conversación
        id_conv = conversaciones_adapter.crear_conversacion(
            engine=engine_projects,
            id_organizacion=org_id,
            id_usuario_cliente=user_id,
            asunto="TEST: Obtener conversaciones"
        )

        # Obtener conversaciones
        conversaciones = conversaciones_adapter.obtener_conversaciones_cliente(
            engine=engine_projects,
            id_usuario_cliente=user_id,
            id_organizacion=org_id,
            solo_activas=True
        )

        assert len(conversaciones) > 0
        assert any(c['id_conversacion'] == id_conv for c in conversaciones)

    def test_obtener_conversaciones_organizacion(self, engine_projects, setup_test_data):
        """Verifica que se pueden obtener todas las conversaciones de una org."""
        user_id = setup_test_data['user_id']
        org_id = setup_test_data['org_id']

        # Crear conversación
        id_conv = conversaciones_adapter.crear_conversacion(
            engine=engine_projects,
            id_organizacion=org_id,
            id_usuario_cliente=user_id,
            asunto="TEST: Conversaciones org"
        )

        # Obtener conversaciones de la organización
        conversaciones = conversaciones_adapter.obtener_conversaciones_organizacion(
            engine=engine_projects,
            id_organizacion=org_id,
            solo_activas=True
        )

        assert len(conversaciones) > 0
        assert any(c['id_conversacion'] == id_conv for c in conversaciones)

    def test_unirse_a_conversacion(self, engine_projects, setup_test_data):
        """Verifica que un usuario interno puede unirse a una conversación."""
        user_id = setup_test_data['user_id']
        org_id = setup_test_data['org_id']

        # Crear conversación
        id_conv = conversaciones_adapter.crear_conversacion(
            engine=engine_projects,
            id_organizacion=org_id,
            id_usuario_cliente=user_id,
            asunto="TEST: Unirse a conversación"
        )

        interno_id = 57 if user_id != 57 else user_id + 1
        result = conversaciones_adapter.unirse_a_conversacion(
            engine=engine_projects,
            id_conversacion=id_conv,
            id_usuario_interno=interno_id
        )

        assert result == True

        # Verificar que está en participantes
        with engine_projects.connect() as conn:
            result = conn.execute(
                text("""SELECT * FROM participantes_conversacion
                        WHERE id_conversacion = :id_conv AND id_usuario = :user_id
                        AND tipo_participante = 'interno'"""),
                {"id_conv": id_conv, "user_id": interno_id}
            )
            row = result.fetchone()
            assert row is not None

    def test_cerrar_conversacion(self, engine_projects, setup_test_data):
        """Verifica que se puede cerrar una conversación."""
        user_id = setup_test_data['user_id']
        org_id = setup_test_data['org_id']

        # Crear conversación
        id_conv = conversaciones_adapter.crear_conversacion(
            engine=engine_projects,
            id_organizacion=org_id,
            id_usuario_cliente=user_id,
            asunto="TEST: Cerrar conversación"
        )

        # Cerrar
        result = conversaciones_adapter.cerrar_conversacion(
            engine=engine_projects,
            id_conversacion=id_conv,
            cerrada_por=user_id,
            estado_final="cerrada"
        )

        assert result == True

        # Verificar estado
        with engine_projects.connect() as conn:
            result = conn.execute(
                text("SELECT estado, cerrada_por FROM conversaciones WHERE id_conversacion = :id"),
                {"id": id_conv}
            )
            row = result.fetchone()
            assert row[0] == "cerrada"
            assert row[1] == user_id


class TestMensajes:
    """Tests para gestión de mensajes."""

    def test_enviar_mensaje(self, engine_projects, setup_test_data):
        """Verifica que se puede enviar un mensaje."""
        user_id = setup_test_data['user_id']
        org_id = setup_test_data['org_id']

        # Crear conversación
        id_conv = conversaciones_adapter.crear_conversacion(
            engine=engine_projects,
            id_organizacion=org_id,
            id_usuario_cliente=user_id,
            asunto="TEST: Enviar mensaje"
        )

        # Enviar mensaje
        id_mensaje = conversaciones_adapter.enviar_mensaje(
            engine=engine_projects,
            id_conversacion=id_conv,
            id_usuario_emisor=user_id,
            tipo_emisor="cliente",
            texto_mensaje="TEST: Este es un mensaje de prueba"
        )

        assert id_mensaje > 0

        # Verificar que se creó
        with engine_projects.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM mensajes_conversacion WHERE id_mensaje = :id"),
                {"id": id_mensaje}
            )
            row = result.fetchone()
            assert row is not None
            assert row[5] == "TEST: Este es un mensaje de prueba"

        # Verificar que el trigger actualizó la conversación
        with engine_projects.connect() as conn:
            result = conn.execute(
                text("SELECT total_mensajes, ultimo_mensaje_texto FROM conversaciones WHERE id_conversacion = :id"),
                {"id": id_conv}
            )
            row = result.fetchone()
            assert row[0] == 1  # total_mensajes
            assert "TEST: Este es un mensaje de prueba" in row[1]  # ultimo_mensaje_texto

    def test_enviar_mensaje_con_ticket(self, engine_projects, setup_test_data):
        """Verifica que se puede enviar mensaje referenciando un ticket."""
        user_id = setup_test_data['user_id']
        org_id = setup_test_data['org_id']
        ticket_id = setup_test_data['ticket_id']

        if not ticket_id:
            pytest.skip("No hay tickets en la base de datos")

        # Crear conversación
        id_conv = conversaciones_adapter.crear_conversacion(
            engine=engine_projects,
            id_organizacion=org_id,
            id_usuario_cliente=user_id,
            asunto="TEST: Mensaje con ticket"
        )

        # Enviar mensaje referenciando ticket
        id_mensaje = conversaciones_adapter.enviar_mensaje(
            engine=engine_projects,
            id_conversacion=id_conv,
            id_usuario_emisor=user_id,
            tipo_emisor="interno",
            texto_mensaje="TEST: Mensaje relacionado con ticket",
            id_ticket_referenciado=ticket_id
        )

        assert id_mensaje > 0

        # Verificar que se creó la relación automáticamente (trigger)
        with engine_projects.connect() as conn:
            result = conn.execute(
                text("""SELECT * FROM conversaciones_tickets_relacionados
                        WHERE id_conversacion = :id_conv AND id_ticket = :ticket_id"""),
                {"id_conv": id_conv, "ticket_id": ticket_id}
            )
            row = result.fetchone()
            assert row is not None
            assert row[3] == "mencionado"

    def test_obtener_mensajes_conversacion(self, engine_projects, setup_test_data):
        """Verifica que se pueden obtener todos los mensajes de una conversación."""
        user_id = setup_test_data['user_id']
        org_id = setup_test_data['org_id']

        # Crear conversación
        id_conv = conversaciones_adapter.crear_conversacion(
            engine=engine_projects,
            id_organizacion=org_id,
            id_usuario_cliente=user_id,
            asunto="TEST: Obtener mensajes"
        )

        # Enviar varios mensajes
        conversaciones_adapter.enviar_mensaje(
            engine=engine_projects,
            id_conversacion=id_conv,
            id_usuario_emisor=user_id,
            tipo_emisor="cliente",
            texto_mensaje="TEST: Mensaje 1"
        )
        conversaciones_adapter.enviar_mensaje(
            engine=engine_projects,
            id_conversacion=id_conv,
            id_usuario_emisor=user_id,
            tipo_emisor="interno",
            texto_mensaje="TEST: Mensaje 2"
        )

        # Obtener mensajes
        mensajes = conversaciones_adapter.obtener_mensajes_conversacion(
            engine=engine_projects,
            id_conversacion=id_conv
        )

        assert len(mensajes) == 2
        assert mensajes[0]['texto_mensaje'] == "TEST: Mensaje 1"
        assert mensajes[1]['texto_mensaje'] == "TEST: Mensaje 2"

    def test_marcar_mensajes_como_leidos(self, engine_projects, setup_test_data):
        """Verifica que se pueden marcar mensajes como leídos."""
        user_id = setup_test_data['user_id']
        org_id = setup_test_data['org_id']

        # Crear conversación
        id_conv = conversaciones_adapter.crear_conversacion(
            engine=engine_projects,
            id_organizacion=org_id,
            id_usuario_cliente=user_id,
            asunto="TEST: Marcar leídos"
        )

        # Enviar mensaje de interno
        conversaciones_adapter.enviar_mensaje(
            engine=engine_projects,
            id_conversacion=id_conv,
            id_usuario_emisor=user_id,
            tipo_emisor="interno",
            texto_mensaje="TEST: Mensaje para leer"
        )

        # Verificar contador antes
        with engine_projects.connect() as conn:
            result = conn.execute(
                text("SELECT mensajes_sin_leer_cliente FROM conversaciones WHERE id_conversacion = :id"),
                {"id": id_conv}
            )
            count_before = result.fetchone()[0]

        # Marcar como leídos
        conversaciones_adapter.marcar_mensajes_como_leidos(
            engine=engine_projects,
            id_conversacion=id_conv,
            tipo_lector="cliente"
        )

        # Verificar contador después (trigger debería decrementar)
        with engine_projects.connect() as conn:
            result = conn.execute(
                text("SELECT mensajes_sin_leer_cliente FROM conversaciones WHERE id_conversacion = :id"),
                {"id": id_conv}
            )
            count_after = result.fetchone()[0]

        assert count_after < count_before


class TestTicketsRelacionados:
    """Tests para gestión de tickets relacionados."""

    def test_obtener_tickets_conversacion(self, engine_projects, setup_test_data):
        """Verifica que se pueden obtener los tickets de una conversación."""
        user_id = setup_test_data['user_id']
        org_id = setup_test_data['org_id']
        ticket_id = setup_test_data['ticket_id']

        if not ticket_id:
            pytest.skip("No hay tickets en la base de datos")

        # Crear conversación con ticket principal
        id_conv = conversaciones_adapter.crear_conversacion(
            engine=engine_projects,
            id_organizacion=org_id,
            id_usuario_cliente=user_id,
            asunto="TEST: Tickets relacionados",
            id_ticket_principal=ticket_id
        )

        # Obtener tickets
        tickets = conversaciones_adapter.obtener_tickets_conversacion(
            engine=engine_projects,
            id_conversacion=id_conv
        )

        assert len(tickets) > 0
        assert any(t['id'] == ticket_id for t in tickets)
        assert any(t['tipo_relacion'] == 'principal' for t in tickets)

    def test_obtener_tickets_disponibles(self, engine_projects, setup_test_data):
        """Verifica que se pueden obtener tickets disponibles para referenciar."""
        org_id = setup_test_data['org_id']

        tickets = conversaciones_adapter.obtener_tickets_disponibles_organizacion(
            engine=engine_projects,
            id_organizacion=org_id
        )

        # Puede estar vacío si no hay tickets activos
        assert isinstance(tickets, list)


class TestEstadisticas:
    """Tests para reportes y estadísticas."""

    def test_obtener_estadisticas_organizacion(self, engine_projects, setup_test_data):
        """Verifica que se pueden obtener estadísticas de una organización."""
        user_id = setup_test_data['user_id']
        org_id = setup_test_data['org_id']

        # Crear conversación
        conversaciones_adapter.crear_conversacion(
            engine=engine_projects,
            id_organizacion=org_id,
            id_usuario_cliente=user_id,
            asunto="TEST: Estadísticas"
        )

        # Obtener estadísticas
        stats = conversaciones_adapter.obtener_estadisticas_conversaciones_organizacion(
            engine=engine_projects,
            id_organizacion=org_id
        )

        assert 'total_conversaciones' in stats
        assert 'abiertas' in stats
        assert stats['total_conversaciones'] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
