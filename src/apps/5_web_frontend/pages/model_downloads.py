import reflex as rx
from typing import Any
import sys
import logging
from pathlib import Path
import httpx
import os
import importlib.util

logger = logging.getLogger(__name__)

# Importar SharedSessionState desde el módulo compartido del frontend
sys.path.insert(0, str(Path(__file__).parent.parent))
from web_frontend.shared_state import SharedSessionState
sys.path.pop(0)

from adapters.api_client import (
    get_organization_projects,
    get_project_versions,
    _account_storage_folder,
    _project_storage_folder,
    _version_storage_folder,
)

# Importar el adaptador para hacer llamadas HTTP
try:
    from adapters.api_client import log_security_action
except (ImportError, AttributeError):
    log_security_action = None

# Cargar módulo de SMS
_send_message_by_sms = None
try:
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

from portal_crt import COLORS, CRT_SHELL_CLASS, MARKDOWN_COMPONENT_MAP, SELECT_STYLE

COLORS = {
    **COLORS,
    "text": COLORS["foreground"],
    "heading": COLORS["primary"],
    "warning": "#ffc966",
}


class ModelDownloadState(SharedSessionState):
    """Estado para la página de descargas de modelos."""

    # Lista completa de modelos del middleware (sin filtrar)
    all_models_unfiltered: list[dict[str, Any]] = []

    # Lista de modelos filtrados (se muestra en la UI)
    models: list[dict[str, Any]] = []
    models_loading: bool = False
    models_error: str = ""

    # Selectores de proyecto y versión
    dl_projects: list[dict[str, Any]] = []
    dl_versions: list[dict[str, Any]] = []
    dl_selected_project_id: int = 0
    dl_selected_project_name: str = ""
    dl_selected_version_id: int = 0
    dl_selected_version_name: str = ""

    # Estado del proceso de descarga
    selected_model: dict[str, Any] = {}
    show_otp_modal: bool = False
    otp_code: str = ""
    otp_phone: str = ""
    otp_requested: bool = False
    otp_error: str = ""
    download_in_progress: bool = False

    # Control de visibilidad del panel de modelos
    models_loaded: bool = False

    # Paquetes GGUF (entrenamiento autónomo)
    gguf_packages: list[dict[str, Any]] = []
    gguf_loading: bool = False
    gguf_loaded: bool = False
    gguf_error: str = ""

    # Mensajes
    success_message: str = ""
    error_message: str = ""

    @rx.var
    def can_download_models(self) -> bool:
        """Solo SuperAdmin (1) y Admin Organización (2) pueden descargar modelos."""
        return self.identity_type_id in (1, 2)

    @rx.var
    def dl_project_options(self) -> list[str]:
        """Opciones del selector de proyecto."""
        return [p.get("name", "") for p in self.dl_projects if p.get("name")]

    @rx.var
    def dl_version_options(self) -> list[str]:
        """Opciones del selector de versión."""
        return [v.get("nombre", "") for v in self.dl_versions if v.get("nombre")]

    def on_mount(self):
        """Se ejecuta cuando la página se monta."""
        logger.info("ModelDownloadState montado")
        self.models_loaded = False
        self.models = []
        self.all_models_unfiltered = []
        return self.init_selectors()

    def init_selectors(self):
        """Inicializa los selectores cargando proyectos via API.

        Limpia modelos previos para que solo se muestren tras pulsar Refrescar.
        """
        # Limpiar modelos de sesiones anteriores
        self.models = []
        self.all_models_unfiltered = []
        self.models_loaded = False
        self.models_error = ""
        self.success_message = ""

        if self.organization_id <= 0:
            return

        try:
            projects_data = get_organization_projects(
                organization_id=self.organization_id,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            self.dl_projects = [
                {"id": p.get("id"), "name": p.get("nombre", "")}
                for p in projects_data
            ]
            self.dl_versions = []
            self.dl_selected_project_id = 0
            self.dl_selected_project_name = ""
            self.dl_selected_version_id = 0
            self.dl_selected_version_name = ""
        except Exception as exc:
            logger.error("Error cargando proyectos para selector: %s", exc)

    def dl_set_selected_project(self, project_name: str):
        """Establece el proyecto seleccionado y carga sus versiones."""
        self.dl_selected_project_name = project_name
        self.dl_selected_version_name = ""
        self.dl_selected_version_id = 0
        self.dl_versions = []

        # Buscar el ID correspondiente al nombre
        project_id = 0
        for proj in self.dl_projects:
            if proj.get("name") == project_name:
                project_id = proj.get("id", 0)
                break

        self.dl_selected_project_id = project_id

        if self.dl_selected_project_id > 0:
            self._load_versions()

        # Filtrar modelos por proyecto (sin versión)
        self._filter_models()

    def _load_versions(self):
        """Carga las versiones del proyecto seleccionado via API."""
        if self.dl_selected_project_id == 0:
            return

        try:
            response = get_project_versions(
                project_id=self.dl_selected_project_id,
                organization_id=self.organization_id,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            versiones_data = response.get("versiones", [])
            self.dl_versions = [
                {
                    "id": v.get("id_version", 0),
                    "nombre": f"v{v.get('id_version', 0):03d}",
                }
                for v in versiones_data
                if v.get("id_version", 0) > 0
            ]
        except Exception as exc:
            logger.error("Error cargando versiones para selector: %s", exc)

    def dl_set_selected_version(self, version_name: str):
        """Establece la versión seleccionada y filtra modelos."""
        self.dl_selected_version_name = version_name

        # Buscar el ID correspondiente al nombre
        version_id = 0
        for ver in self.dl_versions:
            if ver.get("nombre") == version_name:
                version_id = ver.get("id", 0)
                break

        self.dl_selected_version_id = version_id
        self._filter_models()

    def _filter_models(self):
        """Filtra modelos según proyecto y versión seleccionados."""
        filtered = list(self.all_models_unfiltered)

        if self.dl_selected_project_id > 0:
            filtered = [
                m for m in filtered
                if m.get("project_id") == self.dl_selected_project_id
            ]

        if self.dl_selected_version_id > 0:
            filtered = [
                m for m in filtered
                if m.get("version_id") == self.dl_selected_version_id
            ]

        self.models = filtered

    @rx.event(background=True)
    async def load_models(self):
        """Carga la lista de modelos disponibles desde el middleware."""
        async with self:
            self.models_loading = True
            self.models_error = ""
            self.error_message = ""

        try:
            access_token = self.access_token
            session_token = self.session_token

            if not session_token:
                async with self:
                    self.models_error = "Token de sesión no proporcionado"
                    self.models_loading = False
                return

            middleware_url = os.getenv("MIDDLEWARE_BASE_URL", "http://localhost:8007")
            url = f"{middleware_url}/models/list"

            # En frontend, el middleware filtra automáticamente por organización del usuario
            params: dict[str, Any] = {}

            headers = {
                "Content-Type": "application/json",
                "X-Session-Token": session_token,
            }

            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params, headers=headers)

            if response.status_code == 200:
                data = response.json()
                all_models = data.get("models", [])
                async with self:
                    self.all_models_unfiltered = all_models
                    self._filter_models()
                    self.success_message = data.get("message", "Modelos cargados exitosamente")
                    self.models_loading = False
                    self.models_loaded = True
                logger.info("Modelos cargados: %d", len(all_models))
            else:
                error_detail = response.json().get("detail", "Error desconocido")
                async with self:
                    self.models_error = f"Error al cargar modelos: {error_detail}"
                    self.models_loading = False
                logger.error("Error al cargar modelos: %s - %s", response.status_code, error_detail)

        except Exception as e:
            async with self:
                self.models_error = f"Error de conexión: {str(e)}"
                self.models_loading = False
            logger.error("Excepción al cargar modelos: %s", e, exc_info=True)

        # Cargar paquetes GGUF si hay versión seleccionada
        await self._load_gguf_packages()

    async def _load_gguf_packages(self):
        """Busca paquetes GGUF en la carpeta modelos/ de la versión seleccionada."""
        org_id = self.organization_id
        prj_id = self.dl_selected_project_id
        ver_id = self.dl_selected_version_id

        if prj_id <= 0 or ver_id <= 0:
            async with self:
                self.gguf_packages = []
                self.gguf_loaded = True
                self.gguf_loading = False
            return

        async with self:
            self.gguf_loading = True
            self.gguf_error = ""

        try:
            middleware_url = os.getenv("MIDDLEWARE_BASE_URL", "http://localhost:8007")
            url = f"{middleware_url}/fmanagement/list"

            headers = {
                "Content-Type": "application/json",
                "X-Session-Token": self.session_token,
            }
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"

            payload = {
                "org_folder": _account_storage_folder(org_id, self.user_id),
                "prj_folder": _project_storage_folder(prj_id),
                "version_folder": _version_storage_folder(ver_id),
            }

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])

                packages = []
                for item in items:
                    if item.get("is_dir") and item.get("name") == "modelos":
                        for child in (item.get("items") or []):
                            if not child.get("is_dir") and child.get("name", "").endswith(".zip"):
                                size_bytes = child.get("size_bytes", 0)
                                size_mb = round(size_bytes / (1024 * 1024), 2) if size_bytes else 0
                                packages.append({
                                    "filename": child["name"],
                                    "size_bytes": size_bytes,
                                    "size_mb": size_mb,
                                    "organization_id": org_id,
                                    "project_id": prj_id,
                                    "version_id": ver_id,
                                })

                async with self:
                    self.gguf_packages = packages
                    self.gguf_loaded = True
                    self.gguf_loading = False
            else:
                async with self:
                    self.gguf_packages = []
                    self.gguf_loaded = True
                    self.gguf_loading = False

        except Exception as exc:
            logger.error("Error buscando paquetes GGUF: %s", exc)
            async with self:
                self.gguf_error = f"Error buscando paquetes: {str(exc)}"
                self.gguf_packages = []
                self.gguf_loaded = True
                self.gguf_loading = False

    def download_gguf_package(self, pkg: dict[str, Any]):
        """Descarga un paquete GGUF desde fmanagement."""
        from adapters.api_client import generate_file_download_token

        filename = pkg.get("filename", "")
        prj_id = pkg.get("project_id", 0)
        ver_id = pkg.get("version_id", 0)

        try:
            response = generate_file_download_token(
                project_id=prj_id,
                version_id=ver_id,
                filename=filename,
                relative_path="modelos",
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if not response.get("success"):
                error_msg = response.get("message") or response.get(
                    "detail", "Error al generar token"
                )
                return rx.toast.error(
                    f"Error: {error_msg}", position="bottom-right", duration=5000
                )

            download_url = response.get("download_url")
            if not download_url:
                return rx.toast.error(
                    "Error: respuesta incompleta del servidor",
                    position="bottom-right",
                    duration=5000,
                )

            download_script = f"""
            (function() {{
                const link = document.createElement('a');
                link.href = '{download_url}';
                link.download = '{filename}';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }})();
            """
            return rx.call_script(download_script)

        except Exception as exc:
            return rx.toast.error(
                f"Error: {str(exc)}", position="bottom-right", duration=5000
            )

    @rx.event(background=True)
    async def download_model_file(self, model: dict[str, Any]):
        """Descarga directa de un fichero de modelo via sesión (sin OTP)."""
        filename = model.get("filename", "")
        org_id = model.get("organization_id", 0)
        prj_id = model.get("project_id", 0)
        ver_id = model.get("version_id", 0)

        async with self:
            self.error_message = ""

        try:
            middleware_url = os.getenv("MIDDLEWARE_BASE_URL", "http://localhost:8007")
            url = f"{middleware_url}/models/download/session"

            params = {
                "organization_id": org_id,
                "project_id": prj_id,
                "version_id": ver_id,
                "filename": filename,
            }
            headers = {
                "X-Session-Token": self.session_token,
            }
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.get(url, params=params, headers=headers)

            if response.status_code == 200:
                import base64
                file_b64 = base64.b64encode(response.content).decode("utf-8")
                async with self:
                    self.success_message = f"Descargando {filename}..."
                return rx.download(data=file_b64, filename=filename)
            else:
                detail = "Error desconocido"
                try:
                    detail = response.json().get("detail", detail)
                except Exception:
                    detail = response.text[:200]
                async with self:
                    self.error_message = f"Error descargando {filename}: {detail}"
        except Exception as exc:
            logger.error("Error download_model_file: %s", exc, exc_info=True)
            async with self:
                self.error_message = f"Error: {str(exc)}"

    def open_otp_modal(self, model: dict[str, Any]):
        """Abre el modal para solicitar OTP (solo SuperAdmin y Admin Org)."""
        # Validación de seguridad: solo identity_type_id 1 (SuperAdmin) y 2 (Admin Org)
        if self.identity_type_id not in (1, 2):
            self.error_message = "No tiene permisos para descargar modelos"
            logger.warning(
                "Intento de descarga sin permisos: user_id=%s identity_type_id=%s",
                self.user_id, self.identity_type_id,
            )
            return

        self.selected_model = model
        self.show_otp_modal = True
        self.otp_requested = False
        self.otp_code = ""
        self.otp_error = ""
        self.error_message = ""
        logger.info("Modal OTP abierto para modelo: %s", model.get("filename"))

    def close_otp_modal(self):
        """Cierra el modal de OTP."""
        self.show_otp_modal = False
        self.selected_model = {}
        self.otp_requested = False
        self.otp_code = ""
        self.otp_phone = ""
        self.otp_error = ""

    @rx.event(background=True)
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
            # Obtener tokens de sesión (heredados de SharedSessionState)
            access_token = self.access_token
            session_token = self.session_token

            if not session_token:
                async with self:
                    self.otp_error = "Token de sesión no proporcionado"
                return

            # Llamar al endpoint de solicitud de OTP
            middleware_url = os.getenv("MIDDLEWARE_BASE_URL", "http://localhost:8007")
            url = f"{middleware_url}/models/download/request-otp"

            payload = {
                "organization_id": model["organization_id"],
                "project_id": model["project_id"],
                "version_id": model["version_id"]
            }

            headers = {
                "Content-Type": "application/json",
                "X-Session-Token": session_token,
            }

            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers
                )

            if response.status_code == 200:
                data = response.json()

                # Usuario exento de OTP: saltar modal y proceder a descarga
                if data.get("otp_exempt"):
                    logger.info("Usuario exento de OTP, procediendo a descarga directa")
                    async with self:
                        self.download_in_progress = True
                        self.success_message = "Usuario exento de OTP, descargando..."

                    # Validar con OTP dummy (backend lo ignora para exempt)
                    validate_url = f"{middleware_url}/models/download/validate-otp"
                    validate_payload = {
                        "organization_id": model["organization_id"],
                        "project_id": model["project_id"],
                        "version_id": model["version_id"],
                        "otp": "0000",
                    }
                    async with httpx.AsyncClient(timeout=30.0) as val_client:
                        val_response = await val_client.post(
                            validate_url, json=validate_payload, headers=headers
                        )

                    if val_response.status_code == 200:
                        val_data = val_response.json()
                        download_token = val_data.get("download_token", "")
                        filename = model.get("filename")

                        from urllib.parse import quote
                        dl_url = (
                            f"{middleware_url}/models/download/direct"
                            f"?token={quote(download_token)}"
                            f"&filename={quote(filename)}"
                        )
                        async with httpx.AsyncClient(timeout=60.0) as dl_client:
                            dl_response = await dl_client.get(dl_url)

                        if dl_response.status_code == 200:
                            import base64
                            file_b64 = base64.b64encode(dl_response.content).decode("utf-8")
                            async with self:
                                self.success_message = f"Descargando {filename}..."
                                self.download_in_progress = False
                                self.show_otp_modal = False
                            return rx.download(data=file_b64, filename=filename)
                        else:
                            async with self:
                                self.otp_error = f"Error descargando archivo: {dl_response.status_code}"
                                self.download_in_progress = False
                    else:
                        error_detail = val_response.json().get("detail", "Error desconocido")
                        async with self:
                            self.otp_error = f"Error al validar descarga: {error_detail}"
                            self.download_in_progress = False
                    return

                otp = data.get("otp")
                phone = data.get("phone_number")

                # Enviar SMS con el OTP
                if _send_message_by_sms and otp and phone:
                    # send_message_by_sms retorna un booleano (True/False)
                    sms_result = _send_message_by_sms(otp, phone)
                    if sms_result:
                        async with self:
                            self.otp_requested = True
                            self.otp_phone = phone
                            self.success_message = "SMS enviado exitosamente. Por favor, ingrese el código OTP."
                        logger.info(f"SMS enviado a {phone}")
                    else:
                        async with self:
                            self.otp_error = "No se pudo enviar el SMS"
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

    @rx.event(background=True)
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
            # Obtener tokens de sesión (heredados de SharedSessionState)
            access_token = self.access_token
            session_token = self.session_token

            if not session_token:
                async with self:
                    self.otp_error = "Token de sesión no proporcionado"
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

            headers = {
                "Content-Type": "application/json",
                "X-Session-Token": session_token,
            }

            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers
                )

            if response.status_code == 200:
                data = response.json()
                download_token = data.get("download_token", "")
                filename = model.get("filename")

                logger.info(
                    "OTP validado, descargando modelo server-side: org=%s prj=%s ver=%s",
                    model['organization_id'], model['project_id'], model['version_id'],
                )

                # Descargar el archivo server-side via middleware (sin exponer URLs)
                from urllib.parse import quote
                dl_url = (
                    f"{middleware_url}/models/download/direct"
                    f"?token={quote(download_token)}"
                    f"&filename={quote(filename)}"
                )

                async with httpx.AsyncClient(timeout=60.0) as dl_client:
                    dl_response = await dl_client.get(dl_url)

                if dl_response.status_code == 200:
                    import base64
                    file_b64 = base64.b64encode(dl_response.content).decode("utf-8")

                    async with self:
                        self.success_message = f"Descargando {filename}..."
                        self.download_in_progress = False
                        self.show_otp_modal = False

                    return rx.download(data=file_b64, filename=filename)
                else:
                    async with self:
                        self.otp_error = f"Error descargando archivo: {dl_response.status_code}"
                        self.download_in_progress = False

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
                f"Tamaño: {model['file_size_mb']} MB",
                color=COLORS["text"],
                size="2",
                font_weight="bold",
            ),
            rx.cond(
                ModelDownloadState.can_download_models,
                rx.button(
                    rx.icon("download", size=16),
                    "Descargar",
                    on_click=lambda: ModelDownloadState.download_model_file(model),
                    color_scheme="green",
                    size="3",
                    style={"font_weight": "bold", "color": "black"},
                    width="100%",
                ),
                rx.text(
                    "Solo administradores pueden descargar modelos",
                    color=COLORS["muted_foreground"],
                    size="1",
                    font_style="italic",
                ),
            ),
            spacing="3",
            align="start",
        ),
        size="2",
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
                        color=COLORS["text"],
                        size="2",
                        font_weight="bold",
                    ),
                ),
                rx.cond(
                    ~ModelDownloadState.otp_requested,
                    # Paso 1: Solicitar OTP
                    rx.vstack(
                        rx.text(
                            "Se enviará un código OTP por SMS a su teléfono registrado.",
                            color=COLORS["text"],
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
                            font_weight="bold",
                        ),
                        rx.input(
                            placeholder="Ingrese el código OTP de 4 dígitos",
                            value=ModelDownloadState.otp_code,
                            on_change=ModelDownloadState.set_otp_code,
                            max_length=4,
                            width="100%",
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
                "padding": "2rem",
                "max_width": "500px",
            },
        ),
        open=ModelDownloadState.show_otp_modal,
    )


def gguf_package_card(pkg: dict[str, Any]) -> rx.Component:
    """Tarjeta para mostrar un paquete GGUF descargable."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.badge(
                    f"PRJ {pkg['project_id']:05d}",
                    color_scheme="green",
                ),
                rx.badge(
                    f"v{pkg['version_id']:03d}",
                    color_scheme="purple",
                ),
                spacing="2",
                width="100%",
            ),
            rx.hstack(
                rx.icon("package", size=18, color=COLORS["accent"]),
                rx.heading(
                    pkg["filename"],
                    size="4",
                    color=COLORS["foreground"],
                ),
                spacing="2",
                align="center",
            ),
            rx.text(
                f"Tamano: {pkg['size_mb']} MB",
                color=COLORS["text"],
                size="2",
                font_weight="bold",
            ),
            rx.cond(
                ModelDownloadState.can_download_models,
                rx.button(
                    rx.icon("download", size=16),
                    "Descargar Paquete GGUF",
                    on_click=lambda: ModelDownloadState.download_gguf_package(pkg),
                    color_scheme="green",
                    size="3",
                    style={"font_weight": "bold", "color": "black"},
                    width="100%",
                ),
                rx.text(
                    "Solo administradores pueden descargar",
                    color=COLORS["muted_foreground"],
                    size="1",
                    font_style="italic",
                ),
            ),
            spacing="3",
            align="start",
        ),
        size="2",
    )


def gguf_packages_section() -> rx.Component:
    """Seccion de paquetes GGUF del entrenamiento autonomo."""
    return rx.cond(
        ModelDownloadState.gguf_loaded,
        rx.vstack(
            rx.hstack(
                rx.icon("cpu", size=20, color=COLORS["accent"]),
                rx.text(
                    "Paquetes GGUF (Entrenamiento Autonomo)",
                    size="4",
                    weight="bold",
                    color=COLORS["foreground"],
                ),
                spacing="2",
                align="center",
            ),
            rx.cond(
                ModelDownloadState.gguf_error,
                rx.callout(
                    ModelDownloadState.gguf_error,
                    icon="alert_circle",
                    color_scheme="red",
                ),
            ),
            rx.cond(
                ModelDownloadState.gguf_loading,
                rx.center(rx.spinner(size="3"), padding="1rem"),
                rx.cond(
                    ModelDownloadState.gguf_packages,
                    rx.grid(
                        rx.foreach(
                            ModelDownloadState.gguf_packages,
                            gguf_package_card,
                        ),
                        columns="3",
                        spacing="4",
                        width="100%",
                    ),
                    rx.center(
                        rx.text(
                            "No hay paquetes GGUF para esta version",
                            color=COLORS["muted_foreground"],
                            size="2",
                        ),
                        padding="1rem",
                    ),
                ),
            ),
            spacing="3",
            width="100%",
        ),
    )


def model_downloads_panel() -> rx.Component:
    """Panel de descargas de modelos para integrar en el info_panel."""
    return rx.vstack(
        # Selectores de proyecto y versión
        rx.card(
            rx.vstack(
                rx.text(
                    "Filtrar por proyecto y versión",
                    size="3",
                    weight="bold",
                    color=COLORS["foreground"],
                ),
                rx.hstack(
                    # Selector de proyecto
                    rx.vstack(
                        rx.text(
                            "Proyecto",
                            size="2",
                            color=COLORS["accent"],
                            font_weight="bold",
                        ),
                        rx.select(
                            ModelDownloadState.dl_project_options,
                            placeholder="Seleccione un proyecto",
                            value=ModelDownloadState.dl_selected_project_name,
                            on_change=ModelDownloadState.dl_set_selected_project,
                            width="250px",
                        ),
                        spacing="1",
                    ),
                    # Selector de versión
                    rx.vstack(
                        rx.text(
                            "Versión",
                            size="2",
                            color=COLORS["accent"],
                            font_weight="bold",
                        ),
                        rx.select(
                            ModelDownloadState.dl_version_options,
                            placeholder="Seleccione una versión",
                            value=ModelDownloadState.dl_selected_version_name,
                            on_change=ModelDownloadState.dl_set_selected_version,
                            width="180px",
                        ),
                        spacing="1",
                    ),
                    # Botón de refrescar
                    rx.box(
                        rx.button(
                            rx.icon("refresh_cw", size=16),
                            "Refrescar",
                            on_click=ModelDownloadState.load_models,
                            color_scheme="green",
                            size="3",
                            style={"font_weight": "bold", "color": "black"},
                            loading=ModelDownloadState.models_loading,
                        ),
                        padding_top="1.3rem",
                    ),
                    spacing="4",
                    width="100%",
                    align="end",
                ),
                spacing="3",
                width="100%",
            ),
            size="2",
        ),
        # Mensajes de error
        rx.cond(
            ModelDownloadState.models_error,
            rx.callout(
                ModelDownloadState.models_error,
                icon="alert_circle",
                color_scheme="red",
            ),
        ),
        # Panel de modelos: solo visible después de pulsar "Refrescar"
        rx.cond(
            ModelDownloadState.models_loaded,
            # Modelos cargados: mostrar spinner o resultados
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
                                "No hay modelos disponibles para el filtro seleccionado",
                                color=COLORS["muted_foreground"],
                                size="3",
                            ),
                            rx.text(
                                "Pruebe a seleccionar otro proyecto o versión",
                                color=COLORS["muted_foreground"],
                                size="2",
                            ),
                            spacing="2",
                        ),
                        padding="4rem",
                    ),
                ),
            ),
            # Aún no se ha pulsado "Refrescar"
            rx.cond(
                ModelDownloadState.models_loading,
                rx.center(
                    rx.spinner(size="3"),
                    padding="2rem",
                ),
                rx.center(
                    rx.vstack(
                        rx.icon("search", size=48, color=COLORS["muted_foreground"]),
                        rx.text(
                            "Seleccione proyecto y versión, luego pulse Refrescar",
                            color=COLORS["muted_foreground"],
                            size="3",
                        ),
                        spacing="2",
                    ),
                    padding="4rem",
                ),
            ),
        ),
        # Sección de paquetes GGUF
        gguf_packages_section(),
        # Modal de OTP
        otp_modal(),
        spacing="5",
        width="100%",
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
                color=COLORS["text"],
                size="3",
            ),
            rx.divider(),
            model_downloads_panel(),
            spacing="5",
            width="100%",
            padding="2rem",
        ),
    )
