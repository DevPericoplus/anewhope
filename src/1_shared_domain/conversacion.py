"""
Entidades de dominio para el sistema de conversaciones.

Estas entidades representan el núcleo del dominio de negocio
para las conversaciones entre clientes e internos.
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum


class EstadoConversacion(str, Enum):
    """Estados posibles de una conversación."""
    ABIERTA = "abierta"
    EN_CURSO = "en_curso"
    RESUELTA = "resuelta"
    CERRADA = "cerrada"


class PrioridadConversacion(str, Enum):
    """Niveles de prioridad de una conversación."""
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    URGENTE = "urgente"


class TipoParticipante(str, Enum):
    """Tipo de participante en una conversación."""
    CLIENTE = "cliente"
    INTERNO = "interno"


class TipoRelacionTicket(str, Enum):
    """Tipo de relación entre conversación y ticket."""
    PRINCIPAL = "principal"
    SECUNDARIO = "secundario"
    MENCIONADO = "mencionado"


class Conversacion:
    """
    Entidad principal que representa una conversación.

    Una conversación es el hilo de comunicación entre un usuario cliente
    y uno o más usuarios internos de la organización.
    """

    def __init__(
        self,
        id_conversacion: Optional[int] = None,
        id_organizacion: int = None,
        id_usuario_cliente: int = None,
        id_ticket_principal: Optional[int] = None,
        asunto: Optional[str] = None,
        estado: EstadoConversacion = EstadoConversacion.ABIERTA,
        prioridad: PrioridadConversacion = PrioridadConversacion.MEDIA,
        fecha_creacion: Optional[datetime] = None,
        fecha_ultima_actualizacion: Optional[datetime] = None,
        ultimo_mensaje_texto: Optional[str] = None,
        ultimo_mensaje_de: Optional[TipoParticipante] = None,
        ultimo_mensaje_fecha: Optional[datetime] = None,
        mensajes_sin_leer_cliente: int = 0,
        mensajes_sin_leer_interno: int = 0,
        total_mensajes: int = 0,
        cerrada_por: Optional[int] = None,
        fecha_cierre: Optional[datetime] = None
    ):
        self.id_conversacion = id_conversacion
        self.id_organizacion = id_organizacion
        self.id_usuario_cliente = id_usuario_cliente
        self.id_ticket_principal = id_ticket_principal
        self.asunto = asunto
        self.estado = estado
        self.prioridad = prioridad
        self.fecha_creacion = fecha_creacion or datetime.now()
        self.fecha_ultima_actualizacion = fecha_ultima_actualizacion or datetime.now()
        self.ultimo_mensaje_texto = ultimo_mensaje_texto
        self.ultimo_mensaje_de = ultimo_mensaje_de
        self.ultimo_mensaje_fecha = ultimo_mensaje_fecha
        self.mensajes_sin_leer_cliente = mensajes_sin_leer_cliente
        self.mensajes_sin_leer_interno = mensajes_sin_leer_interno
        self.total_mensajes = total_mensajes
        self.cerrada_por = cerrada_por
        self.fecha_cierre = fecha_cierre

    def esta_activa(self) -> bool:
        """Verifica si la conversación está activa."""
        return self.estado in [EstadoConversacion.ABIERTA, EstadoConversacion.EN_CURSO]

    def tiene_mensajes_sin_leer_para_cliente(self) -> bool:
        """Verifica si hay mensajes sin leer por el cliente."""
        return self.mensajes_sin_leer_cliente > 0

    def tiene_mensajes_sin_leer_para_interno(self) -> bool:
        """Verifica si hay mensajes sin leer por internos."""
        return self.mensajes_sin_leer_interno > 0

    def cambiar_estado(self, nuevo_estado: EstadoConversacion, usuario_id: Optional[int] = None):
        """Cambia el estado de la conversación."""
        self.estado = nuevo_estado
        if nuevo_estado in [EstadoConversacion.RESUELTA, EstadoConversacion.CERRADA]:
            self.fecha_cierre = datetime.now()
            self.cerrada_por = usuario_id

    def es_urgente(self) -> bool:
        """Verifica si la conversación es urgente."""
        return self.prioridad == PrioridadConversacion.URGENTE

    def to_dict(self) -> dict:
        """Convierte la entidad a diccionario."""
        return {
            "id_conversacion": self.id_conversacion,
            "id_organizacion": self.id_organizacion,
            "id_usuario_cliente": self.id_usuario_cliente,
            "id_ticket_principal": self.id_ticket_principal,
            "asunto": self.asunto,
            "estado": self.estado.value if isinstance(self.estado, EstadoConversacion) else self.estado,
            "prioridad": self.prioridad.value if isinstance(self.prioridad, PrioridadConversacion) else self.prioridad,
            "fecha_creacion": self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            "fecha_ultima_actualizacion": self.fecha_ultima_actualizacion.isoformat() if self.fecha_ultima_actualizacion else None,
            "ultimo_mensaje_texto": self.ultimo_mensaje_texto,
            "ultimo_mensaje_de": self.ultimo_mensaje_de.value if isinstance(self.ultimo_mensaje_de, TipoParticipante) else self.ultimo_mensaje_de,
            "ultimo_mensaje_fecha": self.ultimo_mensaje_fecha.isoformat() if self.ultimo_mensaje_fecha else None,
            "mensajes_sin_leer_cliente": self.mensajes_sin_leer_cliente,
            "mensajes_sin_leer_interno": self.mensajes_sin_leer_interno,
            "total_mensajes": self.total_mensajes,
            "cerrada_por": self.cerrada_por,
            "fecha_cierre": self.fecha_cierre.isoformat() if self.fecha_cierre else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Conversacion':
        """Crea una instancia desde un diccionario."""
        return cls(
            id_conversacion=data.get("id_conversacion"),
            id_organizacion=data.get("id_organizacion"),
            id_usuario_cliente=data.get("id_usuario_cliente"),
            id_ticket_principal=data.get("id_ticket_principal"),
            asunto=data.get("asunto"),
            estado=EstadoConversacion(data.get("estado", "abierta")),
            prioridad=PrioridadConversacion(data.get("prioridad", "media")),
            fecha_creacion=data.get("fecha_creacion"),
            fecha_ultima_actualizacion=data.get("fecha_ultima_actualizacion"),
            ultimo_mensaje_texto=data.get("ultimo_mensaje_texto"),
            ultimo_mensaje_de=TipoParticipante(data["ultimo_mensaje_de"]) if data.get("ultimo_mensaje_de") else None,
            ultimo_mensaje_fecha=data.get("ultimo_mensaje_fecha"),
            mensajes_sin_leer_cliente=data.get("mensajes_sin_leer_cliente", 0),
            mensajes_sin_leer_interno=data.get("mensajes_sin_leer_interno", 0),
            total_mensajes=data.get("total_mensajes", 0),
            cerrada_por=data.get("cerrada_por"),
            fecha_cierre=data.get("fecha_cierre")
        )

    def __repr__(self) -> str:
        return f"<Conversacion id={self.id_conversacion} asunto='{self.asunto}' estado={self.estado}>"


class MensajeConversacion:
    """
    Entidad que representa un mensaje dentro de una conversación.

    Los mensajes pueden ser enviados por clientes o por usuarios internos,
    y pueden referenciar tickets de soporte.
    """

    def __init__(
        self,
        id_mensaje: Optional[int] = None,
        id_conversacion: int = None,
        id_usuario_emisor: int = None,
        tipo_emisor: TipoParticipante = None,
        id_ticket_referenciado: Optional[int] = None,
        texto_mensaje: str = "",
        fecha_envio: Optional[datetime] = None,
        leido_por_cliente: bool = False,
        leido_por_interno: bool = False,
        fecha_lectura_cliente: Optional[datetime] = None,
        fecha_lectura_interno: Optional[datetime] = None,
        editado: bool = False,
        fecha_edicion: Optional[datetime] = None,
        editado_por: Optional[int] = None,
        mensaje_sistema: bool = False
    ):
        self.id_mensaje = id_mensaje
        self.id_conversacion = id_conversacion
        self.id_usuario_emisor = id_usuario_emisor
        self.tipo_emisor = tipo_emisor
        self.id_ticket_referenciado = id_ticket_referenciado
        self.texto_mensaje = texto_mensaje
        self.fecha_envio = fecha_envio or datetime.now()
        self.leido_por_cliente = leido_por_cliente
        self.leido_por_interno = leido_por_interno
        self.fecha_lectura_cliente = fecha_lectura_cliente
        self.fecha_lectura_interno = fecha_lectura_interno
        self.editado = editado
        self.fecha_edicion = fecha_edicion
        self.editado_por = editado_por
        self.mensaje_sistema = mensaje_sistema

    def es_de_cliente(self) -> bool:
        """Verifica si el mensaje fue enviado por un cliente."""
        return self.tipo_emisor == TipoParticipante.CLIENTE

    def es_de_interno(self) -> bool:
        """Verifica si el mensaje fue enviado por un interno."""
        return self.tipo_emisor == TipoParticipante.INTERNO

    def tiene_ticket_referenciado(self) -> bool:
        """Verifica si el mensaje referencia un ticket."""
        return self.id_ticket_referenciado is not None

    def marcar_como_leido_por_cliente(self):
        """Marca el mensaje como leído por el cliente."""
        if not self.leido_por_cliente:
            self.leido_por_cliente = True
            self.fecha_lectura_cliente = datetime.now()

    def marcar_como_leido_por_interno(self):
        """Marca el mensaje como leído por un usuario interno."""
        if not self.leido_por_interno:
            self.leido_por_interno = True
            self.fecha_lectura_interno = datetime.now()

    def editar(self, nuevo_texto: str, editado_por: int):
        """Edita el contenido del mensaje."""
        self.texto_mensaje = nuevo_texto
        self.editado = True
        self.fecha_edicion = datetime.now()
        self.editado_por = editado_por

    def to_dict(self) -> dict:
        """Convierte la entidad a diccionario."""
        return {
            "id_mensaje": self.id_mensaje,
            "id_conversacion": self.id_conversacion,
            "id_usuario_emisor": self.id_usuario_emisor,
            "tipo_emisor": self.tipo_emisor.value if isinstance(self.tipo_emisor, TipoParticipante) else self.tipo_emisor,
            "id_ticket_referenciado": self.id_ticket_referenciado,
            "texto_mensaje": self.texto_mensaje,
            "fecha_envio": self.fecha_envio.isoformat() if self.fecha_envio else None,
            "leido_por_cliente": self.leido_por_cliente,
            "leido_por_interno": self.leido_por_interno,
            "fecha_lectura_cliente": self.fecha_lectura_cliente.isoformat() if self.fecha_lectura_cliente else None,
            "fecha_lectura_interno": self.fecha_lectura_interno.isoformat() if self.fecha_lectura_interno else None,
            "editado": self.editado,
            "fecha_edicion": self.fecha_edicion.isoformat() if self.fecha_edicion else None,
            "editado_por": self.editado_por,
            "mensaje_sistema": self.mensaje_sistema
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'MensajeConversacion':
        """Crea una instancia desde un diccionario."""
        return cls(
            id_mensaje=data.get("id_mensaje"),
            id_conversacion=data.get("id_conversacion"),
            id_usuario_emisor=data.get("id_usuario_emisor"),
            tipo_emisor=TipoParticipante(data.get("tipo_emisor")) if data.get("tipo_emisor") else None,
            id_ticket_referenciado=data.get("id_ticket_referenciado"),
            texto_mensaje=data.get("texto_mensaje", ""),
            fecha_envio=data.get("fecha_envio"),
            leido_por_cliente=data.get("leido_por_cliente", False),
            leido_por_interno=data.get("leido_por_interno", False),
            fecha_lectura_cliente=data.get("fecha_lectura_cliente"),
            fecha_lectura_interno=data.get("fecha_lectura_interno"),
            editado=data.get("editado", False),
            fecha_edicion=data.get("fecha_edicion"),
            editado_por=data.get("editado_por"),
            mensaje_sistema=data.get("mensaje_sistema", False)
        )

    def __repr__(self) -> str:
        return f"<MensajeConversacion id={self.id_mensaje} tipo={self.tipo_emisor} leido_cliente={self.leido_por_cliente}>"


class ParticipanteConversacion:
    """
    Entidad que representa la participación de un usuario en una conversación.

    Múltiples usuarios internos pueden participar en una misma conversación.
    """

    def __init__(
        self,
        id_participante: Optional[int] = None,
        id_conversacion: int = None,
        id_usuario: int = None,
        tipo_participante: TipoParticipante = None,
        fecha_union: Optional[datetime] = None,
        activo: bool = True,
        ultimo_acceso: Optional[datetime] = None,
        notificaciones_activadas: bool = True
    ):
        self.id_participante = id_participante
        self.id_conversacion = id_conversacion
        self.id_usuario = id_usuario
        self.tipo_participante = tipo_participante
        self.fecha_union = fecha_union or datetime.now()
        self.activo = activo
        self.ultimo_acceso = ultimo_acceso
        self.notificaciones_activadas = notificaciones_activadas

    def es_cliente(self) -> bool:
        """Verifica si el participante es un cliente."""
        return self.tipo_participante == TipoParticipante.CLIENTE

    def es_interno(self) -> bool:
        """Verifica si el participante es un usuario interno."""
        return self.tipo_participante == TipoParticipante.INTERNO

    def actualizar_ultimo_acceso(self):
        """Actualiza la marca de tiempo del último acceso."""
        self.ultimo_acceso = datetime.now()

    def desactivar(self):
        """Desactiva la participación."""
        self.activo = False

    def activar(self):
        """Activa la participación."""
        self.activo = True

    def to_dict(self) -> dict:
        """Convierte la entidad a diccionario."""
        return {
            "id_participante": self.id_participante,
            "id_conversacion": self.id_conversacion,
            "id_usuario": self.id_usuario,
            "tipo_participante": self.tipo_participante.value if isinstance(self.tipo_participante, TipoParticipante) else self.tipo_participante,
            "fecha_union": self.fecha_union.isoformat() if self.fecha_union else None,
            "activo": self.activo,
            "ultimo_acceso": self.ultimo_acceso.isoformat() if self.ultimo_acceso else None,
            "notificaciones_activadas": self.notificaciones_activadas
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ParticipanteConversacion':
        """Crea una instancia desde un diccionario."""
        return cls(
            id_participante=data.get("id_participante"),
            id_conversacion=data.get("id_conversacion"),
            id_usuario=data.get("id_usuario"),
            tipo_participante=TipoParticipante(data.get("tipo_participante")) if data.get("tipo_participante") else None,
            fecha_union=data.get("fecha_union"),
            activo=data.get("activo", True),
            ultimo_acceso=data.get("ultimo_acceso"),
            notificaciones_activadas=data.get("notificaciones_activadas", True)
        )

    def __repr__(self) -> str:
        return f"<ParticipanteConversacion id={self.id_participante} usuario={self.id_usuario} tipo={self.tipo_participante}>"


class AsignacionOrganizacionInterna:
    """
    Entidad que representa la asignación de un usuario interno a una organización.

    Define qué usuarios internos atienden qué organizaciones cliente.
    """

    def __init__(
        self,
        id_asignacion: Optional[int] = None,
        id_usuario_interno: int = None,
        id_organizacion: int = None,
        id_rol: int = None,
        fecha_asignacion: Optional[datetime] = None,
        activo: bool = True,
        asignado_por: int = None,
        notas: Optional[str] = None,
        fecha_desactivacion: Optional[datetime] = None,
        desactivado_por: Optional[int] = None
    ):
        self.id_asignacion = id_asignacion
        self.id_usuario_interno = id_usuario_interno
        self.id_organizacion = id_organizacion
        self.id_rol = id_rol
        self.fecha_asignacion = fecha_asignacion or datetime.now()
        self.activo = activo
        self.asignado_por = asignado_por
        self.notas = notas
        self.fecha_desactivacion = fecha_desactivacion
        self.desactivado_por = desactivado_por

    def desactivar(self, usuario_id: int):
        """Desactiva la asignación."""
        self.activo = False
        self.fecha_desactivacion = datetime.now()
        self.desactivado_por = usuario_id

    def reactivar(self):
        """Reactiva la asignación."""
        self.activo = True
        self.fecha_desactivacion = None
        self.desactivado_por = None

    def to_dict(self) -> dict:
        """Convierte la entidad a diccionario."""
        return {
            "id_asignacion": self.id_asignacion,
            "id_usuario_interno": self.id_usuario_interno,
            "id_organizacion": self.id_organizacion,
            "id_rol": self.id_rol,
            "fecha_asignacion": self.fecha_asignacion.isoformat() if self.fecha_asignacion else None,
            "activo": self.activo,
            "asignado_por": self.asignado_por,
            "notas": self.notas,
            "fecha_desactivacion": self.fecha_desactivacion.isoformat() if self.fecha_desactivacion else None,
            "desactivado_por": self.desactivado_por
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'AsignacionOrganizacionInterna':
        """Crea una instancia desde un diccionario."""
        return cls(
            id_asignacion=data.get("id_asignacion"),
            id_usuario_interno=data.get("id_usuario_interno"),
            id_organizacion=data.get("id_organizacion"),
            id_rol=data.get("id_rol"),
            fecha_asignacion=data.get("fecha_asignacion"),
            activo=data.get("activo", True),
            asignado_por=data.get("asignado_por"),
            notas=data.get("notas"),
            fecha_desactivacion=data.get("fecha_desactivacion"),
            desactivado_por=data.get("desactivado_por")
        )

    def __repr__(self) -> str:
        return f"<AsignacionOrganizacionInterna id={self.id_asignacion} usuario={self.id_usuario_interno} org={self.id_organizacion}>"
