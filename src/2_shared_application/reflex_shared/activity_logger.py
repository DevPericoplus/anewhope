"""
Sistema de logging de actividad para aplicaciones Reflex (frontend/backoffice).

Este módulo proporciona un logger configurado para registrar:
- Actividad del usuario (login, logout, navegación)
- Interacciones con el middleware
- Errores y warnings
- Mensajes de consola

Todos los logs se escriben a:
- console.log: archivo unificado para trazabilidad de soporte
- activity.log: archivo específico de actividad
- stdout: salida de consola en tiempo real
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Optional

# Constantes de rotación de logs
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


class ActivityLogger:
    """
    Logger de actividad para aplicaciones web Reflex.
    
    Escribe logs en:
    - Archivo: logs/console.log (unificado para soporte)
    - Archivo: logs/activity.log (actividad específica)
    - Consola: stdout (opcional)
    """
    
    def __init__(
        self,
        app_name: str,
        logs_dir: Path,
        log_to_console: bool = True,
        log_level: int = logging.INFO,
    ):
        """
        Inicializa el logger de actividad.
        
        Args:
            app_name: Nombre de la aplicación (frontend/backoffice)
            logs_dir: Directorio donde guardar los logs
            log_to_console: Si True, también muestra logs en consola
            log_level: Nivel de logging (default: INFO)
        """
        self.app_name = app_name
        self.logs_dir = logs_dir
        self._logger = self._setup_logger(log_to_console, log_level)
    
    def _setup_logger(self, log_to_console: bool, log_level: int) -> logging.Logger:
        """Configura el logger con handlers de archivo y consola."""
        
        logger_name = f"activity.{self.app_name}"
        logger = logging.getLogger(logger_name)
        
        # Evitar duplicados si ya está configurado
        if logger.handlers:
            return logger
        
        logger.setLevel(log_level)
        logger.propagate = False
        
        # Crear directorio de logs si no existe
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Filtro de contexto
        context_filter = AppContextFilter(self.app_name)
        logger.addFilter(context_filter)
        
        # Formato del log (legible para técnicos de soporte)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(app_name)-15s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        
        # Handler de archivo console.log (unificado para soporte)
        console_log_file = self.logs_dir / "console.log"
        console_file_handler = RotatingFileHandler(
            console_log_file,
            maxBytes=MAX_LOG_SIZE,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        console_file_handler.setFormatter(formatter)
        console_file_handler.setLevel(log_level)
        console_file_handler.addFilter(context_filter)
        logger.addHandler(console_file_handler)
        
        # Handler de archivo activity.log (específico de actividad)
        activity_log_file = self.logs_dir / "activity.log"
        activity_file_handler = RotatingFileHandler(
            activity_log_file,
            maxBytes=MAX_LOG_SIZE,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        activity_file_handler.setFormatter(formatter)
        activity_file_handler.setLevel(log_level)
        activity_file_handler.addFilter(context_filter)
        logger.addHandler(activity_file_handler)
        
        # Handler de consola (opcional)
        if log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            console_handler.setLevel(log_level)
            console_handler.addFilter(context_filter)
            logger.addHandler(console_handler)
        
        return logger
    
    def _log(self, level: int, message: str, **kwargs: Any) -> None:
        """Log con contexto adicional."""
        extra = {"app_name": self.app_name}
        extra.update(kwargs)
        self._logger.log(level, message, extra=extra)
    
    # ========================================
    # Métodos de logging por categoría
    # ========================================
    
    def info(self, message: str, **kwargs: Any) -> None:
        """Log de información general."""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs: Any) -> None:
        """Log de advertencia."""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs: Any) -> None:
        """Log de error."""
        self._log(logging.ERROR, message, **kwargs)
    
    def debug(self, message: str, **kwargs: Any) -> None:
        """Log de debug."""
        self._log(logging.DEBUG, message, **kwargs)
    
    # ========================================
    # Métodos específicos de actividad
    # ========================================
    
    def log_user_login(self, username: str, success: bool, user_id: Optional[int] = None) -> None:
        """Registra intento de login."""
        status = "SUCCESS" if success else "FAILED"
        msg = f"LOGIN {status} | user={username}"
        if user_id:
            msg += f" | user_id={user_id}"
        self._log(logging.INFO if success else logging.WARNING, msg)
    
    def log_user_logout(self, user_id: int, username: str) -> None:
        """Registra logout de usuario."""
        self._log(logging.INFO, f"LOGOUT | user_id={user_id} | user={username}")
    
    def log_navigation(self, user_id: int, menu: str) -> None:
        """Registra navegación del usuario."""
        self._log(logging.INFO, f"NAVIGATION | user_id={user_id} | menu={menu}")
    
    def log_middleware_request(
        self,
        endpoint: str,
        method: str = "GET",
        status_code: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        """Registra interacción con el middleware."""
        msg = f"MIDDLEWARE {method} {endpoint}"
        if status_code:
            msg += f" | status={status_code}"
        if error:
            msg += f" | error={error}"
            self._log(logging.ERROR, msg)
        else:
            self._log(logging.INFO, msg)
    
    def log_middleware_response(
        self,
        endpoint: str,
        success: bool,
        response_time_ms: Optional[float] = None,
    ) -> None:
        """Registra respuesta del middleware."""
        status = "OK" if success else "ERROR"
        msg = f"MIDDLEWARE RESPONSE {endpoint} | status={status}"
        if response_time_ms:
            msg += f" | time={response_time_ms:.2f}ms"
        level = logging.INFO if success else logging.ERROR
        self._log(level, msg)
    
    def log_permission_check(
        self,
        user_id: int,
        permission: str,
        granted: bool,
    ) -> None:
        """Registra verificación de permisos."""
        status = "GRANTED" if granted else "DENIED"
        self._log(
            logging.INFO if granted else logging.WARNING,
            f"PERMISSION CHECK | user_id={user_id} | permission={permission} | {status}",
        )
    
    def log_session_activity(
        self,
        user_id: int,
        activity: str,
    ) -> None:
        """Registra actividad de sesión."""
        self._log(logging.INFO, f"SESSION | user_id={user_id} | activity={activity}")
    
    def log_app_event(self, event: str, details: Optional[str] = None) -> None:
        """Registra evento de la aplicación."""
        msg = f"APP EVENT | {event}"
        if details:
            msg += f" | {details}"
        self._log(logging.INFO, msg)
    
    def log_startup(self) -> None:
        """Registra inicio de la aplicación."""
        self._log(logging.INFO, f"APPLICATION STARTUP | {self.app_name}")
    
    def log_shutdown(self) -> None:
        """Registra cierre de la aplicación."""
        self._log(logging.INFO, f"APPLICATION SHUTDOWN | {self.app_name}")

    # ========================================
    # Métodos específicos de asignaciones
    # ========================================

    def log_assignment_create(
        self,
        user_id: int,
        assignment_type: str,
        assignment_id: int,
        target_user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        project_id: Optional[int] = None,
        role_id: Optional[int] = None,
    ) -> None:
        """Registra creación de asignación."""
        msg = f"ASSIGNMENT_CREATE | user={user_id} | type={assignment_type} | id={assignment_id}"
        if target_user_id:
            msg += f" | target_user={target_user_id}"
        if organization_id:
            msg += f" | org={organization_id}"
        if project_id:
            msg += f" | project={project_id}"
        if role_id:
            msg += f" | role={role_id}"
        self._log(logging.INFO, msg)

    def log_assignment_update(
        self,
        user_id: int,
        assignment_type: str,
        assignment_id: int,
        changes: dict[str, Any],
    ) -> None:
        """Registra actualización de asignación."""
        changes_str = ", ".join(f"{k}={v}" for k, v in changes.items())
        msg = f"ASSIGNMENT_UPDATE | user={user_id} | type={assignment_type} | id={assignment_id} | changes=[{changes_str}]"
        self._log(logging.INFO, msg)

    def log_assignment_delete(
        self,
        user_id: int,
        assignment_type: str,
        assignment_id: int,
    ) -> None:
        """Registra eliminación de asignación."""
        msg = f"ASSIGNMENT_DELETE | user={user_id} | type={assignment_type} | id={assignment_id}"
        self._log(logging.WARNING, msg)

    def log_assignment_list(
        self,
        user_id: int,
        assignment_type: str,
        filter_id: int,
        count: int,
    ) -> None:
        """Registra consulta de lista de asignaciones."""
        filter_type = "org" if assignment_type == "organization" else "project"
        msg = f"ASSIGNMENT_LIST | user={user_id} | type={assignment_type} | {filter_type}={filter_id} | count={count}"
        self._log(logging.INFO, msg)


# ========================================
# Instancias singleton para cada aplicación
# ========================================

_frontend_logger: Optional[ActivityLogger] = None
_backoffice_logger: Optional[ActivityLogger] = None
_laimweb_logger: Optional[ActivityLogger] = None


def get_frontend_logger() -> ActivityLogger:
    """Obtiene el logger del frontend (singleton)."""
    global _frontend_logger
    if _frontend_logger is None:
        logs_dir = Path(__file__).resolve().parents[2] / "apps" / "5_web_frontend" / "logs"
        _frontend_logger = ActivityLogger("frontend", logs_dir)
    return _frontend_logger


def get_backoffice_logger() -> ActivityLogger:
    """Obtiene el logger del backoffice (singleton)."""
    global _backoffice_logger
    if _backoffice_logger is None:
        logs_dir = Path(__file__).resolve().parents[2] / "apps" / "6_web_backoffice" / "logs"
        _backoffice_logger = ActivityLogger("backoffice", logs_dir)
    return _backoffice_logger


def get_laimweb_logger() -> ActivityLogger:
    """Obtiene el logger de LAIM Web (singleton)."""
    global _laimweb_logger
    if _laimweb_logger is None:
        logs_dir = Path(__file__).resolve().parents[2] / "apps" / "9_laimweb" / "logs"
        _laimweb_logger = ActivityLogger("laimweb", logs_dir)
    return _laimweb_logger
