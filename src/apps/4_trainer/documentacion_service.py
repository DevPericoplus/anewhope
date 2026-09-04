"""Servicio de análisis de documentación para el Trainer.

Encapsula la lógica de negocio para:
- Leer archivos del storage externo (external)
- Construir un prompt con árbol de directorios + contenido
- Enviar a Ollama para análisis (primera llamada)
- Enriquecer el informe con plantilla Jinja2 y segunda llamada a Ollama (fusión)
- Escribir resultado markdown en storage interno (internal)
- Notificar al Backend Core para actualizar estado del job
"""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from trainer_core_lookup import (
    notify_job_complete,
    payload_owner_user_id,
    resolve_account_folder,
)

logger = logging.getLogger("trainer_api")

# Extensiones de archivos legibles como texto
TEXT_EXTENSIONS: set[str] = {
    ".txt", ".md", ".csv", ".json", ".xml", ".html", ".htm",
    ".py", ".yml", ".yaml", ".log", ".cfg", ".ini", ".rst",
    ".tsv", ".css", ".js", ".ts", ".sql", ".sh", ".bat",
    ".toml", ".env", ".gitignore", ".dockerfile", ".conf",
    ".r", ".rmd", ".tex", ".bib", ".properties", ".gradle",
}


def _load_shared_module(module_name: str, relative_path: str) -> Any:
    """Carga un módulo compartido desde src/."""
    base = Path(__file__).resolve().parents[2]
    module_path = base / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar {module_name} desde {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Cargar módulos compartidos
_storage_structure = _load_shared_module(
    "storage_structure_doc",
    "2_shared_application/storage_access_structure.py",
)
get_folder_by_id_project = _storage_structure.get_folder_by_id_project
get_folder_by_id_version = _storage_structure.get_folder_by_id_version

_env_settings = _load_shared_module(
    "env_settings_doc",
    "2_shared_application/config/env_settings.py",
)
get_env_value = _env_settings.get_env_value

# Ruta al directorio de plantillas Jinja2
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
PROMPT_FUSION_DOCUMENTOS = "formateador_documental_documentos"


# ---------------------------------------------------------------------------
# Funciones auxiliares de renderizado y cálculo
# ---------------------------------------------------------------------------


def _render_template_report(template_vars: dict[str, Any]) -> str:
    """Renderiza la plantilla Jinja2 evaluacion_documental.j2.

    Args:
        template_vars: Diccionario con todas las variables para la plantilla

    Returns:
        Contenido markdown renderizado
    """
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        keep_trailing_newline=True,
    )
    template = env.get_template("evaluacion_documental.j2")
    return template.render(**template_vars)


def _format_elapsed_time(seconds: float) -> str:
    """Formatea segundos transcurridos en formato legible.

    Args:
        seconds: Tiempo en segundos

    Returns:
        Cadena formateada (ej: "5m 32s", "2h 15m 8s")
    """
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours = int(minutes // 60)
    mins = minutes % 60
    return f"{hours}h {mins}m {secs}s"


def _calculate_num_ctx(prompt_text: str) -> int:
    """Calcula num_ctx dinámicamente basado en la longitud del prompt.

    Estima ~3 caracteres por token, añade margen de 4096 tokens para la
    respuesta, y redondea al siguiente múltiplo de 2048. Limita entre
    8192 (mínimo) y 65536 (máximo).

    Args:
        prompt_text: Texto completo del prompt

    Returns:
        Valor de num_ctx para Ollama
    """
    estimated_tokens = len(prompt_text) // 3
    num_ctx = min(65536, max(8192, ((estimated_tokens + 4096) // 2048 + 1) * 2048))
    return num_ctx


def _compute_output_path(
    internal_base: str,
    account_folder: str,
    id_proyecto: int,
    id_version: int,
) -> Path:
    """Calcula la ruta del archivo de salida y crea los directorios necesarios.

    Args:
        internal_base: Ruta base del storage interno
        account_folder: Carpeta de cuenta (ORG##### o USER#####)
        id_proyecto: ID del proyecto
        id_version: ID de la versión

    Returns:
        Ruta absoluta completa del archivo de salida (aún no creado)
    """
    org_folder = account_folder
    prj_folder = get_folder_by_id_project(id_proyecto)
    ver_folder = get_folder_by_id_version(id_version)

    base = Path(os.path.expanduser(internal_base))
    output_dir = base / org_folder / prj_folder / ver_folder
    output_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    filename = now.strftime("%Y_%m_%d_%H%M") + "_analisis_documental.md"
    return output_dir / filename


def _is_text_file(filepath: Path) -> bool:
    """Determina si un archivo es legible como texto por su extensión."""
    return filepath.suffix.lower() in TEXT_EXTENSIONS


def _human_size(size_bytes: int) -> str:
    """Convierte bytes a formato legible (KB, MB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def _get_analisys_mode() -> str:
    """Obtiene el analisys_mode del .envglobal.

    Returns:
        analisys_mode: simulation, test o production (default: production)
    """
    # Leer .envglobal para obtener analisys_mode
    base_path = Path(__file__).resolve().parents[3]
    envglobal_path = base_path / ".envglobal"

    analisys_mode = "production"  # default

    if envglobal_path.exists():
        with open(envglobal_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("analisys_mode:"):
                    analisys_mode = line.split(":", 1)[1].strip()
                    break

    logger.info(f"[DOCUMENTACION] analisys_mode detectado: {analisys_mode}")
    return analisys_mode


def read_version_files(base_path: Path, analisys_mode: str = "production") -> tuple[str, str, int, int, int]:
    """Lee todos los archivos de una versión y genera árbol + contenido.

    Args:
        base_path: Ruta absoluta a la carpeta de la versión
        analisys_mode: Modo de análisis:
            - simulation: Solo metadata (nombres, tamaños, jerarquía), sin contenido
            - test: Análisis de subset (primeros 20 archivos de texto)
            - production: Análisis completo de contenido

    Returns:
        Tupla con (arbol_texto, contenido_texto, num_texto, num_binarios, total_kb)
    """
    if not base_path.exists():
        logger.warning("[DOCUMENTACION] Ruta no existe: %s", base_path)
        return "(Directorio vacío o no encontrado)", "", 0, 0, 0

    tree_lines: list[str] = []
    content_parts: list[str] = []
    num_text = 0
    num_binary = 0
    total_bytes = 0

    # Límite de archivos para modo test
    max_files_test = 20
    files_read_count = 0

    # Recorrer recursivamente
    all_files = sorted(base_path.rglob("*"))

    for filepath in all_files:
        if filepath.is_dir():
            continue

        relative = filepath.relative_to(base_path)
        file_size = filepath.stat().st_size
        total_bytes += file_size
        size_str = _human_size(file_size)

        if _is_text_file(filepath):
            num_text += 1
            tree_lines.append(f"  {relative} ({size_str})")

            # Decidir si leer contenido según el modo
            should_read_content = False

            if analisys_mode == "production":
                # Modo production: leer todo
                should_read_content = True
            elif analisys_mode == "test":
                # Modo test: solo primeros N archivos
                if files_read_count < max_files_test:
                    should_read_content = True
                    files_read_count += 1
            # elif analisys_mode == "simulation":
            #     should_read_content = False  (implícito, no se lee nada)

            if should_read_content:
                # Leer contenido
                try:
                    text = filepath.read_text(encoding="utf-8", errors="replace")
                    content_parts.append(f"--- [{relative}] ---\n{text}")
                except Exception as e:
                    content_parts.append(f"--- [{relative}] ---\n[Error leyendo archivo: {e}]")
                    logger.warning("[DOCUMENTACION] Error leyendo %s: %s", relative, e)
        else:
            num_binary += 1
            tree_lines.append(f"  {relative} ({size_str}) [BINARIO]")

    tree_text = "\n".join(tree_lines) if tree_lines else "(Sin archivos)"

    # En modo simulation, no hay contenido
    if analisys_mode == "simulation":
        content_text = "(Modo simulation: solo metadata, sin análisis de contenido)"
    elif analisys_mode == "test" and files_read_count < num_text:
        content_text = (
            f"(Modo test: análisis de {files_read_count} de {num_text} archivos)\n\n"
            + ("\n\n".join(content_parts) if content_parts else "(Sin contenido)")
        )
    else:
        content_text = "\n\n".join(content_parts) if content_parts else "(Sin contenido de texto)"

    total_kb = total_bytes // 1024

    return tree_text, content_text, num_text, num_binary, total_kb


def build_full_prompt(prompt_final: str, tree_text: str, content_text: str) -> str:
    """Construye el prompt completo para Ollama.

    Concatena el prompt del usuario con la estructura de archivos y su contenido.

    Args:
        prompt_final: Prompt compuesto (identidad + contexto + solicitud + modalidad)
        tree_text: Representación textual del árbol de directorios
        content_text: Contenido concatenado de todos los archivos de texto

    Returns:
        Prompt completo listo para enviar a Ollama
    """
    return (
        f"{prompt_final}\n\n"
        f"=== ESTRUCTURA DE DIRECTORIOS ===\n{tree_text}\n\n"
        f"=== CONTENIDO DE ARCHIVOS ===\n\n{content_text}"
    )


def process_documentacion(data: dict[str, Any]) -> None:
    """Proceso principal de análisis de documentación (ejecutado en background thread).

    Pasos:
    1. Leer archivos del storage externo
    2. Construir prompt con árbol + contenido
    3. Enviar a Ollama (primera llamada - análisis de documentación)
    4. Enriquecer informe: renderizar plantilla Jinja2 y fusionar con segunda
       llamada a Ollama usando el prompt de fusión almacenado en BD
    5. Escribir informe final enriquecido a disco
    6. Notificar a Backend Core

    Args:
        data: Diccionario con todos los datos del request (DocumentacionRequest)
    """
    job_id = data.get("id_job", 0)
    id_org = data.get("id_organizacion", 0)
    id_prj = data.get("id_proyecto", 0)
    id_ver = data.get("id_version", 0)
    id_user = payload_owner_user_id(data)
    prompt_final = data.get("prompt_final", "")
    modelo_nombre = data.get("modelo_nombre", "")

    start_time = time.time()
    logger.info(
        "[DOCUMENTACION] Thread background iniciado para job_id=%s org=%s prj=%s ver=%s",
        job_id, id_org, id_prj, id_ver,
    )

    try:
        # === PASO 0: Obtener modo de análisis ===
        analisys_mode = _get_analisys_mode()
        logger.info(
            "[DOCUMENTACION] Ejecutando en modo: %s "
            "(simulation=metadata only, test=subset, production=full)",
            analisys_mode,
        )

        # === PASO 1: Resolver carpeta de cuenta via Broker → Core ===
        org_folder, job_ctx = resolve_account_folder(
            organization_id=id_org,
            owner_user_id=id_user,
            project_id=id_prj,
            prompt_name=PROMPT_FUSION_DOCUMENTOS,
        )
        id_org = int(job_ctx.get("organization_id") or id_org)
        prj_folder = get_folder_by_id_project(id_prj)
        ver_folder = get_folder_by_id_version(id_ver)

        # === PASO 1b: Leer archivos del storage externo ===
        external_base = get_env_value(
            "backend_ia_base_storage",
            "~/data/anewhope/files/trainer_server/external",
        )

        version_path = (
            Path(os.path.expanduser(external_base))
            / org_folder / prj_folder / ver_folder
        )
        logger.info("[DOCUMENTACION] Leyendo archivos de: %s", version_path)

        tree_text, content_text, num_text, num_binary, total_kb = read_version_files(
            version_path,
            analisys_mode=analisys_mode,
        )
        logger.info(
            "[DOCUMENTACION] Arbol de directorios: %s archivos texto, "
            "%s binarios, %s KB total",
            num_text, num_binary, total_kb,
        )

        # === PASO 2: Construir prompt de análisis ===
        full_prompt = build_full_prompt(prompt_final, tree_text, content_text)
        logger.info(
            "[DOCUMENTACION] Prompt de análisis construido: %s caracteres totales",
            len(full_prompt),
        )

        # === PASO 3: Primera llamada a Ollama (análisis documental) ===
        model_name = modelo_nombre or "llama3:latest"
        num_ctx_analysis = _calculate_num_ctx(full_prompt)

        logger.info(
            "[DOCUMENTACION] [1/2] Enviando a Ollama: modelo=%s num_ctx=%d",
            model_name, num_ctx_analysis,
        )

        ollama_start = time.time()

        # Importar adaptador y DTOs (se cargan una vez y quedan en caché)
        ollama_dtos = _load_shared_module(
            "ollama_dtos_doc",
            "2_shared_application/dtos/ollama_dtos.py",
        )
        GenerateRequestDto = ollama_dtos.GenerateRequestDto

        from apitrainer_ollama import get_ollama_adapter
        adapter = get_ollama_adapter()

        logger.info(
            "[DOCUMENTACION] [1/2] num_ctx calculado: %d (prompt ~%d tokens estimados)",
            num_ctx_analysis, len(full_prompt) // 3,
        )

        request_dto = GenerateRequestDto(
            model=model_name,
            prompt=full_prompt,
            stream=False,
            options={
                "num_ctx": num_ctx_analysis,
                "num_predict": -1,
                "temperature": 0.3,
            },
        )

        response = adapter.generate(request_dto)
        ollama_elapsed = time.time() - ollama_start
        analisis_ollama = response.response if response.response else ""

        logger.info(
            "[DOCUMENTACION] [1/2] Respuesta de análisis recibida: %s caracteres en %s",
            len(analisis_ollama), _format_elapsed_time(ollama_elapsed),
        )

        if not analisis_ollama.strip():
            logger.error(
                "[DOCUMENTACION][ERROR] Ollama devolvió respuesta vacía para job_id=%s",
                job_id,
            )
            _notify_backend_core_error(
                job_id, id_org, id_prj, id_ver,
                "Ollama devolvió respuesta vacía en análisis",
            )
            return

        # === PASO 4: Enriquecer informe con Jinja2 + segunda llamada a Ollama ===
        logger.info(
            "[DOCUMENTACION] Iniciando enriquecimiento del informe con Jinja2",
        )

        # --- 4a: Reutilizar contexto resuelto via Broker → Backend Core ---
        nombre_organizacion = str(job_ctx.get("organization_name") or "")
        nombre_proyecto = str(job_ctx.get("project_name") or "")
        fusion_prompt = str(job_ctx.get("prompt") or "")
        logger.info(
            "[DOCUMENTACION] Contexto via Broker: org='%s', prj='%s' folder='%s'",
            nombre_organizacion,
            nombre_proyecto,
            org_folder,
        )

        # --- 4b: Calcular ruta de salida (antes de renderizar, para incluirla) ---
        internal_base = get_env_value(
            "backend_ia_reports_storage",
            "~/data/anewhope/files/trainer_server/internal/reports",
        )
        output_path = _compute_output_path(internal_base, org_folder, id_prj, id_ver)

        # --- 4c: Renderizar plantilla Jinja2 → "plantilla_informe" ---
        now = datetime.now(timezone.utc)
        template_vars: dict[str, Any] = {
            # Datos del payload original
            "id_job": job_id,
            "id_organizacion": id_org,
            "id_proyecto": id_prj,
            "id_version": id_ver,
            "nombre_job": data.get("nombre_job", ""),
            "descripcion_job": data.get("descripcion_job", ""),
            "id_template": data.get("id_template", 0),
            "template_nombre": data.get("template_nombre", ""),
            "modelo_nombre": model_name,
            "salida_nombre": data.get("salida_nombre", ""),
            "estado_nombre": data.get("estado_nombre", "Finalizado"),
            # Datos derivados
            "nombre_organizacion": nombre_organizacion,
            "nombre_proyecto": nombre_proyecto,
            "org_folder": org_folder,
            "prj_folder": prj_folder,
            "ver_folder": ver_folder,
            "ruta_external": f"{org_folder}/{prj_folder}/{ver_folder}",  # Solo ruta relativa, no path completo
            "ruta_internal": f"{org_folder}/{prj_folder}/{ver_folder}",  # Solo ruta relativa, no path completo
            "ruta_salida": os.path.basename(str(output_path)),  # Solo filename, no path completo
            # Estadísticas de archivos
            "num_text": num_text,
            "num_binary": num_binary,
            "total_files": num_text + num_binary,
            "total_kb": total_kb,
            "tree_text": tree_text,
            # Respuesta de Ollama (primera llamada - análisis)
            "ollama_response": analisis_ollama,
            # Datos de ejecución
            "fecha_ejecucion": now.strftime("%Y-%m-%d"),
            "hora_ejecucion": now.strftime("%H:%M:%S"),
            "tiempo_ollama": _format_elapsed_time(ollama_elapsed),
            "tiempo_total": _format_elapsed_time(time.time() - start_time),
        }

        plantilla_informe = _render_template_report(template_vars)
        logger.info(
            "[DOCUMENTACION] Plantilla Jinja2 renderizada: %d caracteres",
            len(plantilla_informe),
        )

        # --- 4d: Prompt de fusión (obtenido en 4a via Broker) ---
        if not fusion_prompt:
            # Fallback: si no hay prompt de fusión, escribir la plantilla directamente
            logger.warning(
                "[DOCUMENTACION] No se encontró prompt de fusión en BD. "
                "Escribiendo informe de plantilla sin fusionar.",
            )
            output_path.write_text(plantilla_informe, encoding="utf-8")
            logger.info("[DOCUMENTACION] Informe (sin fusionar) escrito en: %s", output_path)
        else:
            # --- 4e: Construir prompt de fusión con los dos documentos ---
            fusion_full_prompt = fusion_prompt.replace(
                "{plantilla_informe}", plantilla_informe,
            ).replace(
                "{analisis_ollama}", analisis_ollama,
            )

            logger.info(
                "[DOCUMENTACION] Prompt de fusión construido: %d caracteres "
                "(plantilla=%d + análisis=%d)",
                len(fusion_full_prompt), len(plantilla_informe), len(analisis_ollama),
            )

            # --- 4f: Segunda llamada a Ollama (fusión de documentos) ---
            fusion_num_ctx = _calculate_num_ctx(fusion_full_prompt)
            logger.info(
                "[DOCUMENTACION] [2/2] Enviando fusión a Ollama: "
                "modelo=%s num_ctx=%d",
                model_name, fusion_num_ctx,
            )

            fusion_start = time.time()

            fusion_request = GenerateRequestDto(
                model=model_name,
                prompt=fusion_full_prompt,
                stream=False,
                options={
                    "num_ctx": fusion_num_ctx,
                    "num_predict": -1,
                    "temperature": 0.2,
                },
            )

            fusion_response = adapter.generate(fusion_request)
            fusion_elapsed = time.time() - fusion_start
            final_report = fusion_response.response if fusion_response.response else ""

            logger.info(
                "[DOCUMENTACION] [2/2] Respuesta de fusión recibida: "
                "%d caracteres en %s",
                len(final_report), _format_elapsed_time(fusion_elapsed),
            )

            # === PASO 5: Escribir informe final a disco ===
            if final_report.strip():
                output_path.write_text(final_report, encoding="utf-8")
                logger.info(
                    "[DOCUMENTACION] Informe FINAL fusionado escrito en: %s",
                    output_path,
                )
            else:
                # Fallback: si la fusión devolvió vacío, escribir la plantilla
                logger.warning(
                    "[DOCUMENTACION] La fusión devolvió respuesta vacía. "
                    "Escribiendo informe de plantilla como fallback.",
                )
                output_path.write_text(plantilla_informe, encoding="utf-8")

        # === PASO 6: Notificar a Backend Core ===
        logger.info(
            "[DOCUMENTACION] Notificando a Backend Core: job_id=%s estado=finalizado",
            job_id,
        )

        descripcion = (
            f"Evaluación documental completada: {num_text} archivos texto, "
            f"{num_binary} binarios analizados. "
            f"Informe enriquecido con plantilla Jinja2 y fusión IA."
        )

        try:
            result = _notify_backend_core_complete(
                job_id=job_id,
                id_organizacion=id_org,
                id_proyecto=id_prj,
                id_version=id_ver,
                descripcion=descripcion,
                referencia_salida=str(output_path),
            )
            id_cambio = result.get("id_cambio", "?")
            logger.info("[DOCUMENTACION] Backend Core actualizado: id_cambio=%s", id_cambio)
        except Exception as e:
            logger.error(
                "[DOCUMENTACION][ERROR] Fallo al notificar Backend Core para job_id=%s: %s",
                job_id, e,
            )

        total_elapsed = time.time() - start_time
        logger.info(
            "[DOCUMENTACION] Proceso completado exitosamente para job_id=%s en %s",
            job_id, _format_elapsed_time(total_elapsed),
        )

    except Exception as e:
        total_elapsed = time.time() - start_time
        logger.error(
            "[DOCUMENTACION][ERROR] %s para job_id=%s (tras %s)",
            e, job_id, _format_elapsed_time(total_elapsed),
        )
        # Intentar notificar error al Backend Core
        try:
            _notify_backend_core_error(job_id, id_org, id_prj, id_ver, str(e))
        except Exception as notify_err:
            logger.error(
                "[DOCUMENTACION][ERROR] No se pudo notificar error al Backend Core: %s",
                notify_err,
            )


def _notify_backend_core_complete(
    job_id: int,
    id_organizacion: int,
    id_proyecto: int,
    id_version: int,
    descripcion: str,
    referencia_salida: str,
) -> dict[str, Any]:
    """Notifica el cierre exitoso del job via Broker → Backend Core."""
    return notify_job_complete(
        job_id=job_id,
        id_organizacion=id_organizacion,
        id_proyecto=id_proyecto,
        id_version=id_version,
        descripcion=descripcion,
        referencia_salida=referencia_salida,
        tipo_cambio="evaluacion_documental",
    )


def _notify_backend_core_error(
    job_id: int,
    id_organizacion: int,
    id_proyecto: int,
    id_version: int,
    error_message: str,
) -> None:
    """Notifica el fallo del job via Broker → Backend Core (estado=3)."""
    try:
        notify_job_complete(
            job_id=job_id,
            id_organizacion=id_organizacion,
            id_proyecto=id_proyecto,
            id_version=id_version,
            descripcion=f"Error en evaluación documental: {error_message}",
            referencia_salida="",
            tipo_cambio="evaluacion_documental_error",
            id_estado=3,
        )
    except Exception as e:
        logger.error(
            "[DOCUMENTACION][ERROR] Fallo al notificar error via Broker: %s",
            e,
        )
