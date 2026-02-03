"""
Módulo para verificar el estado de entrega de mensajes SMS enviados a través de Infobip.

Este módulo proporciona funciones para:
- Consultar delivery reports de Infobip
- Verificar el estado final de entrega de un mensaje SMS
- Distinguir entre estados intermedios (PENDING) y finales (DELIVERED/REJECTED)
"""

import logging
import time
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)


def _get_requests_module():
    """Importa requests de forma lazy."""
    try:
        import requests
        return requests
    except ImportError:
        logger.error("El módulo 'requests' no está instalado")
        return None


def check_sms_delivery_status(
    message_id: str,
    api_url: str,
    api_key: str,
    max_wait_seconds: int = 30,
    check_interval: int = 5,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verifica el estado final de entrega de un mensaje SMS consultando el delivery report de Infobip.

    Esta función hace polling al endpoint de delivery reports de Infobip hasta que el mensaje
    alcanza un estado final (DELIVERED, REJECTED, etc.) o hasta que se alcance el timeout.

    Args:
        message_id: ID del mensaje devuelto por Infobip al enviar el SMS.
        api_url: URL base de la API de Infobip (ej: https://pdy6d3.api.infobip.com).
        api_key: API key de Infobip.
        max_wait_seconds: Tiempo máximo en segundos para esperar el delivery report (default: 30).
        check_interval: Intervalo en segundos entre consultas (default: 5).

    Returns:
        Tupla de (delivered, status_name, full_report):
        - delivered (bool): True si el mensaje fue entregado exitosamente.
        - status_name (str): Nombre del estado final (ej: "DELIVERED_TO_HANDSET", "REJECTED").
        - full_report (dict): Diccionario completo con el delivery report de Infobip.

    Ejemplo:
        >>> delivered, status, report = check_sms_delivery_status(
        ...     message_id="4700646034707951434964",
        ...     api_url="https://pdy6d3.api.infobip.com",
        ...     api_key="your-api-key"
        ... )
        >>> print(f"Delivered: {delivered}, Status: {status}")
        Delivered: True, Status: DELIVERED_TO_HANDSET

    Estados Finales de Infobip:
        - DELIVERED_TO_HANDSET: Entregado exitosamente al dispositivo
        - DELIVERED_TO_NETWORK: Entregado a la red del operador
        - REJECTED: Rechazado por el operador
        - UNDELIVERABLE: No se pudo entregar
        - EXPIRED: Expiró antes de entregarse
        - PENDING_*: Estados intermedios (aún en tránsito)
    """
    req = _get_requests_module()
    if req is None:
        logger.error("requests no está disponible, no se puede verificar delivery status")
        return False, "ERROR", None

    # Construir endpoint de delivery reports
    # Documentación: https://www.infobip.com/docs/api/channels/sms/sms-messaging/logs-and-status-reports/get-outbound-sms-message-delivery-reports
    endpoint = f"{api_url}/sms/3/reports"

    headers = {
        "Authorization": f"App {api_key}",
        "Accept": "application/json",
    }

    params = {
        "messageId": message_id,
    }

    logger.info(f"Iniciando verificación de delivery status para messageId: {message_id}")

    # Estados finales (el mensaje ya no cambiará)
    FINAL_STATES = {
        "DELIVERED_TO_HANDSET",
        "DELIVERED_TO_NETWORK",
        "REJECTED",
        "REJECTED_NETWORK",
        "UNDELIVERABLE",
        "EXPIRED",
        "MESSAGE_NOT_SENT",
    }

    # Estados que indican entrega exitosa
    SUCCESS_STATES = {
        "DELIVERED_TO_HANDSET",
        "DELIVERED_TO_NETWORK",
    }

    start_time = time.time()
    attempt = 0

    while (time.time() - start_time) < max_wait_seconds:
        attempt += 1

        try:
            logger.debug(f"Intento {attempt}: Consultando delivery report para {message_id}")

            response = req.get(
                endpoint,
                headers=headers,
                params=params,
                timeout=10,
            )

            if response.status_code != 200:
                logger.warning(
                    f"Error al consultar delivery report (HTTP {response.status_code}): {response.text}"
                )
                # Esperar antes del siguiente intento
                time.sleep(check_interval)
                continue

            data = response.json()

            # Verificar si hay resultados
            results = data.get("results", [])
            if not results:
                logger.debug(f"No hay delivery reports disponibles aún para {message_id}")
                time.sleep(check_interval)
                continue

            # Obtener el primer resultado (debería ser único por messageId)
            report = results[0]
            status = report.get("status", {})
            status_name = status.get("name", "UNKNOWN")
            status_description = status.get("description", "")

            logger.info(
                f"Delivery report obtenido - MessageId: {message_id}, "
                f"Status: {status_name}, Description: {status_description}"
            )

            # Verificar si es un estado final
            if status_name in FINAL_STATES:
                delivered = status_name in SUCCESS_STATES
                logger.info(
                    f"Estado final alcanzado para {message_id}: {status_name} "
                    f"(Entregado: {delivered})"
                )
                return delivered, status_name, report
            else:
                logger.debug(
                    f"Estado intermedio {status_name} para {message_id}, "
                    f"esperando estado final..."
                )
                time.sleep(check_interval)
                continue

        except Exception as e:
            logger.error(f"Error al consultar delivery report: {e}", exc_info=True)
            time.sleep(check_interval)
            continue

    # Timeout alcanzado sin estado final
    logger.warning(
        f"Timeout alcanzado ({max_wait_seconds}s) esperando delivery report para {message_id}. "
        f"El mensaje puede estar aún en tránsito."
    )
    return False, "TIMEOUT", None


def get_delivery_status_summary(status_name: str) -> str:
    """
    Obtiene un resumen legible en español del estado de entrega.

    Args:
        status_name: Nombre del estado de Infobip (ej: "DELIVERED_TO_HANDSET").

    Returns:
        Mensaje descriptivo en español del estado.
    """
    status_messages = {
        "DELIVERED_TO_HANDSET": "✅ Mensaje entregado exitosamente al dispositivo",
        "DELIVERED_TO_NETWORK": "✅ Mensaje entregado a la red del operador",
        "PENDING_ACCEPTED": "⏳ Mensaje aceptado, en proceso de entrega",
        "PENDING": "⏳ Mensaje en tránsito",
        "REJECTED": "❌ Mensaje rechazado por el operador",
        "REJECTED_NETWORK": "❌ Mensaje rechazado por la red",
        "UNDELIVERABLE": "❌ Mensaje no se pudo entregar",
        "EXPIRED": "❌ Mensaje expiró antes de entregarse",
        "MESSAGE_NOT_SENT": "❌ Mensaje no fue enviado",
        "TIMEOUT": "⏱️ Timeout: no se pudo verificar el estado final",
        "ERROR": "❌ Error al verificar el estado",
        "UNKNOWN": "❓ Estado desconocido",
    }

    return status_messages.get(status_name, f"Estado: {status_name}")


# Ejemplo de uso
if __name__ == "__main__":
    # Configurar logging para el ejemplo
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s",
    )

    # Importar credenciales desde protected_values
    import sys
    from pathlib import Path

    # Agregar rutas necesarias
    project_root = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(project_root))

    # Cargar protected_values
    import importlib.util
    protected_values_path = (
        project_root / "infrastructure" / "environments" / "macbook" / "protected_values.py"
    )
    spec = importlib.util.spec_from_file_location("protected_values", protected_values_path)
    protected_values = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(protected_values)

    # Ejemplo: verificar el delivery status del último mensaje
    TEST_MESSAGE_ID = "4700646034707951434964"  # Cambiar por tu messageId

    print(f"\n{'='*60}")
    print("VERIFICACIÓN DE DELIVERY STATUS")
    print(f"{'='*60}\n")

    delivered, status, report = check_sms_delivery_status(
        message_id=TEST_MESSAGE_ID,
        api_url=protected_values.sms_api_url,
        api_key=protected_values.sms_api_key,
        max_wait_seconds=30,
        check_interval=5,
    )

    print(f"\n{'='*60}")
    print("RESULTADO:")
    print(f"{'='*60}")
    print(f"Message ID: {TEST_MESSAGE_ID}")
    print(f"Entregado: {delivered}")
    print(f"Estado: {status}")
    print(f"Descripción: {get_delivery_status_summary(status)}")

    if report:
        print(f"\nDetalles:")
        print(f"  Destinatario: {report.get('to')}")
        print(f"  Enviado en: {report.get('sentAt')}")
        print(f"  Entregado en: {report.get('doneAt')}")
        if 'price' in report:
            price_info = report['price']
            print(f"  Costo: {price_info.get('pricePerMessage')} {price_info.get('currency')}")
    print(f"{'='*60}\n")
