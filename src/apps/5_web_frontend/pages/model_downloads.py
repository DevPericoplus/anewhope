import reflex as rx
from typing import Optional, Any
import sys
import logging
from pathlib import Path
import httpx
import os

logger = logging.getLogger(__name__)

# Importar el adaptador para hacer llamadas HTTP
try:
    import importlib.util
    adapter_path = Path(__file__).parent.parent / "adapters" / "api_client.py"
    if adapter_path.exists():
        spec = importlib.util.spec_from_file_location("api_client", adapter_path)
        if spec and spec.loader:
            api_client_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(api_client_module)
            if hasattr(api_client_module, "log_security_action"):
                log_security_action = api_client_module.log_security_action
            else:
                log_security_action = None
    else:
        log_security_action = None
except Exception as e:
    log_security_action = None
    logger.error(f"Error al cargar api_client: {e}")

# Cargar módulo de SMS
_send_message_by_sms = None
try:
    import importlib.util
    common_security_path = (
        Path(__file__).parent.parent.parent.parent
        / "2_shared_application"
        / "security"
        / "common_security.py"
    )
    if common_security_path.exists():
        spec = importlib.util.spec_from_file_location("common_security", common_security_path)
        if spec and spec.loader:
            common_security_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(common_security_module)
            _send_message_by_sms = getattr(common_security_module, "send_message_by_sms", None)
            if _send_message_by_sms:
                logger.info("Módulo send_message_by_sms cargado exitosamente")
except Exception as e:
    logger.error(f"Error al cargar módulo de SMS: {e}")

# Colores del tema
COLORS = {
    "background": "#1a1a1a",
    "card": "#6B6B6B",
    "foreground": "#f2f2f5",
    "primary": "#22c55e",
    "secondary": "#383854",
    "border": "#000000",
    "input": "#383854",
    "muted_foreground": "#E0E0E0",
    "accent": "#22c55e",
    "success": "#22c55e",
    "error": "#ef4444",
    "warning": "#f59e0b",
}


class ModelDownloadState(rx.State):
    """Estado para la página de descargas de modelos."""

    # Lista de modelos disponibles
    models: list[dict[str, Any]] = []
    models_loading: bool = False
    models_error: str = ""

    # Filtros (en frontend solo se muestran modelos de la propia organización)
    selected_organization_id: int | None = None

    # Estado del proceso de descarga
    selected_model: dict[str, Any] = {}
    show_otp_modal: bool = False
    otp_code: str = ""
    otp_phone: str = ""
    otp_requested: bool = False
    otp_error: str = ""
    download_in_progress: bool = False

    # Mensajes
    success_message: str = ""
    error_message: str = ""

    def on_mount(self):
        """Se ejecuta cuando la página se monta."""
        logger.info("ModelDownloadState montado")
        # Cargar modelos al montar la página
        return self.load_models()

    @rx.background
    async def load_models(self):
        """Carga la lista de modelos disponibles."""
        async with self:
            self.models_loading = True
            self.models_error = ""
            self.error_message = ""

        try:
            # Obtener token de sesión
            access_token = self.router.session.client_token
            if not access_token:
                async with self:
                    self.models_error = "No hay sesión activa. Por favor, inicie sesión."
                    self.models_loading = False
                return

            # Llamar al endpoint de middleware
            middleware_url = os.getenv("MIDDLEWARE_BASE_URL", "http://localhost:8007")
            url = f"{middleware_url}/models/list"

            # En frontend, usar la organización del usuario (no puede ver otras)
            # El middleware automáticamente filtrará por la organización del usuario si no se especifica
            params = {}

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    url,
                    params=params,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                )

            if response.status_code == 200:
                data = response.json()
                async with self:
                    self.models = data.get("models", [])
                    self.success_message = data.get("message", "Modelos cargados exitosamente")
                    self.models_loading = False
                logger.info(f"Modelos cargados: {len(self.models)}")
            else:
                error_detail = response.json().get("detail", "Error desconocido")
                async with self:
                    self.models_error = f"Error al cargar modelos: {error_detail}"
                    self.models_loading = False
                logger.error(f"Error al cargar modelos: {response.status_code} - {error_detail}")

        except Exception as e:
            async with self:
                self.models_error = f"Error de conexión: {str(e)}"
                self.models_loading = False
            logger.error(f"Excepción al cargar modelos: {e}", exc_info=True)

    def open_otp_modal(self, model: dict[str, Any]):
        """Abre el modal para solicitar OTP."""
        self.selected_model = model
        self.show_otp_modal = True
        self.otp_requested = False
        self.otp_code = ""
        self.otp_error = ""
        self.error_message = ""
        logger.info(f"Modal OTP abierto para modelo: {model.get('filename')}")

    def close_otp_modal(self):
        """Cierra el modal de OTP."""
        self.show_otp_modal = False
        self.selected_model = {}
        self.otp_requested = False
        self.otp_code = ""
        self.otp_phone = ""
        self.otp_error = ""

    @rx.background
    async def request_otp(self):
        """Solicita el OTP para descarga."""
        async with self:
            self.otp_error = ""
            self.error_message = ""

        model = self.selected_model
        if not model:
            async with self:
                self.otp_error = "No hay modelo seleccionado"
            return

        try:
            # Obtener token de sesión
            access_token = self.router.session.client_token
            if not access_token:
                async with self:
                    self.otp_error = "No hay sesión activa"
                return

            # Llamar al endpoint de solicitud de OTP
            middleware_url = os.getenv("MIDDLEWARE_BASE_URL", "http://localhost:8007")
            url = f"{middleware_url}/models/download/request-otp"

            payload = {
                "organization_id": model["organization_id"],
                "project_id": model["project_id"],
                "version_id": model["version_id"]
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                )

            if response.status_code == 200:
                data = response.json()
                otp = data.get("otp")
                phone = data.get("phone_number")

                # Enviar SMS con el OTP
                if _send_message_by_sms and otp and phone:
                    message = f"Tu código OTP para descargar el modelo es: {otp}"
                    sms_result = _send_message_by_sms(phone, message)
                    if sms_result.get("success"):
                        async with self:
                            self.otp_requested = True
                            self.otp_phone = phone
                            self.success_message = "SMS enviado exitosamente. Por favor, ingrese el código OTP."
                        logger.info(f"SMS enviado a {phone}")
                    else:
                        async with self:
                            self.otp_error = f"Error al enviar SMS: {sms_result.get('message')}"
                else:
                    async with self:
                        self.otp_error = "No se pudo enviar el SMS (servicio no disponible)"
                    logger.warning("Servicio de SMS no disponible")
            else:
                error_detail = response.json().get("detail", "Error desconocido")
                async with self:
                    self.otp_error = f"Error al solicitar OTP: {error_detail}"
                logger.error(f"Error al solicitar OTP: {response.status_code} - {error_detail}")

        except Exception as e:
            async with self:
                self.otp_error = f"Error de conexión: {str(e)}"
            logger.error(f"Excepción al solicitar OTP: {e}", exc_info=True)

    @rx.background
    async def validate_otp_and_download(self):
        """Valida el OTP e inicia la descarga del modelo."""
        async with self:
            self.download_in_progress = True
            self.otp_error = ""
            self.error_message = ""

        model = self.selected_model
        otp = self.otp_code.strip()

        if not model:
            async with self:
                self.otp_error = "No hay modelo seleccionado"
                self.download_in_progress = False
            return

        if not otp:
            async with self:
                self.otp_error = "Por favor, ingrese el código OTP"
                self.download_in_progress = False
            return

        try:
            # Obtener token de sesión
            access_token = self.router.session.client_token
            if not access_token:
                async with self:
                    self.otp_error = "No hay sesión activa"
                    self.download_in_progress = False
                return

            # Llamar al endpoint de validación de OTP
            middleware_url = os.getenv("MIDDLEWARE_BASE_URL", "http://localhost:8007")
            url = f"{middleware_url}/models/download/validate-otp"

            payload = {
                "organization_id": model["organization_id"],
                "project_id": model["project_id"],
                "version_id": model["version_id"],
                "otp": otp
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                )

            if response.status_code == 200:
                data = response.json()
                download_token = data.get("download_token")
                fmanagement_url = data.get("fmanagement_url", "http://localhost:1666")
                filename = model.get("filename")

                # Construir URL de descarga
                download_url = f"{fmanagement_url}/models/download?filename={filename}&token={download_token}"

                async with self:
                    self.success_message = f"OTP validado. Descargando {filename}..."
                    self.download_in_progress = False
                    self.show_otp_modal = False
                    # En Reflex, podemos usar rx.download para descargar el archivo
                    # pero necesitamos usar JavaScript para esto
                logger.info(f"Token de descarga obtenido: {download_url}")

                # Usar JavaScript para descargar el archivo
                yield rx.download(download_url)

            else:
                error_detail = response.json().get("detail", "Error desconocido")
                async with self:
                    self.otp_error = f"Error al validar OTP: {error_detail}"
                    self.download_in_progress = False
                logger.error(f"Error al validar OTP: {response.status_code} - {error_detail}")

        except Exception as e:
            async with self:
                self.otp_error = f"Error de conexión: {str(e)}"
                self.download_in_progress = False
            logger.error(f"Excepción al validar OTP: {e}", exc_info=True)


def model_card(model: dict[str, Any]) -> rx.Component:
    """Tarjeta para mostrar un modelo."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.badge(
                    f"ORG {model['organization_id']:05d}",
                    color_scheme="blue",
                ),
                rx.badge(
                    f"PRJ {model['project_id']:05d}",
                    color_scheme="green",
                ),
                rx.badge(
                    f"v{model['version_id']:03d}",
                    color_scheme="purple",
                ),
                spacing="2",
                width="100%",
            ),
            rx.heading(
                model["filename"],
                size="4",
                color=COLORS["foreground"],
            ),
            rx.text(
                f"Tamaño: {model['file_size'] / (1024*1024):.2f} MB",
                color=COLORS["muted_foreground"],
                size="2",
            ),
            rx.button(
                "Descargar con OTP",
                on_click=lambda: ModelDownloadState.open_otp_modal(model),
                color_scheme="green",
                width="100%",
            ),
            spacing="3",
            align="start",
        ),
        style={
            "background": COLORS["card"],
            "padding": "1rem",
            "border_radius": "8px",
        },
    )


def otp_modal() -> rx.Component:
    """Modal para solicitar y validar OTP."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.dialog.title(
                    "Descargar Modelo con OTP",
                    color=COLORS["foreground"],
                ),
                rx.cond(
                    ModelDownloadState.selected_model,
                    rx.text(
                        f"Archivo: {ModelDownloadState.selected_model['filename']}",
                        color=COLORS["muted_foreground"],
                        size="2",
                    ),
                ),
                rx.cond(
                    ~ModelDownloadState.otp_requested,
                    # Paso 1: Solicitar OTP
                    rx.vstack(
                        rx.text(
                            "Se enviará un código OTP por SMS a su teléfono registrado.",
                            color=COLORS["foreground"],
                        ),
                        rx.button(
                            "Enviar OTP por SMS",
                            on_click=ModelDownloadState.request_otp,
                            color_scheme="blue",
                            width="100%",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    # Paso 2: Validar OTP
                    rx.vstack(
                        rx.text(
                            f"SMS enviado a {ModelDownloadState.otp_phone}",
                            color=COLORS["success"],
                            size="2",
                        ),
                        rx.input(
                            placeholder="Ingrese el código OTP de 4 dígitos",
                            value=ModelDownloadState.otp_code,
                            on_change=ModelDownloadState.set_otp_code,
                            max_length=4,
                            style={
                                "background": COLORS["input"],
                                "color": COLORS["foreground"],
                                "width": "100%",
                            },
                        ),
                        rx.button(
                            "Validar y Descargar",
                            on_click=ModelDownloadState.validate_otp_and_download,
                            color_scheme="green",
                            width="100%",
                            loading=ModelDownloadState.download_in_progress,
                        ),
                        spacing="3",
                        width="100%",
                    ),
                ),
                rx.cond(
                    ModelDownloadState.otp_error,
                    rx.callout(
                        ModelDownloadState.otp_error,
                        icon="alert_circle",
                        color_scheme="red",
                    ),
                ),
                rx.dialog.close(
                    rx.button(
                        "Cancelar",
                        on_click=ModelDownloadState.close_otp_modal,
                        color_scheme="gray",
                        width="100%",
                    ),
                ),
                spacing="4",
                width="100%",
            ),
            style={
                "background": COLORS["background"],
                "padding": "2rem",
                "max_width": "500px",
            },
        ),
        open=ModelDownloadState.show_otp_modal,
    )


def model_downloads_page() -> rx.Component:
    """Página principal de descargas de modelos."""
    return rx.box(
        rx.vstack(
            rx.heading(
                "Descargas de Modelos",
                size="8",
                color=COLORS["foreground"],
            ),
            rx.text(
                "Descargue modelos entrenados de forma segura con validación OTP",
                color=COLORS["muted_foreground"],
                size="3",
            ),
            rx.divider(),
            # Toolbar con filtros y botón de refrescar
            rx.hstack(
                rx.button(
                    rx.icon("refresh_cw"),
                    " Refrescar",
                    on_click=ModelDownloadState.load_models,
                    color_scheme="blue",
                    loading=ModelDownloadState.models_loading,
                ),
                spacing="3",
                width="100%",
                justify="end",
            ),
            # Mensajes de éxito/error
            rx.cond(
                ModelDownloadState.success_message,
                rx.callout(
                    ModelDownloadState.success_message,
                    icon="check_circle",
                    color_scheme="green",
                ),
            ),
            rx.cond(
                ModelDownloadState.models_error,
                rx.callout(
                    ModelDownloadState.models_error,
                    icon="alert_circle",
                    color_scheme="red",
                ),
            ),
            # Lista de modelos
            rx.cond(
                ModelDownloadState.models_loading,
                rx.center(
                    rx.spinner(size="3"),
                    padding="2rem",
                ),
                rx.cond(
                    ModelDownloadState.models,
                    rx.grid(
                        rx.foreach(
                            ModelDownloadState.models,
                            model_card,
                        ),
                        columns="3",
                        spacing="4",
                        width="100%",
                    ),
                    rx.center(
                        rx.vstack(
                            rx.icon("inbox", size=48, color=COLORS["muted_foreground"]),
                            rx.text(
                                "No hay modelos disponibles",
                                color=COLORS["muted_foreground"],
                                size="3",
                            ),
                            spacing="2",
                        ),
                        padding="4rem",
                    ),
                ),
            ),
            spacing="5",
            width="100%",
            padding="2rem",
        ),
        # Modal de OTP
        otp_modal(),
        style={
            "background": COLORS["background"],
            "min_height": "100vh",
        },
    )
