"""Gestor del servidor ChromaDB para el backend IA (trainer).

Este módulo arranca un servidor ChromaDB embebido en un thread independiente
cuando el trainer se inicializa, proporcionando una base de datos vectorial
autónoma accesible vía HTTP.

Arquitectura:
    Trainer (FastAPI:8004) ──arranca──► ChromaDB Server (HTTP:8100)
    Trainer (chromadb.HttpClient) ──opera──► ChromaDB Server

Configuración:
    - Variables públicas: env.yaml (chroma_host, chroma_port, chroma_persist_directory, etc.)
    - Variables protegidas: protected_values.py (chroma_auth_token, chroma_auth_provider, etc.)
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import chromadb

logger = logging.getLogger(__name__)

# Referencia global al proceso del servidor
_chroma_process: subprocess.Popen[bytes] | None = None
_chroma_client: chromadb.HttpClient | None = None


def _get_env_value(name: str, default: str) -> str:
    """Obtiene un valor de entorno usando el sistema de configuración del proyecto.

    Intenta cargar desde env_settings.py (patrón obligatorio del proyecto).
    Si no está disponible, usa os.environ como fallback.
    """
    try:
        # Intentar usar el sistema de configuración del proyecto
        root_dir = Path(__file__).resolve().parents[3]
        if str(root_dir) not in sys.path:
            sys.path.insert(0, str(root_dir))
        from src.config_application.config.env_settings import get_env_value
        return get_env_value(name.upper(), default)
    except (ImportError, Exception):
        pass

    try:
        from src.shared_application.config.env_settings import get_env_value
        return get_env_value(name.upper(), default)
    except (ImportError, Exception):
        pass

    return os.environ.get(name.upper(), default)


def _get_protected_value(name: str, default: str = "") -> str:
    """Obtiene un valor protegido (credenciales) desde protected_values.py."""
    try:
        root_dir = Path(__file__).resolve().parents[3]
        if str(root_dir) not in sys.path:
            sys.path.insert(0, str(root_dir))
        from src.config_application.config.env_settings import get_protected_value
        value = get_protected_value(name, default)
        return str(value) if value is not None else default
    except (ImportError, Exception):
        pass

    try:
        from src.shared_application.config.env_settings import get_protected_value
        value = get_protected_value(name, default)
        return str(value) if value is not None else default
    except (ImportError, Exception):
        pass

    return os.environ.get(name.upper(), default)


def get_chroma_settings() -> dict[str, Any]:
    """Obtiene la configuración de ChromaDB desde las variables de entorno.

    Returns:
        Diccionario con la configuración completa de ChromaDB.
    """
    persist_dir = _get_env_value("CHROMA_PERSIST_DIRECTORY", "~/data/anewhope/files/trainer_server/persistence/chroma")
    persist_dir = os.path.expanduser(persist_dir)

    return {
        "host": _get_env_value("CHROMA_HOST", "localhost"),
        "port": int(_get_env_value("CHROMA_PORT", "8100")),
        "persist_directory": persist_dir,
        "collection_name": _get_env_value("CHROMA_COLLECTION_NAME", "myllm_embeddings"),
        "anonymized_telemetry": _get_env_value("CHROMA_ANONYMIZED_TELEMETRY", "false").lower() == "true",
        "log_level": _get_env_value("CHROMA_LOG_LEVEL", "INFO"),
        "auth_token": _get_protected_value("chroma_auth_token", ""),
        "auth_provider": _get_protected_value("chroma_auth_provider", ""),
        "auth_credentials_provider": _get_protected_value("chroma_auth_credentials_provider", ""),
    }


def start_chroma_server() -> bool:
    """Arranca el servidor ChromaDB como proceso independiente.

    El servidor se ejecuta en un subproceso separado para funcionar de forma
    autónoma. El trainer puede operar sobre él mediante chromadb.HttpClient.

    Returns:
        True si el servidor arrancó correctamente, False en caso de error.
    """
    global _chroma_process

    if _chroma_process is not None and _chroma_process.poll() is None:
        logger.info("[CHROMADB] El servidor ya está en ejecución (PID=%s)", _chroma_process.pid)
        return True

    settings = get_chroma_settings()
    host = settings["host"]
    port = settings["port"]
    persist_dir = settings["persist_directory"]
    log_level = settings["log_level"]

    # Crear directorio de persistencia si no existe
    persist_path = Path(persist_dir)
    persist_path.mkdir(parents=True, exist_ok=True)
    logger.info("[CHROMADB] Directorio de persistencia: %s", persist_dir)

    # Construir comando para arrancar el servidor ChromaDB
    # Desde ChromaDB 1.5.0, el CLI nativo es 'chroma run' (binario Rust)
    venv_bin = Path(sys.executable).parent
    chroma_cli = venv_bin / "chroma"

    chroma_cmd = [
        str(chroma_cli), "run",
        "--host", "0.0.0.0",
        "--port", str(port),
        "--path", persist_dir,
    ]

    # Configurar variables de entorno para el proceso del servidor
    env = os.environ.copy()
    env["ANONYMIZED_TELEMETRY"] = str(settings["anonymized_telemetry"]).lower()
    env["CHROMA_SERVER_LOG_LEVEL"] = log_level

    # Configurar autenticación si hay token
    # NOTA: En ChromaDB 1.5.0+, la autenticación se configura vía variables de entorno
    auth_token = settings["auth_token"]
    if auth_token and auth_token != "CAMBIAR-EN-PRODUCCION-token-seguro-aqui":
        env["CHROMA_SERVER_AUTHN_PROVIDER"] = settings["auth_provider"]
        env["CHROMA_SERVER_AUTHN_CREDENTIALS"] = auth_token
        logger.info("[CHROMADB] Autenticación por token habilitada")
    else:
        logger.warning("[CHROMADB] Sin autenticación configurada (solo desarrollo)")

    try:
        logger.info(
            "[CHROMADB] Arrancando servidor en %s:%s (persist=%s, log_level=%s)",
            host, port, persist_dir, log_level,
        )

        # Asegurar que el directorio de logs existe
        logs_dir = Path(__file__).resolve().parent / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        _chroma_process = subprocess.Popen(
            chroma_cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )

        logger.info("[CHROMADB] Proceso arrancado con PID=%s", _chroma_process.pid)

        # Esperar a que el servidor esté disponible
        if _wait_for_server(host="localhost", port=port, timeout=30):
            logger.info("[CHROMADB] Servidor disponible en http://localhost:%s", port)
            return True
        else:
            logger.error("[CHROMADB] Timeout esperando al servidor en puerto %s", port)
            stop_chroma_server()
            return False

    except Exception as exc:
        logger.error("[CHROMADB] Error arrancando servidor: %s", exc, exc_info=True)
        return False


def _wait_for_server(host: str, port: int, timeout: int = 30) -> bool:
    """Espera a que el servidor ChromaDB esté disponible.

    Args:
        host: Host donde escucha el servidor.
        port: Puerto donde escucha el servidor.
        timeout: Segundos máximos de espera.

    Returns:
        True si el servidor responde, False si se agota el timeout.
    """
    import httpx

    # ChromaDB 1.5.0 usa API v2 (v1 está deprecada)
    url = f"http://{host}:{port}/api/v2/heartbeat"
    start_time = time.time()
    attempt = 0

    while time.time() - start_time < timeout:
        attempt += 1
        try:
            response = httpx.get(url, timeout=2.0)
            if response.status_code == 200:
                elapsed = time.time() - start_time
                logger.info(
                    "[CHROMADB] Heartbeat OK tras %d intentos (%.1fs)",
                    attempt, elapsed,
                )
                return True
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout):
            pass
        except Exception as exc:
            logger.debug("[CHROMADB] Intento %d: %s", attempt, exc)

        time.sleep(1.0)

    return False


def stop_chroma_server() -> None:
    """Detiene el servidor ChromaDB si está en ejecución."""
    global _chroma_process, _chroma_client

    _chroma_client = None

    if _chroma_process is not None:
        pid = _chroma_process.pid
        logger.info("[CHROMADB] Deteniendo servidor (PID=%s)...", pid)
        try:
            _chroma_process.terminate()
            _chroma_process.wait(timeout=10)
            logger.info("[CHROMADB] Servidor detenido correctamente (PID=%s)", pid)
        except subprocess.TimeoutExpired:
            logger.warning("[CHROMADB] Forzando kill del servidor (PID=%s)", pid)
            _chroma_process.kill()
            _chroma_process.wait(timeout=5)
        except Exception as exc:
            logger.error("[CHROMADB] Error deteniendo servidor: %s", exc)
        finally:
            _chroma_process = None


def get_chroma_client() -> chromadb.HttpClient | None:
    """Obtiene un cliente HTTP para operar sobre el servidor ChromaDB.

    El cliente se crea como singleton y reutiliza la conexión.

    Returns:
        Cliente HTTP de ChromaDB o None si el servidor no está disponible.
    """
    global _chroma_client

    if _chroma_client is not None:
        return _chroma_client

    settings = get_chroma_settings()
    port = settings["port"]
    auth_token = settings["auth_token"]

    try:
        client_kwargs: dict[str, Any] = {
            "host": "localhost",
            "port": port,
        }

        # Configurar autenticación del cliente si hay token
        if auth_token:
            client_kwargs["headers"] = {
                "Authorization": f"Bearer {auth_token}",
            }

        _chroma_client = chromadb.HttpClient(**client_kwargs)

        # Verificar conexión con heartbeat
        _chroma_client.heartbeat()
        logger.info("[CHROMADB] Cliente HTTP conectado a localhost:%s", port)

        return _chroma_client
    except Exception as exc:
        logger.error("[CHROMADB] Error conectando al servidor: %s", exc)
        _chroma_client = None
        return None


def get_or_create_collection(
    collection_name: str | None = None,
) -> chromadb.Collection | None:
    """Obtiene o crea una colección en ChromaDB.

    Args:
        collection_name: Nombre de la colección. Si es None, usa la configurada.

    Returns:
        Colección de ChromaDB o None si no se pudo crear.
    """
    client = get_chroma_client()
    if client is None:
        logger.error("[CHROMADB] No hay cliente disponible para crear colección")
        return None

    if collection_name is None:
        settings = get_chroma_settings()
        collection_name = settings["collection_name"]

    try:
        collection = client.get_or_create_collection(name=collection_name)
        logger.info(
            "[CHROMADB] Colección '%s' disponible (count=%d)",
            collection_name,
            collection.count(),
        )
        return collection
    except Exception as exc:
        logger.error("[CHROMADB] Error creando colección '%s': %s", collection_name, exc)
        return None


def is_server_running() -> bool:
    """Verifica si el servidor ChromaDB está en ejecución y responde.

    Returns:
        True si el servidor responde al heartbeat.
    """
    if _chroma_process is None or _chroma_process.poll() is not None:
        return False

    settings = get_chroma_settings()
    try:
        import httpx
        response = httpx.get(
            f"http://localhost:{settings['port']}/api/v2/heartbeat",
            timeout=5.0,
        )
        return response.status_code == 200
    except Exception:
        return False


def get_server_info() -> dict[str, Any]:
    """Obtiene información del estado del servidor ChromaDB.

    Returns:
        Diccionario con información del servidor.
    """
    settings = get_chroma_settings()
    running = is_server_running()

    info: dict[str, Any] = {
        "running": running,
        "host": settings["host"],
        "port": settings["port"],
        "persist_directory": settings["persist_directory"],
        "collection_name": settings["collection_name"],
        "pid": _chroma_process.pid if _chroma_process and _chroma_process.poll() is None else None,
        "authenticated": bool(settings["auth_token"]),
    }

    if running:
        client = get_chroma_client()
        if client is not None:
            try:
                info["heartbeat"] = client.heartbeat()
                info["collections"] = [c.name for c in client.list_collections()]
                info["version"] = chromadb.__version__
            except Exception as exc:
                info["error"] = str(exc)

    return info
