"""Utilidades de seguridad comunes para aplicaciones web con Reflex."""
import ast
import datetime
import importlib.util
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional, Tuple

# requests se importa de forma lazy en las funciones que lo necesitan
# para evitar problemas de caché durante el desarrollo
requests = None  # Se cargará dinámicamente cuando sea necesario


def _get_requests_module():
    """Importa requests de forma lazy para evitar problemas de caché."""
    global requests
    if requests is None:
        try:
            import requests as req_module
            requests = req_module
        except ImportError:
            logging.warning(
                "El módulo 'requests' no está instalado. "
                "La funcionalidad de SMS no estará disponible."
            )
    return requests

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

# SMS provider https://www.infobip.com/es

def _load_sms_credentials_from_file(protected_values_path: Path) -> dict[str, str]:
    """Carga credenciales desde protected_values.py sin ejecutar código."""

    try:
        content = protected_values_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise FileNotFoundError(
            f"No se pudo leer protected_values.py en {protected_values_path}"
        ) from exc

    try:
        tree = ast.parse(content, filename=str(protected_values_path))
    except SyntaxError as exc:
        raise ValueError("protected_values.py no es válido") from exc

    allowed_keys = {"sms_api_url", "sms_api_key", "sms_sender_id"}
    values: dict[str, str] = {}

    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
        else:
            continue

        for target in targets:
            if isinstance(target, ast.Name) and target.id in allowed_keys:
                try:
                    literal_value = ast.literal_eval(node.value)
                except (ValueError, SyntaxError) as exc:
                    raise ValueError(
                        f"Valor inválido para {target.id} en protected_values.py"
                    ) from exc
                if not isinstance(literal_value, str):
                    raise ValueError(
                        f"{target.id} debe ser una cadena en protected_values.py"
                    )
                values[target.id] = literal_value

    return values


def get_sms_api_credentials() -> Tuple[str, str, str]:
    """
    Obtiene credenciales SMS desde variables de entorno o protected_values.py.

    Returns:
        Tupla (sms_api_url, sms_api_key, sms_sender_id).
        Si sms_sender_id no está definido, retorna "ServiceSMS" por defecto.

    Raises:
        FileNotFoundError: Si no existe protected_values.py cuando se requiere.
        ValueError: Si alguna de las variables requeridas no se encuentra o no es válida.

    Nota:
        - Prioriza variables de entorno: SMS_API_URL, SMS_API_KEY, SMS_SENDER_ID.
        - Si no están definidas, lee protected_values.py de forma segura
          (sin ejecutar código).
        - El sms_sender_id puede ser un remitente alfanumérico o un número de teléfono.
    """
    sms_api_url = os.environ.get("SMS_API_URL")
    sms_api_key = os.environ.get("SMS_API_KEY")
    sms_sender_id = os.environ.get("SMS_SENDER_ID", "ServiceSMS")

    if sms_api_url and sms_api_key:
        return sms_api_url, sms_api_key, sms_sender_id

    env_settings = _load_env_settings_module("shared_env_settings")
    protected_values_path = env_settings.get_protected_values_path()
    if not protected_values_path.exists():
        raise FileNotFoundError(
            f"No se encontró protected_values.py en {protected_values_path}"
        )

    values = _load_sms_credentials_from_file(protected_values_path)
    sms_api_url = values.get("sms_api_url")
    sms_api_key = values.get("sms_api_key")
    sms_sender_id = values.get("sms_sender_id", "ServiceSMS")

    if not sms_api_url or not sms_api_key:
        raise ValueError(
            "sms_api_url o sms_api_key no se encontraron en protected_values.py"
        )

    return sms_api_url, sms_api_key, sms_sender_id


def _load_env_settings_module(module_name: str) -> object:
    """Carga el módulo de configuración compartida."""

    module_path = (
        Path(__file__).resolve().parents[2]
        / "2_shared_application/config/env_settings.py"
    )
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar el módulo de configuración")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def send_sms_details_to_log(
    otp: str,
    phone_number: str,
    success: bool,
    response_data: Optional[dict] = None,
    error_message: Optional[str] = None,
) -> bool:
    """
    Registra los detalles del envío de un SMS en el archivo de log de seguridad.
    
    Escribe en el archivo frontend_secure.log con el formato CSV:
    fecha,ip,webbrowser,action,entity_id
    
    Args:
        otp: Código OTP que se intentó enviar.
        phone_number: Número de teléfono destinatario.
        success: True si el SMS se envió exitosamente, False en caso contrario.
        response_data: Datos de respuesta de la API (opcional, solo si success=True).
        error_message: Mensaje de error (opcional, solo si success=False).
    
    Returns:
        True si el log se escribió exitosamente, False en caso contrario.
    
    Nota:
        - El archivo de log se encuentra en: src/apps/5_web_frontend/logs/frontend_secure.log
        - El formato de fecha es: YYYY-MM-DD-HH:MM (igual que otros logs de seguridad)
        - La acción registrada será "SMS enviado"
        - El entity_id incluirá el número de teléfono y el OTP
    """
    # Ruta al archivo de log del frontend
    project_root = Path(__file__).parent.parent.parent.parent
    log_file_path = project_root / "src" / "apps" / "5_web_frontend" / "logs" / "frontend_secure.log"
    
    # Obtener fecha en el formato correcto (YYYY-MM-DD-HH:MM)
    now = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M")
    
    # Construir entity_id con información relevante
    # Incluimos el número de teléfono y el OTP para trazabilidad
    entity_id = f"{phone_number}|OTP:{otp}"
    if success and response_data:
        # Incluir información de la respuesta de la API si está disponible
        try:
            # Intentar extraer messageId o status de la respuesta
            if isinstance(response_data, dict):
                messages = response_data.get("messages", [])
                if messages and isinstance(messages, list) and len(messages) > 0:
                    msg = messages[0]
                    message_id = msg.get("messageId", "")
                    if message_id:
                        entity_id += f"|MsgID:{message_id}"
                    
                    # Incluir estado del mensaje si está disponible
                    status = msg.get("status", {})
                    if isinstance(status, dict):
                        status_name = status.get("name", "")
                        status_description = status.get("description", "")
                        if status_name:
                            entity_id += f"|Status:{status_name}"
                        if status_description:
                            # Limitar longitud de la descripción
                            entity_id += f"|Desc:{status_description[:30]}"
        except (KeyError, IndexError, TypeError) as e:
            logger.debug(f"No se pudo extraer información de la respuesta: {e}")
    elif not success and error_message:
        entity_id += f"|Error:{error_message[:50]}"  # Limitar longitud del error
    
    # IP y webbrowser vacíos (no hay request HTTP en este contexto)
    ip = ""
    webbrowser = ""
    action = "SMS enviado"
    
    # Construir línea de log en formato CSV
    log_line = f"{now},{ip},{webbrowser},{action},{entity_id}\n"
    
    # Escribir registro (crear archivo y directorio si no existen)
    try:
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        with log_file_path.open("a", encoding="utf-8") as log_file:
            log_file.write(log_line)
        logger.debug(f"Detalles de SMS registrados en log: {phone_number} - OTP: {otp} - Success: {success}")
        return True
    except Exception as e:
        logger.error(f"Error al escribir en el log de SMS {log_file_path}: {e}")
        return False


def send_message_by_sms(otp: str, phone_number: str) -> bool:
    """
    Envía un mensaje SMS con un código OTP a un número de teléfono usando la API de Infobip.
    
    Args:
        otp: Código OTP de 4 dígitos a enviar en el mensaje.
        phone_number: Número de teléfono del destinatario en formato internacional (ej: +34639775978).
    
    Returns:
        True si el mensaje se envió exitosamente, False en caso contrario.
    
    Raises:
        FileNotFoundError: Si no se encuentra el archivo protected_values.py.
        ValueError: Si las credenciales de la API no están disponibles.
        ImportError: Si el módulo 'requests' no está instalado.
        requests.RequestException: Si hay un error en la comunicación con la API.
    
    Nota:
        - Utiliza las credenciales obtenidas de get_sms_api_credentials().
        - El mensaje enviado será: "Su código OTP es: {otp}".
        - La función valida que el OTP tenga 4 dígitos antes de enviar.
        - Requiere que el módulo 'requests' esté instalado.
    """
    # Verificar que requests esté disponible (lazy import)
    req = _get_requests_module()
    if req is None:
        logger.error("El módulo 'requests' no está instalado. Instálalo con: pip install requests")
        send_sms_details_to_log(otp, phone_number or "N/A", success=False, error_message="requests module not installed")
        return False
    
    # Validar que el OTP tenga 4 dígitos
    if not otp or len(otp) != 4 or not otp.isdigit():
        logger.error(f"El OTP debe tener exactamente 4 dígitos. OTP recibido: {otp}")
        send_sms_details_to_log(otp, phone_number or "N/A", success=False, error_message=f"OTP inválido: {otp}")
        return False
    
    # Validar formato del número de teléfono
    if not phone_number or not phone_number.startswith("+"):
        logger.error(
            f"El número de teléfono debe estar en formato internacional (ej: +34639775978). "
            f"Recibido: {phone_number}"
        )
        send_sms_details_to_log(otp, phone_number or "N/A", success=False, error_message=f"Número de teléfono inválido: {phone_number}")
        return False
    
    try:
        # Obtener credenciales de la API
        sms_api_url, sms_api_key, sms_sender_id = get_sms_api_credentials()
        
        # Construir el endpoint de la API de Infobip
        # La URL base ya viene completa desde protected_values.py
        endpoint = f"{sms_api_url}/sms/2/text/advanced"
        
        # Preparar headers
        headers = {
            "Authorization": f"App {sms_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        # Preparar el payload según la documentación de Infobip
        payload = {
            "messages": [
                {
                    "from": sms_sender_id,  # Remitente configurable desde protected_values.py
                    "destinations": [
                        {"to": phone_number}
                    ],
                    "text": f"Su código OTP es: {otp}",
                }
            ]
        }
        
        # Enviar la solicitud POST
        logger.info(f"Enviando SMS con OTP {otp} al número {phone_number} desde remitente '{sms_sender_id}'")
        response = req.post(
            endpoint,
            headers=headers,
            data=json.dumps(payload),
            timeout=30,  # Timeout de 30 segundos
        )
        
        # Verificar la respuesta
        if response.status_code == 200:
            response_data = response.json()
            logger.info(f"SMS enviado exitosamente al número {phone_number}")
            logger.info(f"Respuesta completa de la API: {json.dumps(response_data, indent=2)}")
            
            # Verificar el estado de entrega en la respuesta
            # La API de Infobip puede retornar 200 pero con información sobre el estado de entrega
            sms_actually_sent = True
            try:
                if "messages" in response_data:
                    for msg in response_data.get("messages", []):
                        status = msg.get("status", {})
                        status_name = status.get("name", "UNKNOWN")
                        status_description = status.get("description", "")
                        message_id = msg.get("messageId", "")
                        
                        logger.info(
                            f"Estado del mensaje (ID: {message_id}): {status_name} - {status_description}"
                        )
                        
                        # Si el estado no es "PENDING_ACCEPTED" o similar, puede haber un problema
                        # Estados comunes de Infobip: PENDING, PENDING_ACCEPTED, ACCEPTED, DELIVERED, REJECTED, etc.
                        if status_name not in ["PENDING", "PENDING_ACCEPTED", "ACCEPTED", "DELIVERED", "DELIVERED_TO_HANDSET"]:
                            logger.warning(
                                f"⚠️ El mensaje puede no haberse enviado correctamente. "
                                f"Estado: {status_name} - {status_description}"
                            )
                            # Si el estado es REJECTED o similar, registrar como error
                            if status_name in ["REJECTED", "UNDELIVERABLE", "EXPIRED", "MESSAGE_NOT_SENT"]:
                                logger.error(
                                    f"❌ El SMS fue rechazado o no se pudo entregar. "
                                    f"Estado: {status_name} - {status_description}"
                                )
                                sms_actually_sent = False
            except Exception as e:
                logger.debug(f"No se pudo analizar el estado de entrega: {e}")
            
            # Registrar en log de seguridad
            send_sms_details_to_log(otp, phone_number, success=sms_actually_sent, response_data=response_data)
            return sms_actually_sent
        else:
            error_msg = f"Status:{response.status_code}|{response.text[:100]}"
            logger.error(
                f"Error al enviar SMS. Código de estado: {response.status_code}, "
                f"Respuesta: {response.text}"
            )
            # Registrar en log de seguridad
            send_sms_details_to_log(otp, phone_number, success=False, error_message=error_msg)
            return False
            
    except FileNotFoundError as e:
        logger.error(f"Error al obtener credenciales: {e}")
        send_sms_details_to_log(otp, phone_number, success=False, error_message=f"FileNotFoundError: {str(e)}")
        return False
    except ValueError as e:
        logger.error(f"Error de validación de credenciales: {e}")
        send_sms_details_to_log(otp, phone_number, success=False, error_message=f"ValueError: {str(e)}")
        return False
    except Exception as e:
        # Captura tanto RequestException como cualquier otro error
        error_type = type(e).__name__
        logger.error(f"Error al enviar SMS ({error_type}): {e}", exc_info=True)
        send_sms_details_to_log(otp, phone_number, success=False, error_message=f"{error_type}: {str(e)}")
        return False

