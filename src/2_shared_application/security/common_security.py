"""Utilidades de seguridad comunes para aplicaciones web con Reflex."""
import datetime
import json
import logging
from pathlib import Path
from typing import Optional, Any, Tuple

try:
    import requests
except ImportError:
    requests = None
    logging.warning("El módulo 'requests' no está instalado. La funcionalidad de SMS no estará disponible.")

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

def get_sms_api_credentials() -> Tuple[str, str]:
    """
    Obtiene los valores de sms_api_url y sms_api_key del archivo protected_values.py.

    Returns:
        Tupla (sms_api_url, sms_api_key)

    Raises:
        FileNotFoundError: Si el archivo protected_values.py no existe.
        ValueError: Si alguna de las variables no se encuentra o no es válida.
    
    Nota:
        Este método lee y ejecuta de manera controlada las variables del archivo
        protected_values.py que debe estar en el directorio raíz del proyecto.
    """
    # Ruta relativa (se asume que el archivo está en el root del repo/proyecto)
    protected_values_path = Path(__file__).parent.parent.parent.parent / "protected_values.py"
    if not protected_values_path.exists():
        # El archivo no existe en la ruta esperada
        raise FileNotFoundError(f"No se encontró protected_values.py en {protected_values_path}")

    # Leer el contenido y extraer las variables requeridas
    namespace = {}
    with open(protected_values_path, "r", encoding="utf-8") as f:
        exec(f.read(), {}, namespace)

    sms_api_url = namespace.get("sms_api_url")
    sms_api_key = namespace.get("sms_api_key")

    if not sms_api_url or not sms_api_key:
        raise ValueError("sms_api_url o sms_api_key no se encontraron en protected_values.py")

    return sms_api_url, sms_api_key


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
    # Verificar que requests esté disponible
    if requests is None:
        logger.error("El módulo 'requests' no está instalado. Instálalo con: pip install requests")
        return False
    
    # Validar que el OTP tenga 4 dígitos
    if not otp or len(otp) != 4 or not otp.isdigit():
        logger.error(f"El OTP debe tener exactamente 4 dígitos. OTP recibido: {otp}")
        return False
    
    # Validar formato del número de teléfono
    if not phone_number or not phone_number.startswith("+"):
        logger.error(
            f"El número de teléfono debe estar en formato internacional (ej: +34639775978). "
            f"Recibido: {phone_number}"
        )
        return False
    
    try:
        # Obtener credenciales de la API
        sms_api_url, sms_api_key = get_sms_api_credentials()
        
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
                    "from": "ServiceSMS",  # Remitente por defecto (puede configurarse)
                    "destinations": [
                        {"to": phone_number}
                    ],
                    "text": f"Su código OTP es: {otp}",
                }
            ]
        }
        
        # Enviar la solicitud POST
        logger.info(f"Enviando SMS con OTP {otp} al número {phone_number}")
        response = requests.post(
            endpoint,
            headers=headers,
            data=json.dumps(payload),
            timeout=30,  # Timeout de 30 segundos
        )
        
        # Verificar la respuesta
        if response.status_code == 200:
            logger.info(f"SMS enviado exitosamente al número {phone_number}")
            response_data = response.json()
            logger.debug(f"Respuesta de la API: {response_data}")
            return True
        else:
            logger.error(
                f"Error al enviar SMS. Código de estado: {response.status_code}, "
                f"Respuesta: {response.text}"
            )
            return False
            
    except FileNotFoundError as e:
        logger.error(f"Error al obtener credenciales: {e}")
        return False
    except ValueError as e:
        logger.error(f"Error de validación de credenciales: {e}")
        return False
    except requests.RequestException as e:
        logger.error(f"Error de comunicación con la API de Infobip: {e}")
        return False
    except Exception as e:
        logger.error(f"Error inesperado al enviar SMS: {e}", exc_info=True)
        return False

