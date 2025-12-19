"""Utilidades de seguridad comunes para aplicaciones web con Reflex."""
import datetime
import logging
from pathlib import Path
from typing import Optional, Any

logger = logging.getLogger(__name__)


def get_client_ip(request: Any) -> Optional[str]:
    """
    Obtiene la dirección IP del cliente a partir de la solicitud web en Reflex.

    Args:
        request: Objeto de solicitud HTTP proporcionado por Reflex.

    Returns:
        La dirección IP del cliente como cadena, o None si no se puede determinar.

    Nota:
        - Este método debe ser invocado en el contexto del backend de Reflex,
          donde se tiene acceso al objeto de la solicitud.
        - Si hay proxies o balanceadores, se intentará extraer la IP original
          desde 'X-Forwarded-For'.
    """
    # Extraer la IP considerando posible uso de proxies
    # Reflex usa starlette bajo el capó, así que intentamos acceder a los headers típicos
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        # Podría ser una lista de IPs, tomamos la primera
        ip = x_forwarded_for.split(",")[0].strip()
        if ip:
            return ip
    # Si no existe 'x-forwarded-for', obtenerla directamente del scope/client
    if hasattr(request, "client") and request.client:
        return request.client.host
    # Starlette: request.scope['client'] es (host, port)
    scope = getattr(request, "scope", None)
    if scope and "client" in scope:
        return scope["client"][0]
    # Si no se puede determinar
    return None

def get_webbrowser_model(request: Any) -> Optional[str]:
    """
    Obtiene el modelo del navegador web utilizado por el cliente.

    Args:
        request: Objeto de solicitud HTTP proporcionado por Reflex.

    Returns:
        El modelo (user agent) del navegador como cadena, o None si no se puede determinar.

    Nota:
        - Extrae la cabecera 'User-Agent' de la solicitud HTTP.
        - Esta información depende de lo que envía el cliente, puede no estar presente.
    """
    # Intentar obtener el 'User-Agent' del header
    user_agent = request.headers.get("user-agent")
    if user_agent:
        return user_agent
    # También intentar en scope si fuera necesario
    scope = getattr(request, "scope", None)
    if scope and "headers" in scope:
        # Encabezados en scope son una lista de tuplas (bytes, bytes)
        for key, value in scope["headers"]:
            if key.lower() == b"user-agent":
                try:
                    return value.decode("utf-8")
                except Exception:
                    return None
    return None


def log_security_action(
    request: Any,
    action: str,
    entity_id: Optional[int] = None,
    log_file_path: Optional[Path] = None,
) -> bool:
    """
    Registra una acción de seguridad en un archivo de log en formato CSV.
    
    Esta función puede ser usada por todas las aplicaciones web que usen Reflex
    para registrar acciones de seguridad como creación de usuarios, login, etc.
    
    Formato del log CSV: fecha,ip,webbrowser,action,entity_id
    
    Args:
        request: Objeto de solicitud HTTP proporcionado por Reflex. Puede ser None.
        action: Descripción de la acción realizada (ej: "Created user", "User login", etc.).
        entity_id: Identificador opcional de la entidad relacionada (ej: user_id).
        log_file_path: Ruta opcional al archivo de log. Si es None, no se escribe el log.
    
    Returns:
        True si el log se escribió exitosamente, False en caso contrario.
    
    Nota:
        - Esta función debe ser invocada desde un contexto donde se tenga acceso
          al objeto request HTTP (endpoints API, eventos de backend, etc.).
        - Si el request es None, se registrará el log con IP y webbrowser vacíos.
        - Si log_file_path es None, la función retornará False sin escribir nada.
    """
    if log_file_path is None:
        logger.warning("log_file_path es None, no se puede escribir el log de seguridad")
        return False
    
    # Obtener datos relevantes
    now = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M")
    ip = ""
    webbrowser = ""
    
    # Intentar obtener IP y user agent si hay request
    if request:
        try:
            ip_result = get_client_ip(request)
            if ip_result:
                ip = ip_result
        except Exception as e:
            logger.debug(f"Error al obtener IP del cliente: {e}")
        
        try:
            webbrowser_result = get_webbrowser_model(request)
            if webbrowser_result:
                webbrowser = webbrowser_result
        except Exception as e:
            logger.debug(f"Error al obtener user agent: {e}")
    else:
        logger.debug("Request es None, IP y webbrowser estarán vacíos en el log")
    
    # Construir línea de log en formato CSV
    entity_id_str = str(entity_id) if entity_id is not None else ""
    log_line = f"{now},{ip},{webbrowser},{action},{entity_id_str}\n"
    
    # Escribir registro (crear archivo y directorio si no existen)
    try:
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        with log_file_path.open("a", encoding="utf-8") as log_file:
            log_file.write(log_line)
        logger.debug(f"Acción de seguridad registrada: {action} (entity_id: {entity_id})")
        return True
    except Exception as e:
        logger.error(f"Error al escribir en el log de seguridad {log_file_path}: {e}")
        return False
