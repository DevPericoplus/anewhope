"""
Adapter para gestión de conversaciones entre clientes e internos.

Este módulo proporciona funciones para:
- Gestionar conversaciones
- Enviar y recibir mensajes
- Tracking de participantes
- Marcar mensajes como leídos
- Relacionar conversaciones con tickets
"""

from sqlalchemy import text, Engine
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================================
# ASIGNACIONES DE USUARIOS INTERNOS A ORGANIZACIONES
# ============================================================================

def crear_asignacion_interna(
    engine: Engine,
    id_usuario_interno: int,
    id_organizacion: int,
    id_rol: int,
    asignado_por: int,
    notas: str = None
) -> int:
    """
    Asigna un usuario interno a una organización con un rol.

    Args:
        engine: Motor de base de datos
        id_usuario_interno: ID del usuario interno
        id_organizacion: ID de la organización
        id_rol: ID del rol (desde proyectos_roles_base)
        asignado_por: ID del super admin que hace la asignación
        notas: Notas opcionales sobre la asignación

    Returns:
        ID de la asignación creada
    """
    with engine.connect() as conn:
        query = text("""
            INSERT INTO myllm_projects_db.asignaciones_organizaciones_internas
                (id_usuario_interno, id_organizacion, id_rol, asignado_por, notas)
            VALUES
                (:id_usuario_interno, :id_organizacion, :id_rol, :asignado_por, :notas)
        """)
        result = conn.execute(query, {
            "id_usuario_interno": id_usuario_interno,
            "id_organizacion": id_organizacion,
            "id_rol": id_rol,
            "asignado_por": asignado_por,
            "notas": notas
        })
        conn.commit()
        return result.lastrowid


def obtener_organizaciones_asignadas(engine: Engine, id_usuario_interno: int) -> List[Dict[str, Any]]:
    """
    Obtiene las organizaciones asignadas a un usuario interno.

    Args:
        engine: Motor de base de datos
        id_usuario_interno: ID del usuario interno

    Returns:
        Lista de organizaciones con sus datos
    """
    with engine.connect() as conn:
        query = text("""
            SELECT DISTINCT
                o.id,
                o.nombre,
                o.email,
                r.nombre as rol_nombre,
                aoi.fecha_asignacion,
                COUNT(DISTINCT c.id_conversacion) as conversaciones_activas
            FROM myllm_projects_db.organizaciones o
            JOIN myllm_projects_db.asignaciones_organizaciones_internas aoi
                ON o.id = aoi.id_organizacion
            LEFT JOIN myllm_projects_db.proyectos_roles_base r
                ON aoi.id_rol = r.id
            LEFT JOIN myllm_projects_db.conversaciones c
                ON o.id = c.id_organizacion AND c.estado IN ('abierta', 'en_curso')
            WHERE aoi.id_usuario_interno = :user_id
              AND aoi.activo = TRUE
            GROUP BY o.id
            ORDER BY o.nombre
        """)
        result = conn.execute(query, {"user_id": id_usuario_interno})
        return [dict(row._mapping) for row in result]


def desactivar_asignacion_interna(
    engine: Engine,
    id_asignacion: int,
    desactivado_por: int
) -> bool:
    """
    Desactiva una asignación de usuario interno a organización.

    Args:
        engine: Motor de base de datos
        id_asignacion: ID de la asignación
        desactivado_por: ID del usuario que desactiva

    Returns:
        True si se desactivó correctamente
    """
    with engine.connect() as conn:
        query = text("""
            UPDATE myllm_projects_db.asignaciones_organizaciones_internas
            SET activo = FALSE,
                fecha_desactivacion = NOW(),
                desactivado_por = :desactivado_por
            WHERE id = :id_asignacion
        """)
        result = conn.execute(query, {
            "id_asignacion": id_asignacion,
            "desactivado_por": desactivado_por
        })
        conn.commit()
        return result.rowcount > 0


# ============================================================================
# CONVERSACIONES
# ============================================================================

def crear_conversacion(
    engine: Engine,
    id_organizacion: int,
    id_usuario_cliente: int,
    asunto: str = None,
    id_ticket_principal: int = None,
    prioridad: str = "media"
) -> int:
    """
    Crea una nueva conversación iniciada por un cliente.

    Args:
        engine: Motor de base de datos
        id_organizacion: ID de la organización
        id_usuario_cliente: ID del usuario cliente
        asunto: Asunto de la conversación
        id_ticket_principal: ID del ticket principal (opcional)
        prioridad: Prioridad de la conversación

    Returns:
        ID de la conversación creada
    """
    with engine.connect() as conn:
        # Crear conversación
        query_conv = text("""
            INSERT INTO myllm_projects_db.conversaciones
                (id_organizacion, id_usuario_cliente, asunto, id_ticket_principal, prioridad)
            VALUES
                (:id_organizacion, :id_usuario_cliente, :asunto, :id_ticket_principal, :prioridad)
        """)
        result = conn.execute(query_conv, {
            "id_organizacion": id_organizacion,
            "id_usuario_cliente": id_usuario_cliente,
            "asunto": asunto,
            "id_ticket_principal": id_ticket_principal,
            "prioridad": prioridad
        })
        id_conversacion = result.lastrowid

        # Añadir cliente como participante
        query_part = text("""
            INSERT INTO myllm_projects_db.participantes_conversacion
                (id_conversacion, id_usuario, tipo_participante)
            VALUES
                (:id_conversacion, :id_usuario, 'cliente')
        """)
        conn.execute(query_part, {
            "id_conversacion": id_conversacion,
            "id_usuario": id_usuario_cliente
        })

        # Si hay ticket principal, crear relación
        if id_ticket_principal:
            query_ticket = text("""
                INSERT INTO myllm_projects_db.conversaciones_tickets_relacionados
                    (id_conversacion, id_ticket, tipo_relacion, mencionado_por)
                VALUES
                    (:id_conversacion, :id_ticket, 'principal', :mencionado_por)
            """)
            conn.execute(query_ticket, {
                "id_conversacion": id_conversacion,
                "id_ticket": id_ticket_principal,
                "mencionado_por": id_usuario_cliente
            })

        conn.commit()
        return id_conversacion


def obtener_conversaciones_cliente(
    engine: Engine,
    id_usuario_cliente: int,
    id_organizacion: int,
    solo_activas: bool = True
) -> List[Dict[str, Any]]:
    """
    Obtiene las conversaciones de un cliente.

    Args:
        engine: Motor de base de datos
        id_usuario_cliente: ID del usuario cliente
        id_organizacion: ID de la organización
        solo_activas: Si True, solo devuelve conversaciones activas

    Returns:
        Lista de conversaciones
    """
    with engine.connect() as conn:
        estado_filter = "AND c.estado IN ('abierta', 'en_curso')" if solo_activas else ""

        query = text(f"""
            SELECT
                c.id_conversacion,
                c.asunto,
                c.estado,
                c.prioridad,
                c.fecha_creacion,
                c.fecha_ultima_actualizacion,
                c.ultimo_mensaje_texto,
                c.ultimo_mensaje_de,
                c.mensajes_sin_leer_cliente,
                c.total_mensajes,
                t.titulo as ticket_titulo,
                t.estado as ticket_estado
            FROM myllm_projects_db.conversaciones c
            LEFT JOIN myllm_projects_db.tickets t ON c.id_ticket_principal = t.id
            WHERE c.id_usuario_cliente = :user_id
              AND c.id_organizacion = :org_id
              {estado_filter}
            ORDER BY c.fecha_ultima_actualizacion DESC
        """)
        result = conn.execute(query, {
            "user_id": id_usuario_cliente,
            "org_id": id_organizacion
        })
        return [dict(row._mapping) for row in result]


def obtener_conversaciones_organizacion(
    engine: Engine,
    id_organizacion: int,
    solo_activas: bool = True
) -> List[Dict[str, Any]]:
    """
    Obtiene todas las conversaciones de una organización (vista de backoffice).

    Args:
        engine: Motor de base de datos
        id_organizacion: ID de la organización
        solo_activas: Si True, solo devuelve conversaciones activas

    Returns:
        Lista de conversaciones con datos de cliente
    """
    with engine.connect() as conn:
        estado_filter = "AND c.estado IN ('abierta', 'en_curso')" if solo_activas else ""

        query = text(f"""
            SELECT
                c.id_conversacion,
                c.id_usuario_cliente,
                c.asunto,
                c.estado,
                c.prioridad,
                c.fecha_creacion,
                c.fecha_ultima_actualizacion,
                c.ultimo_mensaje_texto,
                c.ultimo_mensaje_de,
                c.mensajes_sin_leer_interno,
                c.total_mensajes,
                t.titulo as ticket_titulo,
                t.estado as ticket_estado
            FROM myllm_projects_db.conversaciones c
            LEFT JOIN myllm_projects_db.tickets t ON c.id_ticket_principal = t.id
            WHERE c.id_organizacion = :org_id
              {estado_filter}
            ORDER BY c.fecha_ultima_actualizacion DESC
        """)
        result = conn.execute(query, {"org_id": id_organizacion})
        return [dict(row._mapping) for row in result]


def unirse_a_conversacion(
    engine: Engine,
    id_conversacion: int,
    id_usuario_interno: int
) -> bool:
    """
    Un usuario interno se une a una conversación como participante.

    Args:
        engine: Motor de base de datos
        id_conversacion: ID de la conversación
        id_usuario_interno: ID del usuario interno

    Returns:
        True si se unió correctamente
    """
    with engine.connect() as conn:
        # Verificar si ya es participante
        query_check = text("""
            SELECT id FROM myllm_projects_db.participantes_conversacion
            WHERE id_conversacion = :id_conversacion
              AND id_usuario = :id_usuario
        """)
        result = conn.execute(query_check, {
            "id_conversacion": id_conversacion,
            "id_usuario": id_usuario_interno
        })

        if result.fetchone():
            # Ya es participante, actualizar último acceso
            query_update = text("""
                UPDATE myllm_projects_db.participantes_conversacion
                SET ultimo_acceso = NOW(), activo = TRUE
                WHERE id_conversacion = :id_conversacion
                  AND id_usuario = :id_usuario
            """)
            conn.execute(query_update, {
                "id_conversacion": id_conversacion,
                "id_usuario": id_usuario_interno
            })
        else:
            # Añadir como nuevo participante
            query_insert = text("""
                INSERT INTO myllm_projects_db.participantes_conversacion
                    (id_conversacion, id_usuario, tipo_participante, ultimo_acceso)
                VALUES
                    (:id_conversacion, :id_usuario, 'interno', NOW())
            """)
            conn.execute(query_insert, {
                "id_conversacion": id_conversacion,
                "id_usuario": id_usuario_interno
            })

        # Cambiar estado de conversación a "en_curso" si estaba "abierta"
        query_estado = text("""
            UPDATE myllm_projects_db.conversaciones
            SET estado = 'en_curso'
            WHERE id_conversacion = :id_conversacion
              AND estado = 'abierta'
        """)
        conn.execute(query_estado, {"id_conversacion": id_conversacion})

        conn.commit()
        return True


# ============================================================================
# MENSAJES
# ============================================================================

def enviar_mensaje(
    engine: Engine,
    id_conversacion: int,
    id_usuario_emisor: int,
    tipo_emisor: str,
    texto_mensaje: str,
    id_ticket_referenciado: int = None
) -> int:
    """
    Envía un mensaje en una conversación.

    Args:
        engine: Motor de base de datos
        id_conversacion: ID de la conversación
        id_usuario_emisor: ID del usuario que envía
        tipo_emisor: 'cliente' o 'interno'
        texto_mensaje: Contenido del mensaje
        id_ticket_referenciado: ID del ticket mencionado (opcional)

    Returns:
        ID del mensaje creado
    """
    with engine.connect() as conn:
        query = text("""
            INSERT INTO myllm_projects_db.mensajes_conversacion
                (id_conversacion, id_usuario_emisor, tipo_emisor, texto_mensaje, id_ticket_referenciado)
            VALUES
                (:id_conversacion, :id_usuario_emisor, :tipo_emisor, :texto_mensaje, :id_ticket_referenciado)
        """)
        result = conn.execute(query, {
            "id_conversacion": id_conversacion,
            "id_usuario_emisor": id_usuario_emisor,
            "tipo_emisor": tipo_emisor,
            "texto_mensaje": texto_mensaje,
            "id_ticket_referenciado": id_ticket_referenciado
        })
        conn.commit()
        return result.lastrowid


def obtener_mensajes_conversacion(
    engine: Engine,
    id_conversacion: int
) -> List[Dict[str, Any]]:
    """
    Obtiene todos los mensajes de una conversación.

    Args:
        engine: Motor de base de datos
        id_conversacion: ID de la conversación

    Returns:
        Lista de mensajes (sin datos de usuario ya que users está en myllm_core_db)
    """
    with engine.connect() as conn:
        query = text("""
            SELECT
                m.id_mensaje,
                m.id_usuario_emisor,
                m.texto_mensaje,
                m.tipo_emisor,
                m.fecha_envio,
                m.leido_por_cliente,
                m.leido_por_interno,
                m.editado,
                m.mensaje_sistema,
                m.id_ticket_referenciado,
                t.titulo as ticket_titulo,
                t.estado as ticket_estado
            FROM myllm_projects_db.mensajes_conversacion m
            LEFT JOIN myllm_projects_db.tickets t ON m.id_ticket_referenciado = t.id
            WHERE m.id_conversacion = :id_conversacion
            ORDER BY m.fecha_envio ASC
        """)
        result = conn.execute(query, {"id_conversacion": id_conversacion})
        return [dict(row._mapping) for row in result]


def marcar_mensajes_como_leidos(
    engine: Engine,
    id_conversacion: int,
    tipo_lector: str
) -> bool:
    """
    Marca todos los mensajes de una conversación como leídos.

    Args:
        engine: Motor de base de datos
        id_conversacion: ID de la conversación
        tipo_lector: 'cliente' o 'interno'

    Returns:
        True si se marcaron correctamente
    """
    with engine.connect() as conn:
        if tipo_lector == 'cliente':
            query = text("""
                UPDATE myllm_projects_db.mensajes_conversacion
                SET leido_por_cliente = TRUE,
                    fecha_lectura_cliente = NOW()
                WHERE id_conversacion = :id_conversacion
                  AND tipo_emisor = 'interno'
                  AND leido_por_cliente = FALSE
            """)
        else:  # interno
            query = text("""
                UPDATE myllm_projects_db.mensajes_conversacion
                SET leido_por_interno = TRUE,
                    fecha_lectura_interno = NOW()
                WHERE id_conversacion = :id_conversacion
                  AND tipo_emisor = 'cliente'
                  AND leido_por_interno = FALSE
            """)

        conn.execute(query, {"id_conversacion": id_conversacion})
        conn.commit()
        return True


# ============================================================================
# TICKETS RELACIONADOS
# ============================================================================

def obtener_tickets_conversacion(
    engine: Engine,
    id_conversacion: int
) -> List[Dict[str, Any]]:
    """
    Obtiene todos los tickets relacionados con una conversación.

    Args:
        engine: Motor de base de datos
        id_conversacion: ID de la conversación

    Returns:
        Lista de tickets relacionados
    """
    with engine.connect() as conn:
        query = text("""
            SELECT
                t.id,
                t.titulo,
                t.estado,
                t.prioridad,
                ctr.tipo_relacion,
                ctr.fecha_vinculacion,
                u.nombre as vinculado_por
            FROM myllm_projects_db.conversaciones_tickets_relacionados ctr
            JOIN myllm_projects_db.tickets t ON ctr.id_ticket = t.id
            LEFT JOIN myllm_projects_db.users u ON ctr.mencionado_por = u.id
            WHERE ctr.id_conversacion = :id_conversacion
            ORDER BY ctr.fecha_vinculacion DESC
        """)
        result = conn.execute(query, {"id_conversacion": id_conversacion})
        return [dict(row._mapping) for row in result]


def obtener_tickets_disponibles_organizacion(
    engine: Engine,
    id_organizacion: int,
    id_usuario: int = None
) -> List[Dict[str, Any]]:
    """
    Obtiene los tickets disponibles de una organización para referenciar.

    Args:
        engine: Motor de base de datos
        id_organizacion: ID de la organización
        id_usuario: ID del usuario (si es cliente, filtrar por su id)

    Returns:
        Lista de tickets
    """
    with engine.connect() as conn:
        user_filter = "AND t.cliente_id = :user_id" if id_usuario else ""

        query = text(f"""
            SELECT
                t.id,
                t.titulo,
                t.estado,
                t.prioridad,
                t.fecha_creacion
            FROM myllm_projects_db.tickets t
            WHERE t.id_organizacion = :org_id
              AND t.estado IN ('abierto', 'en_espera')
              {user_filter}
            ORDER BY t.fecha_creacion DESC
            LIMIT 50
        """)

        params = {"org_id": id_organizacion}
        if id_usuario:
            params["user_id"] = id_usuario

        result = conn.execute(query, params)
        return [dict(row._mapping) for row in result]


# ============================================================================
# UTILIDADES Y REPORTES
# ============================================================================

def obtener_estadisticas_conversaciones_organizacion(
    engine: Engine,
    id_organizacion: int
) -> Dict[str, Any]:
    """
    Obtiene estadísticas de conversaciones de una organización.

    Args:
        engine: Motor de base de datos
        id_organizacion: ID de la organización

    Returns:
        Diccionario con estadísticas
    """
    with engine.connect() as conn:
        query = text("""
            SELECT
                COUNT(*) as total_conversaciones,
                SUM(CASE WHEN estado = 'abierta' THEN 1 ELSE 0 END) as abiertas,
                SUM(CASE WHEN estado = 'en_curso' THEN 1 ELSE 0 END) as en_curso,
                SUM(CASE WHEN estado = 'resuelta' THEN 1 ELSE 0 END) as resueltas,
                SUM(CASE WHEN estado = 'cerrada' THEN 1 ELSE 0 END) as cerradas,
                SUM(mensajes_sin_leer_interno) as total_mensajes_sin_leer,
                AVG(total_mensajes) as promedio_mensajes_por_conversacion
            FROM myllm_projects_db.conversaciones
            WHERE id_organizacion = :org_id
        """)
        result = conn.execute(query, {"org_id": id_organizacion})
        row = result.fetchone()
        return dict(row._mapping) if row else {}


def cerrar_conversacion(
    engine: Engine,
    id_conversacion: int,
    cerrada_por: int,
    estado_final: str = "cerrada"
) -> bool:
    """
    Cierra una conversación.

    Args:
        engine: Motor de base de datos
        id_conversacion: ID de la conversación
        cerrada_por: ID del usuario que cierra
        estado_final: 'resuelta' o 'cerrada'

    Returns:
        True si se cerró correctamente
    """
    with engine.connect() as conn:
        query = text("""
            UPDATE myllm_projects_db.conversaciones
            SET estado = :estado_final,
                cerrada_por = :cerrada_por,
                fecha_cierre = NOW()
            WHERE id_conversacion = :id_conversacion
        """)
        result = conn.execute(query, {
            "id_conversacion": id_conversacion,
            "estado_final": estado_final,
            "cerrada_por": cerrada_por
        })
        conn.commit()
        return result.rowcount > 0
