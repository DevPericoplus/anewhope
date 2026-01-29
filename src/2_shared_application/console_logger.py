"""
Sistema de logging de consola unificado para todas las aplicaciones.

Este módulo proporciona configuración de logging que escribe simultáneamente a:
- Consola (stdout): para visualización en tiempo real
- Archivo console.log: para trazabilidad y soporte técnico

Uso:
    from src.2_shared_application.console_logger import setup_console_logging

    # En el punto de entrada de cada aplicación (main.py o similar)
    logger = setup_console_logging("backend_core", logs_dir)
    logger.info("Aplicación iniciada")
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


# Formato legible para técnicos de soporte
SUPPORT_LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(app_name)-15s | %(message)s"
)
SUPPORT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Tamaño máximo del archivo de log (10 MB) y número de backups
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5


class AppContextFilter(logging.Filter):
    """Filtro que añade el nombre de la aplicación al contexto del log."""

    def __init__(self, app_name: str):
        super().__init__()
        self.app_name = app_name

    def filter(self, record: logging.LogRecord) -> bool:
        """Añade app_name al registro si no existe."""
        if not hasattr(record, "app_name"):
            record.app_name = self.app_name
        return True


def setup_console_logging(
    app_name: str,
    logs_dir: Path | str,
    log_level: int = logging.INFO,
    log_to_console: bool = True,
    max_bytes: int = MAX_LOG_SIZE,
    backup_count: int = BACKUP_COUNT,
) -> logging.Logger:
    """
    Configura el logging de consola para una aplicación.

    Args:
        app_name: Nombre identificador de la aplicación (ej: "backend_core", "middleware")
        logs_dir: Directorio donde guardar console.log
        log_level: Nivel mínimo de logging (default: INFO)
        log_to_console: Si True, también muestra en stdout (default: True)
        max_bytes: Tamaño máximo del archivo antes de rotar (default: 10MB)
        backup_count: Número de archivos de backup a mantener (default: 5)

    Returns:
        Logger configurado para la aplicación

    Example:
        >>> from pathlib import Path
        >>> logs_dir = Path("/app/logs")
        >>> logger = setup_console_logging("backend_core", logs_dir)
        >>> logger.info("Servidor iniciado en puerto 8003")
    """
    if isinstance(logs_dir, str):
        logs_dir = Path(logs_dir)

    # Crear directorio de logs si no existe
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Logger principal para la aplicación
    logger_name = f"console.{app_name}"
    logger = logging.getLogger(logger_name)

    # Evitar configuración duplicada
    if logger.handlers:
        return logger

    logger.setLevel(log_level)
    logger.propagate = False  # Evitar duplicados en root logger

    # Añadir filtro de contexto
    context_filter = AppContextFilter(app_name)
    logger.addFilter(context_filter)

    # Formatter común
    formatter = logging.Formatter(SUPPORT_LOG_FORMAT, datefmt=SUPPORT_DATE_FORMAT)

    # Handler de archivo con rotación
    log_file = logs_dir / "console.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    file_handler.addFilter(context_filter)
    logger.addHandler(file_handler)

    # Handler de consola
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        console_handler.addFilter(context_filter)
        logger.addHandler(console_handler)

    return logger


def get_console_logger(app_name: str) -> logging.Logger:
    """
    Obtiene un logger de consola ya configurado.

    Si no existe, devuelve el logger sin handlers (se debe llamar a setup_console_logging primero).

    Args:
        app_name: Nombre de la aplicación

    Returns:
        Logger para la aplicación
    """
    return logging.getLogger(f"console.{app_name}")


class ConsoleLoggerAdapter:
    """
    Adaptador que facilita el logging con contexto adicional.

    Proporciona métodos convenientes para loguear eventos comunes
    de forma consistente entre aplicaciones.
    """

    def __init__(self, logger: logging.Logger, app_name: str):
        """
        Inicializa el adaptador.

        Args:
            logger: Logger configurado
            app_name: Nombre de la aplicación
        """
        self._logger = logger
        self.app_name = app_name

    # ========================================
    # Métodos básicos de logging
    # ========================================

    def debug(self, message: str) -> None:
        """Log de debug."""
        self._logger.debug(message)

    def info(self, message: str) -> None:
        """Log de información."""
        self._logger.info(message)

    def warning(self, message: str) -> None:
        """Log de advertencia."""
        self._logger.warning(message)

    def error(self, message: str) -> None:
        """Log de error."""
        self._logger.error(message)

    def critical(self, message: str) -> None:
        """Log crítico."""
        self._logger.critical(message)

    def exception(self, message: str) -> None:
        """Log de excepción con traceback."""
        self._logger.exception(message)

    # ========================================
    # Métodos de eventos de aplicación
    # ========================================

    def startup(self, host: str = "", port: int = 0) -> None:
        """Registra inicio de la aplicación."""
        msg = "APPLICATION STARTUP"
        if host and port:
            msg += f" | listening on {host}:{port}"
        self._logger.info(msg)

    def shutdown(self) -> None:
        """Registra cierre de la aplicación."""
        self._logger.info("APPLICATION SHUTDOWN")

    def ready(self, details: str = "") -> None:
        """Registra que la aplicación está lista."""
        msg = "APPLICATION READY"
        if details:
            msg += f" | {details}"
        self._logger.info(msg)

    # ========================================
    # Métodos de eventos HTTP/API
    # ========================================

    def request(
        self,
        method: str,
        path: str,
        client_ip: str = "",
        user_id: Optional[int] = None,
    ) -> None:
        """Registra una petición HTTP entrante."""
        msg = f"REQUEST {method} {path}"
        if client_ip:
            msg += f" | client={client_ip}"
        if user_id:
            msg += f" | user_id={user_id}"
        self._logger.info(msg)

    def response(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: Optional[float] = None,
    ) -> None:
        """Registra una respuesta HTTP."""
        msg = f"RESPONSE {method} {path} | status={status_code}"
        if duration_ms is not None:
            msg += f" | duration={duration_ms:.2f}ms"
        level = logging.INFO if status_code < 400 else logging.WARNING
        self._logger.log(level, msg)

    def api_call(
        self,
        target: str,
        method: str,
        endpoint: str,
        status_code: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        """Registra llamada a API externa."""
        msg = f"API CALL {target} | {method} {endpoint}"
        if status_code:
            msg += f" | status={status_code}"
        if error:
            msg += f" | error={error}"
            self._logger.error(msg)
        else:
            self._logger.info(msg)

    # ========================================
    # Métodos de eventos de negocio
    # ========================================

    def operation(
        self,
        operation_name: str,
        success: bool = True,
        details: str = "",
        user_id: Optional[int] = None,
    ) -> None:
        """Registra una operación de negocio."""
        status = "SUCCESS" if success else "FAILED"
        msg = f"OPERATION {operation_name} | {status}"
        if user_id:
            msg += f" | user_id={user_id}"
        if details:
            msg += f" | {details}"
        level = logging.INFO if success else logging.ERROR
        self._logger.log(level, msg)

    def auth(
        self,
        action: str,
        username: str = "",
        user_id: Optional[int] = None,
        success: bool = True,
        reason: str = "",
    ) -> None:
        """Registra evento de autenticación."""
        status = "SUCCESS" if success else "FAILED"
        msg = f"AUTH {action} | {status}"
        if username:
            msg += f" | user={username}"
        if user_id:
            msg += f" | user_id={user_id}"
        if reason:
            msg += f" | reason={reason}"
        level = logging.INFO if success else logging.WARNING
        self._logger.log(level, msg)

    def permission(
        self,
        action: str,
        permission: str,
        granted: bool,
        user_id: Optional[int] = None,
    ) -> None:
        """Registra verificación de permisos."""
        status = "GRANTED" if granted else "DENIED"
        msg = f"PERMISSION {action} | {permission} | {status}"
        if user_id:
            msg += f" | user_id={user_id}"
        level = logging.INFO if granted else logging.WARNING
        self._logger.log(level, msg)

    def data(
        self,
        operation: str,
        entity: str,
        entity_id: Optional[int] = None,
        success: bool = True,
        details: str = "",
    ) -> None:
        """Registra operación de datos (CRUD)."""
        status = "OK" if success else "ERROR"
        msg = f"DATA {operation} | {entity}"
        if entity_id:
            msg += f" | id={entity_id}"
        msg += f" | {status}"
        if details:
            msg += f" | {details}"
        level = logging.INFO if success else logging.ERROR
        self._logger.log(level, msg)

    # ========================================
    # Métodos de eventos de sistema
    # ========================================

    def config(self, key: str, value: str, masked: bool = False) -> None:
        """Registra configuración cargada."""
        display_value = "****" if masked else value
        self._logger.info(f"CONFIG | {key}={display_value}")

    def connection(
        self,
        service: str,
        status: str,
        details: str = "",
    ) -> None:
        """Registra estado de conexión a servicio externo."""
        msg = f"CONNECTION {service} | {status}"
        if details:
            msg += f" | {details}"
        level = logging.INFO if status.upper() == "OK" else logging.WARNING
        self._logger.log(level, msg)

    def sync(
        self,
        source: str,
        target: str,
        status: str,
        records: Optional[int] = None,
    ) -> None:
        """Registra sincronización de datos."""
        msg = f"SYNC {source} -> {target} | {status}"
        if records is not None:
            msg += f" | records={records}"
        self._logger.info(msg)


def create_console_logger(
    app_name: str,
    logs_dir: Path | str,
    **kwargs,
) -> ConsoleLoggerAdapter:
    """
    Crea y configura un logger de consola con adaptador.

    Función de conveniencia que combina setup_console_logging y ConsoleLoggerAdapter.

    Args:
        app_name: Nombre de la aplicación
        logs_dir: Directorio de logs
        **kwargs: Argumentos adicionales para setup_console_logging

    Returns:
        ConsoleLoggerAdapter configurado

    Example:
        >>> logger = create_console_logger("backend_core", Path("./logs"))
        >>> logger.startup(host="0.0.0.0", port=8003)
        >>> logger.operation("create_user", success=True, user_id=1)
    """
    raw_logger = setup_console_logging(app_name, logs_dir, **kwargs)
    return ConsoleLoggerAdapter(raw_logger, app_name)


# ========================================
# Funciones de conveniencia por aplicación
# ========================================

_loggers: dict[str, ConsoleLoggerAdapter] = {}


def get_app_logger(app_name: str, logs_dir: Optional[Path] = None) -> ConsoleLoggerAdapter:
    """
    Obtiene o crea un logger para una aplicación (singleton).

    Args:
        app_name: Nombre de la aplicación
        logs_dir: Directorio de logs (solo necesario la primera vez)

    Returns:
        ConsoleLoggerAdapter para la aplicación
    """
    global _loggers

    if app_name not in _loggers:
        if logs_dir is None:
            # Intentar determinar logs_dir automáticamente
            base = Path(__file__).resolve().parents[1] / "apps"
            app_dirs = {
                "backend_core": "3_backend",
                "trainer": "4_trainer",
                "frontend": "5_web_frontend",
                "backoffice": "6_web_backoffice",
                "middleware": "7_service_frontend",
                "broker": "8_service_backend",
            }
            if app_name in app_dirs:
                logs_dir = base / app_dirs[app_name] / "logs"
            else:
                raise ValueError(f"logs_dir requerido para app desconocida: {app_name}")

        _loggers[app_name] = create_console_logger(app_name, logs_dir)

    return _loggers[app_name]
