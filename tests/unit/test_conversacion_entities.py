"""
Tests unitarios para las entidades de dominio de conversaciones.

Estos tests no requieren base de datos, solo verifican la lógica de negocio
en las entidades del dominio.
"""

import pytest
from datetime import datetime, timedelta

from tests.helpers import load_module_from_path

_mod = load_module_from_path("conversacion", "src/1_shared_domain/conversacion.py")
Conversacion = _mod.Conversacion
MensajeConversacion = _mod.MensajeConversacion
ParticipanteConversacion = _mod.ParticipanteConversacion
AsignacionOrganizacionInterna = _mod.AsignacionOrganizacionInterna
EstadoConversacion = _mod.EstadoConversacion
PrioridadConversacion = _mod.PrioridadConversacion
TipoParticipante = _mod.TipoParticipante
TipoRelacionTicket = _mod.TipoRelacionTicket


class TestConversacionEntity:
    """Tests para la entidad Conversacion."""

    def test_crear_conversacion_basica(self):
        """Verifica que se puede crear una conversación con valores por defecto."""
        conv = Conversacion(
            id_organizacion=1,
            id_usuario_cliente=2,
            asunto="Consulta sobre proyecto"
        )

        assert conv.id_organizacion == 1
        assert conv.id_usuario_cliente == 2
        assert conv.asunto == "Consulta sobre proyecto"
        assert conv.estado == EstadoConversacion.ABIERTA
        assert conv.prioridad == PrioridadConversacion.MEDIA
        assert conv.total_mensajes == 0
        assert conv.mensajes_sin_leer_cliente == 0
        assert conv.mensajes_sin_leer_interno == 0

    def test_conversacion_esta_activa(self):
        """Verifica el método esta_activa()."""
        conv_abierta = Conversacion(
            id_organizacion=1,
            id_usuario_cliente=2,
            estado=EstadoConversacion.ABIERTA
        )
        conv_curso = Conversacion(
            id_organizacion=1,
            id_usuario_cliente=2,
            estado=EstadoConversacion.EN_CURSO
        )
        conv_cerrada = Conversacion(
            id_organizacion=1,
            id_usuario_cliente=2,
            estado=EstadoConversacion.CERRADA
        )

        assert conv_abierta.esta_activa() == True
        assert conv_curso.esta_activa() == True
        assert conv_cerrada.esta_activa() == False

    def test_conversacion_es_urgente(self):
        """Verifica el método es_urgente()."""
        conv_urgente = Conversacion(
            id_organizacion=1,
            id_usuario_cliente=2,
            prioridad=PrioridadConversacion.URGENTE
        )
        conv_normal = Conversacion(
            id_organizacion=1,
            id_usuario_cliente=2,
            prioridad=PrioridadConversacion.MEDIA
        )

        assert conv_urgente.es_urgente() == True
        assert conv_normal.es_urgente() == False

    def test_conversacion_tiene_mensajes_sin_leer(self):
        """Verifica los métodos de mensajes sin leer."""
        conv = Conversacion(
            id_organizacion=1,
            id_usuario_cliente=2,
            mensajes_sin_leer_cliente=3,
            mensajes_sin_leer_interno=0
        )

        assert conv.tiene_mensajes_sin_leer_para_cliente() == True
        assert conv.tiene_mensajes_sin_leer_para_interno() == False

    def test_conversacion_cambiar_estado(self):
        """Verifica el método cambiar_estado()."""
        conv = Conversacion(
            id_organizacion=1,
            id_usuario_cliente=2,
            estado=EstadoConversacion.ABIERTA
        )

        conv.cambiar_estado(EstadoConversacion.EN_CURSO)
        assert conv.estado == EstadoConversacion.EN_CURSO
        assert conv.fecha_cierre is None
        assert conv.cerrada_por is None

        conv.cambiar_estado(EstadoConversacion.CERRADA, usuario_id=5)
        assert conv.estado == EstadoConversacion.CERRADA
        assert conv.fecha_cierre is not None
        assert conv.cerrada_por == 5

    def test_conversacion_to_dict(self):
        """Verifica la serialización a diccionario."""
        conv = Conversacion(
            id_conversacion=123,
            id_organizacion=1,
            id_usuario_cliente=2,
            asunto="Test",
            estado=EstadoConversacion.ABIERTA,
            prioridad=PrioridadConversacion.ALTA
        )

        data = conv.to_dict()

        assert data['id_conversacion'] == 123
        assert data['id_organizacion'] == 1
        assert data['id_usuario_cliente'] == 2
        assert data['asunto'] == "Test"
        assert data['estado'] == "abierta"
        assert data['prioridad'] == "alta"

    def test_conversacion_from_dict(self):
        """Verifica la deserialización desde diccionario."""
        data = {
            "id_conversacion": 123,
            "id_organizacion": 1,
            "id_usuario_cliente": 2,
            "asunto": "Test",
            "estado": "en_curso",
            "prioridad": "urgente",
            "total_mensajes": 5
        }

        conv = Conversacion.from_dict(data)

        assert conv.id_conversacion == 123
        assert conv.estado == EstadoConversacion.EN_CURSO
        assert conv.prioridad == PrioridadConversacion.URGENTE
        assert conv.total_mensajes == 5


class TestMensajeConversacionEntity:
    """Tests para la entidad MensajeConversacion."""

    def test_crear_mensaje_basico(self):
        """Verifica que se puede crear un mensaje."""
        msg = MensajeConversacion(
            id_conversacion=1,
            id_usuario_emisor=2,
            tipo_emisor=TipoParticipante.CLIENTE,
            texto_mensaje="Hola, necesito ayuda"
        )

        assert msg.id_conversacion == 1
        assert msg.id_usuario_emisor == 2
        assert msg.tipo_emisor == TipoParticipante.CLIENTE
        assert msg.texto_mensaje == "Hola, necesito ayuda"
        assert msg.leido_por_cliente == False
        assert msg.leido_por_interno == False
        assert msg.editado == False

    def test_mensaje_es_de_cliente(self):
        """Verifica el método es_de_cliente()."""
        msg_cliente = MensajeConversacion(
            id_conversacion=1,
            id_usuario_emisor=2,
            tipo_emisor=TipoParticipante.CLIENTE,
            texto_mensaje="Test"
        )
        msg_interno = MensajeConversacion(
            id_conversacion=1,
            id_usuario_emisor=3,
            tipo_emisor=TipoParticipante.INTERNO,
            texto_mensaje="Test"
        )

        assert msg_cliente.es_de_cliente() == True
        assert msg_cliente.es_de_interno() == False
        assert msg_interno.es_de_cliente() == False
        assert msg_interno.es_de_interno() == True

    def test_mensaje_tiene_ticket_referenciado(self):
        """Verifica el método tiene_ticket_referenciado()."""
        msg_sin_ticket = MensajeConversacion(
            id_conversacion=1,
            id_usuario_emisor=2,
            tipo_emisor=TipoParticipante.INTERNO,
            texto_mensaje="Respuesta general"
        )
        msg_con_ticket = MensajeConversacion(
            id_conversacion=1,
            id_usuario_emisor=2,
            tipo_emisor=TipoParticipante.INTERNO,
            texto_mensaje="Relacionado con tu ticket",
            id_ticket_referenciado=456
        )

        assert msg_sin_ticket.tiene_ticket_referenciado() == False
        assert msg_con_ticket.tiene_ticket_referenciado() == True

    def test_mensaje_marcar_como_leido(self):
        """Verifica los métodos de marcar como leído."""
        msg = MensajeConversacion(
            id_conversacion=1,
            id_usuario_emisor=2,
            tipo_emisor=TipoParticipante.INTERNO,
            texto_mensaje="Test"
        )

        assert msg.leido_por_cliente == False
        assert msg.fecha_lectura_cliente is None

        msg.marcar_como_leido_por_cliente()

        assert msg.leido_por_cliente == True
        assert msg.fecha_lectura_cliente is not None

        # Marcar por interno
        msg.marcar_como_leido_por_interno()

        assert msg.leido_por_interno == True
        assert msg.fecha_lectura_interno is not None

    def test_mensaje_editar(self):
        """Verifica el método editar()."""
        msg = MensajeConversacion(
            id_conversacion=1,
            id_usuario_emisor=2,
            tipo_emisor=TipoParticipante.CLIENTE,
            texto_mensaje="Texto original"
        )

        assert msg.editado == False
        assert msg.fecha_edicion is None

        msg.editar("Texto editado", editado_por=2)

        assert msg.texto_mensaje == "Texto editado"
        assert msg.editado == True
        assert msg.fecha_edicion is not None
        assert msg.editado_por == 2

    def test_mensaje_to_dict(self):
        """Verifica la serialización a diccionario."""
        msg = MensajeConversacion(
            id_mensaje=789,
            id_conversacion=1,
            id_usuario_emisor=2,
            tipo_emisor=TipoParticipante.CLIENTE,
            texto_mensaje="Test",
            leido_por_cliente=True
        )

        data = msg.to_dict()

        assert data['id_mensaje'] == 789
        assert data['tipo_emisor'] == "cliente"
        assert data['texto_mensaje'] == "Test"
        assert data['leido_por_cliente'] == True

    def test_mensaje_from_dict(self):
        """Verifica la deserialización desde diccionario."""
        data = {
            "id_mensaje": 789,
            "id_conversacion": 1,
            "id_usuario_emisor": 2,
            "tipo_emisor": "interno",
            "texto_mensaje": "Test",
            "id_ticket_referenciado": 456,
            "leido_por_interno": True
        }

        msg = MensajeConversacion.from_dict(data)

        assert msg.id_mensaje == 789
        assert msg.tipo_emisor == TipoParticipante.INTERNO
        assert msg.id_ticket_referenciado == 456
        assert msg.leido_por_interno == True


class TestParticipanteConversacionEntity:
    """Tests para la entidad ParticipanteConversacion."""

    def test_crear_participante(self):
        """Verifica que se puede crear un participante."""
        part = ParticipanteConversacion(
            id_conversacion=1,
            id_usuario=2,
            tipo_participante=TipoParticipante.CLIENTE
        )

        assert part.id_conversacion == 1
        assert part.id_usuario == 2
        assert part.tipo_participante == TipoParticipante.CLIENTE
        assert part.activo == True
        assert part.notificaciones_activadas == True

    def test_participante_es_cliente(self):
        """Verifica los métodos es_cliente() e es_interno()."""
        part_cliente = ParticipanteConversacion(
            id_conversacion=1,
            id_usuario=2,
            tipo_participante=TipoParticipante.CLIENTE
        )
        part_interno = ParticipanteConversacion(
            id_conversacion=1,
            id_usuario=3,
            tipo_participante=TipoParticipante.INTERNO
        )

        assert part_cliente.es_cliente() == True
        assert part_cliente.es_interno() == False
        assert part_interno.es_cliente() == False
        assert part_interno.es_interno() == True

    def test_participante_actualizar_ultimo_acceso(self):
        """Verifica el método actualizar_ultimo_acceso()."""
        part = ParticipanteConversacion(
            id_conversacion=1,
            id_usuario=2,
            tipo_participante=TipoParticipante.INTERNO
        )

        assert part.ultimo_acceso is None

        part.actualizar_ultimo_acceso()

        assert part.ultimo_acceso is not None

    def test_participante_desactivar_activar(self):
        """Verifica los métodos desactivar() y activar()."""
        part = ParticipanteConversacion(
            id_conversacion=1,
            id_usuario=2,
            tipo_participante=TipoParticipante.INTERNO
        )

        assert part.activo == True

        part.desactivar()
        assert part.activo == False

        part.activar()
        assert part.activo == True

    def test_participante_to_dict(self):
        """Verifica la serialización a diccionario."""
        part = ParticipanteConversacion(
            id_participante=456,
            id_conversacion=1,
            id_usuario=2,
            tipo_participante=TipoParticipante.INTERNO,
            activo=True
        )

        data = part.to_dict()

        assert data['id_participante'] == 456
        assert data['tipo_participante'] == "interno"
        assert data['activo'] == True


class TestAsignacionOrganizacionInternaEntity:
    """Tests para la entidad AsignacionOrganizacionInterna."""

    def test_crear_asignacion(self):
        """Verifica que se puede crear una asignación."""
        asig = AsignacionOrganizacionInterna(
            id_usuario_interno=1,
            id_organizacion=2,
            id_rol=3,
            asignado_por=1,
            notas="Asignación inicial"
        )

        assert asig.id_usuario_interno == 1
        assert asig.id_organizacion == 2
        assert asig.id_rol == 3
        assert asig.asignado_por == 1
        assert asig.activo == True
        assert asig.notas == "Asignación inicial"

    def test_asignacion_desactivar(self):
        """Verifica el método desactivar()."""
        asig = AsignacionOrganizacionInterna(
            id_usuario_interno=1,
            id_organizacion=2,
            id_rol=3,
            asignado_por=1
        )

        assert asig.activo == True
        assert asig.fecha_desactivacion is None

        asig.desactivar(usuario_id=5)

        assert asig.activo == False
        assert asig.fecha_desactivacion is not None
        assert asig.desactivado_por == 5

    def test_asignacion_reactivar(self):
        """Verifica el método reactivar()."""
        asig = AsignacionOrganizacionInterna(
            id_usuario_interno=1,
            id_organizacion=2,
            id_rol=3,
            asignado_por=1
        )

        # Desactivar primero
        asig.desactivar(usuario_id=5)
        assert asig.activo == False

        # Reactivar
        asig.reactivar()

        assert asig.activo == True
        assert asig.fecha_desactivacion is None
        assert asig.desactivado_por is None

    def test_asignacion_to_dict(self):
        """Verifica la serialización a diccionario."""
        asig = AsignacionOrganizacionInterna(
            id_asignacion=123,
            id_usuario_interno=1,
            id_organizacion=2,
            id_rol=3,
            asignado_por=1,
            activo=True
        )

        data = asig.to_dict()

        assert data['id_asignacion'] == 123
        assert data['id_usuario_interno'] == 1
        assert data['id_organizacion'] == 2
        assert data['activo'] == True


class TestEnums:
    """Tests para los enums."""

    def test_estado_conversacion_enum(self):
        """Verifica que el enum EstadoConversacion funciona."""
        assert EstadoConversacion.ABIERTA.value == "abierta"
        assert EstadoConversacion.EN_CURSO.value == "en_curso"
        assert EstadoConversacion.RESUELTA.value == "resuelta"
        assert EstadoConversacion.CERRADA.value == "cerrada"

    def test_prioridad_conversacion_enum(self):
        """Verifica que el enum PrioridadConversacion funciona."""
        assert PrioridadConversacion.BAJA.value == "baja"
        assert PrioridadConversacion.MEDIA.value == "media"
        assert PrioridadConversacion.ALTA.value == "alta"
        assert PrioridadConversacion.URGENTE.value == "urgente"

    def test_tipo_participante_enum(self):
        """Verifica que el enum TipoParticipante funciona."""
        assert TipoParticipante.CLIENTE.value == "cliente"
        assert TipoParticipante.INTERNO.value == "interno"

    def test_tipo_relacion_ticket_enum(self):
        """Verifica que el enum TipoRelacionTicket funciona."""
        assert TipoRelacionTicket.PRINCIPAL.value == "principal"
        assert TipoRelacionTicket.SECUNDARIO.value == "secundario"
        assert TipoRelacionTicket.MENCIONADO.value == "mencionado"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
