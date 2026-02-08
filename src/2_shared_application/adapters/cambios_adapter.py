"""
Adaptador para acceder a la tabla cambios en la base de datos.
Proporciona funciones para obtener eventos del calendario basados en cambios.
"""
from datetime import date, datetime
from typing import Optional
from sqlalchemy import Engine, text
import sys
import importlib.util
from pathlib import Path


def _load_calendario_event_module():
    """Carga el módulo de entidades del calendario."""
    entity_path = (
        Path(__file__).resolve().parents[2]
        / "1_shared_domain/entities/calendario_event.py"
    )
    spec = importlib.util.spec_from_file_location("calendario_event", entity_path)
    if spec is None or spec.loader is None:
        raise ImportError("No se pudo cargar el módulo calendario_event")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Cargar módulo
calendario_event = _load_calendario_event_module()
CambioEvento = calendario_event.CambioEvento
agrupar_eventos_por_dia = calendario_event.agrupar_eventos_por_dia


def obtener_cambios_por_organizacion(
    engine: Engine,
    id_organizacion: int,
    mes: Optional[int] = None,
    anio: Optional[int] = None,
    id_proyecto: Optional[int] = None
) -> list[CambioEvento]:
    """
    Obtiene los cambios (eventos) para una organización, con filtros opcionales.

    Args:
        engine: SQLAlchemy engine
        id_organizacion: ID de la organización
        mes: Mes opcional para filtrar (1-12)
        anio: Año opcional para filtrar
        id_proyecto: ID del proyecto opcional para filtrar

    Returns:
        Lista de CambioEvento ordenados por fecha descendente
    """
    # Construir filtros opcionales
    filtros = ["c.id_organizacion = :org_id"]
    params = {"org_id": id_organizacion}

    if mes and anio:
        filtros.append("MONTH(c.fecha_cambio) = :mes")
        filtros.append("YEAR(c.fecha_cambio) = :anio")
        params["mes"] = mes
        params["anio"] = anio

    if id_proyecto is not None:
        filtros.append("c.id_proyecto = :proyecto_id")
        params["proyecto_id"] = id_proyecto

    where_clause = " AND ".join(filtros)

    query = text(f"""
        SELECT
            c.id,
            c.fecha_cambio,
            c.tipo_cambio,
            c.descripcion,
            c.id_organizacion,
            c.id_proyecto,
            c.id_version
        FROM myllm_projects_db.cambios c
        WHERE {where_clause}
        ORDER BY c.fecha_cambio DESC
    """)

    with engine.connect() as conn:
        result = conn.execute(query, params)
        rows = result.fetchall()

        eventos = []
        for row in rows:
            evento = CambioEvento(
                id=row.id,
                fecha_cambio=row.fecha_cambio if isinstance(row.fecha_cambio, date) else row.fecha_cambio.date(),
                tipo_cambio=row.tipo_cambio,
                descripcion=row.descripcion or "",
                id_organizacion=row.id_organizacion,
                id_proyecto=row.id_proyecto,
                id_version=row.id_version,
                tipo_usuario=None,  # No disponible en la tabla cambios
            )
            eventos.append(evento)

        return eventos


def obtener_tipos_cambio_unicos(engine: Engine) -> list[str]:
    """
    Obtiene todos los tipos de cambio únicos registrados en el sistema.
    Útil para generar mapeos de colores dinámicamente.

    Returns:
        Lista de tipos de cambio únicos
    """
    query = text("""
        SELECT DISTINCT tipo_cambio
        FROM myllm_projects_db.cambios
        WHERE tipo_cambio IS NOT NULL
        ORDER BY tipo_cambio
    """)

    with engine.connect() as conn:
        result = conn.execute(query)
        return [row.tipo_cambio for row in result.fetchall()]


def determinar_tipo_usuario(engine: Engine, id_usuario: int) -> Optional[str]:
    """
    Determina si un usuario es 'cliente' o 'interno'.
    Se basa en el campo training_create de la tabla users.

    Args:
        engine: SQLAlchemy engine
        id_usuario: ID del usuario a verificar

    Returns:
        'cliente', 'interno', o None si no se encuentra
    """
    query = text("""
        SELECT training_create
        FROM myllm_core_db.users
        WHERE id = :user_id
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"user_id": id_usuario})
            row = result.fetchone()

            if row is None:
                return None

            # training_create = true -> interno, false -> cliente
            return "interno" if row.training_create else "cliente"
    except Exception:
        # Si hay error (ej: cross-database access), retornar None
        return None


def obtener_cambios_agrupados_por_dia(
    engine: Engine,
    id_organizacion: int,
    mes: int,
    anio: int,
    id_proyecto: Optional[int] = None
) -> list[dict]:
    """
    Obtiene cambios agrupados por día, con detección de eventos mixtos.

    Args:
        engine: SQLAlchemy engine
        id_organizacion: ID de la organización
        mes: Mes a consultar (1-12)
        anio: Año a consultar
        id_proyecto: ID del proyecto opcional

    Returns:
        Lista de diccionarios con eventos agrupados por día
    """
    eventos = obtener_cambios_por_organizacion(
        engine=engine,
        id_organizacion=id_organizacion,
        mes=mes,
        anio=anio,
        id_proyecto=id_proyecto
    )

    eventos_dia = agrupar_eventos_por_dia(eventos)
    return [ed.to_calendar_event() for ed in eventos_dia]


def obtener_proyectos_organizacion(engine: Engine, id_organizacion: int) -> list[dict]:
    """
    Obtiene los proyectos asociados a una organización.

    Args:
        engine: SQLAlchemy engine
        id_organizacion: ID de la organización

    Returns:
        Lista de proyectos con id y nombre
    """
    query = text("""
        SELECT
            id,
            nombre
        FROM myllm_projects_db.proyectos
        WHERE id_organizacion = :org_id
        ORDER BY nombre
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {"org_id": id_organizacion})
        return [
            {"id": row.id, "nombre": row.nombre}
            for row in result.fetchall()
        ]


def obtener_organizaciones_internas_usuario(engine: Engine, id_usuario: int) -> list[dict]:
    """
    Obtiene las organizaciones asignadas a un usuario interno (backoffice).

    Args:
        engine: SQLAlchemy engine
        id_usuario: ID del usuario interno

    Returns:
        Lista de organizaciones con id y nombre
    """
    query = text("""
        SELECT DISTINCT
            o.organization_id as id,
            o.organization_name as nombre
        FROM myllm_core_db.organizations o
        INNER JOIN myllm_projects_db.asignaciones_organizaciones_internas aoi
            ON o.organization_id = aoi.id_organizacion
        WHERE aoi.id_usuario_interno = :user_id
          AND aoi.activo = 1
        ORDER BY o.organization_name
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"user_id": id_usuario})
            return [
                {"id": row.id, "nombre": row.nombre}
                for row in result.fetchall()
            ]
    except Exception as e:
        print(f"Error obteniendo organizaciones internas: {e}")
        import traceback
        traceback.print_exc()
        return []


def registrar_cambio(
    engine: Engine,
    id_organizacion: int,
    tipo_cambio: str,
    descripcion: str,
    id_usuario: int,
    id_proyecto: Optional[int] = None,
) -> bool:
    """
    Registra un cambio/evento en la tabla cambios.

    Método compartido que puede ser utilizado desde cualquier parte de la aplicación
    para registrar eventos en el sistema de seguimiento de cambios.

    Utiliza el stored procedure sp_registrar_cambio_proyecto que internamente
    determina el id_version basándose en el id_proyecto.

    Args:
        engine: SQLAlchemy engine para conexión a la BD
        id_organizacion: ID de la organización (requerido)
        tipo_cambio: Tipo de cambio/evento (ej: "Solicitud soporte proyecto",
                     "Solicitud soporte organización", "Versión publicada", etc.)
        descripcion: Descripción del cambio
        id_usuario: ID del usuario que realiza el cambio
        id_proyecto: ID del proyecto (opcional, puede ser None para cambios a nivel organización)

    Returns:
        True si el registro fue exitoso, False en caso contrario

    Ejemplos:
        >>> # Registrar ticket de soporte sin proyecto (a nivel organización)
        >>> registrar_cambio(
        ...     engine=db_engine,
        ...     id_organizacion=1,
        ...     tipo_cambio="Solicitud soporte organización",
        ...     descripcion="Ticket #123: Consulta sobre facturación",
        ...     id_usuario=5,
        ...     id_proyecto=None
        ... )

        >>> # Registrar ticket de soporte con proyecto
        >>> registrar_cambio(
        ...     engine=db_engine,
        ...     id_organizacion=1,
        ...     tipo_cambio="Solicitud soporte proyecto",
        ...     descripcion="Ticket #124: Error en deployment",
        ...     id_usuario=5,
        ...     id_proyecto=10
        ... )

        >>> # Registrar cambio de versión
        >>> registrar_cambio(
        ...     engine=db_engine,
        ...     id_organizacion=1,
        ...     tipo_cambio="Versión publicada",
        ...     descripcion="Versión v003 publicada para producción",
        ...     id_usuario=8,
        ...     id_proyecto=10
        ... )
    """
    query = text("""
        CALL sp_registrar_cambio_proyecto(
            :p_id_proyecto,
            :p_id_organizacion,
            :p_tipo_cambio,
            :p_descripcion,
            :p_id_usuario
        )
    """)

    try:
        with engine.connect() as conn:
            conn.execute(
                query,
                {
                    "p_id_proyecto": id_proyecto,
                    "p_id_organizacion": id_organizacion,
                    "p_tipo_cambio": tipo_cambio,
                    "p_descripcion": descripcion,
                    "p_id_usuario": id_usuario,
                },
            )
            conn.commit()
            return True
    except Exception as e:
        print(f"Error registrando cambio: {e}")
        import traceback
        traceback.print_exc()
        return False
