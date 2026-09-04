"""Lecturas y escrituras de negocio del Trainer via Broker → Backend Core.

El Backend IA no abre conexiones a MariaDB. Todas las consultas de nombres,
prompts de fusión y el cierre de jobs pasan por el Broker.
"""

from __future__ import annotations

import logging
from typing import Any

from broker_client import TrainerBrokerClient

logger = logging.getLogger("trainer_api")

MSG_ORG_FALLBACK = "Organización {id_organizacion}"
MSG_PRJ_FALLBACK = "Proyecto {id_proyecto}"


def fetch_job_context(
    organization_id: int = 0,
    project_id: int = 0,
    prompt_name: str = "",
    client: TrainerBrokerClient | None = None,
) -> dict[str, Any]:
    """Obtiene contexto de job via Broker → Backend Core."""
    broker = client or TrainerBrokerClient()
    try:
        result = broker.get_job_context(
            organization_id=organization_id,
            project_id=project_id,
            prompt_name=prompt_name,
        )
        return result
    except Exception as exc:
        logger.warning(
            "[TRAINER-CORE] Error obteniendo contexto org=%s prj=%s: %s",
            organization_id,
            project_id,
            exc,
        )
        return {
            "organization_name": (
                MSG_ORG_FALLBACK.format(id_organizacion=organization_id)
                if organization_id > 0
                else ""
            ),
            "project_name": (
                MSG_PRJ_FALLBACK.format(id_proyecto=project_id)
                if project_id > 0
                else ""
            ),
            "prompt": "",
            "prompt_name": prompt_name,
        }


def fetch_organization_name(
    organization_id: int,
    client: TrainerBrokerClient | None = None,
) -> str:
    """Obtiene el nombre de la organización via Broker → Backend Core."""
    ctx = fetch_job_context(organization_id=organization_id, client=client)
    name = str(ctx.get("organization_name") or "").strip()
    return name or MSG_ORG_FALLBACK.format(id_organizacion=organization_id)


def fetch_project_name(
    project_id: int,
    client: TrainerBrokerClient | None = None,
) -> str:
    """Obtiene el nombre del proyecto via Broker → Backend Core."""
    ctx = fetch_job_context(project_id=project_id, client=client)
    name = str(ctx.get("project_name") or "").strip()
    return name or MSG_PRJ_FALLBACK.format(id_proyecto=project_id)


def fetch_fusion_prompt(
    prompt_name: str,
    client: TrainerBrokerClient | None = None,
) -> str:
    """Obtiene un prompt de fusión activo via Broker → Backend Core."""
    ctx = fetch_job_context(prompt_name=prompt_name, client=client)
    prompt_text = str(ctx.get("prompt") or "")
    if prompt_text:
        logger.info(
            "[TRAINER-CORE] Prompt de fusión '%s' obtenido: %d caracteres",
            prompt_name,
            len(prompt_text),
        )
        return prompt_text
    logger.error(
        "[TRAINER-CORE] Prompt '%s' no encontrado o inactivo",
        prompt_name,
    )
    return ""


def notify_job_complete(
    job_id: int,
    id_organizacion: int,
    id_proyecto: int,
    id_version: int,
    descripcion: str,
    referencia_salida: str = "",
    tipo_cambio: str = "evaluacion_documental",
    id_estado: int = 4,
    client: TrainerBrokerClient | None = None,
) -> dict[str, Any]:
    """Notifica el cierre de un job via Broker → Backend Core."""
    broker = client or TrainerBrokerClient()
    return broker.complete_job(
        job_id=job_id,
        id_organizacion=id_organizacion,
        id_proyecto=id_proyecto,
        id_version=id_version,
        descripcion=descripcion,
        referencia_salida=referencia_salida,
        tipo_cambio=tipo_cambio,
        id_estado=id_estado,
    )
