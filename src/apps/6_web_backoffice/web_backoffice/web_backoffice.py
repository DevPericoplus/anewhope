import base64
import importlib.util
import json
import logging
import sys
from pathlib import Path
from typing import Any, AsyncGenerator, Optional, TypedDict

from sqlalchemy import text

# Configurar sys.path ANTES de cualquier import local
# para que los módulos puedan encontrar adapters, components, etc.
_backoffice_dir = Path(__file__).parent.parent
if str(_backoffice_dir) not in sys.path:
    sys.path.insert(0, str(_backoffice_dir))

import reflex as rx

from adapters.api_client import (
    add_ticket_response,
    actualizar_tecnologia,
    asignar_tecnologia,
    create_organization_user,
    create_project,
    create_project_assignment,
    create_project_version,
    create_version_full,
    ensure_valid_tokens,
    get_organization_projects,
    get_organization_tickets,
    get_organization_users,
    get_project_versions,
    get_proyecto_tecnologia,
    get_roles,
    get_tecnologias,
    get_tecnologias_asignadas_org,
    get_user_permissions,
    login_user,
    logout_user,
    refresh_tokens,
    request_login_otp,
    update_project_existence,
    update_project_status,
    update_ticket_status,
    update_user_status,
)
from pages.flujos import FlujosState, flujos_diagram, load_flujos_content
from pages.model_downloads import ModelDownloadState, model_downloads_panel
from pages.organizacion import load_organizacion_content
from pages.proyecciones import load_proyecciones_content
from pages.tecnologias import load_tecnologias_content
from pages.estado_proyectos import estado_proyectos_panel, EstadoProyectosState
from pages.analisis_resultados import analisis_resultados_page, AnalisisResultadosState
from low_panel_pages.show_md import show_md  # noqa: F401 - Importado para registrar la ruta
from web_backoffice.shared_state import SharedSessionState
from components.explorador import explorador_panel, ExploradorState
from components.org_selector import org_selector_bar, org_project_selector_bar, org_project_version_selector_bar
from components.seguimiento import seguimiento_panel, SeguimientoState
from components.informes import informes_panel, InformesState

# Importar logger de actividad usando importlib (el directorio tiene número)
_activity_logger_path = Path(__file__).resolve().parents[3] / "2_shared_application" / "reflex_shared" / "activity_logger.py"
_spec = importlib.util.spec_from_file_location("activity_logger", _activity_logger_path)
_activity_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_activity_module)

# Logger de actividad del backoffice
activity_log = _activity_module.get_backoffice_logger()
activity_log.log_startup()

# Importar storage_access_structure usando importlib
_storage_structure_path = Path(__file__).resolve().parents[3] / "2_shared_application" / "storage_access_structure.py"
_storage_spec = importlib.util.spec_from_file_location("storage_access_structure", _storage_structure_path)
_storage_module = importlib.util.module_from_spec(_storage_spec)
_storage_spec.loader.exec_module(_storage_module)
get_folder_by_id_organization = _storage_module.get_folder_by_id_organization
get_folder_by_id_project = _storage_module.get_folder_by_id_project
get_folder_by_id_version = _storage_module.get_folder_by_id_version

# Importar version_reader usando importlib
_version_reader_path = Path(__file__).resolve().parents[3] / "2_shared_application" / "utils" / "version_reader.py"
_version_spec = importlib.util.spec_from_file_location("version_reader", _version_reader_path)
_version_module = importlib.util.module_from_spec(_version_spec)
_version_spec.loader.exec_module(_version_module)
get_version = _version_module.get_version

# Obtener versión del backoffice
APP_VERSION = get_version("backoffice")

# Importar org_selector_helpers usando importlib (el directorio tiene número)
_org_selector_helpers_path = Path(__file__).resolve().parents[3] / "2_shared_application" / "reflex_shared" / "org_selector_helpers.py"
_org_helpers_spec = importlib.util.spec_from_file_location("org_selector_helpers", _org_selector_helpers_path)
_org_helpers_module = importlib.util.module_from_spec(_org_helpers_spec)
_org_helpers_spec.loader.exec_module(_org_helpers_module)
load_organizations_for_selector = _org_helpers_module.load_organizations_for_selector
load_projects_for_selector = _org_helpers_module.load_projects_for_selector
load_versions_for_selector = _org_helpers_module.load_versions_for_selector
find_org_id_by_name = _org_helpers_module.find_org_id_by_name

# Importar db_query_helper para acceso a myllm_projects_db (plantillas de jobs)
_db_helper_path = Path(__file__).resolve().parents[3] / "2_shared_application" / "db_query_helper.py"
_db_helper_spec = importlib.util.spec_from_file_location("db_query_helper_bo", _db_helper_path)
_db_helper_module = importlib.util.module_from_spec(_db_helper_spec)
_db_helper_spec.loader.exec_module(_db_helper_module)
get_projects_db_engine = _db_helper_module.get_projects_db_engine
get_projects_db_writer_engine = _db_helper_module.get_projects_db_writer_engine

# Importar env_settings para acceso a variables de entorno (backend_ia_base_storage, etc.)
_env_settings_path = Path(__file__).resolve().parents[3] / "2_shared_application" / "config" / "env_settings.py"
_env_settings_spec = importlib.util.spec_from_file_location("env_settings_bo_main", _env_settings_path)
_env_settings_bo = importlib.util.module_from_spec(_env_settings_spec)
_env_settings_spec.loader.exec_module(_env_settings_bo)
get_env_value = _env_settings_bo.get_env_value

# Cargar módulo de SMS para envío de OTP
_send_message_by_sms = None
try:
    _common_security_path = (
        Path(__file__).resolve().parents[3]
        / "2_shared_application"
        / "security"
        / "common_security.py"
    )
    if _common_security_path.exists():
        _sec_spec = importlib.util.spec_from_file_location("common_security_bo", _common_security_path)
        if _sec_spec and _sec_spec.loader:
            _sec_module = importlib.util.module_from_spec(_sec_spec)
            _sec_spec.loader.exec_module(_sec_module)
            _send_message_by_sms = getattr(_sec_module, "send_message_by_sms", None)
except Exception as _sec_exc:
    logging.getLogger(__name__).error("Error al cargar módulo de SMS: %s", _sec_exc)


# TypedDict para tipado de fases y subfases del entrenamiento
class SubfaseDict(TypedDict):
    """Estructura de una subfase de entrenamiento."""
    key: str
    nombre: str
    status: str
    tiempo: str


class PhaseDict(TypedDict):
    """Estructura de una fase de entrenamiento."""
    key: str
    nombre: str
    emoji: str
    descripcion: str
    status: str
    tiempo: str
    subfases: list[SubfaseDict]


class PackageDict(TypedDict):
    """Estructura de un paquete de entrenamiento disponible para descarga."""
    id_entrenamiento: int
    package_filename: str
    training_mode: str
    created_at: str
    file_size_mb: float
    ollama_model_name: str
    gguf_quantization: str
    package_size_mb: float
    dataset_size: int
    package_generated_at: str


COLORS = {
    "background": "#1a1a1a",
    "card": "#2d2d2d",
    "foreground": "#f2f2f5",
    "primary": "#FF8C00",  # Naranja para backoffice
    "secondary": "#383854",
    "border": "#404040",
    "input": "#3a3a3a",
    "muted": "#9CA3AF",  # Gris medio para textos secundarios
    "muted_foreground": "#E0E0E0",
    "accent": "#FF8C00",  # Naranja para backoffice
}

# Define the State class for managing application state
class State(SharedSessionState):
    """Backoffice state with Redis-based session sharing."""

    # User portal state (campos locales del backoffice, no compartidos)
    user_active_menu: str = "inicio"
    user_username: str = ""
    user_password: str = ""
    user_otp: str = ""
    user_active_tab: str = "resumen"
    user_permissions: list[dict[str, str]] = []
    login_error: str = ""
    otp_request_message: str = ""

    # Internal menu state
    internal_active_menu: str = ""

    # Estado para página Asistente (Ollama)
    asistente_ollama_available: bool = False
    asistente_ollama_status: str = "Verificando..."
    asistente_models: list[str] = []
    asistente_selected_model: str = ""
    asistente_prompt: str = ""
    asistente_response: str = ""
    asistente_is_loading: bool = False
    asistente_error: str = ""

    # Estado para página Sistema (sys_ prefix) - Health checks
    # Panel Frontend
    sys_frontend_status: str = "Verificando..."
    sys_frontend_available: bool = False
    sys_backoffice_status: str = "Verificando..."
    sys_backoffice_available: bool = False
    sys_middleware_status: str = "Verificando..."
    sys_middleware_available: bool = False
    sys_redis_status: str = "Verificando..."
    sys_redis_available: bool = False
    sys_sms_api_status: str = "Verificando..."
    sys_sms_api_available: bool = False

    # Panel Backend
    sys_broker_status: str = "Verificando..."
    sys_broker_available: bool = False
    sys_backend_core_status: str = "Verificando..."
    sys_backend_core_available: bool = False
    sys_fmanagement_status: str = "Verificando..."
    sys_fmanagement_available: bool = False
    sys_mariadb_status: str = "Verificando..."
    sys_mariadb_available: bool = False

    # Panel Trainer
    sys_trainer_status: str = "Verificando..."
    sys_trainer_available: bool = False
    sys_chromadb_status: str = "Verificando..."
    sys_chromadb_available: bool = False
    sys_ollama_status: str = "Verificando..."
    sys_ollama_available: bool = False

    # Estado para página Descargas (dl_ prefix)
    dl_otp_validated: bool = False
    dl_otp_loading: bool = False
    dl_selected_org_id: int = 0
    dl_selected_org_name: str = ""
    dl_selected_project_id: int = 0
    dl_selected_project_name: str = ""
    dl_selected_version_id: int = 0
    dl_selected_version_name: str = ""
    dl_organizations: list[dict] = []
    dl_projects: list[dict] = []
    dl_versions: list[dict] = []
    dl_packages: list[PackageDict] = []
    dl_loading_packages: bool = False
    dl_downloading: bool = False
    dl_error: str = ""

    # Estado del modal OTP para descargas
    dl_show_otp_modal: bool = False
    dl_otp_code: str = ""
    dl_otp_phone: str = ""
    dl_otp_requested: bool = False
    dl_otp_error: str = ""
    dl_otp_pkg_id: int = 0

    @rx.var
    def can_download_models(self) -> bool:
        """Solo SuperAdmin (1) y Admin Organización (2) pueden descargar."""
        return self.identity_type_id in (1, 2)

    @rx.var
    def dl_organization_options(self) -> list[str]:
        """Opciones para selector de organizaciones."""
        return [org.get("name", "") for org in self.dl_organizations if org.get("name")]

    @rx.var
    def dl_project_options(self) -> list[str]:
        """Opciones para selector de proyectos."""
        return [prj.get("name", "") for prj in self.dl_projects if prj.get("name")]

    @rx.var
    def dl_version_options(self) -> list[str]:
        """Opciones para selector de versiones."""
        return [ver.get("nombre", "") for ver in self.dl_versions if ver.get("nombre")]

    # Estado para gestión de usuarios y proyectos de la organización
    # Estado para gestión de usuarios de la organización
    # Estructura: {"user_id": int, "user_name": str, "active": bool}
    org_users: list[dict] = []
    org_projects: list[dict] = [
        {"id": 1, "name": "Asistente Comercial", "description": "Modelo de lenguaje para atención al cliente", "locked": False},
    ]
    
    # Estado del modal de creación de usuario
    show_create_user_modal: bool = False
    new_user_name: str = ""
    new_user_email: str = ""
    new_user_mobile: str = ""
    create_user_error: str = ""
    create_user_success: str = ""
    is_creating_user: bool = False

    # Estado del modal de creación de proyecto
    show_create_project_modal: bool = False
    new_project_name: str = ""
    new_project_description: str = ""
    create_project_error: str = ""
    create_project_success: str = ""
    is_creating_project: bool = False

    # Estado para gestión de tickets de soporte
    org_tickets: list[dict] = []  # Lista de tickets de la organización

    # Estado del modal de solicitud de soporte (crear ticket desde proyecto)
    show_support_modal: bool = False
    support_project_id: int = 0
    support_project_name: str = ""
    support_titulo: str = ""
    support_consulta: str = ""
    support_error: str = ""
    support_success: str = ""
    is_creating_support: bool = False

    # Estado del modal de gestión de ticket
    show_ticket_modal: bool = False
    selected_ticket_id: int = 0
    selected_ticket_titulo: str = ""
    selected_ticket_consulta: str = ""
    selected_ticket_estado: str = "abierto"
    selected_ticket_prioridad: str = "media"
    selected_ticket_respuesta: str = ""
    ticket_modal_error: str = ""
    ticket_modal_success: str = ""

    # Estado del modal de asignación de usuario a proyecto
    show_assign_user_modal: bool = False
    assign_user_id: int = 0
    assign_user_name: str = ""
    assign_selected_project_id: int = 0
    assign_selected_role_id: int = 0
    assign_error: str = ""
    assign_success: str = ""
    assign_roles: list[dict] = []  # Lista de roles disponibles
    is_updating_ticket: bool = False

    # Estado para panel de asignaciones de proyectos (solo lectura, en página Organización)
    org_project_assignments: list[dict] = []  # [{proyecto_nombre, usuario_nombre, rol_nombre}]

    # Estado para gestión de tecnologías
    tecnologias_list: list[dict] = []  # Lista de tecnologías disponibles
    selected_tech_project_id: int = 0  # Proyecto seleccionado
    selected_tecnologia_id: int = 0  # Tecnología seleccionada
    proyecto_tecnologia_asignada: dict = {}  # Asignación actual del proyecto
    tech_assign_error: str = ""
    tech_assign_success: str = ""
    is_loading_tecnologias: bool = False
    tecnologias_asignadas_list: list[dict] = []  # Proyectos con sus tecnologías asignadas
    
    # Estado para gestión de proyecciones (versiones y contenidos)
    proyecciones_project_id: int = 0  # Proyecto seleccionado en proyecciones
    proyecciones_project_name: str = ""  # Nombre del proyecto seleccionado
    proyecciones_versions: list[dict] = []  # Lista de versiones del proyecto
    proyecciones_version_id: int = 0  # Versión seleccionada
    proyecciones_version_folder: str = ""  # Carpeta de versión (v001, v002, etc.)
    proyecciones_org_folder: str = ""  # Carpeta de organización (ORG00001, etc.)
    proyecciones_prj_folder: str = ""  # Carpeta de proyecto (PRJ0001, etc.)
    proyecciones_error: str = ""
    proyecciones_success: str = ""
    is_loading_versions: bool = False

    # Estado para Gestor de Asignaciones (SuperAdmin only)
    assignments_active_tab: str = "organizaciones"  # "organizaciones" or "proyectos"
    assignments_internal_users: list[dict] = []
    assignments_organizations: list[dict] = []
    assignments_projects: list[dict] = []
    assignments_org_roles: list[dict] = []  # Role catalog for organizations
    assignments_project_roles: list[dict] = []  # From proyectos_roles_base

    # Organization assignment form
    selected_user_org: int = 0
    selected_organization_assign: int = 0
    selected_org_role: int = 0
    org_assignments_list: list[dict] = []
    org_assignment_error: str = ""
    org_assignment_success: str = ""

    # Project assignment form
    selected_user_project: int = 0
    selected_org_for_project: int = 0
    selected_project_assign: int = 0
    selected_project_role: int = 0
    project_assignments_list: list[dict] = []
    project_assignment_error: str = ""
    project_assignment_success: str = ""
    prerequisite_validation_error: str = ""

    # Prompts management (SuperAdmin only)
    prompts_category: str = "identidades"  # identidades, contexto, solicitudes, modalidad
    prompts_list: list[dict] = []
    selected_prompt_id: int = 0
    form_mode: str = "create"  # "create" or "edit"
    form_name: str = ""
    form_description: str = ""
    form_prompt: str = ""
    form_error: str = ""
    form_success: str = ""

    # Job Templates management (SuperAdmin only)
    jt_list: list[dict] = []  # Lista de plantillas cargadas
    jt_tipos: list[dict] = []  # Catálogo jobs_tipos
    jt_estados: list[dict] = []  # Catálogo jobs_estados
    jt_modelos: list[dict] = []  # Catálogo jobs_modelos
    jt_salidas: list[dict] = []  # Catálogo jobs_salidas
    jt_form_mode: str = "create"  # "create" o "edit"
    jt_selected_id: int = 0
    jt_nombre: str = ""
    jt_descripcion: str = ""
    jt_id_tipo: int = 0
    jt_es_programable: bool = False
    jt_id_estado_inicial: int = 0
    jt_id_modelo: int = 0
    jt_id_salida: int = 0
    jt_acepta_entrada: bool = False
    jt_permite_hijos: bool = False
    jt_error: str = ""
    jt_success: str = ""

    # Análisis de Documentación - Selectores y estado
    ad_org_id: int = 0
    ad_orgs: list[dict] = []  # [{"id": int, "name": str}]
    ad_project_id: int = 0
    ad_projects: list[dict] = []  # [{"id": int, "name": str}]
    ad_version_id: int = 0
    ad_versions: list[dict] = []  # [{"id_version": int, "version_folder": str}]
    # Análisis de Documentación - Plantillas y formulario
    ad_templates: list[dict] = []  # Plantillas filtradas por tipo analisis_documentacion
    ad_selected_template_id: int = 0
    ad_job_nombre: str = ""
    ad_job_descripcion: str = ""
    ad_job_id_modelo: int = 0
    ad_job_id_salida: int = 0
    ad_job_id_estado: int = 0
    ad_job_programado_para: str = ""  # datetime como string
    ad_modelos: list[dict] = []
    ad_salidas: list[dict] = []
    ad_estados: list[dict] = []
    ad_error: str = ""
    ad_success: str = ""
    # Análisis de Documentación - Visor de jobs
    ad_jobs: list[dict] = []
    # Análisis de Documentación - Modal de job + prompt builder
    ad_modal_open: bool = False
    ad_modal_job: dict = {}
    ad_prompts_identidades: list[dict] = []
    ad_prompts_contexto: list[dict] = []
    ad_prompts_solicitudes: list[dict] = []
    ad_prompts_modalidad: list[dict] = []
    ad_sel_identidad: str = ""
    ad_sel_contexto: str = ""
    ad_sel_solicitud: str = ""
    ad_sel_modalidad: str = ""
    ad_prompt_final: str = ""
    ad_trainer_ack: bool = False
    ad_trainer_sending: bool = False
    ad_trainer_error: str = ""

    # Entrenamientos (ent_ prefix)
    ent_pending_versions: list[dict] = []
    ent_error: str = ""
    ent_loading: bool = False
    ent_sending_state_id: int = 0
    ent_send_error: str = ""

    # Modal de parámetros de entrenamiento (ent_modal_ prefix)
    ent_modal_open: bool = False
    ent_modal_loading: bool = False
    ent_modal_version_data: dict = {}
    ent_modal_es_primer: bool = True
    ent_modal_es_reentrenamiento: bool = False
    # Grupo 1: Preparación de datos
    ent_modal_chunk_size: str = "1000"
    ent_modal_chunk_overlap: str = "200"
    ent_modal_embedding_dimension: str = "768"
    ent_modal_sequence_length: str = "512"
    ent_modal_distance_metric: str = "cosine"
    # Grupo 2: Modelo y generación
    ent_modal_model_type: str = ""
    ent_modal_modelos_disponibles: list[str] = []
    ent_modal_temperature: str = "0.7"
    ent_modal_max_tokens: str = "2048"
    ent_modal_top_k: str = "5"
    # Grupo 3: Optimización
    ent_modal_learning_rate: str = "0.001"
    ent_modal_batch_size: str = "32"
    ent_modal_epochs: str = "10"
    ent_modal_hidden_units: str = "256"
    ent_modal_dropout_rate: str = "0.1"
    ent_modal_loss_function: str = "cross_entropy"
    ent_modal_optimizer: str = "adam"
    # Warnings de validación
    ent_modal_warnings: list[str] = []

    # Modal de confirmación entrenamiento autónomo (ent_auto_modal_ prefix)
    ent_auto_modal_open: bool = False
    ent_auto_modal_training_mode: str = ""
    ent_auto_modal_version_data: dict = {}

    # Evolución de entrenamiento (ent_evo_ prefix)
    ent_evo_active: bool = False
    ent_evo_version_label: str = ""
    ent_evo_org_name: str = ""
    ent_evo_project_name: str = ""
    ent_evo_phases: list[PhaseDict] = []
    ent_evo_id_entrenamiento: int = 0         # ID del entrenamiento en curso
    ent_evo_current_phase: str = ""           # Fase actual (ej: "3.2")
    ent_evo_current_phase_name: str = ""      # Nombre legible
    ent_evo_can_cancel: bool = True           # Si se puede cancelar
    ent_evo_cancelling: bool = False          # Si está cancelando
    ent_evo_expanded_phase: str = ""          # Key de la fase expandida (vacío = ninguna)
    ent_evo_is_autonomous: bool = False       # Si es entrenamiento autónomo (fases 6-9)
    ent_evo_training_mode: str = ""           # Modo: simulation, test, production
    ent_evo_version_data: dict = {}           # Datos completos de la versión en entrenamiento

    @rx.var
    def ent_evo_rag_completed(self) -> bool:
        """Indica si el entrenamiento RAG (fases 2-5) está completado y listo para autónomo.

        Returns:
            True si todas las fases RAG están completadas y NO es un entrenamiento autónomo
        """
        if self.ent_evo_is_autonomous:
            return False

        if not self.ent_evo_active or len(self.ent_evo_phases) == 0:
            return False

        # Verificar que todas las fases estén completadas
        return all(phase.get("status") == "completed" for phase in self.ent_evo_phases)

    @rx.var
    def ent_evo_autonomous_completed(self) -> bool:
        """Indica si el entrenamiento autónomo (fases 6-9) está completado.

        Returns:
            True si todas las subfases autónomas están completadas
        """
        if not self.ent_evo_is_autonomous or not self.ent_evo_active:
            return False

        if len(self.ent_evo_phases) == 0:
            return False

        # Verificar que todas las fases autónomas estén completadas
        return all(phase.get("status") == "completed" for phase in self.ent_evo_phases)

    # Selector de organización para backoffice (filtrado por asignaciones)
    # Usado por páginas: Organizacion, Tecnologias, Proyecciones
    bo_organizations: list[dict] = []
    bo_selected_org_id: int = 0

    # Nota: Los siguientes campos ya vienen de SharedSessionState:
    # - is_logged_in, access_token, session_token, user_id, organization_id
    # - user_name, user_email, user_mobile, identity_type_id
    # - 45 permisos (can_training_create, can_folder_rename, etc.)
    # - Métodos: load_user_data(), clear_session(), go_to_frontend(), etc.
    
    # ========== Propiedades computadas de permisos ==========
    
    @rx.var
    def can_manage_org_users(self) -> bool:
        """Indica si el usuario actual puede gestionar usuarios de la organización.
        
        Regla de seguridad: Solo pueden gestionar usuarios:
        - SuperAdmin (identity_type_id = 1)
        - Administrador de Organización (identity_type_id = 2)
        - Agentes automáticos con rol admin (identity_type_id = 10)
        
        Los editores (3), lectores (4), auditores (5) y agentes no-admin (11-13)
        NO pueden gestionar usuarios.
        """
        if self.identity_type_id <= 0:
            return False
        # SuperAdmin, Admin de Org, o Agente Admin
        return self.identity_type_id in (1, 2, 10)

    # ========== Selector de organización para backoffice ==========

    @rx.var
    def bo_organization_names(self) -> list[str]:
        """Nombres de organizaciones accesibles para el selector."""
        return [org["name"] for org in self.bo_organizations]

    @rx.var
    def bo_selected_org_display(self) -> str:
        """Nombre de la organización seleccionada en el selector."""
        if self.bo_selected_org_id > 0:
            for org in self.bo_organizations:
                if org["id"] == self.bo_selected_org_id:
                    return org["name"]
        return ""

    def bo_load_organizations(self) -> None:
        """Carga las organizaciones accesibles por el usuario interno."""
        orgs, default_id = load_organizations_for_selector(
            user_id=self.user_id,
            identity_type_id=self.identity_type_id,
            session_org_id=self.organization_id,
        )
        self.bo_organizations = orgs
        if self.bo_selected_org_id == 0 and default_id > 0:
            self.bo_selected_org_id = default_id
            self.organization_id = default_id

    def bo_set_organization(self, org_name: str) -> None:
        """Cambia la organización seleccionada y recarga datos de la página actual."""
        new_id = find_org_id_by_name(self.bo_organizations, org_name)
        if new_id <= 0:
            return

        self.bo_selected_org_id = new_id
        self.organization_id = new_id

        # Recargar datos según la página activa
        current_menu = self.user_active_menu
        if current_menu == "organizacion":
            self.load_org_users()
            self.load_org_projects()
            self.load_org_tickets()
            self.load_org_project_assignments()
        elif current_menu == "tecnologias":
            self.load_org_projects()
            self.load_tecnologias_asignadas()
        elif current_menu == "proyecciones":
            self.load_org_projects()
            self.proyecciones_project_id = 0
            self.proyecciones_project_name = ""
            self.proyecciones_versions = []

    # ========== Propiedades computadas de tecnologías ==========

    @rx.var
    def projects_for_tech_select(self) -> list[str]:
        """Lista de proyectos activos para el selector de tecnologías.

        Muestra solo el nombre del proyecto (igual que en frontend).
        """
        if not self.org_projects:
            return []
        return [
            p.get("name", p.get("nombre", "Sin nombre"))
            for p in self.org_projects
            if p.get("active", True) and p.get("existe", True) and p.get("name", p.get("nombre"))
        ]

    @rx.var
    def assign_project_names(self) -> list[str]:
        """Lista de nombres de proyectos para el selector de asignación."""
        if not self.org_projects:
            return []
        return [
            p.get("name", p.get("nombre", "Sin nombre"))
            for p in self.org_projects
            if p.get("name", p.get("nombre"))
        ]

    @rx.var
    def assign_role_names(self) -> list[str]:
        """Lista de nombres de roles para el selector de asignación.

        Solo muestra roles de usuarios regulares (Editor=3, Lector=4, Auditor=5).
        No permite crear más administradores ni asignar roles de agentes.
        """
        if not self.assign_roles:
            return []
        # Solo roles permitidos: Editor (3), Lector (4), Auditor (5)
        allowed_role_ids = [3, 4, 5]
        return [
            r.get("identity_type_name", "Sin nombre")
            for r in self.assign_roles
            if r.get("identity_type_id") in allowed_role_ids and r.get("identity_type_name")
        ]

    @rx.var
    def selected_tech_project_name(self) -> str:
        """Nombre del proyecto seleccionado para tecnologías."""
        if self.selected_tech_project_id <= 0:
            return ""
        for p in self.org_projects:
            if p.get("id") == self.selected_tech_project_id:
                return p.get("name", p.get("nombre", ""))
        return ""

    @rx.var
    def can_manage_assignments(self) -> bool:
        """Only SuperAdmin can access assignments manager."""
        return self.identity_type_id == 1

    @rx.var
    def internal_users_for_select(self) -> list[str]:
        """User names for selector."""
        return [u.get("user_name", "") for u in self.assignments_internal_users]

    @rx.var
    def organizations_for_select(self) -> list[str]:
        """Organization names for selector."""
        return [o.get("organization_name", "") for o in self.assignments_organizations]

    @rx.var
    def projects_filtered_by_org(self) -> list[dict]:
        """Projects filtered by selected organization (already filtered by load_projects_for_org)."""
        return self.assignments_projects

    @rx.var
    def projects_for_select(self) -> list[str]:
        """Project names for selector."""
        return [p.get("nombre", "") for p in self.assignments_projects]

    @rx.var
    def filtered_org_roles(self) -> list[dict]:
        """Filtered organization roles (exclude SuperAdmin and internal roles).

        Shows only roles with identity_type_id between 2 and 5:
        - Excludes: identity_type_id = 1 (SuperAdmin)
        - Excludes: identity_type_id >= 6 (Internal roles)
        """
        return [
            r for r in self.assignments_org_roles
            if 1 < r.get("identity_type_id", 0) < 6
        ]

    @rx.var
    def org_roles_for_select(self) -> list[str]:
        """Organization role names for selector."""
        return [r.get("identity_type_name", "") for r in self.assignments_org_roles]

    @rx.var
    def project_roles_for_select(self) -> list[str]:
        """Project role names for selector."""
        return [r.get("nombre_rol", "") for r in self.assignments_project_roles]

    def check_backoffice_access(self):
        """
        Verifica que el usuario tiene acceso al backoffice.
        Redirige al frontend si no tiene permiso.
        """
        if not self.can_access_backoffice:
            return self.go_to_frontend()
    
    def load_tokens_from_url(self, access_token: str, session_token: str, user_id: str, org_id: str):
        """
        Carga tokens desde parámetros de URL (pasados desde el frontend).
        """
        if access_token and session_token:
            self.access_token = access_token
            self.session_token = session_token
            self.user_id = int(user_id) if user_id else 0
            self.organization_id = int(org_id) if org_id else 0
            self.is_logged_in = True
            # Cargar permisos desde el middleware
            return self.load_permissions_from_session()
        return None
    
    def load_permissions_from_session(self):
        """
        Carga permisos del usuario desde el middleware si no están en sesión.
        
        Este método se ejecuta al entrar al backoffice para asegurar que:
        1. Los permisos están cargados en SharedSessionState (sincronizados vía Redis)
        2. Si no hay permisos en Redis, los carga desde el middleware (fallback)
        3. Verifica que el usuario tiene acceso al backoffice
        
        Returns:
            Redirección al frontend si no tiene acceso o error
        """
        # Si no hay tokens, redirigir al frontend para login
        if not self.access_token or not self.session_token:
            self.login_error = "Debe iniciar sesión desde el sitio principal"
            return self.go_to_frontend()
        
        # Si ya tiene permisos cargados (desde Redis), verificar acceso
        if self.can_training_create:
            # Los permisos ya están sincronizados desde el frontend vía Redis
            self.current_app = "backoffice"
            self.update_activity()
            return None
        
        # Fallback: Si Redis no tiene permisos, cargar desde middleware
        try:
            permissions_response = get_user_permissions(
                self.access_token, self.session_token
            )
            
            if not permissions_response:
                self.login_error = "No se pudieron obtener los permisos del usuario"
                return self.go_to_frontend()
            
            # Obtener permisos de bajo nivel
            low_level_permissions = permissions_response.get("low_level_permissions", {})
            
            # Actualizar permisos en SharedSessionState (se sincroniza con Redis)
            self._load_permissions(low_level_permissions)
            
            # Actualizar datos de usuario si es necesario
            self.user_id = int(permissions_response.get("user_id", self.user_id))
            self.organization_id = int(permissions_response.get("organization_id", self.organization_id))
            self.identity_type_id = int(permissions_response.get("identity_type_id", self.identity_type_id))
            self.is_logged_in = True
            self.current_app = "backoffice"
            self.update_activity()

            # Verificar que tiene acceso al backoffice
            if not self.can_access_backoffice:
                self.login_error = "No tiene permisos para acceder al backoffice"
                return self.go_to_frontend()

            return None
            
        except Exception as exc:
            self.login_error = f"Error al cargar permisos: {str(exc)}"
            return self.go_to_frontend()
    
    def set_user_menu(self, menu: str):
        """Set active menu item for user portal."""
        self.user_active_menu = menu
        self.internal_active_menu = ""  # Desactivar menú interno cuando se activa menú principal

        # Asegurar que identity_type_id y organization_id están disponibles desde el token
        if self.access_token:
            if self.identity_type_id <= 0:
                extracted_identity = self._extract_identity_type_id_from_token(self.access_token)
                if extracted_identity > 0:
                    self.identity_type_id = extracted_identity
            if self.organization_id <= 0:
                extracted_org = self._extract_org_id_from_token(self.access_token)
                if extracted_org > 0:
                    self.organization_id = extracted_org

        # Log de navegación
        if self.is_logged_in and self.user_id > 0:
            activity_log.log_navigation(self.user_id, menu)

        # NOTA: Cargas de datos comentadas temporalmente para evitar bloqueos
        # Las páginas deben cargar sus propios datos cuando se renderizan
        if menu == "flujos":
            organization_id = self.organization_id
            if organization_id <= 0 and self.access_token:
                organization_id = self._extract_org_id_from_token(self.access_token)
                if organization_id > 0:
                    self.organization_id = organization_id
            return FlujosState.initialize_from_session(
                organization_id,
                user_id=self.user_id,
                identity_type_id=self.identity_type_id,
            )
        if menu in ("organizacion", "tecnologias", "proyecciones"):
            self.bo_load_organizations()
            if menu == "organizacion":
                self.load_org_users()
                self.load_org_projects()
                self.load_org_tickets()
                self.load_org_project_assignments()
            elif menu == "tecnologias":
                self.load_org_projects()
                self.load_tecnologias()
                self.load_tecnologias_asignadas()
            elif menu == "proyecciones":
                self.load_org_projects()
                self.proyecciones_project_id = 0
                self.proyecciones_project_name = ""
                self.proyecciones_versions = []
        if menu == "descargas":
            return self.dl_init_page()

    def set_internal_menu(self, menu: str):
        """Set active menu item for internal tools."""
        print(f"[DEBUG] set_internal_menu called with menu='{menu}'")
        self.internal_active_menu = menu
        self.user_active_menu = ""  # Desactivar menú principal cuando se activa menú interno

        # Resetear panel de evolución al navegar a entrenamientos
        if menu == "entrenamientos":
            self.ent_evo_reset()

        # Inicializar Descargas al navegar (cargar organizaciones)
        if menu == "descargas":
            self.dl_init_page()

        # Inicializar Estado de Proyectos al navegar
        if menu == "estado_proyectos":
            return self.ep_init_page()

        # Inicializar Asistente al navegar (health check + modelos)
        if menu == "asistente":
            self.check_ollama_health()
            self.load_ollama_models()

        # Log de navegación
        if self.is_logged_in and self.user_id > 0:
            activity_log.log_navigation(self.user_id, f"internal:{menu}")

    # ========== Página Estado de Proyectos (ep_ prefix) ==========

    def ep_init_page(self):
        """Inicializa Estado de Proyectos: copia tokens y carga organizaciones."""
        print(f"[EP] ep_init_page: user_id={self.user_id}, access_token={'SET' if self.access_token else 'EMPTY'}")

        # Asegurar que los tokens son válidos (renovar si expiraron)
        if not self.ensure_tokens_valid():
            print("[EP] ep_init_page: tokens no válidos, no se puede cargar")
            return

        print(f"[EP] ep_init_page: tokens válidos, procediendo con carga")

        from pages.estado_proyectos import EstadoProyectosState

        # Cargar organizaciones directamente con los tokens del main State
        try:
            from adapters.api_client import get_all_organizations

            orgs_data = get_all_organizations(
                access_token=self.access_token,
                session_token=self.session_token,
            )
            print(f"[EP] ep_init_page: API returned {len(orgs_data)} orgs")
            if orgs_data:
                print(f"[EP] ep_init_page: first org: {orgs_data[0]}")
        except Exception as e:
            print(f"[EP] ep_init_page: EXCEPTION: {e}")
            orgs_data = []

        organizations = [
            {
                "id": int(org.get("organization_id", org.get("id", 0))),
                "name": org.get("organization_name", org.get("name", "")),
            }
            for org in orgs_data
            if org.get("organization_id", org.get("id", 0))
        ]

        # Cargar proyectos del primer org (o la org del usuario)
        selected_org_id = self.organization_id if self.organization_id > 0 else (organizations[0]["id"] if organizations else 0)

        projects = []
        if selected_org_id > 0:
            try:
                from adapters.api_client import get_organization_projects

                projects_data = get_organization_projects(
                    organization_id=selected_org_id,
                    access_token=self.access_token,
                    session_token=self.session_token,
                    include_deleted=False,
                )
                projects = [
                    {
                        "id": int(p.get("id", 0)),
                        "name": p.get("name", p.get("nombre", "")),
                    }
                    for p in projects_data
                    if p.get("active", True) and p.get("existe", True)
                ]
                print(f"[EP] ep_init_page: {len(projects)} projects for org {selected_org_id}")
            except Exception as e:
                print(f"[EP] ep_init_page: projects EXCEPTION: {e}")

        # Cargar versiones del primer proyecto
        selected_project_id = projects[0]["id"] if projects else 0
        versions = []
        if selected_project_id > 0 and selected_org_id > 0:
            try:
                from adapters.api_client import get_project_versions

                result = get_project_versions(
                    project_id=selected_project_id,
                    organization_id=selected_org_id,
                    access_token=self.access_token,
                    session_token=self.session_token,
                )
                versions_data = result.get("versiones", [])
                versions = [
                    {
                        "version_id": int(v.get("id_version", 0)),
                        "state_internal": v.get("state_internal", ""),
                        "created_at": v.get("created_at", ""),
                    }
                    for v in versions_data
                    if v.get("id_version", 0)
                ]
                print(f"[EP] ep_init_page: {len(versions)} versions for project {selected_project_id}")
            except Exception as e:
                print(f"[EP] ep_init_page: versions EXCEPTION: {e}")

        # Cargar estado de la primera versión
        selected_version_id = versions[0]["version_id"] if versions else 0
        current_state = {}
        if selected_project_id > 0 and selected_version_id > 0:
            try:
                from adapters.api_client import get_version_state

                result = get_version_state(
                    project_id=selected_project_id,
                    version_id=selected_version_id,
                    access_token=self.access_token,
                    session_token=self.session_token,
                )
                state = result.get("data", result.get("state", result))
                if state and result.get("success", True):
                    def to_bool(val):
                        if isinstance(val, bool):
                            return val
                        if isinstance(val, int):
                            return val == 1
                        if isinstance(val, str):
                            return val in ("1", "true", "True")
                        return False

                    current_state = {
                        "id": int(state.get("id", 0)),
                        "state": state.get("state", ""),
                        "state_internal": state.get("state_internal", ""),
                        "protected": to_bool(state.get("protected", False)),
                        "size": int(state.get("size", 0)),
                        "final_c": to_bool(state.get("final_c", False)),
                        "final_i": to_bool(state.get("final_i", False)),
                        "revision_interna": to_bool(state.get("revision_interna", False)),
                        "propuesta_mejoras": to_bool(state.get("propuesta_mejoras", False)),
                        "entrenamiento_inicial_solicitado": to_bool(state.get("entrenamiento_inicial_solicitado", False)),
                        "entrenamiento_inicial_completado": to_bool(state.get("entrenamiento_inicial_completado", False)),
                        "entrenamiento_inicial_fecha": state.get("entrenamiento_inicial_fecha"),
                        "evaluacion_entrenamiento": to_bool(state.get("evaluacion_entrenamiento", False)),
                        "reentrenamiento": to_bool(state.get("reentrenamiento", False)),
                        "optimizacion": to_bool(state.get("optimizacion", False)),
                        "control_calidad_aprobado": to_bool(state.get("control_calidad_aprobado", False)),
                        "generacion_llm_solicitada": to_bool(state.get("generacion_llm_solicitada", False)),
                        "generacion_llm_completada": to_bool(state.get("generacion_llm_completada", False)),
                        "generacion_llm_fecha": state.get("generacion_llm_fecha"),
                        "ruta_fichero_modelo": state.get("ruta_fichero_modelo"),
                        "notificacion_descarga_enviada": to_bool(state.get("notificacion_descarga_enviada", False)),
                        "notificacion_descarga_fecha": state.get("notificacion_descarga_fecha"),
                        "created_at": state.get("created_at"),
                        "updated_at": state.get("updated_at"),
                        "updated_by": int(state["updated_by"]) if state.get("updated_by") else None,
                    }
                    print(f"[EP] ep_init_page: state loaded, state_internal={current_state.get('state_internal')}")
            except Exception as e:
                print(f"[EP] ep_init_page: state EXCEPTION: {e}")

        # Usar yield para retornar un evento que actualice el EstadoProyectosState
        # En su lugar, devolvemos el evento con los datos
        return EstadoProyectosState.ep_receive_data(
            self.user_id,
            self.organization_id,
            self.identity_type_id,
            self.access_token,
            self.session_token,
            organizations,
            selected_org_id,
            projects,
            selected_project_id,
            versions,
            selected_version_id,
            current_state,
        )

    # ========== Página Asistente (Ollama) ==========

    def check_ollama_health(self):
        """Verifica si Ollama está disponible en el trainer (conexion directa)."""
        try:
            from adapters.api_client import check_ollama_health_direct

            result = check_ollama_health_direct()

            if result and result.get("status") == "healthy":
                self.asistente_ollama_available = True
                self.asistente_ollama_status = "✅ Ollama disponible"
            else:
                self.asistente_ollama_available = False
                self.asistente_ollama_status = "❌ Ollama no disponible"
        except Exception as e:
            self.asistente_ollama_available = False
            self.asistente_ollama_status = f"❌ Error: {str(e)}"

    def load_ollama_models(self):
        """Carga la lista de modelos disponibles desde jobs_modelos (BD directa)."""
        try:
            engine = self._get_projects_engine()
            with engine.connect() as conn:
                rows = conn.execute(text(
                    "SELECT nombre FROM jobs_modelos WHERE activo = 1 ORDER BY nombre"
                )).fetchall()
                model_names = [r[0] for r in rows if r[0] and r[0].strip()]

            self.asistente_models = model_names
            if self.asistente_models:
                self.asistente_selected_model = self.asistente_models[0]
            else:
                self.asistente_error = "No se encontraron modelos activos en BD"
        except Exception as e:
            self.asistente_models = []
            self.asistente_error = f"Error cargando modelos: {str(e)}"

    def set_asistente_model(self, model: str):
        """Cambia el modelo seleccionado."""
        self.asistente_selected_model = model

    def set_asistente_prompt(self, prompt: str):
        """Actualiza el prompt."""
        self.asistente_prompt = prompt

    @rx.event(background=True)
    async def submit_asistente_prompt(self):
        """Envía el prompt al modelo seleccionado y obtiene la respuesta."""
        # Leer valores antes del context manager
        prompt = self.asistente_prompt
        model = self.asistente_selected_model
        access_token = self.access_token
        session_token = self.session_token

        if not prompt or not model:
            async with self:
                self.asistente_error = "Debe seleccionar un modelo e ingresar un prompt"
            return

        async with self:
            self.asistente_is_loading = True
            self.asistente_error = ""
            self.asistente_response = ""

        try:
            from adapters.api_client import generate_with_ollama, chat_with_ollama

            # Intento 1: Usar endpoint generate
            result = generate_with_ollama(
                model=model,
                prompt=prompt,
                access_token=access_token,
                session_token=session_token,
            )

            if result and result.get("response", "").strip():
                async with self:
                    self.asistente_response = result["response"]
            else:
                # Fallback: Usar endpoint chat
                result = chat_with_ollama(
                    model=model,
                    message=prompt,
                    access_token=access_token,
                    session_token=session_token,
                )

                if result and result.get("message", {}).get("content", "").strip():
                    async with self:
                        self.asistente_response = result["message"]["content"]
                else:
                    async with self:
                        self.asistente_error = "El modelo no generó respuesta"

        except Exception as e:
            async with self:
                self.asistente_error = f"Error: {str(e)}"
        finally:
            async with self:
                self.asistente_is_loading = False

    # ========== Página Sistema - Health Checks ==========

    def check_all_services(self):
        """Verifica el estado de todos los servicios del sistema."""
        # Panel Frontend
        self.check_frontend_service()
        self.check_backoffice_service()
        self.check_middleware_service()
        self.check_redis_service()
        self.check_sms_api_service()

        # Panel Backend
        self.check_broker_service()
        self.check_backend_core_service()
        self.check_fmanagement_service()
        self.check_mariadb_service()

        # Panel Trainer
        self.check_trainer_service()
        self.check_chromadb_service()
        self.check_ollama_service()

    def check_frontend_service(self):
        """Verifica el estado del servicio Frontend."""
        try:
            from adapters.api_client import check_frontend_health
            result = check_frontend_health()
            self.sys_frontend_available = result.get("status") == "healthy"
            self.sys_frontend_status = "✅ Activo" if self.sys_frontend_available else "❌ Inactivo"
        except Exception as e:
            self.sys_frontend_available = False
            self.sys_frontend_status = f"❌ Error: {str(e)}"

    def check_backoffice_service(self):
        """Verifica el estado del servicio Backoffice."""
        try:
            from adapters.api_client import check_backoffice_health
            result = check_backoffice_health()
            self.sys_backoffice_available = result.get("status") == "healthy"
            self.sys_backoffice_status = "✅ Activo" if self.sys_backoffice_available else "❌ Inactivo"
        except Exception as e:
            self.sys_backoffice_available = False
            self.sys_backoffice_status = f"❌ Error: {str(e)}"

    def check_middleware_service(self):
        """Verifica el estado del Middleware."""
        try:
            from adapters.api_client import check_middleware_health
            result = check_middleware_health()
            self.sys_middleware_available = result.get("status") == "healthy"
            self.sys_middleware_status = "✅ Activo" if self.sys_middleware_available else "❌ Inactivo"
        except Exception as e:
            self.sys_middleware_available = False
            self.sys_middleware_status = f"❌ Error: {str(e)}"

    def check_redis_service(self):
        """Verifica el estado de Redis."""
        try:
            from adapters.api_client import check_redis_health
            result = check_redis_health()
            self.sys_redis_available = result.get("status") == "healthy"
            self.sys_redis_status = "✅ Operativo (vía Backend)" if self.sys_redis_available else "❌ Inactivo"
        except Exception as e:
            self.sys_redis_available = False
            self.sys_redis_status = f"❌ Error: {str(e)}"

    def check_sms_api_service(self):
        """Verifica si la API de SMS es alcanzable."""
        try:
            from adapters.api_client import check_sms_api_health
            result = check_sms_api_health()
            detail = result.get("detail", "")
            if detail == "No configurado":
                self.sys_sms_api_available = False
                self.sys_sms_api_status = "⚠️ No configurado"
            else:
                self.sys_sms_api_available = result.get("status") == "healthy"
                self.sys_sms_api_status = "✅ Alcanzable" if self.sys_sms_api_available else "❌ No alcanzable"
        except Exception as e:
            self.sys_sms_api_available = False
            self.sys_sms_api_status = f"❌ Error: {str(e)}"

    def check_broker_service(self):
        """Verifica el estado del Broker."""
        try:
            from adapters.api_client import check_broker_health
            result = check_broker_health()
            self.sys_broker_available = result.get("status") == "healthy"
            self.sys_broker_status = "✅ Activo" if self.sys_broker_available else "❌ Inactivo"
        except Exception as e:
            self.sys_broker_available = False
            self.sys_broker_status = f"❌ Error: {str(e)}"

    def check_backend_core_service(self):
        """Verifica el estado del Backend Core."""
        try:
            from adapters.api_client import check_backend_core_health
            result = check_backend_core_health()
            self.sys_backend_core_available = result.get("status") == "healthy"
            self.sys_backend_core_status = "✅ Activo" if self.sys_backend_core_available else "❌ Inactivo"
        except Exception as e:
            self.sys_backend_core_available = False
            self.sys_backend_core_status = f"❌ Error: {str(e)}"

    def check_fmanagement_service(self):
        """Verifica el estado de fmanagement."""
        try:
            from adapters.api_client import check_fmanagement_health
            result = check_fmanagement_health()
            self.sys_fmanagement_available = result.get("status") == "healthy"
            self.sys_fmanagement_status = "✅ Activo" if self.sys_fmanagement_available else "❌ Inactivo"
        except Exception as e:
            self.sys_fmanagement_available = False
            self.sys_fmanagement_status = f"❌ Error: {str(e)}"

    def check_mariadb_service(self):
        """Verifica el estado de MariaDB."""
        try:
            from adapters.api_client import check_mariadb_health
            result = check_mariadb_health()
            self.sys_mariadb_available = result.get("status") == "healthy"
            self.sys_mariadb_status = "✅ Operativo (vía Backend)" if self.sys_mariadb_available else "❌ Inactivo"
        except Exception as e:
            self.sys_mariadb_available = False
            self.sys_mariadb_status = f"❌ Error: {str(e)}"

    def check_trainer_service(self):
        """Verifica el estado del Backend IA/Trainer."""
        try:
            from adapters.api_client import check_trainer_health
            result = check_trainer_health()
            self.sys_trainer_available = result.get("status") == "healthy"
            self.sys_trainer_status = "✅ Activo" if self.sys_trainer_available else "❌ Inactivo"
        except Exception as e:
            self.sys_trainer_available = False
            self.sys_trainer_status = f"❌ Error: {str(e)}"

    def check_chromadb_service(self):
        """Verifica el estado de ChromaDB."""
        try:
            from adapters.api_client import check_chromadb_health
            result = check_chromadb_health()
            self.sys_chromadb_available = result.get("status") == "healthy"
            self.sys_chromadb_status = "✅ Activo" if self.sys_chromadb_available else "❌ Inactivo"
        except Exception as e:
            self.sys_chromadb_available = False
            self.sys_chromadb_status = f"❌ Error: {str(e)}"

    def check_ollama_service(self):
        """Verifica el estado de Ollama (conexion directa, sin middleware/auth)."""
        try:
            from adapters.api_client import check_ollama_health_direct
            result = check_ollama_health_direct()
            self.sys_ollama_available = result.get("status") == "healthy"
            self.sys_ollama_status = "✅ Activo" if self.sys_ollama_available else "❌ Inactivo"
        except Exception as e:
            self.sys_ollama_available = False
            self.sys_ollama_status = f"❌ Error: {str(e)}"

    # ========== Gestión de Usuarios de la Organización ==========
    
    def load_org_users(self):
        """Carga los usuarios de la organización actual desde la base de datos.

        Filtra por:
        - bo_selected_org_id (organización seleccionada en el selector)
        - identity_type_id = 5 (auditores/usuarios base)
        """
        # Asegurar que identity_type_id está cargado desde el token si no está en el estado
        if self.identity_type_id <= 0 and self.access_token:
            extracted_identity = self._extract_identity_type_id_from_token(self.access_token)
            if extracted_identity > 0:
                self.identity_type_id = extracted_identity

        # Usar la organización del selector del backoffice
        org_id = self.bo_selected_org_id
        
        if org_id <= 0:
            # Si no hay organización, mostrar lista vacía
            self.org_users = []
            return
        
        # Llamar al middleware para obtener usuarios reales de la organización
        # BACKOFFICE: active_only=False para ver TODOS los usuarios (activos e inactivos)
        # Esto permite reactivar usuarios que fueron borrados lógicamente
        users = get_organization_users(
            organization_id=org_id,
            access_token=self.access_token,
            session_token=self.session_token,
            identity_type_id=5,  # Solo auditores (usuarios de organización)
            active_only=False,   # Backoffice muestra todos para poder reactivarlos
        )

        # Transformar al formato esperado por la UI
        # Estructura: {"user_id": int, "user_name": str, "active": bool, "is_internal": bool}
        org_users_list = [
            {
                "user_id": user.get("user_id", 0),
                "user_name": user.get("user_name", ""),
                "active": user.get("active", True),
                "is_internal": False,  # Usuarios propios de la organización
            }
            for user in users
        ]

        # Cargar también usuarios internos (staff) asignados a esta organización
        # Solo si el usuario logueado es SuperAdmin o Admin de Org
        if self.identity_type_id in (1, 2):
            try:
                from adapters.api_client import get_organization_assignments
                assignments = get_organization_assignments(
                    organization_id=org_id,
                    access_token=self.access_token,
                    session_token=self.session_token,
                )
                # Agregar usuarios internos a la lista
                for assignment in assignments:
                    if assignment.get("active", False):
                        org_users_list.append({
                            "user_id": assignment.get("user_id", 0),
                            "user_name": assignment.get("user_name", ""),
                            "active": True,
                            "is_internal": True,  # Usuario interno (staff)
                            "role_name": assignment.get("role_name", ""),
                        })
            except Exception as e:
                print(f"[DEBUG] No se pudieron cargar usuarios internos: {e}")
                # No es crítico, continuar sin usuarios internos

        self.org_users = org_users_list
    
    def create_user(self):
        """Abre el modal para crear un nuevo usuario."""
        self.show_create_user_modal = True
        self.new_user_name = ""
        self.new_user_email = ""
        self.new_user_mobile = ""
        self.create_user_error = ""
        self.create_user_success = ""
        self.is_creating_user = False
    
    def close_create_user_modal(self):
        """Cierra el modal de creación de usuario sin guardar."""
        self.show_create_user_modal = False
        self.new_user_name = ""
        self.new_user_email = ""
        self.new_user_mobile = ""
        self.create_user_error = ""
        self.create_user_success = ""
        self.is_creating_user = False
    
    def save_new_user(self):
        """Guarda el nuevo usuario llamando al middleware."""
        # Validaciones básicas
        if not self.new_user_name.strip():
            self.create_user_error = "El nombre de usuario es obligatorio"
            return
        if not self.new_user_email.strip():
            self.create_user_error = "El correo electrónico es obligatorio"
            return
        if not self.new_user_mobile.strip():
            self.create_user_error = "El teléfono es obligatorio"
            return
        
        self.create_user_error = ""
        self.is_creating_user = True

        # Usar la organización del selector del backoffice
        org_id = self.bo_selected_org_id

        if org_id <= 0:
            self.create_user_error = "Seleccione una organización primero"
            self.is_creating_user = False
            return

        # Llamar al API para crear el usuario
        result = create_organization_user(
            organization_id=org_id,
            user_name=self.new_user_name.strip(),
            user_email=self.new_user_email.strip(),
            user_mobile=self.new_user_mobile.strip(),
            access_token=self.access_token,
            session_token=self.session_token,
        )
        
        self.is_creating_user = False
        
        if result.get("success"):
            self.create_user_success = f"Usuario '{self.new_user_name}' creado exitosamente"
            # Limpiar campos
            self.new_user_name = ""
            self.new_user_email = ""
            self.new_user_mobile = ""
            # Cerrar modal
            self.show_create_user_modal = False
            # Recargar lista de usuarios (después de cerrar modal para que se vea)
            self.load_org_users()
        else:
            self.create_user_error = result.get("error", "Error al crear el usuario")
    
    def set_new_user_name(self, value: str):
        """Actualiza el nombre del nuevo usuario."""
        self.new_user_name = value
    
    def set_new_user_email(self, value: str):
        """Actualiza el email del nuevo usuario."""
        self.new_user_email = value
    
    def set_new_user_mobile(self, value: str):
        """Actualiza el teléfono del nuevo usuario."""
        self.new_user_mobile = value
    
    def enable_user(self, user_id: int):
        """Habilita un usuario de la organización."""
        try:
            update_user_status(
                user_id=user_id,
                active=True,
                access_token=self.access_token,
                session_token=self.session_token,
            )
        except Exception as e:
            print(f"[ERROR] Error habilitando usuario: {e}")
        finally:
            self.load_org_users()

    def disable_user(self, user_id: int):
        """Deshabilita un usuario de la organización."""
        try:
            update_user_status(
                user_id=user_id,
                active=False,
                access_token=self.access_token,
                session_token=self.session_token,
            )
        except Exception as e:
            print(f"[ERROR] Error deshabilitando usuario: {e}")
        finally:
            self.load_org_users()
    
    def assign_user_to_projects(self, user_id: int):
        """Abre el modal para asignar un usuario a proyectos."""
        print(f"[DEBUG] Abrir modal de asignación para usuario: {user_id}")

        # Buscar el nombre del usuario
        user_name = ""
        for user in self.org_users:
            if user["user_id"] == user_id:
                user_name = user["user_name"]
                break

        # Cargar roles disponibles
        try:
            print(f"[DEBUG] Cargando roles...")
            roles = get_roles(
                access_token=self.access_token,
                session_token=self.session_token,
            )
            print(f"[DEBUG] Roles cargados: {len(roles) if roles else 0}")
            if roles and len(roles) > 0:
                print(f"[DEBUG] Primer rol: {roles[0]}")
            self.assign_roles = roles if roles else []
        except Exception as e:
            print(f"[ERROR] Error cargando roles: {e}")
            import traceback
            traceback.print_exc()
            self.assign_roles = []

        # Configurar estado del modal
        self.assign_user_id = user_id
        self.assign_user_name = user_name
        self.assign_selected_project_id = 0
        self.assign_selected_role_id = 0
        self.assign_error = ""
        self.assign_success = ""
        self.show_assign_user_modal = True

    def close_assign_user_modal(self):
        """Cierra el modal de asignación."""
        self.show_assign_user_modal = False
        self.assign_error = ""
        self.assign_success = ""

    def set_assign_project(self, project_name: str):
        """Establece el proyecto seleccionado para asignación."""
        for project in self.org_projects:
            if project.get("name") == project_name or project.get("nombre") == project_name:
                self.assign_selected_project_id = project.get("id", 0)
                break

    def set_assign_role(self, role_name: str):
        """Establece el rol seleccionado para asignación."""
        for role in self.assign_roles:
            if role.get("identity_type_name") == role_name:
                self.assign_selected_role_id = role.get("identity_type_id", 0)
                break

    def confirm_assign_user(self):
        """Confirma la asignación del usuario al proyecto con el rol seleccionado."""
        if self.assign_selected_project_id == 0:
            self.assign_error = "Debe seleccionar un proyecto"
            return

        if self.assign_selected_role_id == 0:
            self.assign_error = "Debe seleccionar un rol"
            return

        try:
            print(f"[DEBUG] Asignando usuario {self.assign_user_id} al proyecto {self.assign_selected_project_id} con rol {self.assign_selected_role_id}")
            result = create_project_assignment(
                user_id=self.assign_user_id,
                organization_id=self.bo_selected_org_id,  # Usar la organización del selector
                project_id=self.assign_selected_project_id,
                role_id=self.assign_selected_role_id,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if result.get("success"):
                self.assign_success = f"Usuario asignado correctamente al proyecto"
                self.assign_error = ""
                self.load_org_project_assignments()
            else:
                error_msg = result.get("error", "Error al asignar usuario")
                # Asegurar que el error sea string
                if isinstance(error_msg, bool):
                    error_msg = result.get("detail", "Error al asignar usuario")
                self.assign_error = str(error_msg)
                self.assign_success = ""
        except Exception as e:
            print(f"[ERROR] Error asignando usuario: {e}")
            error_str = str(e)
            # Extraer el mensaje real del error si está en el formato "Error HTTP..."
            if "El usuario debe tener" in error_str:
                self.assign_error = "El usuario debe tener un rol en la organización antes de asignarlo a proyectos"
            else:
                self.assign_error = f"Error al asignar usuario: {error_str}"
            self.assign_success = ""

    def load_org_project_assignments(self):
        """Carga todas las asignaciones activas de usuarios a proyectos de la organización.

        Itera sobre los usuarios de la org y consulta sus roles en proyectos.
        Resultado en org_project_assignments: [{proyecto_nombre, usuario_nombre, rol_nombre}]
        """
        from adapters.api_client import get_user_project_roles

        org_id = self.bo_selected_org_id
        if org_id <= 0:
            self.org_project_assignments = []
            return

        try:
            assignments = []
            rol_nombres = {3: "Editor", 4: "Lector", 5: "Auditor"}

            existing_project_ids = {
                p.get("id") for p in self.org_projects if p.get("existe", True)
            }

            for user in self.org_users:
                user_id = user.get("user_id", 0)
                user_name = user.get("user_name", "Sin nombre")
                if user_id <= 0:
                    continue

                response = get_user_project_roles(
                    user_id=user_id,
                    organization_id=org_id,
                    access_token=self.access_token,
                    session_token=self.session_token,
                )

                for role in response.get("roles", []):
                    project_id = role.get("id_proyecto", 0)
                    if role.get("active", False) and project_id in existing_project_ids:
                        assignments.append({
                            "proyecto_nombre": role.get("proyecto_nombre", "Sin proyecto"),
                            "usuario_nombre": user_name,
                            "rol_nombre": rol_nombres.get(role.get("id_rol", 0), "Desconocido"),
                        })

            self.org_project_assignments = sorted(
                assignments,
                key=lambda x: (x["proyecto_nombre"], x["usuario_nombre"]),
            )
        except Exception as e:
            print(f"[ERROR] load_org_project_assignments: {e}")
            self.org_project_assignments = []

    def remove_user_from_projects(self, user_id: int):
        """Quita un usuario de proyectos."""
        # TODO: Implementar modal de desasignación
        print(f"[DEBUG] Quitar usuario de proyectos: {user_id}")
    
    def delete_user(self, user_id: int):
        """Borrado LÓGICO de un usuario (active=false).
        
        IMPORTANTE: Este NO es un borrado físico. Solo marca el usuario
        como inactivo (active=0) en la base de datos. El usuario puede
        ser reactivado posteriormente usando el botón "Habilitar usuario".
        
        Args:
            user_id: ID del usuario a desactivar
        """
        print(f"[DEBUG] Borrado lógico de usuario: {user_id}")
        try:
            result = update_user_status(
                user_id=user_id,
                active=False,  # Borrado lógico: active = 0
                access_token=self.access_token,
                session_token=self.session_token,
            )
            if result.get("success"):
                # Actualizar estado local (el usuario sigue visible pero con badge "Inactivo")
                for user in self.org_users:
                    if user["user_id"] == user_id:
                        user["active"] = False
                self.org_users = self.org_users.copy()
                print(f"[DEBUG] Usuario {user_id} desactivado correctamente")
            else:
                print(f"[ERROR] No se pudo desactivar usuario: {result}")
        except Exception as e:
            print(f"[ERROR] delete_user: {type(e).__name__}: {e}")

    # ========== Gestión de Proyectos de la Organización ==========
    
    def load_org_projects(self):
        """Carga los proyectos de la organización actual desde la base de datos.

        En el backoffice se cargan TODOS los proyectos (incluyendo borrados lógicos)
        para permitir su recuperación.
        """
        try:
            # Usar la organización del selector del backoffice
            org_id = self.bo_selected_org_id

            if org_id <= 0:
                self.org_projects = []
                return

            # En backoffice incluimos todos los proyectos (include_deleted=True)
            projects = get_organization_projects(
                organization_id=org_id,
                access_token=self.access_token,
                session_token=self.session_token,
                include_deleted=True,  # Incluir borrados lógicos
            )
            
            # Transformar al formato esperado por la UI
            # active=True: desbloqueado, active=False: bloqueado
            # existe=True: existe, existe=False: borrado lógico
            self.org_projects = [
                {
                    "id": p.get("id", 0),
                    "name": p.get("name", p.get("nombre", "Sin nombre")),
                    "description": p.get("descripcion", ""),
                    "active": p.get("active", True),
                    "existe": p.get("existe", True),
                }
                for p in projects
            ]
            print(f"[DEBUG] load_org_projects: {len(self.org_projects)} proyectos cargados")
        except Exception as e:
            print(f"[ERROR] load_org_projects: {type(e).__name__}: {e}")
            self.org_projects = []
    
    def open_create_project_modal(self):
        """Abre el modal para crear un nuevo proyecto."""
        self.new_project_name = ""
        self.new_project_description = ""
        self.create_project_error = ""
        self.create_project_success = ""
        self.show_create_project_modal = True

    def close_create_project_modal(self):
        """Cierra el modal de creación de proyecto."""
        self.show_create_project_modal = False
        self.create_project_error = ""
        self.create_project_success = ""

    def set_new_project_name(self, value: str):
        """Actualiza el nombre del nuevo proyecto."""
        self.new_project_name = value

    def set_new_project_description(self, value: str):
        """Actualiza la descripción del nuevo proyecto."""
        self.new_project_description = value

    def save_new_project(self):
        """Guarda el nuevo proyecto con el flujo 'Propuesta Cliente' (id_flujo=1)."""
        # Validaciones
        if not self.new_project_name.strip():
            self.create_project_error = "El nombre del proyecto es obligatorio"
            return

        self.create_project_error = ""
        self.is_creating_project = True

        # Usar la organización del selector del backoffice
        org_id = self.bo_selected_org_id

        if org_id <= 0:
            self.create_project_error = "Seleccione una organización primero"
            self.is_creating_project = False
            return

        # Llamar al API para crear el proyecto con id_flujo=1 (Propuesta Cliente)
        result = create_project(
            nombre=self.new_project_name.strip(),
            descripcion=self.new_project_description.strip(),
            id_organizacion=org_id,
            id_flujo=1,  # IMPORTANTE: Siempre crear con "Propuesta Cliente"
            active=True,
            access_token=self.access_token,
            session_token=self.session_token,
        )

        self.is_creating_project = False

        if result.get("success"):
            self.create_project_success = f"Proyecto '{self.new_project_name}' creado exitosamente con estado 'Propuesta Cliente'"
            # Limpiar campos
            self.new_project_name = ""
            self.new_project_description = ""
            # Cerrar modal
            self.show_create_project_modal = False
            # Recargar lista de proyectos
            self.load_org_projects()
        else:
            self.create_project_error = result.get("mensaje", "Error al crear el proyecto")

    def create_project(self):
        """Abre el formulario para crear un nuevo proyecto."""
        # Mantener este método por compatibilidad con el botón existente
        self.open_create_project_modal()
    
    def lock_project(self, project_id: int):
        """Bloquea un proyecto (active=false)."""
        try:
            result = update_project_status(
                project_id=project_id,
                active=False,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            if result.get("success"):
                self.load_org_projects()
        except Exception as e:
            print(f"[ERROR] lock_project: {type(e).__name__}: {e}")

    def unlock_project(self, project_id: int):
        """Desbloquea un proyecto (active=true)."""
        try:
            result = update_project_status(
                project_id=project_id,
                active=True,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            if result.get("success"):
                self.load_org_projects()
        except Exception as e:
            print(f"[ERROR] unlock_project: {type(e).__name__}: {e}")

    def delete_project(self, project_id: int):
        """Borrado lógico de un proyecto (existe=false)."""
        try:
            result = update_project_existence(
                project_id=project_id,
                existe=False,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            if result.get("success"):
                self.load_org_projects()
        except Exception as e:
            print(f"[ERROR] delete_project: {type(e).__name__}: {e}")

    def restore_project(self, project_id: int):
        """Recupera un proyecto borrado lógicamente (existe=true)."""
        try:
            result = update_project_existence(
                project_id=project_id,
                existe=True,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            if result.get("success"):
                self.load_org_projects()
        except Exception as e:
            print(f"[ERROR] restore_project: {type(e).__name__}: {e}")
    
    def request_project_support(self, project_id: int):
        """Abre el modal para solicitar soporte para un proyecto."""
        project_name = ""
        for project in self.org_projects:
            if project.get("id") == project_id:
                project_name = project.get("name", "")
                break

        self.support_project_id = project_id
        self.support_project_name = project_name
        self.support_titulo = ""
        self.support_consulta = ""
        self.support_error = ""
        self.support_success = ""
        self.is_creating_support = False
        self.show_support_modal = True

    def close_support_modal(self):
        """Cierra el modal de solicitud de soporte."""
        self.show_support_modal = False
        self.support_project_id = 0
        self.support_project_name = ""
        self.support_titulo = ""
        self.support_consulta = ""
        self.support_error = ""
        self.support_success = ""
        self.is_creating_support = False

    def set_support_titulo(self, value: str):
        """Establece el motivo del ticket."""
        self.support_titulo = value

    def set_support_consulta(self, value: str):
        """Establece el texto de la consulta."""
        self.support_consulta = value

    def save_support_ticket(self):
        """Envía el ticket de soporte.

        Flujo: Backoffice → Middleware → Broker → Backend Core → MariaDB
        """
        from adapters.api_client import create_support_ticket

        if not self.support_titulo.strip():
            self.support_error = "El motivo es obligatorio"
            return
        if not self.support_consulta.strip():
            self.support_error = "La consulta es obligatoria"
            return

        self.support_error = ""
        self.is_creating_support = True

        try:
            result = create_support_ticket(
                titulo=self.support_titulo,
                consulta=self.support_consulta,
                id_proyecto=self.support_project_id if self.support_project_id > 0 else None,
                id_organizacion=self.bo_selected_org_id,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            print(f"[DEBUG] Resultado crear ticket: {result}")

            if result.get("success"):
                self.support_success = f"Ticket #{result.get('ticket_id', '')} creado correctamente"
                self.support_titulo = ""
                self.support_consulta = ""
                self.close_support_modal()
                # Recargar tickets
                self.load_org_tickets()
            else:
                self.support_error = result.get("error", result.get("mensaje", "Error al crear el ticket"))
        except Exception as e:
            self.support_error = f"Error: {e}"
            print(f"[ERROR] Error creando ticket: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_creating_support = False

    # ========== Gestión de Tickets de Soporte ==========
    
    def load_org_tickets(self):
        """Carga los tickets de la organización desde la base de datos.
        
        Flujo: Backoffice → Middleware → Broker → Backend Core → MariaDB
        """
        try:
            # Usar la organización del selector del backoffice
            org_id = self.bo_selected_org_id

            if org_id <= 0:
                self.org_tickets = []
                return

            tickets = get_organization_tickets(
                organization_id=org_id,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            
            self.org_tickets = tickets
            print(f"[DEBUG] load_org_tickets: {len(self.org_tickets)} tickets cargados")
        except Exception as e:
            print(f"[ERROR] load_org_tickets: {type(e).__name__}: {e}")
            self.org_tickets = []
    
    def open_ticket_modal(self, ticket_id: int):
        """Abre el modal para gestionar un ticket."""
        # Buscar el ticket
        ticket = None
        for t in self.org_tickets:
            if t.get("id") == ticket_id:
                ticket = t
                break
        
        if not ticket:
            print(f"[ERROR] Ticket {ticket_id} no encontrado")
            return
        
        # Cargar datos en el estado
        self.selected_ticket_id = ticket_id
        self.selected_ticket_titulo = ticket.get("titulo", "")
        self.selected_ticket_consulta = ticket.get("consulta", "")
        self.selected_ticket_estado = ticket.get("estado", "abierto")
        self.selected_ticket_prioridad = ticket.get("prioridad", "media")
        self.selected_ticket_respuesta = ticket.get("respuesta", "") or ""
        self.ticket_modal_error = ""
        self.ticket_modal_success = ""
        self.is_updating_ticket = False
        self.show_ticket_modal = True
        print(f"[DEBUG] Abriendo modal de ticket: {ticket_id}")
    
    def close_ticket_modal(self):
        """Cierra el modal de ticket."""
        self.show_ticket_modal = False
        self.selected_ticket_id = 0
        self.selected_ticket_titulo = ""
        self.selected_ticket_consulta = ""
        self.selected_ticket_estado = "abierto"
        self.selected_ticket_prioridad = "media"
        self.selected_ticket_respuesta = ""
        self.ticket_modal_error = ""
        self.ticket_modal_success = ""
        self.is_updating_ticket = False
    
    def set_ticket_estado(self, value: str):
        """Establece el estado del ticket."""
        self.selected_ticket_estado = value
    
    def set_ticket_prioridad(self, value: str):
        """Establece la prioridad del ticket."""
        self.selected_ticket_prioridad = value
    
    def set_ticket_respuesta(self, value: str):
        """Establece la respuesta del ticket."""
        self.selected_ticket_respuesta = value
    
    def save_ticket_changes(self):
        """Guarda los cambios del ticket (estado/prioridad).
        
        Flujo: Backoffice → Middleware → Broker → Backend Core → MariaDB
        """
        self.ticket_modal_error = ""
        self.is_updating_ticket = True
        
        try:
            result = update_ticket_status(
                ticket_id=self.selected_ticket_id,
                estado=self.selected_ticket_estado,
                prioridad=self.selected_ticket_prioridad,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            
            if result.get("success"):
                self.ticket_modal_success = "Ticket actualizado correctamente"
                # Actualizar en la lista local
                for t in self.org_tickets:
                    if t.get("id") == self.selected_ticket_id:
                        t["estado"] = self.selected_ticket_estado
                        t["prioridad"] = self.selected_ticket_prioridad
                self.org_tickets = self.org_tickets.copy()
            else:
                self.ticket_modal_error = "Error al actualizar el ticket"
        except Exception as e:
            self.ticket_modal_error = f"Error: {e}"
            print(f"[ERROR] save_ticket_changes: {e}")
        finally:
            self.is_updating_ticket = False
    
    def save_ticket_response(self):
        """Guarda la respuesta del ticket.
        
        Flujo: Backoffice → Middleware → Broker → Backend Core → MariaDB
        """
        if not self.selected_ticket_respuesta.strip():
            self.ticket_modal_error = "La respuesta no puede estar vacía"
            return
        
        self.ticket_modal_error = ""
        self.is_updating_ticket = True
        
        try:
            result = add_ticket_response(
                ticket_id=self.selected_ticket_id,
                respuesta=self.selected_ticket_respuesta,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            
            if result.get("success"):
                self.ticket_modal_success = "Respuesta enviada correctamente"
                # Actualizar en la lista local
                for t in self.org_tickets:
                    if t.get("id") == self.selected_ticket_id:
                        t["respuesta"] = self.selected_ticket_respuesta
                self.org_tickets = self.org_tickets.copy()
            else:
                self.ticket_modal_error = "Error al enviar la respuesta"
        except Exception as e:
            self.ticket_modal_error = f"Error: {e}"
            print(f"[ERROR] save_ticket_response: {e}")
        finally:
            self.is_updating_ticket = False

    # ========== Gestión de Tecnologías ==========
    
    def load_tecnologias(self):
        """Carga la lista de tecnologías disponibles desde la base de datos.
        
        Flujo: Backoffice → Middleware → Broker → Backend Core → MariaDB
        """
        try:
            self.is_loading_tecnologias = True
            result = get_tecnologias(
                access_token=self.access_token,
                session_token=self.session_token,
            )
            
            if result.get("tecnologias"):
                self.tecnologias_list = result["tecnologias"]
                print(f"[DEBUG] load_tecnologias: {len(self.tecnologias_list)} tecnologías cargadas")
            else:
                self.tecnologias_list = []
        except Exception as e:
            print(f"[ERROR] load_tecnologias: {type(e).__name__}: {e}")
            self.tecnologias_list = []
        finally:
            self.is_loading_tecnologias = False

    def load_tecnologias_asignadas(self):
        """Carga la lista de proyectos con sus tecnologías asignadas.
        
        Flujo: Backoffice → Middleware → Broker → Backend Core → MariaDB
        """
        try:
            # Usar la organización del selector del backoffice
            org_id = self.bo_selected_org_id

            if org_id <= 0:
                self.tecnologias_asignadas_list = []
                return

            result = get_tecnologias_asignadas_org(
                org_id=org_id,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            self.tecnologias_asignadas_list = result.get("asignaciones", [])
            print(f"[DEBUG] Tecnologías asignadas cargadas: {len(self.tecnologias_asignadas_list)}")
        except Exception as e:
            print(f"[ERROR] load_tecnologias_asignadas: {type(e).__name__}: {e}")
            self.tecnologias_asignadas_list = []

    # ========== Gestión de Proyecciones (Versiones y Contenidos) ==========

    def reset_proyecciones_state(self):
        """Limpia el estado de proyecciones al cambiar de menú o proyecto."""
        self.proyecciones_project_id = 0
        self.proyecciones_project_name = ""
        self.proyecciones_versions = []
        self.proyecciones_version_id = 0
        self.proyecciones_version_folder = ""
        self.proyecciones_org_folder = ""
        self.proyecciones_prj_folder = ""
        self.proyecciones_error = ""
        self.proyecciones_success = ""

    def set_proyecciones_project(self, value: str):
        """Selecciona un proyecto y carga sus versiones.

        Args:
            value: Nombre del proyecto seleccionado
        """
        if not value:
            self.reset_proyecciones_state()
            return
        
        # Buscar el proyecto por nombre
        for project in self.org_projects:
            if project.get("name") == value:
                self.proyecciones_project_id = project.get("id", 0)
                self.proyecciones_project_name = value

                # Generar carpetas formateadas
                self.proyecciones_org_folder = get_folder_by_id_organization(self.bo_selected_org_id)
                self.proyecciones_prj_folder = get_folder_by_id_project(self.proyecciones_project_id)

                # Cargar versiones del proyecto
                self.load_proyecciones_versions()

                # Inicializar explorador con el nuevo proyecto (mostrará todas las versiones)
                return ExploradorState.reload_project_with_tokens(
                    project_id=self.proyecciones_project_id,
                    org_id=self.bo_selected_org_id,
                    access_token=self.access_token,
                    session_token=self.session_token
                )
        
        self.reset_proyecciones_state()

    def load_proyecciones_versions(self):
        """Carga las versiones del proyecto seleccionado."""
        if self.proyecciones_project_id <= 0:
            self.proyecciones_versions = []
            return
        
        self.is_loading_versions = True
        self.proyecciones_error = ""
        
        try:
            result = get_project_versions(
                project_id=self.proyecciones_project_id,
                organization_id=self.bo_selected_org_id,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            self.proyecciones_versions = result.get("versiones", [])
            print(f"[DEBUG] Versiones cargadas: {len(self.proyecciones_versions)}")
            
            # Seleccionar la primera versión si existe
            if self.proyecciones_versions:
                first_version = self.proyecciones_versions[0]
                self.proyecciones_version_id = first_version.get("id_version", 0)
                self.proyecciones_version_folder = first_version.get("version_folder", "")
        except Exception as e:
            print(f"[ERROR] Error cargando versiones: {type(e).__name__}: {e}")
            self.proyecciones_error = f"Error cargando versiones: {e}"
            self.proyecciones_versions = []
        finally:
            self.is_loading_versions = False

    def set_proyecciones_version(self, value: str):
        """Selecciona una versión e inicializa el explorador.

        Args:
            value: version_folder de la versión seleccionada (ej: "v001")
        """
        for version in self.proyecciones_versions:
            if version.get("version_folder") == value:
                self.proyecciones_version_id = version.get("id_version", 0)
                self.proyecciones_version_folder = value

                # Inicializar explorador con el proyecto (mostrará todas las versiones)
                if self.proyecciones_project_id > 0:
                    return ExploradorState.init_page(
                        project_id=self.proyecciones_project_id,
                        user_id=self.user_id,
                        identity_type_id=self.identity_type_id,
                        org_id=self.bo_selected_org_id,
                        access_token=self.access_token,
                        session_token=self.session_token,
                    )

    def create_new_version(self):
        """Crea una nueva versión completa (DB + fmanagement) para el proyecto seleccionado."""
        if self.proyecciones_project_id <= 0:
            self.proyecciones_error = "Selecciona un proyecto primero"
            return

        self.is_loading_versions = True
        self.proyecciones_error = ""
        self.proyecciones_success = ""
        yield  # Actualizar UI

        try:
            # Generar nombre de versión (V001, V002, etc.)
            existing_versions = len(self.proyecciones_versions)
            version_name = f"V{existing_versions + 1:03d}"

            # Llamar al endpoint atómico create_version_full
            result = create_version_full(
                project_id=self.proyecciones_project_id,
                organization_id=self.bo_selected_org_id,
                version_name=version_name,
                user_id=self.user_id,
                user_name=self.user_name,
                identity_type_id=self.identity_type_id,
                description=f"Versión creada por {self.user_name} (Backoffice)",
                clone_from_version_id=self.proyecciones_version_id if self.proyecciones_version_id > 0 else None,
                initial_state="Abierta",
                protected=False,
                final_c=False,
                final_i=False,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            print(f"[DEBUG] Resultado de create_version_full: {result}")
            print(f"[DEBUG] Tipo de result: {type(result)}")
            print(f"[DEBUG] Keys en result: {result.keys() if isinstance(result, dict) else 'N/A'}")
            print(f"[DEBUG] version_id en result: {result.get('version_id') if isinstance(result, dict) else 'N/A'}")

            if result.get("success"):
                new_version_id = result.get("version_id", 0)
                print(f"[DEBUG] new_version_id extraído: {new_version_id} (tipo: {type(new_version_id)})")
                self.proyecciones_success = f"✅ Versión {version_name} creada correctamente (ID: {new_version_id})"
                # Recargar versiones
                self.load_proyecciones_versions()
                # Seleccionar automáticamente la nueva versión
                self.proyecciones_version_id = new_version_id
                self.proyecciones_version_folder = version_name

                # Recargar explorador del proyecto (mostrará todas las versiones incluyendo la nueva)
                yield ExploradorState.init_page(
                    project_id=self.proyecciones_project_id,
                    user_id=self.user_id,
                    identity_type_id=self.identity_type_id,
                    org_id=self.bo_selected_org_id,
                    access_token=self.access_token,
                    session_token=self.session_token,
                )
            else:
                # El backend devuelve "message", no "mensaje"
                self.proyecciones_error = result.get("message") or result.get("mensaje") or "Error al crear versión"
        except Exception as e:
            print(f"[ERROR] Error creando versión completa: {type(e).__name__}: {e}")
            self.proyecciones_error = f"Error creando versión: {e}"
        finally:
            self.is_loading_versions = False
            yield  # Actualizar UI final

    @rx.var
    def proyecciones_projects_select(self) -> list[str]:
        """Lista de nombres de proyectos para el selector."""
        return [
            project.get("name", "Sin nombre")
            for project in self.org_projects
            if project.get("name") and project.get("existe", True)
        ]

    @rx.var
    def proyecciones_versions_select(self) -> list[str]:
        """Lista de versiones formateadas para el selector."""
        return [v.get("version_folder", "") for v in self.proyecciones_versions if v.get("version_folder")]
    
    def select_tech_project(self, value: str):
        """Selecciona un proyecto para asignar tecnología.
        
        Al seleccionar carga la tecnología actual asignada (si existe).
        El valor es el nombre del proyecto (igual que en frontend).
        """
        try:
            # Buscar el proyecto por nombre
            project_id = 0
            for p in self.org_projects:
                if p.get("name", p.get("nombre")) == value:
                    project_id = p.get("id", 0)
                    break
            
            self.selected_tech_project_id = project_id
            self.tech_assign_error = ""
            self.tech_assign_success = ""
            
            if self.selected_tech_project_id > 0:
                # Cargar tecnología actual del proyecto
                result = get_proyecto_tecnologia(
                    project_id=self.selected_tech_project_id,
                    access_token=self.access_token,
                    session_token=self.session_token,
                )
                
                if result.get("success") and result.get("asignacion"):
                    asignacion = result["asignacion"]
                    self.proyecto_tecnologia_asignada = asignacion
                    self.selected_tecnologia_id = asignacion.get("id_tecnologia", 0)
                else:
                    self.proyecto_tecnologia_asignada = {}
                    self.selected_tecnologia_id = 0
            else:
                self.proyecto_tecnologia_asignada = {}
                self.selected_tecnologia_id = 0
        except Exception as e:
            print(f"[ERROR] select_tech_project: {type(e).__name__}: {e}")
            self.tech_assign_error = f"Error al cargar proyecto: {e}"
    
    def select_tecnologia(self, tech: dict):
        """Selecciona una tecnología.
        
        Recibe el diccionario completo de la tecnología.
        """
        tech_id = tech.get("id", 0) if isinstance(tech, dict) else 0
        is_active = tech.get("active", False) if isinstance(tech, dict) else False
        if is_active:
            self.selected_tecnologia_id = tech_id
            self.tech_assign_error = ""
            print(f"[DEBUG] Tecnología seleccionada: {tech_id}")
    
    def asignar_tecnologia_proyecto(self):
        """Asigna o actualiza la tecnología de un proyecto.
        
        En el Backoffice se permite cambiar la tecnología (UPDATE).
        
        Flujo: Backoffice → Middleware → Broker → Backend Core → MariaDB
        """
        self.tech_assign_error = ""
        self.tech_assign_success = ""
        
        if self.selected_tech_project_id <= 0:
            self.tech_assign_error = "Selecciona un proyecto"
            return
        
        if self.selected_tecnologia_id <= 0:
            self.tech_assign_error = "Selecciona una tecnología"
            return
        
        try:
            # Si ya tiene asignación, actualizar (UPDATE)
            if self.proyecto_tecnologia_asignada:
                result = actualizar_tecnologia(
                    project_id=self.selected_tech_project_id,
                    id_tecnologia=self.selected_tecnologia_id,
                    access_token=self.access_token,
                    session_token=self.session_token,
                )
                
                if result.get("success"):
                    self.tech_assign_success = "Tecnología actualizada correctamente"
                    # Actualizar estado local
                    self.proyecto_tecnologia_asignada = {
                        "id_tecnologia": self.selected_tecnologia_id,
                    }
                else:
                    self.tech_assign_error = result.get("error", "Error al actualizar tecnología")
            else:
                # Primera asignación (INSERT)
                result = asignar_tecnologia(
                    project_id=self.selected_tech_project_id,
                    id_tecnologia=self.selected_tecnologia_id,
                    access_token=self.access_token,
                    session_token=self.session_token,
                )
                
                if result.get("success"):
                    self.tech_assign_success = "Tecnología asignada correctamente"
                    # Actualizar estado local
                    self.proyecto_tecnologia_asignada = {
                        "id_tecnologia": self.selected_tecnologia_id,
                    }
                else:
                    self.tech_assign_error = result.get("error", "Error al asignar tecnología")
        except Exception as e:
            self.tech_assign_error = f"Error: {e}"
            print(f"[ERROR] asignar_tecnologia_proyecto: {type(e).__name__}: {e}")

    def on_page_load(self):
        """
        Ejecuta acciones al recargar la página del backoffice.
        
        1. Carga tokens desde URL si están presentes (navegación desde frontend)
        2. Carga permisos desde sesión (Redis) o middleware (fallback)
        3. Verifica acceso al backoffice
        4. Inicializa componentes según el menú activo
        """
        # Leer parámetros de query (pasados desde el frontend)
        params = self.router.page.params
        session_id = params.get("session_id", "")  # NUEVO: modo seguro
        access_token = params.get("access_token", "")  # Legacy
        session_token = params.get("session_token", "")  # Legacy
        user_id = params.get("user_id", "")
        org_id = params.get("org_id", "")

        # PRIORIDAD 1: Modo seguro (solo session_id en URL, tokens desde Redis)
        if session_id:
            self.session_id = session_id
            self.user_id = int(user_id) if user_id else 0
            self.organization_id = int(org_id) if org_id else 0

            # Cargar tokens desde Redis
            tokens_loaded = self._load_tokens_from_redis()
            if tokens_loaded:
                self.is_logged_in = True
                activity_log.log_session_activity(
                    self.user_id,
                    f"session restored from Redis (SECURE MODE) | session_id={session_id} | org_id={self.organization_id}"
                )
            else:
                activity_log.warning(f"Failed to load tokens from Redis | session_id={session_id}")
                return rx.redirect("/")

        # PRIORIDAD 2: Modo legacy (tokens completos en URL)
        elif access_token and session_token:
            self.access_token = access_token
            self.session_token = session_token
            self.user_id = int(user_id) if user_id else 0
            self.organization_id = int(org_id) if org_id else 0
            self.is_logged_in = True

            # IMPORTANTE: Extraer timestamps de expiración desde los JWTs
            self.access_token_expires_at = self._extract_exp_from_token(access_token)
            self.session_token_expires_at = self._extract_exp_from_token(session_token)
            self.session_id = session_token  # Usar session_token como session_id
            self.last_activity = datetime.now().isoformat()

            # Guardar tokens en Redis para sincronización
            self._save_tokens_to_redis()

            activity_log.log_session_activity(
                self.user_id,
                f"session loaded from URL (LEGACY MODE) | org_id={self.organization_id}"
            )
        
        # Cargar permisos (obligatorio)
        activity_log.log_middleware_request("/auth/permissions", "GET")
        permission_result = self.load_permissions_from_session()
        if permission_result is not None:
            activity_log.warning(f"Permission check failed | user_id={self.user_id} | redirecting to frontend")
            return permission_result
        
        activity_log.log_session_activity(self.user_id, "permissions loaded successfully")

        # Continuar con la lógica de inicialización de componentes según menú activo
        if self.user_active_menu == "organizacion":
            # Cargar selector de organizaciones y datos de la org seleccionada
            self.bo_load_organizations()
            self.load_org_users()
            self.load_org_projects()
            self.load_org_tickets()
        elif self.user_active_menu in ("tecnologias", "proyecciones"):
            self.bo_load_organizations()
            self.load_org_projects()
            if self.user_active_menu == "tecnologias":
                self.load_tecnologias()
                self.load_tecnologias_asignadas()
        elif self.user_active_menu == "flujos":
            organization_id = self.organization_id
            if organization_id <= 0 and self.access_token:
                organization_id = self._extract_org_id_from_token(self.access_token)
                if organization_id > 0:
                    self.organization_id = organization_id
            return FlujosState.initialize_from_session(
                organization_id,
                user_id=self.user_id,
                identity_type_id=self.identity_type_id,
            )
        elif self.user_active_menu == "descargas":
            # Reiniciar estado de descargas
            self.dl_otp_validated = False
            self.dl_otp_code = ""
            self.dl_otp_error = ""
            self.dl_selected_org_id = 0
            self.dl_selected_org_name = ""
            self.dl_selected_project_id = 0
            self.dl_selected_project_name = ""
            self.dl_selected_version_id = 0
            self.dl_selected_version_name = ""
            self.dl_packages = []

        # Iniciar loop de renovación automática de tokens en background
        return State.auto_renew_tokens_loop

    def _extract_org_id_from_token(self, token: str) -> int:
        """Extrae organization_id desde el payload del JWT."""

        try:
            parts = token.split(".")
            if len(parts) < 2:
                return 0
            payload = parts[1]
            padded = payload + "=" * (-len(payload) % 4)
            data = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
            return int(data.get("organization_id", 0))
        except Exception:
            return 0

    def _extract_identity_type_id_from_token(self, token: str) -> int:
        """Extrae identity_type_id desde el payload del JWT."""

        try:
            parts = token.split(".")
            if len(parts) < 2:
                return 0
            payload = parts[1]
            padded = payload + "=" * (-len(payload) % 4)
            data = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
            return int(data.get("identity_type_id", 0))
        except Exception:
            return 0

    def _extract_exp_from_token(self, token: str) -> int:
        """Extrae timestamp de expiración (exp) desde el payload del JWT."""
        try:
            parts = token.split(".")
            if len(parts) < 2:
                return 0
            payload = parts[1]
            padded = payload + "=" * (-len(payload) % 4)
            data = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
            return int(data.get("exp", 0))
        except Exception:
            return 0
    
    def set_user_username(self, username: str):
        """Set user username."""
        self.user_username = username
    
    def set_user_password(self, password: str):
        """Set user password."""
        self.user_password = password

    def set_user_otp(self, otp: str):
        """Set user OTP."""
        self.user_otp = otp
    
    def user_login(self):
        """
        Login deshabilitado en backoffice.
        Los usuarios deben loguearse en el frontend.
        """
        self.login_error = "El login debe realizarse desde el sitio principal"
        return
    
    def user_logout(self):
        """
        Handle user portal logout.
        Limpia la sesión y redirige al frontend.
        """
        if self.access_token and self.session_token:
            logout_user(self.access_token, self.session_token)
        
        # Limpiar SharedSessionState (se sincroniza automáticamente con Redis)
        self.clear_session()
        
        # Limpiar estado local del backoffice
        self.is_logged_in = False
        self.user_username = ""
        self.user_password = ""
        self.user_otp = ""
        self.user_permissions = []
        self.login_error = ""
        self.otp_request_message = ""
        self.user_active_menu = "inicio"
        
        # Redirigir al frontend principal
        return self.go_to_frontend()

    def refresh_session_tokens(self):
        """Renueva los tokens de sesión mediante el middleware."""

        if not self.session_token:
            self.login_error = "No hay sesión activa para renovar"
            return
        response = refresh_tokens(self.session_token)
        access_token = response.get("access_token")
        session_token = response.get("session_token")
        if not access_token or not session_token:
            self.login_error = "No se pudieron renovar los tokens"
            return
        
        # Actualizar tokens y timestamps usando método de SharedSessionState
        self.update_tokens(
            access_token=access_token,
            session_token=session_token,
            access_expires_at=int(response.get("access_expires_at", 0)),
            session_expires_at=int(response.get("session_expires_at", 0)),
        )

    def ensure_tokens_valid(self) -> bool:
        """Verifica y renueva tokens automáticamente si es necesario.
        
        Esta función debe llamarse antes de cada operación que requiera autenticación.
        Retorna True si los tokens son válidos (o se renovaron exitosamente).
        Retorna False si la sesión expiró y el usuario debe re-autenticarse.
        """
        if not self.access_token or not self.session_token:
            return False
        
        result = ensure_valid_tokens(
            access_token=self.access_token,
            session_token=self.session_token,
            access_expires_at=self.access_token_expires_at,
            session_expires_at=self.session_token_expires_at,
        )
        
        if result.get("error"):
            # Si hay error, la sesión expiró - limpiar y forzar re-login
            self.login_error = result["error"]
            self.clear_session()
            return False
        
        if result.get("renewed"):
            # Tokens renovados - actualizar en el state
            self.update_tokens(
                access_token=result["access_token"],
                session_token=result["session_token"],
                access_expires_at=result["access_expires_at"],
                session_expires_at=result["session_expires_at"],
            )
        
        return True

    @rx.event(background=True)
    async def auto_renew_tokens_loop(self):
        """
        Loop en background que verifica y renueva tokens automáticamente cada 2 minutos.

        Este método se ejecuta continuamente mientras el usuario está logueado,
        verificando si los tokens están próximos a expirar y renovándolos automáticamente.
        """
        import asyncio
        import time

        while True:
            async with self:
                # Solo ejecutar si el usuario está logueado
                if not self.is_logged_in or not self.session_token or not self.session_token:
                    break

                # PASO 1: Verificar si hay tokens más recientes en Redis (sincronización entre apps)
                tokens_updated_from_redis = self._load_tokens_from_redis()
                if tokens_updated_from_redis:
                    print("[TOKEN AUTO-RENEW BACKOFFICE] Tokens sincronizados desde Redis (renovados por otra app)")

                # PASO 2: Verificar estado de los tokens
                check_result = self.check_token_expiration()

                # Si el session_token expiró, detener el loop y forzar logout
                if check_result["session_expired"]:
                    print("[TOKEN AUTO-RENEW BACKOFFICE] Session token expirado, cerrando sesión")
                    self.login_error = "Su sesión ha expirado. Por favor, inicie sesión nuevamente."
                    self.clear_session()
                    break

                # PASO 3: Si el access_token necesita renovación, intentar renovar
                if check_result["needs_renewal"]:
                    seconds_left = check_result["seconds_until_access_expires"]
                    print(f"[TOKEN AUTO-RENEW BACKOFFICE] Access token expira en {seconds_left}s, renovando...")

                    # Llamar a ensure_tokens_valid que maneja la renovación
                    success = self.ensure_tokens_valid()

                    if success:
                        print("[TOKEN AUTO-RENEW BACKOFFICE] Tokens renovados exitosamente")
                    else:
                        # Si la renovación falla, verificar si es un error fatal
                        if self.login_error and "expirado" in self.login_error.lower():
                            # Sesión realmente expirada - detener loop
                            print("[TOKEN AUTO-RENEW BACKOFFICE] Sesión expirada, deteniendo loop")
                            self.clear_session()
                            break
                        else:
                            # Error temporal o sesión no registrada - continuar con tokens actuales
                            # El usuario podrá seguir trabajando hasta que expiren realmente
                            print("[TOKEN AUTO-RENEW BACKOFFICE] Renovación falló, continuando con tokens actuales")
                            # Limpiar error para no confundir al usuario
                            self.login_error = ""
                else:
                    seconds_left = check_result["seconds_until_access_expires"]
                    print(f"[TOKEN AUTO-RENEW BACKOFFICE] Tokens válidos (expira en {seconds_left}s)")

            # Esperar 2 minutos antes de la próxima verificación
            await asyncio.sleep(120)

    def request_login_otp(self):
        """Solicita el código OTP para el login."""

        if not self.user_username or not self.user_password:
            self.otp_request_message = "Debe ingresar usuario y contraseña"
            return

        response = request_login_otp(self.user_username, self.user_password)
        if response.get("success"):
            self.otp_request_message = "Código OTP enviado por SMS"
            self.login_error = ""
            return
        self.otp_request_message = "No se pudo enviar el código OTP"
    
    def set_user_tab(self, tab: str):
        """Set active tab for user dashboard."""
        self.user_active_tab = tab

    # ========================================================================
    # ASSIGNMENTS MANAGER - Gestor de asignaciones (SuperAdmin only)
    # ========================================================================

    # Setters para conversión de string a int (requerido por Reflex)
    def set_selected_user_org_from_str(self, val: str):
        """Converts string to int for selected_user_org."""
        self.selected_user_org = int(val) if val else 0

    def set_selected_organization_assign_from_str(self, val: str):
        """Converts string to int for selected_organization_assign."""
        self.selected_organization_assign = int(val) if val else 0

    def set_selected_org_role_from_str(self, val: str):
        """Converts string to int for selected_org_role."""
        self.selected_org_role = int(val) if val else 0

    def set_selected_user_project_from_str(self, val: str):
        """Converts string to int for selected_user_project."""
        self.selected_user_project = int(val) if val else 0

    def set_selected_org_for_project_from_str(self, val: str):
        """Converts string to int for selected_org_for_project."""
        self.selected_org_for_project = int(val) if val else 0
        self.selected_project_assign = 0
        self.selected_project_role = 0
        if self.selected_org_for_project > 0:
            self.load_projects_for_org(self.selected_org_for_project)
        else:
            self.assignments_projects = []

    def set_selected_project_assign_from_str(self, val: str):
        """Converts string to int for selected_project_assign."""
        self.selected_project_assign = int(val) if val else 0
        if self.selected_project_assign > 0:
            self.load_project_assignments()

    def set_selected_project_role_from_str(self, val: str):
        """Converts string to int for selected_project_role."""
        self.selected_project_role = int(val) if val else 0

    def load_assignments_data(self):
        """Loads all data for assignments manager."""
        from adapters.api_client import get_internal_users, get_all_organizations, get_roles

        print("[DEBUG] load_assignments_data: Iniciando carga de datos...")

        # Load internal users
        try:
            print("[DEBUG] load_assignments_data: Cargando usuarios internos...")
            users = get_internal_users(
                access_token=self.access_token,
                session_token=self.session_token,
            )
            self.assignments_internal_users = users
            print(f"[DEBUG] load_assignments_data: Usuarios internos cargados: {len(users)}")
        except Exception as e:
            print(f"[ERROR] load_internal_users: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            self.assignments_internal_users = []

        # Load organizations
        try:
            print("[DEBUG] load_assignments_data: Cargando organizaciones...")
            orgs = get_all_organizations(
                access_token=self.access_token,
                session_token=self.session_token,
            )
            self.assignments_organizations = orgs
            print(f"[DEBUG] load_assignments_data: Organizaciones cargadas: {len(orgs)}")
            if len(orgs) > 0:
                print(f"[DEBUG] load_assignments_data: Primera organización: {orgs[0]}")
        except Exception as e:
            print(f"[ERROR] load_organizations: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            self.assignments_organizations = []

        # Load roles
        try:
            print("[DEBUG] load_assignments_data: Cargando roles...")
            roles = get_roles(
                access_token=self.access_token,
                session_token=self.session_token,
            )
            self.assignments_org_roles = roles
            print(f"[DEBUG] load_assignments_data: Roles cargados: {len(roles)}")
            if len(roles) > 0:
                print(f"[DEBUG] load_assignments_data: Primer rol: {roles[0]}")
        except Exception as e:
            print(f"[ERROR] load_roles: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            self.assignments_org_roles = []

        print(f"[DEBUG] load_assignments_data: Carga completada. Users={len(self.assignments_internal_users)}, Orgs={len(self.assignments_organizations)}, Roles={len(self.assignments_org_roles)}")

    def load_projects_for_org(self, organization_id: int):
        """Loads projects for a specific organization."""
        from adapters.api_client import get_organization_projects

        print(f"[DEBUG ASSIGNMENTS] load_projects_for_org: org_id={organization_id}")

        try:
            projects = get_organization_projects(
                organization_id=organization_id,
                access_token=self.access_token,
                session_token=self.session_token,
                include_deleted=False,  # Solo proyectos activos
            )

            print(f"[DEBUG ASSIGNMENTS] API retornó {len(projects)} proyectos")
            if projects:
                print(f"[DEBUG ASSIGNMENTS] Primer proyecto: {projects[0]}")

            # Filtrar y formatear proyectos
            self.assignments_projects = [
                {
                    "id_proyecto": p.get("id", 0),
                    "nombre": p.get("name", p.get("nombre", "Sin nombre")),
                    "id_organizacion": organization_id,
                    "active": p.get("active", True),
                }
                for p in projects
                if p.get("active", True) and p.get("existe", True)
            ]

            print(f"[DEBUG ASSIGNMENTS] Proyectos filtrados: {len(self.assignments_projects)}")
            if self.assignments_projects:
                print(f"[DEBUG ASSIGNMENTS] Primer proyecto filtrado: {self.assignments_projects[0]}")

        except Exception as e:
            print(f"[ERROR] load_projects_for_org: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            self.assignments_projects = []

        # Load project roles catalog (hardcoded for now)
        # TODO: Add API to fetch proyectos_roles_base
        self.assignments_project_roles = [
            {"id": 3, "nombre_rol": "Editor"},
            {"id": 4, "nombre_rol": "Lector"},
            {"id": 5, "nombre_rol": "Auditor"},
        ]

        # Note: Org roles are now loaded in load_assignments_data() via get_roles() API

    def set_assignments_tab(self, tab: str):
        """Changes active tab."""
        self.assignments_active_tab = tab
        if tab == "organizaciones":
            self.load_org_assignments()
        elif tab == "proyectos":
            self.load_project_assignments()
        elif tab == "job_templates":
            self.load_jt_data()
        elif tab == "prompts":
            self.load_prompts()

    def load_org_assignments(self):
        """Loads organization assignments for selected org."""
        if self.selected_organization_assign <= 0:
            self.org_assignments_list = []
            return

        from adapters.api_client import get_organization_assignments

        try:
            assignments = get_organization_assignments(
                organization_id=self.selected_organization_assign,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            self.org_assignments_list = assignments
            # Log assignment list query
            activity_log.log_assignment_list(
                user_id=self.user_id,
                assignment_type="organization",
                filter_id=self.selected_organization_assign,
                count=len(assignments),
            )
        except Exception as e:
            print(f"[ERROR] load_org_assignments: {e}")
            self.org_assignment_error = str(e)
            self.org_assignments_list = []

    @rx.event(background=True)
    async def create_org_assignment(self):
        """Creates organization assignment."""
        from adapters.api_client import create_organization_assignment

        async with self:
            self.org_assignment_error = ""
            self.org_assignment_success = ""

        try:
            print(f"[DEBUG] Creating assignment: user={self.selected_user_org}, org={self.selected_organization_assign}, role={self.selected_org_role}")
            result = create_organization_assignment(
                user_id=self.selected_user_org,
                organization_id=self.selected_organization_assign,
                role_id=self.selected_org_role,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            print(f"[DEBUG] Assignment result: {result}")
            print(f"[DEBUG] Result type: {type(result)}")

            async with self:
                if result.get("success"):
                    self.org_assignment_success = result.get("message", "Creado")
                    assignment_id = result.get("assignment_id", 0)
                    # Log successful assignment creation
                    activity_log.log_assignment_create(
                        user_id=self.user_id,
                        assignment_type="organization",
                        assignment_id=assignment_id,
                        target_user_id=self.selected_user_org,
                        organization_id=self.selected_organization_assign,
                        role_id=self.selected_org_role,
                    )
                    self.load_org_assignments()
                else:
                    error_detail = result.get("detail", "Error")
                    print(f"[DEBUG] Error detail: {error_detail}, type: {type(error_detail)}")
                    # Asegurar que el error sea una string
                    self.org_assignment_error = str(error_detail) if not isinstance(error_detail, str) else error_detail
        except Exception as e:
            print(f"[DEBUG] Exception in create_org_assignment: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            async with self:
                self.org_assignment_error = str(e)

    def toggle_org_assignment(self, assignment_id: int):
        """Toggles organization assignment active status."""
        from adapters.api_client import update_organization_assignment

        # Find current active status
        current_active = True
        for assignment in self.org_assignments_list:
            if assignment.get("id") == assignment_id:
                current_active = assignment.get("active", True)
                break

        try:
            result = update_organization_assignment(
                assignment_id=assignment_id,
                active=not current_active,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if result.get("success"):
                # Log assignment update
                activity_log.log_assignment_update(
                    user_id=self.user_id,
                    assignment_type="organization",
                    assignment_id=assignment_id,
                    changes={"active": not current_active},
                )
                self.load_org_assignments()
                self.org_assignment_success = result.get("message", "Actualizado")
        except Exception as e:
            self.org_assignment_error = str(e)

    def delete_org_assignment(self, assignment_id: int):
        """Deletes organization assignment permanently."""
        from adapters.api_client import delete_organization_assignment

        try:
            result = delete_organization_assignment(
                assignment_id=assignment_id,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if result.get("success"):
                # Log assignment deletion
                activity_log.log_assignment_delete(
                    user_id=self.user_id,
                    assignment_type="organization",
                    assignment_id=assignment_id,
                )
                self.load_org_assignments()
                self.org_assignment_success = "Asignación eliminada"
        except Exception as e:
            self.org_assignment_error = str(e)

    def load_project_assignments(self):
        """Loads project assignments for selected project."""
        if self.selected_project_assign <= 0:
            self.project_assignments_list = []
            return

        from adapters.api_client import get_project_assignments

        try:
            assignments = get_project_assignments(
                project_id=self.selected_project_assign,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            self.project_assignments_list = assignments
            # Log project assignment list query
            activity_log.log_assignment_list(
                user_id=self.user_id,
                assignment_type="project",
                filter_id=self.selected_project_assign,
                count=len(assignments),
            )
        except Exception as e:
            print(f"[ERROR] load_project_assignments: {e}")
            self.project_assignment_error = str(e)
            self.project_assignments_list = []

    @rx.event(background=True)
    async def create_project_assignment(self):
        """Creates project assignment with prerequisite validation."""
        from adapters.api_client import create_project_assignment

        async with self:
            self.project_assignment_error = ""
            self.project_assignment_success = ""
            self.prerequisite_validation_error = ""

        try:
            print(
                f"[DEBUG ASSIGNMENTS] create_project_assignment: "
                f"user_id={self.selected_user_project} "
                f"org_id={self.selected_org_for_project} "
                f"project_id={self.selected_project_assign} "
                f"role_id={self.selected_project_role}"
            )
            result = create_project_assignment(
                user_id=self.selected_user_project,
                organization_id=self.selected_org_for_project,
                project_id=self.selected_project_assign,
                role_id=self.selected_project_role,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            async with self:
                if result.get("success"):
                    self.project_assignment_success = result.get("message", "Creado")
                    assignment_id = result.get("assignment_id", 0)
                    # Log successful project assignment creation
                    activity_log.log_assignment_create(
                        user_id=self.user_id,
                        assignment_type="project",
                        assignment_id=assignment_id,
                        target_user_id=self.selected_user_project,
                        organization_id=self.selected_org_for_project,
                        project_id=self.selected_project_assign,
                        role_id=self.selected_project_role,
                    )
                    self.load_project_assignments()
                else:
                    error_msg = result.get("detail", "Error")
                    if "organización" in error_msg.lower():
                        self.prerequisite_validation_error = error_msg
                    else:
                        self.project_assignment_error = error_msg
        except Exception as e:
            async with self:
                self.project_assignment_error = str(e)

    def toggle_project_assignment(self, assignment_id: int):
        """Toggles project assignment active status."""
        from adapters.api_client import update_project_assignment

        # Find current active status
        current_active = True
        for assignment in self.project_assignments_list:
            if assignment.get("id") == assignment_id:
                current_active = assignment.get("active", True)
                break

        try:
            result = update_project_assignment(
                assignment_id=assignment_id,
                active=not current_active,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if result.get("success"):
                # Log project assignment update
                activity_log.log_assignment_update(
                    user_id=self.user_id,
                    assignment_type="project",
                    assignment_id=assignment_id,
                    changes={"active": not current_active},
                )
                self.load_project_assignments()
                self.project_assignment_success = result.get("message", "Actualizado")
        except Exception as e:
            self.project_assignment_error = str(e)

    def delete_project_assignment(self, assignment_id: int):
        """Deletes project assignment permanently."""
        from adapters.api_client import delete_project_assignment

        try:
            result = delete_project_assignment(
                assignment_id=assignment_id,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if result.get("success"):
                # Log project assignment deletion
                activity_log.log_assignment_delete(
                    user_id=self.user_id,
                    assignment_type="project",
                    assignment_id=assignment_id,
                )
                self.load_project_assignments()
                self.project_assignment_success = "Asignación eliminada"
        except Exception as e:
            self.project_assignment_error = str(e)

    # ========================================================================
    # PROMPTS MANAGEMENT - Gestión de Prompts (SuperAdmin only)
    # ========================================================================

    def set_prompts_category(self, category: str):
        """Changes active prompts category."""
        self.prompts_category = category
        self.load_prompts()
        self.clear_prompts_form()

    def load_prompts(self):
        """Loads prompts for the selected category."""
        from adapters.api_client import get_prompts

        try:
            prompts = get_prompts(
                category=self.prompts_category,
                access_token=self.access_token,
                session_token=self.session_token,
            )
            self.prompts_list = prompts
            self.form_error = ""
        except Exception as e:
            self.form_error = f"Error al cargar prompts: {str(e)}"
            self.prompts_list = []

    def select_prompt(self, id_prompt: int):
        """Selects a prompt for editing."""
        prompt = next((p for p in self.prompts_list if p.get("id_prompt") == id_prompt), None)
        if prompt:
            self.selected_prompt_id = id_prompt
            self.form_mode = "edit"
            self.form_name = prompt.get("name", "")
            self.form_description = prompt.get("description", "")
            self.form_prompt = prompt.get("prompt", "")
            self.form_error = ""
            self.form_success = ""

    def clear_prompts_form(self):
        """Clears the prompts form."""
        self.selected_prompt_id = 0
        self.form_mode = "create"
        self.form_name = ""
        self.form_description = ""
        self.form_prompt = ""
        self.form_error = ""
        self.form_success = ""

    @rx.event(background=True)
    async def save_prompt(self):
        """Creates or updates a prompt."""
        from adapters.api_client import create_prompt, update_prompt

        async with self:
            self.form_error = ""
            self.form_success = ""

        try:
            if self.form_mode == "create":
                result = create_prompt(
                    category=self.prompts_category,
                    name=self.form_name,
                    description=self.form_description if self.form_description else None,
                    prompt=self.form_prompt,
                    access_token=self.access_token,
                    session_token=self.session_token,
                )
            else:  # edit
                result = update_prompt(
                    category=self.prompts_category,
                    id_prompt=self.selected_prompt_id,
                    name=self.form_name,
                    description=self.form_description if self.form_description else None,
                    prompt=self.form_prompt,
                    access_token=self.access_token,
                    session_token=self.session_token,
                )

            async with self:
                if result.get("success"):
                    self.form_success = result.get("message", "Guardado exitosamente")
                    self.load_prompts()
                    self.clear_prompts_form()
                else:
                    self.form_error = result.get("detail", "Error al guardar")
        except Exception as e:
            async with self:
                self.form_error = str(e)

    def toggle_prompt_status(self, id_prompt: int, current_active: bool):
        """Toggles prompt active status."""
        from adapters.api_client import toggle_prompt

        try:
            result = toggle_prompt(
                category=self.prompts_category,
                id_prompt=id_prompt,
                active=not current_active,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if result.get("success"):
                self.load_prompts()
                self.form_success = result.get("message", "Estado actualizado")
        except Exception as e:
            self.form_error = str(e)


    # ========================================================================
    # JOB TEMPLATES MANAGER - Gestor de plantillas de jobs (SuperAdmin only)
    # ========================================================================

    def _get_projects_engine(self):
        """Obtiene el engine de lectura de myllm_projects_db."""
        return get_projects_db_engine()

    def _get_projects_writer_engine(self):
        """Obtiene el engine de escritura de myllm_projects_db."""
        return get_projects_db_writer_engine()

    def load_jt_catalogs(self):
        """Carga los catálogos necesarios para el formulario de plantillas de jobs."""
        try:
            engine = self._get_projects_engine()
            with engine.connect() as conn:
                # Cargar tipos
                rows = conn.execute(text(
                    "SELECT id, clave, nombre, pagina_backoffice FROM jobs_tipos WHERE activo = 1 ORDER BY id"
                )).fetchall()
                self.jt_tipos = [
                    {"id": r[0], "clave": r[1], "nombre": r[2], "pagina": r[3]}
                    for r in rows
                ]

                # Cargar estados
                rows = conn.execute(text(
                    "SELECT id, clave, nombre, color FROM jobs_estados WHERE activo = 1 ORDER BY id"
                )).fetchall()
                self.jt_estados = [
                    {"id": r[0], "clave": r[1], "nombre": r[2], "color": r[3]}
                    for r in rows
                ]

                # Cargar modelos
                rows = conn.execute(text(
                    "SELECT id, nombre, familia FROM jobs_modelos WHERE activo = 1 ORDER BY nombre"
                )).fetchall()
                self.jt_modelos = [
                    {"id": r[0], "nombre": r[1], "familia": r[2]}
                    for r in rows
                ]

                # Cargar salidas
                rows = conn.execute(text(
                    "SELECT id, clave, nombre FROM jobs_salidas WHERE activo = 1 ORDER BY id"
                )).fetchall()
                self.jt_salidas = [
                    {"id": r[0], "clave": r[1], "nombre": r[2]}
                    for r in rows
                ]

            print(f"[JOB TEMPLATES] Catálogos cargados: tipos={len(self.jt_tipos)}, "
                  f"estados={len(self.jt_estados)}, modelos={len(self.jt_modelos)}, "
                  f"salidas={len(self.jt_salidas)}")
        except Exception as e:
            print(f"[ERROR JOB TEMPLATES] load_jt_catalogs: {type(e).__name__}: {e}")
            self.jt_error = f"Error cargando catálogos: {e}"

    def load_jt_list(self):
        """Carga la lista de plantillas de jobs con información de catálogos resuelta."""
        try:
            engine = self._get_projects_engine()
            with engine.connect() as conn:
                rows = conn.execute(text("""
                    SELECT
                        jt.id,
                        jt.nombre,
                        jt.descripcion,
                        jt.id_tipo,
                        jtip.nombre       AS tipo_nombre,
                        jtip.pagina_backoffice AS pagina,
                        jt.es_programable,
                        jt.activo,
                        jt.id_estado_inicial,
                        COALESCE(jest.nombre, '-')  AS estado_nombre,
                        jt.id_modelo,
                        COALESCE(jmod.nombre, '-')  AS modelo_nombre,
                        jt.id_salida,
                        COALESCE(jsal.nombre, '-')  AS salida_nombre,
                        jt.acepta_entrada,
                        jt.permite_hijos
                    FROM jobs_templates jt
                    INNER JOIN jobs_tipos jtip   ON jt.id_tipo = jtip.id
                    LEFT  JOIN jobs_estados jest ON jt.id_estado_inicial = jest.id
                    LEFT  JOIN jobs_modelos jmod ON jt.id_modelo = jmod.id
                    LEFT  JOIN jobs_salidas jsal ON jt.id_salida = jsal.id
                    ORDER BY jt.id DESC
                """)).fetchall()
                self.jt_list = [
                    {
                        "id": r[0],
                        "nombre": r[1],
                        "descripcion": r[2] or "",
                        "id_tipo": r[3],
                        "tipo_nombre": r[4],
                        "pagina": r[5],
                        "es_programable": bool(r[6]),
                        "activo": bool(r[7]),
                        "id_estado_inicial": r[8] or 0,
                        "estado_nombre": r[9],
                        "id_modelo": r[10] or 0,
                        "modelo_nombre": r[11],
                        "id_salida": r[12] or 0,
                        "salida_nombre": r[13],
                        "acepta_entrada": bool(r[14]),
                        "permite_hijos": bool(r[15]),
                    }
                    for r in rows
                ]
            print(f"[JOB TEMPLATES] Plantillas cargadas: {len(self.jt_list)}")
        except Exception as e:
            print(f"[ERROR JOB TEMPLATES] load_jt_list: {type(e).__name__}: {e}")
            self.jt_error = f"Error cargando plantillas: {e}"
            self.jt_list = []

    def load_jt_data(self):
        """Carga catálogos y lista de plantillas (punto de entrada principal)."""
        self.jt_error = ""
        self.jt_success = ""
        self.load_jt_catalogs()
        self.load_jt_list()

    def jt_clear_form(self):
        """Limpia el formulario de plantillas."""
        self.jt_form_mode = "create"
        self.jt_selected_id = 0
        self.jt_nombre = ""
        self.jt_descripcion = ""
        self.jt_id_tipo = 0
        self.jt_es_programable = False
        self.jt_id_estado_inicial = 0
        self.jt_id_modelo = 0
        self.jt_id_salida = 0
        self.jt_acepta_entrada = False
        self.jt_permite_hijos = False
        self.jt_error = ""
        self.jt_success = ""

    def jt_select_template(self, template_id: int):
        """Selecciona una plantilla para editar."""
        for t in self.jt_list:
            if t["id"] == template_id:
                self.jt_form_mode = "edit"
                self.jt_selected_id = t["id"]
                self.jt_nombre = t["nombre"]
                self.jt_descripcion = t["descripcion"]
                self.jt_id_tipo = t["id_tipo"]
                self.jt_es_programable = t["es_programable"]
                self.jt_id_estado_inicial = t["id_estado_inicial"]
                self.jt_id_modelo = t["id_modelo"]
                self.jt_id_salida = t["id_salida"]
                self.jt_acepta_entrada = t["acepta_entrada"]
                self.jt_permite_hijos = t["permite_hijos"]
                self.jt_error = ""
                self.jt_success = ""
                return

    # Setters para conversión de string a int (requerido por rx.select)
    def jt_set_id_tipo_from_str(self, val: str):
        """Convierte string a int para id_tipo."""
        self.jt_id_tipo = int(val) if val else 0

    def jt_set_id_estado_from_str(self, val: str):
        """Convierte string a int para id_estado_inicial."""
        self.jt_id_estado_inicial = int(val) if val else 0

    def jt_set_id_modelo_from_str(self, val: str):
        """Convierte string a int para id_modelo."""
        self.jt_id_modelo = int(val) if val else 0

    def jt_set_id_salida_from_str(self, val: str):
        """Convierte string a int para id_salida."""
        self.jt_id_salida = int(val) if val else 0

    def jt_save_template(self):
        """Guarda (crea o actualiza) una plantilla de job."""
        self.jt_error = ""
        self.jt_success = ""

        # Validaciones
        if not self.jt_nombre.strip():
            self.jt_error = "El nombre es obligatorio"
            return
        if self.jt_id_tipo <= 0:
            self.jt_error = "Debe seleccionar un tipo de job"
            return

        try:
            engine = self._get_projects_writer_engine()
            with engine.begin() as conn:
                if self.jt_form_mode == "create":
                    conn.execute(text("""
                        INSERT INTO jobs_templates
                            (nombre, descripcion, id_tipo, es_programable,
                             id_estado_inicial, id_modelo, id_salida,
                             acepta_entrada, permite_hijos, activo)
                        VALUES
                            (:nombre, :descripcion, :id_tipo, :es_programable,
                             :id_estado_inicial, :id_modelo, :id_salida,
                             :acepta_entrada, :permite_hijos, 1)
                    """), {
                        "nombre": self.jt_nombre.strip(),
                        "descripcion": self.jt_descripcion.strip() or None,
                        "id_tipo": self.jt_id_tipo,
                        "es_programable": 1 if self.jt_es_programable else 0,
                        "id_estado_inicial": self.jt_id_estado_inicial if self.jt_id_estado_inicial > 0 else None,
                        "id_modelo": self.jt_id_modelo if self.jt_id_modelo > 0 else None,
                        "id_salida": self.jt_id_salida if self.jt_id_salida > 0 else None,
                        "acepta_entrada": 1 if self.jt_acepta_entrada else 0,
                        "permite_hijos": 1 if self.jt_permite_hijos else 0,
                    })
                    self.jt_success = f"Plantilla '{self.jt_nombre}' creada correctamente"
                    print(f"[JOB TEMPLATES] Plantilla creada: {self.jt_nombre}")
                else:
                    conn.execute(text("""
                        UPDATE jobs_templates SET
                            nombre = :nombre,
                            descripcion = :descripcion,
                            id_tipo = :id_tipo,
                            es_programable = :es_programable,
                            id_estado_inicial = :id_estado_inicial,
                            id_modelo = :id_modelo,
                            id_salida = :id_salida,
                            acepta_entrada = :acepta_entrada,
                            permite_hijos = :permite_hijos
                        WHERE id = :id
                    """), {
                        "id": self.jt_selected_id,
                        "nombre": self.jt_nombre.strip(),
                        "descripcion": self.jt_descripcion.strip() or None,
                        "id_tipo": self.jt_id_tipo,
                        "es_programable": 1 if self.jt_es_programable else 0,
                        "id_estado_inicial": self.jt_id_estado_inicial if self.jt_id_estado_inicial > 0 else None,
                        "id_modelo": self.jt_id_modelo if self.jt_id_modelo > 0 else None,
                        "id_salida": self.jt_id_salida if self.jt_id_salida > 0 else None,
                        "acepta_entrada": 1 if self.jt_acepta_entrada else 0,
                        "permite_hijos": 1 if self.jt_permite_hijos else 0,
                    })
                    self.jt_success = f"Plantilla '{self.jt_nombre}' actualizada correctamente"
                    print(f"[JOB TEMPLATES] Plantilla actualizada: id={self.jt_selected_id}")

            # Recargar lista y limpiar formulario
            self.load_jt_list()
            self.jt_clear_form()
        except Exception as e:
            print(f"[ERROR JOB TEMPLATES] jt_save_template: {type(e).__name__}: {e}")
            self.jt_error = f"Error guardando plantilla: {e}"

    def jt_toggle_active(self, template_id: int):
        """Activa o desactiva una plantilla de job."""
        self.jt_error = ""
        self.jt_success = ""

        # Buscar el estado actual
        current_active = True
        for t in self.jt_list:
            if t["id"] == template_id:
                current_active = t["activo"]
                break

        try:
            engine = self._get_projects_writer_engine()
            with engine.begin() as conn:
                new_active = 0 if current_active else 1
                conn.execute(text(
                    "UPDATE jobs_templates SET activo = :activo WHERE id = :id"
                ), {"activo": new_active, "id": template_id})

            action = "activada" if new_active == 1 else "desactivada"
            self.jt_success = f"Plantilla {action} correctamente"
            print(f"[JOB TEMPLATES] Plantilla {template_id} {action}")
            self.load_jt_list()
        except Exception as e:
            print(f"[ERROR JOB TEMPLATES] jt_toggle_active: {type(e).__name__}: {e}")
            self.jt_error = f"Error cambiando estado: {e}"

    # ========================================================================
    # ANÁLISIS DE DOCUMENTACIÓN - Página de creación de jobs
    # ========================================================================

    # --- Computed properties ---

    @rx.var
    def ad_org_names(self) -> list[str]:
        """Nombres de organizaciones para el selector."""
        return [o["name"] for o in self.ad_orgs]

    @rx.var
    def ad_selected_org_display(self) -> str:
        """Nombre de la organización seleccionada."""
        for o in self.ad_orgs:
            if o["id"] == self.ad_org_id:
                return o["name"]
        return ""

    @rx.var
    def ad_project_names(self) -> list[str]:
        """Nombres de proyectos para el selector."""
        return [p["name"] for p in self.ad_projects]

    @rx.var
    def ad_selected_project_display(self) -> str:
        """Nombre del proyecto seleccionado."""
        for p in self.ad_projects:
            if p["id"] == self.ad_project_id:
                return p["name"]
        return ""

    @rx.var
    def ad_version_names(self) -> list[str]:
        """Carpetas de versiones para el selector."""
        return [v["version_folder"] for v in self.ad_versions]

    @rx.var
    def ad_selected_version_display(self) -> str:
        """Versión seleccionada."""
        for v in self.ad_versions:
            if v["id_version"] == self.ad_version_id:
                return v["version_folder"]
        return ""

    @rx.var
    def ad_template_names(self) -> list[str]:
        """Nombres de plantillas para el selector."""
        return [t["nombre"] for t in self.ad_templates]

    @rx.var
    def ad_selected_template_display(self) -> str:
        """Nombre de la plantilla seleccionada."""
        for t in self.ad_templates:
            if t["id"] == self.ad_selected_template_id:
                return t["nombre"]
        return ""

    @rx.var
    def ad_show_form(self) -> bool:
        """Muestra el formulario solo si hay plantilla seleccionada."""
        return self.ad_selected_template_id > 0

    # --- Carga de datos ---

    def ad_load_organizations(self):
        """Carga organizaciones accesibles para el usuario (consulta directa a BD)."""
        try:
            engine = self._get_projects_engine()
            with engine.connect() as conn:
                if self.identity_type_id == 1:
                    # SuperAdmin ve todas las organizaciones
                    rows = conn.execute(text(
                        "SELECT organization_id, organization_name "
                        "FROM myllm_core_db.organizations "
                        "ORDER BY organization_name"
                    )).fetchall()
                else:
                    # Otros usuarios: filtrar por asignaciones
                    rows = conn.execute(text(
                        "SELECT DISTINCT o.organization_id, o.organization_name "
                        "FROM myllm_core_db.organizations o "
                        "INNER JOIN asignaciones_organizaciones_internas aoi "
                        "  ON o.organization_id = aoi.id_organizacion "
                        "WHERE aoi.id_usuario = :uid AND aoi.active = 1 "
                        "ORDER BY o.organization_name"
                    ), {"uid": self.user_id}).fetchall()

            self.ad_orgs = [{"id": int(r[0]), "name": r[1]} for r in rows]
            print(f"[AD] Organizaciones cargadas: {len(self.ad_orgs)}")

            # Seleccionar organización por defecto
            if self.ad_orgs and self.ad_org_id == 0:
                if self.organization_id > 0:
                    self.ad_org_id = self.organization_id
                else:
                    self.ad_org_id = self.ad_orgs[0]["id"]

            # Cargar proyectos si hay org seleccionada
            if self.ad_org_id > 0:
                self._ad_load_projects()
        except Exception as e:
            print(f"[ERROR AD] ad_load_organizations: {e}")
            self.ad_orgs = []

    def ad_set_organization(self, org_name: str):
        """Cambia la organización y carga sus proyectos."""
        new_id = find_org_id_by_name(self.ad_orgs, org_name)
        if new_id <= 0:
            return
        self.ad_org_id = new_id
        self.ad_project_id = 0
        self.ad_version_id = 0
        self.ad_projects = []
        self.ad_versions = []
        self.ad_jobs = []
        self.ad_selected_template_id = 0
        self._ad_load_projects()

    def _ad_load_projects(self):
        """Carga proyectos de la organización seleccionada (consulta directa a BD)."""
        if self.ad_org_id <= 0:
            self.ad_projects = []
            return
        try:
            engine = self._get_projects_engine()
            with engine.connect() as conn:
                if self.identity_type_id == 1:
                    rows = conn.execute(text(
                        "SELECT id, nombre FROM proyectos "
                        "WHERE id_organizacion = :org_id "
                        "ORDER BY nombre"
                    ), {"org_id": self.ad_org_id}).fetchall()
                else:
                    rows = conn.execute(text(
                        "SELECT DISTINCT p.id, p.nombre "
                        "FROM proyectos p "
                        "LEFT JOIN proyectos_roles pr ON p.id = pr.id_proyecto "
                        "WHERE p.id_organizacion = :org_id "
                        "  AND pr.id_usuario = :uid AND pr.active = 1 "
                        "ORDER BY p.nombre"
                    ), {"org_id": self.ad_org_id, "uid": self.user_id}).fetchall()

            self.ad_projects = [{"id": int(r[0]), "name": r[1]} for r in rows]
            print(f"[AD] Proyectos cargados: {len(self.ad_projects)}")
        except Exception as e:
            print(f"[ERROR AD] _ad_load_projects: {e}")
            self.ad_projects = []

    def ad_set_project(self, project_name: str):
        """Cambia el proyecto y carga sus versiones."""
        for p in self.ad_projects:
            if p["name"] == project_name:
                self.ad_project_id = p["id"]
                break
        else:
            self.ad_project_id = 0
        self.ad_version_id = 0
        self.ad_versions = []
        self.ad_jobs = []
        self.ad_selected_template_id = 0
        if self.ad_project_id > 0:
            self._ad_load_versions()

    def _ad_load_versions(self):
        """Carga versiones del proyecto seleccionado (consulta directa a BD)."""
        if self.ad_org_id <= 0 or self.ad_project_id <= 0:
            self.ad_versions = []
            return
        try:
            engine = self._get_projects_engine()
            with engine.connect() as conn:
                rows = conn.execute(text(
                    "SELECT v.id_version "
                    "FROM versiones v "
                    "WHERE v.id_organizacion = :org_id "
                    "  AND v.id_proyecto = :prj_id "
                    "ORDER BY v.id_version DESC"
                ), {"org_id": self.ad_org_id, "prj_id": self.ad_project_id}).fetchall()

            self.ad_versions = [
                {"id_version": int(r[0]), "version_folder": f"v{int(r[0]):03d}"}
                for r in rows
            ]
            print(f"[AD] Versiones cargadas: {len(self.ad_versions)}")
        except Exception as e:
            print(f"[ERROR AD] _ad_load_versions: {e}")
            self.ad_versions = []

    def ad_set_version(self, version_folder: str):
        """Selecciona una versión y carga jobs existentes."""
        for v in self.ad_versions:
            if v["version_folder"] == version_folder:
                self.ad_version_id = v["id_version"]
                break
        else:
            self.ad_version_id = 0
        self.ad_selected_template_id = 0
        self._ad_load_jobs()

    # --- Plantillas y catálogos ---

    def ad_load_templates_and_catalogs(self):
        """Carga las plantillas de tipo analisis_documentacion y los catálogos."""
        try:
            engine = self._get_projects_engine()
            with engine.connect() as conn:
                # Plantillas activas de tipo analisis_documentacion
                rows = conn.execute(text("""
                    SELECT jt.id, jt.nombre, jt.descripcion,
                           jt.id_estado_inicial, jt.id_modelo, jt.id_salida,
                           jt.es_programable, jt.acepta_entrada, jt.permite_hijos
                    FROM jobs_templates jt
                    INNER JOIN jobs_tipos jtip ON jt.id_tipo = jtip.id
                    WHERE jtip.clave = 'analisis_documentacion'
                      AND jt.activo = 1
                    ORDER BY jt.nombre
                """)).fetchall()
                self.ad_templates = [
                    {
                        "id": r[0], "nombre": r[1], "descripcion": r[2] or "",
                        "id_estado_inicial": r[3] or 0, "id_modelo": r[4] or 0,
                        "id_salida": r[5] or 0, "es_programable": bool(r[6]),
                        "acepta_entrada": bool(r[7]), "permite_hijos": bool(r[8]),
                    }
                    for r in rows
                ]

                # Catálogo de modelos
                rows = conn.execute(text(
                    "SELECT id, nombre, familia FROM jobs_modelos WHERE activo = 1 ORDER BY nombre"
                )).fetchall()
                self.ad_modelos = [{"id": r[0], "nombre": r[1], "familia": r[2]} for r in rows]

                # Catálogo de salidas
                rows = conn.execute(text(
                    "SELECT id, clave, nombre FROM jobs_salidas WHERE activo = 1 ORDER BY id"
                )).fetchall()
                self.ad_salidas = [{"id": r[0], "clave": r[1], "nombre": r[2]} for r in rows]

                # Catálogo de estados
                rows = conn.execute(text(
                    "SELECT id, clave, nombre, color FROM jobs_estados WHERE activo = 1 ORDER BY id"
                )).fetchall()
                self.ad_estados = [
                    {"id": r[0], "clave": r[1], "nombre": r[2], "color": r[3]}
                    for r in rows
                ]

            print(f"[AD] Catálogos: templates={len(self.ad_templates)}, "
                  f"modelos={len(self.ad_modelos)}, salidas={len(self.ad_salidas)}")
        except Exception as e:
            print(f"[ERROR AD] ad_load_templates_and_catalogs: {e}")
            self.ad_error = f"Error cargando catálogos: {e}"

    def ad_select_template(self, template_name: str):
        """Selecciona una plantilla y carga sus valores por defecto en el formulario."""
        self.ad_error = ""
        self.ad_success = ""
        for t in self.ad_templates:
            if t["nombre"] == template_name:
                self.ad_selected_template_id = t["id"]
                self.ad_job_nombre = t["nombre"]
                self.ad_job_descripcion = t["descripcion"]
                self.ad_job_id_modelo = t["id_modelo"]
                self.ad_job_id_salida = t["id_salida"]
                self.ad_job_id_estado = t["id_estado_inicial"]
                self.ad_job_programado_para = ""
                return
        self.ad_selected_template_id = 0

    # Setters para selectores del formulario
    def ad_set_job_modelo_from_str(self, val: str):
        """Convierte string a int para id_modelo."""
        self.ad_job_id_modelo = int(val) if val else 0

    def ad_set_job_salida_from_str(self, val: str):
        """Convierte string a int para id_salida."""
        self.ad_job_id_salida = int(val) if val else 0

    def ad_set_job_estado_from_str(self, val: str):
        """Convierte string a int para id_estado."""
        self.ad_job_id_estado = int(val) if val else 0

    # --- CRUD de jobs ---

    def ad_create_job(self):
        """Crea un nuevo job basado en la plantilla seleccionada."""
        self.ad_error = ""
        self.ad_success = ""

        # Validaciones
        if self.ad_org_id <= 0:
            self.ad_error = "Debe seleccionar una organización"
            return
        if self.ad_project_id <= 0:
            self.ad_error = "Debe seleccionar un proyecto"
            return
        if self.ad_version_id <= 0:
            self.ad_error = "Debe seleccionar una versión"
            return
        if self.ad_selected_template_id <= 0:
            self.ad_error = "Debe seleccionar una plantilla"
            return
        if not self.ad_job_nombre.strip():
            self.ad_error = "El nombre del job es obligatorio"
            return

        # Obtener id_tipo de la plantilla
        id_tipo = 0
        try:
            engine = self._get_projects_engine()
            with engine.connect() as conn:
                row = conn.execute(text(
                    "SELECT id_tipo FROM jobs_templates WHERE id = :id"
                ), {"id": self.ad_selected_template_id}).fetchone()
                if row:
                    id_tipo = row[0]
        except Exception as e:
            self.ad_error = f"Error obteniendo tipo de plantilla: {e}"
            return

        if id_tipo <= 0:
            self.ad_error = "No se pudo determinar el tipo de job"
            return

        # Determinar estado
        id_estado = self.ad_job_id_estado if self.ad_job_id_estado > 0 else 1

        try:
            engine = self._get_projects_writer_engine()
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO jobs
                        (id_template, id_organizacion, id_proyecto, id_version,
                         nombre, descripcion, id_tipo, id_estado,
                         id_modelo, id_salida, programado_para)
                    VALUES
                        (:id_template, :id_org, :id_proyecto, :id_version,
                         :nombre, :descripcion, :id_tipo, :id_estado,
                         :id_modelo, :id_salida, :programado_para)
                """), {
                    "id_template": self.ad_selected_template_id,
                    "id_org": self.ad_org_id,
                    "id_proyecto": self.ad_project_id,
                    "id_version": self.ad_version_id,
                    "nombre": self.ad_job_nombre.strip(),
                    "descripcion": self.ad_job_descripcion.strip() or None,
                    "id_tipo": id_tipo,
                    "id_estado": id_estado,
                    "id_modelo": self.ad_job_id_modelo if self.ad_job_id_modelo > 0 else None,
                    "id_salida": self.ad_job_id_salida if self.ad_job_id_salida > 0 else None,
                    "programado_para": self.ad_job_programado_para if self.ad_job_programado_para.strip() else None,
                })

            self.ad_success = f"Job '{self.ad_job_nombre}' creado correctamente"
            print(f"[AD] Job creado: {self.ad_job_nombre}")
            # Recargar lista y limpiar selección de plantilla
            self._ad_load_jobs()
            self.ad_selected_template_id = 0
            self.ad_job_nombre = ""
            self.ad_job_descripcion = ""
            self.ad_job_programado_para = ""
        except Exception as e:
            print(f"[ERROR AD] ad_create_job: {e}")
            self.ad_error = f"Error creando job: {e}"

    def _ad_load_jobs(self):
        """Carga los jobs de análisis de documentación para org/proyecto/versión."""
        import json as _json

        if self.ad_version_id <= 0:
            self.ad_jobs = []
            return
        try:
            engine = self._get_projects_engine()
            with engine.connect() as conn:
                rows = conn.execute(text("""
                    SELECT
                        j.id, j.nombre, j.descripcion,
                        jest.nombre       AS estado_nombre,
                        jest.color        AS estado_color,
                        COALESCE(jmod.nombre, '-') AS modelo_nombre,
                        COALESCE(jsal.nombre, '-') AS salida_nombre,
                        jt.nombre         AS template_nombre,
                        j.programado_para,
                        j.iniciado_en,
                        j.completado_en,
                        j.error,
                        j.created_at,
                        j.configuracion
                    FROM jobs j
                    INNER JOIN jobs_estados jest   ON j.id_estado = jest.id
                    INNER JOIN jobs_templates jt   ON j.id_template = jt.id
                    LEFT  JOIN jobs_modelos jmod   ON j.id_modelo = jmod.id
                    LEFT  JOIN jobs_salidas jsal   ON j.id_salida = jsal.id
                    INNER JOIN jobs_tipos jtip     ON j.id_tipo = jtip.id
                    WHERE jtip.clave = 'analisis_documentacion'
                      AND j.id_organizacion = :org_id
                      AND j.id_proyecto = :prj_id
                      AND j.id_version = :ver_id
                    ORDER BY j.id DESC
                """), {
                    "org_id": self.ad_org_id,
                    "prj_id": self.ad_project_id,
                    "ver_id": self.ad_version_id,
                }).fetchall()
                result_jobs = []
                for r in rows:
                    # Parsear configuracion JSON
                    config_raw = r[13]
                    config_dict: dict = {}
                    if config_raw:
                        try:
                            if isinstance(config_raw, str):
                                config_dict = _json.loads(config_raw)
                            elif isinstance(config_raw, dict):
                                config_dict = config_raw
                        except (ValueError, TypeError):
                            config_dict = {}
                    result_jobs.append({
                        "id": r[0],
                        "nombre": r[1],
                        "descripcion": r[2] or "",
                        "estado_nombre": r[3],
                        "estado_color": r[4] or "#888",
                        "modelo_nombre": r[5],
                        "salida_nombre": r[6],
                        "template_nombre": r[7],
                        "programado_para": str(r[8]) if r[8] else "-",
                        "iniciado_en": str(r[9]) if r[9] else "-",
                        "completado_en": str(r[10]) if r[10] else "-",
                        "error": r[11] or "",
                        "created_at": str(r[12]) if r[12] else "",
                        "sel_identidad": config_dict.get("sel_identidad", ""),
                        "sel_contexto": config_dict.get("sel_contexto", ""),
                        "sel_solicitud": config_dict.get("sel_solicitud", ""),
                        "sel_modalidad": config_dict.get("sel_modalidad", ""),
                        "prompt_final_guardado": config_dict.get("prompt_final", ""),
                    })
                self.ad_jobs = result_jobs
            print(f"[AD] Jobs cargados: {len(self.ad_jobs)}")
        except Exception as e:
            print(f"[ERROR AD] _ad_load_jobs: {e}")
            self.ad_jobs = []

    def ad_init_page(self):
        """Inicializa la página de Análisis de Documentación."""
        self.ad_load_organizations()
        self.ad_load_templates_and_catalogs()

    # ========================================================================
    # ENTRENAMIENTOS - Visor de versiones pendientes
    # ========================================================================

    def ent_load_pending_versions(self):
        """Carga las versiones con entrenamiento inicial solicitado."""
        self.ent_error = ""
        self.ent_send_error = ""
        self.ent_loading = True

        try:
            from adapters.api_client import get_pending_training_versions

            result = get_pending_training_versions(
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if isinstance(result, dict):
                # Añadir campo 'ack' a cada versión para tracking de envío
                versions = result.get("versions", [])
                self.ent_pending_versions = [
                    {**v, "ack": False} for v in versions
                ]
            else:
                self.ent_pending_versions = []
                self.ent_error = "Respuesta inesperada del servidor"
        except Exception as exc:
            self.ent_error = f"Error cargando versiones: {str(exc)}"
            self.ent_pending_versions = []
        finally:
            self.ent_loading = False

    def ent_open_params_modal(self, state_id: int):
        """Abre el modal de parámetros de entrenamiento.

        Busca la versión en la lista, consulta el endpoint inteligente de
        parámetros y carga los valores en las variables del modal.
        """
        from adapters.api_client import get_training_params

        self.ent_modal_loading = True
        self.ent_modal_warnings = []
        self.ent_send_error = ""

        # Buscar la versión en la lista
        version_data = None
        for v in self.ent_pending_versions:
            if v.get("state_id") == state_id:
                version_data = v
                break

        if not version_data:
            self.ent_send_error = "Versión no encontrada en el listado"
            self.ent_modal_loading = False
            return

        self.ent_modal_version_data = version_data

        try:
            result = get_training_params(
                org_id=version_data["id_organizacion"],
                project_id=version_data["id_proyecto"],
                version_id=version_data["id_version"],
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if not result.get("success", False):
                self.ent_send_error = result.get(
                    "message", "Error obteniendo parámetros"
                )
                self.ent_modal_loading = False
                return

            # Flags informativos
            self.ent_modal_es_primer = result.get("es_primer_entrenamiento", True)
            self.ent_modal_es_reentrenamiento = result.get("es_reentrenamiento", False)

            # Grupo 1: Preparación de datos
            self.ent_modal_chunk_size = str(result.get("chunk_size", 1000))
            self.ent_modal_chunk_overlap = str(result.get("chunk_overlap", 200))
            self.ent_modal_embedding_dimension = str(
                result.get("embedding_dimension", 768)
            )
            self.ent_modal_sequence_length = str(
                result.get("sequence_length", 512)
            )
            self.ent_modal_distance_metric = str(
                result.get("distance_metric", "cosine")
            )

            # Grupo 2: Modelo y generación
            self.ent_modal_model_type = str(result.get("model_type", ""))
            # Convertir lista de dicts a lista de nombres para el dropdown
            raw_modelos = result.get("modelos_disponibles", [])
            self.ent_modal_modelos_disponibles = [
                str(m.get("nombre", "")) if isinstance(m, dict) else str(m)
                for m in raw_modelos
                if m
            ]
            self.ent_modal_temperature = str(result.get("temperature", 0.7))
            self.ent_modal_max_tokens = str(result.get("max_tokens", 2048))
            self.ent_modal_top_k = str(result.get("top_k", 5))

            # Grupo 3: Optimización
            self.ent_modal_learning_rate = str(
                result.get("learning_rate", 0.001)
            )
            self.ent_modal_batch_size = str(result.get("batch_size", 32))
            self.ent_modal_epochs = str(result.get("epochs", 10))
            self.ent_modal_hidden_units = str(result.get("hidden_units", 256))
            self.ent_modal_dropout_rate = str(result.get("dropout_rate", 0.1))
            self.ent_modal_loss_function = str(
                result.get("loss_function", "cross_entropy")
            )
            self.ent_modal_optimizer = str(result.get("optimizer", "adam"))

            self.ent_modal_open = True

        except Exception as exc:
            self.ent_send_error = f"Error cargando parámetros: {str(exc)}"
        finally:
            self.ent_modal_loading = False

    def ent_close_params_modal(self):
        """Cierra el modal de parámetros de entrenamiento."""
        self.ent_modal_open = False
        self.ent_modal_warnings = []

    def ent_open_modal_with_params(self, version_data: dict, params: dict):
        """Abre el modal de entrenamiento con parámetros y datos de versión pre-cargados.

        Usado para reentrenamiento desde Análisis de Resultados.
        """
        print(f"[DEBUG MODAL] ent_open_modal_with_params LLAMADO")
        print(f"[DEBUG MODAL] version_data: {version_data}")
        print(f"[DEBUG MODAL] params keys: {list(params.keys())}")

        self.ent_modal_loading = False
        self.ent_modal_warnings = []
        self.ent_send_error = ""

        # Cargar datos de la versión
        self.ent_modal_version_data = version_data

        # Flags informativos
        self.ent_modal_es_primer = False
        self.ent_modal_es_reentrenamiento = True

        # Cargar todos los parámetros
        self.ent_modal_chunk_size = str(params.get('chunk_size', 1000))
        self.ent_modal_chunk_overlap = str(params.get('chunk_overlap', 200))
        self.ent_modal_temperature = str(params.get('temperature', 0.7))
        self.ent_modal_max_tokens = str(params.get('max_tokens', 2048))
        self.ent_modal_distance_metric = params.get('distance_metric', 'cosine')
        self.ent_modal_top_k = str(params.get('top_k', 5))
        self.ent_modal_learning_rate = str(params.get('learning_rate', 0.001))
        self.ent_modal_batch_size = str(params.get('batch_size', 32))
        self.ent_modal_epochs = str(params.get('epochs', 10))
        self.ent_modal_embedding_dimension = str(params.get('embedding_dimension', 768))
        self.ent_modal_sequence_length = str(params.get('sequence_length', 512))
        self.ent_modal_hidden_units = str(params.get('hidden_units', 256))
        self.ent_modal_dropout_rate = str(params.get('dropout_rate', 0.1))
        self.ent_modal_loss_function = params.get('loss_function', 'categorical_crossentropy')
        self.ent_modal_optimizer = params.get('optimizer', 'adam')
        self.ent_modal_model_type = params.get('model_type', 'llama3.2:latest')

        # Abrir el modal
        self.ent_modal_open = True
        print(f"[DEBUG MODAL] ✅ Modal abierto (ent_modal_open = {self.ent_modal_open})")

    def _ent_validate_params(self):
        """Ejecuta validaciones no bloqueantes sobre los parámetros.

        Genera warnings si los valores están fuera de rangos recomendados.
        No bloquea el envío.
        """
        warnings: list[str] = []
        try:
            temp = float(self.ent_modal_temperature)
            if temp < 0.0 or temp > 1.0:
                warnings.append(
                    "Temperatura fuera del rango recomendado (0.0 - 1.0)"
                )
        except ValueError:
            warnings.append("Temperatura: valor no numérico")

        try:
            chunk = int(self.ent_modal_chunk_size)
            if chunk < 100 or chunk > 5000:
                warnings.append(
                    "Chunk size fuera del rango recomendado (100 - 5000)"
                )
        except ValueError:
            warnings.append("Chunk size: valor no numérico")

        try:
            overlap = int(self.ent_modal_chunk_overlap)
            chunk_val = int(self.ent_modal_chunk_size)
            if overlap < 0 or overlap > chunk_val // 2:
                warnings.append(
                    f"Chunk overlap fuera del rango recomendado (0 - {chunk_val // 2})"
                )
        except ValueError:
            warnings.append("Chunk overlap: valor no numérico")

        try:
            bs = int(self.ent_modal_batch_size)
            if bs < 1 or bs > 256:
                warnings.append(
                    "Batch size fuera del rango recomendado (1 - 256)"
                )
        except ValueError:
            warnings.append("Batch size: valor no numérico")

        try:
            ep = int(self.ent_modal_epochs)
            if ep < 1 or ep > 100:
                warnings.append(
                    "Epochs fuera del rango recomendado (1 - 100)"
                )
        except ValueError:
            warnings.append("Epochs: valor no numérico")

        try:
            lr = float(self.ent_modal_learning_rate)
            if lr < 0.00001 or lr > 0.1:
                warnings.append(
                    "Learning rate fuera del rango recomendado (0.00001 - 0.1)"
                )
        except ValueError:
            warnings.append("Learning rate: valor no numérico")

        try:
            mt = int(self.ent_modal_max_tokens)
            if mt < 256 or mt > 32768:
                warnings.append(
                    "Max tokens fuera del rango recomendado (256 - 32768)"
                )
        except ValueError:
            warnings.append("Max tokens: valor no numérico")

        try:
            tk = int(self.ent_modal_top_k)
            if tk < 1 or tk > 100:
                warnings.append(
                    "Top K fuera del rango recomendado (1 - 100)"
                )
        except ValueError:
            warnings.append("Top K: valor no numérico")

        try:
            dr = float(self.ent_modal_dropout_rate)
            if dr < 0.0 or dr > 0.5:
                warnings.append(
                    "Dropout rate fuera del rango recomendado (0.0 - 0.5)"
                )
        except ValueError:
            warnings.append("Dropout rate: valor no numérico")

        try:
            hu = int(self.ent_modal_hidden_units)
            if hu < 32 or hu > 2048:
                warnings.append(
                    "Hidden units fuera del rango recomendado (32 - 2048)"
                )
        except ValueError:
            warnings.append("Hidden units: valor no numérico")

        try:
            ed = int(self.ent_modal_embedding_dimension)
            if ed < 128 or ed > 2048:
                warnings.append(
                    "Embedding dimension fuera del rango recomendado (128 - 2048)"
                )
        except ValueError:
            warnings.append("Embedding dimension: valor no numérico")

        try:
            sl = int(self.ent_modal_sequence_length)
            if sl < 64 or sl > 4096:
                warnings.append(
                    "Sequence length fuera del rango recomendado (64 - 4096)"
                )
        except ValueError:
            warnings.append("Sequence length: valor no numérico")

        self.ent_modal_warnings = warnings

    def ent_send_to_trainer_from_modal(self) -> list[rx.EventHandler]:
        """Envía solicitud de entrenamiento con los parámetros del modal.

        Recoge todos los params del modal, ejecuta validaciones (warnings,
        no bloqueos), construye payload con ids + pat_version + params y envía.

        Returns:
            Lista con el evento de polling si el envío fue exitoso.
        """
        from adapters.api_client import send_entrenamiento_to_trainer

        print(f"[DEBUG] ent_send_to_trainer_from_modal LLAMADO")
        print(f"[DEBUG] ent_modal_version_data: {self.ent_modal_version_data}")

        # Ejecutar validaciones (warnings, no bloqueo)
        self._ent_validate_params()

        version_data = self.ent_modal_version_data
        if not version_data:
            print(f"[DEBUG] ERROR: No hay version_data")
            self.ent_send_error = "No hay versión seleccionada"
            return []

        state_id = version_data.get("state_id", 0)
        self.ent_sending_state_id = state_id
        self.ent_send_error = ""

        # Construir ruta estática completa: base/ORG00001/PRJ00001/v001
        base_storage = get_env_value(
            "backend_ia_base_storage",
            "~/data/anewhope/files/trainer_server/external",
        )
        org_folder = get_folder_by_id_organization(version_data["id_organizacion"])
        prj_folder = get_folder_by_id_project(version_data["id_proyecto"])
        ver_folder = get_folder_by_id_version(version_data["id_version"])
        pat_version = f"{base_storage}/{org_folder}/{prj_folder}/{ver_folder}"

        # Construir payload con ids + params del modal
        payload: dict[str, Any] = {
            "id_organizacion": version_data["id_organizacion"],
            "id_proyecto": version_data["id_proyecto"],
            "id_version": version_data["id_version"],
            "pat_version": pat_version,
            # Parámetros del modal
            "learning_rate": float(self.ent_modal_learning_rate),
            "batch_size": int(self.ent_modal_batch_size),
            "epochs": int(self.ent_modal_epochs),
            "embedding_dimension": int(self.ent_modal_embedding_dimension),
            "sequence_length": int(self.ent_modal_sequence_length),
            "hidden_units": int(self.ent_modal_hidden_units),
            "dropout_rate": float(self.ent_modal_dropout_rate),
            "chunk_size": int(self.ent_modal_chunk_size),
            "chunk_overlap": int(self.ent_modal_chunk_overlap),
            "temperature": float(self.ent_modal_temperature),
            "max_tokens": int(self.ent_modal_max_tokens),
            "distance_metric": self.ent_modal_distance_metric,
            "top_k": int(self.ent_modal_top_k),
            "loss_function": self.ent_modal_loss_function,
            "optimizer": self.ent_modal_optimizer,
            "model_type": self.ent_modal_model_type,
        }

        print(f"[DEBUG] ent_send_to_trainer INICIO - state_id={state_id}")
        print(f"[DEBUG] payload keys: {list(payload.keys())}")

        try:
            print(f"[DEBUG] Llamando a send_entrenamiento_to_trainer...")
            result = send_entrenamiento_to_trainer(
                payload=payload,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            print(f"[DEBUG] Resultado recibido: success={result.get('success')}, keys={list(result.keys())}")
            print(f"[DEBUG] id_entrenamiento en result: {result.get('id_entrenamiento', 'NO EXISTE')}")

            if result.get("success"):
                import logging
                logger = logging.getLogger("backoffice")
                print(f"[SEND_TO_TRAINER] ✅ Training enviado exitosamente")
                print(f"[SEND_TO_TRAINER] Result: {result}")
                logger.info("[SEND_TO_TRAINER] ✅ Training enviado exitosamente")
                logger.info("[SEND_TO_TRAINER] Result: %s", result)

                # Marcar la versión como ACKed en el visor
                self.ent_pending_versions = [
                    {**v, "ack": True} if v.get("state_id") == state_id else v
                    for v in self.ent_pending_versions
                ]
                self.ent_send_error = ""

                # Cerrar modal
                self.ent_modal_open = False
                self.ent_modal_warnings = []

                # Agregar datos del result al version_data para el polling
                version_data_with_result = {
                    **version_data,
                    "id_entrenamiento": result.get("id_entrenamiento", 0),
                    "collection_name": result.get("collection_name", ""),
                    "numero_secuencia": result.get("numero_secuencia", 0),
                }

                # Inicializar panel de evolución
                self._ent_evo_init(version_data_with_result)

                print(f"[SEND_TO_TRAINER] Panel de evolución inicializado")
                print(f"[SEND_TO_TRAINER] ent_evo_id_entrenamiento={self.ent_evo_id_entrenamiento}")
                print(f"[SEND_TO_TRAINER] ent_evo_active={self.ent_evo_active}")
                print(f"[SEND_TO_TRAINER] 🔄 Retornando polling event...")
                logger.info("[SEND_TO_TRAINER] Panel de evolución inicializado")
                logger.info("[SEND_TO_TRAINER] ent_evo_id_entrenamiento=%s", self.ent_evo_id_entrenamiento)
                logger.info("[SEND_TO_TRAINER] ent_evo_active=%s", self.ent_evo_active)
                logger.info("[SEND_TO_TRAINER] 🔄 Retornando polling event...")

                # Iniciar polling automático
                return [type(self).ent_poll_training_progress]
            else:
                print(f"[DEBUG] ERROR: result.success=False, message={result.get('message')}")
                self.ent_send_error = result.get(
                    "message", "Error desconocido del trainer"
                )
        except Exception as exc:
            print(f"[DEBUG] EXCEPCIÓN: {type(exc).__name__}: {str(exc)}")
            self.ent_send_error = f"Error de comunicación: {str(exc)}"
        finally:
            self.ent_sending_state_id = 0

        return []

    def _ent_evo_init(self, version_data: dict):
        """Inicializa el panel de evolución tras recibir ACK del trainer.

        Define las fases secuenciales del entrenamiento con sus subfases
        correspondientes basadas en el código real del trainer.
        """
        self.ent_evo_active = True
        self.ent_evo_org_name = version_data.get("organization_name", "")
        self.ent_evo_project_name = version_data.get("proyecto_nombre", "")
        self.ent_evo_version_label = version_data.get("version_display", "")
        self.ent_evo_id_entrenamiento = version_data.get("id_entrenamiento", 0)
        self.ent_evo_version_data = version_data  # Guardar datos completos para autónomo
        self.ent_evo_can_cancel = True
        self.ent_evo_cancelling = False
        self.ent_evo_current_phase = "2.1"
        self.ent_evo_current_phase_name = "Verificar directorio"

        # Estructura detallada con subfases basada en el código real del trainer
        # NOTA: Solo incluye fases del trainer. La evaluación de resultados,
        # reentrenamiento, generación LLM y descarga se gestionan desde
        # otras páginas del backoffice (ver roadmap en README.md y AGENTS.md).
        self.ent_evo_phases = [
            {
                "key": "1",
                "nombre": "Recepción",
                "emoji": "📥",
                "color": "#3b82f6",
                "status": "completed",
                "tiempo": "",
                "descripcion": "Solicitud recibida y registrada",
                "subfases": [
                    {"key": "1.1", "nombre": "Registro en BD", "status": "completed", "tiempo": ""},
                    {"key": "1.2", "nombre": "Carga de parámetros", "status": "completed", "tiempo": ""},
                ]
            },
            {
                "key": "2",
                "nombre": "Validación",
                "emoji": "🔍",
                "color": "#8b5cf6",
                "status": "in_progress",
                "tiempo": "",
                "descripcion": "Verificando estructura y contenido",
                "subfases": [
                    {"key": "2.1", "nombre": "Verificar directorio", "status": "in_progress", "tiempo": ""},
                    {"key": "2.2", "nombre": "Escaneo de archivos", "status": "pending", "tiempo": ""},
                    {"key": "2.3", "nombre": "Clasificación por tipo", "status": "pending", "tiempo": ""},
                    {"key": "2.4", "nombre": "Validación de contenido", "status": "pending", "tiempo": ""},
                ]
            },
            {
                "key": "3",
                "nombre": "Preparación",
                "emoji": "📊",
                "color": "#f59e0b",
                "status": "pending",
                "tiempo": "",
                "descripcion": "Procesamiento de datos",
                "subfases": [
                    {"key": "3.1", "nombre": "Carga de documentos", "status": "pending", "tiempo": ""},
                    {"key": "3.2", "nombre": "Chunking", "status": "pending", "tiempo": ""},
                    {"key": "3.3", "nombre": "Generación de embeddings", "status": "pending", "tiempo": ""},
                ]
            },
            {
                "key": "4",
                "nombre": "Configuración",
                "emoji": "⚙️",
                "color": "#06b6d4",
                "status": "pending",
                "tiempo": "",
                "descripcion": "Configuración del modelo",
                "subfases": [
                    {"key": "4.1", "nombre": "Conexión ChromaDB", "status": "pending", "tiempo": ""},
                    {"key": "4.2", "nombre": "Crear colección", "status": "pending", "tiempo": ""},
                    {"key": "4.3", "nombre": "Inserción de documentos", "status": "pending", "tiempo": ""},
                    {"key": "4.4", "nombre": "Verificación de integridad", "status": "pending", "tiempo": ""},
                ]
            },
            {
                "key": "5",
                "nombre": "Entrenamiento",
                "emoji": "🏋️",
                "color": "#10b981",
                "status": "pending",
                "tiempo": "",
                "descripcion": "Entrenamiento del modelo",
                "subfases": [
                    {"key": "5.1", "nombre": "Obtener nombres", "status": "pending", "tiempo": ""},
                    {"key": "5.2", "nombre": "Generar Modelfile", "status": "pending", "tiempo": ""},
                    {"key": "5.3", "nombre": "Guardar Modelfile", "status": "pending", "tiempo": ""},
                    {"key": "5.4", "nombre": "Registrar en Ollama", "status": "pending", "tiempo": ""},
                    {"key": "5.5", "nombre": "Test de verificación", "status": "pending", "tiempo": ""},
                ]
            },
        ]

    def ent_evo_update_phase(self, phase_key: str, new_status: str):
        """Actualiza el estado de una fase del entrenamiento.

        Será invocado cuando el trainer envíe notificaciones de progreso.

        Args:
            phase_key: Clave de la fase (recepcion, validacion, etc.)
            new_status: Nuevo estado (pending, in_progress, completed, error)
        """
        self.ent_evo_phases = [
            {**p, "status": new_status} if p.get("key") == phase_key else p
            for p in self.ent_evo_phases
        ]

    def ent_evo_advance_to_phase(self, phase_key: str):
        """Avanza la ejecución hasta una fase determinada.

        Marca como 'completed' todas las fases anteriores y como
        'in_progress' la fase indicada.

        Args:
            phase_key: Clave de la fase que se activa
        """
        found = False
        updated: list[dict] = []
        for phase in self.ent_evo_phases:
            if phase["key"] == phase_key:
                found = True
                updated.append({**phase, "status": "in_progress"})
            elif not found:
                # Fases anteriores → completadas
                updated.append({**phase, "status": "completed"})
            else:
                # Fases posteriores → pendientes
                updated.append({**phase, "status": "pending"})
        self.ent_evo_phases = updated

    def ent_evo_complete_all(self):
        """Marca todas las fases como completadas (entrenamiento finalizado)."""
        self.ent_evo_phases = [
            {**p, "status": "completed"} for p in self.ent_evo_phases
        ]

    def ent_evo_reset(self):
        """Resetea el panel de evolución."""
        self.ent_evo_active = False
        self.ent_evo_version_label = ""
        self.ent_evo_org_name = ""
        self.ent_evo_project_name = ""
        self.ent_evo_phases = []
        self.ent_evo_id_entrenamiento = 0
        self.ent_evo_current_phase = ""
        self.ent_evo_current_phase_name = ""
        self.ent_evo_can_cancel = True
        self.ent_evo_cancelling = False
        self.ent_evo_expanded_phase = ""
        self.ent_evo_is_autonomous = False
        self.ent_evo_training_mode = ""
        self.ent_evo_version_data = {}

    def ent_evo_toggle_phase(self, phase_key: str):
        """Toggle expansión/colapso de una fase.

        Args:
            phase_key: Clave de la fase a expandir/colapsar (ej: "2", "3", "4", "5")
        """
        if self.ent_evo_expanded_phase == phase_key:
            # Si ya está expandida, colapsar
            self.ent_evo_expanded_phase = ""
        else:
            # Si está colapsada o es otra fase, expandir esta
            self.ent_evo_expanded_phase = phase_key

    def ent_evo_update_subfase(
        self,
        phase_key: str,
        subfase_key: str,
        status: str,
        tiempo: str = "",
    ):
        """Actualiza el estado de una subfase específica.

        Args:
            phase_key: Clave de la fase principal (ej: "3")
            subfase_key: Clave de la subfase (ej: "3.2")
            status: Nuevo estado (pending, in_progress, completed, error)
            tiempo: Tiempo empleado (ej: "2m 15s")
        """
        updated_phases = []
        for phase in self.ent_evo_phases:
            if phase["key"] == phase_key:
                # Actualizar subfase
                updated_subfases = []
                for subfase in phase.get("subfases", []):
                    if subfase["key"] == subfase_key:
                        updated_subfases.append({
                            **subfase,
                            "status": status,
                            "tiempo": tiempo,
                        })
                    else:
                        updated_subfases.append(subfase)

                # Si todas las subfases están completadas, marcar fase como completada
                all_completed = all(
                    sf["status"] == "completed" for sf in updated_subfases
                )
                phase_status = "completed" if all_completed else phase["status"]

                # Si alguna subfase está in_progress, marcar fase como in_progress
                any_in_progress = any(
                    sf["status"] == "in_progress" for sf in updated_subfases
                )
                if any_in_progress:
                    phase_status = "in_progress"

                updated_phases.append({
                    **phase,
                    "subfases": updated_subfases,
                    "status": phase_status,
                    "tiempo": tiempo if all_completed else phase.get("tiempo", ""),
                })
            else:
                updated_phases.append(phase)

        self.ent_evo_phases = updated_phases
        self.ent_evo_current_phase = subfase_key
        self.ent_evo_current_phase_name = next(
            (sf["nombre"] for p in updated_phases if p["key"] == phase_key
             for sf in p.get("subfases", []) if sf["key"] == subfase_key),
            ""
        )

    @rx.event(background=True)
    async def ent_poll_training_progress(self) -> AsyncGenerator[None, None]:
        """Polling automático del progreso del entrenamiento.

        Consulta el endpoint GET de progreso cada 2 segundos y actualiza
        las subfases en tiempo real. Se detiene cuando el entrenamiento
        está completado o hay un error.
        """
        import asyncio
        import logging
        from adapters.api_client import get_training_progress

        logger = logging.getLogger("backoffice")
        logger.info("[POLLING] 🚀 Background event INICIADO")

        while True:
            async with self:
                id_entrenamiento = self.ent_evo_id_entrenamiento
                is_active = self.ent_evo_active
                logger.info("[POLLING] Checking - id_entrenamiento=%s, active=%s", id_entrenamiento, is_active)

                if not is_active or id_entrenamiento == 0:
                    # Polling detenido
                    logger.warning("[POLLING] ⚠️  Detenido: active=%s, id=%s", is_active, id_entrenamiento)
                    break

            # Consultar progreso desde el backend
            try:
                logger.info("[POLLING] 📡 Consultando progreso para id_entrenamiento=%s", id_entrenamiento)
                result = get_training_progress(
                    id_entrenamiento=id_entrenamiento,
                    access_token=self.access_token,
                    session_token=self.session_token,
                )

                if result.get("success") and result.get("data"):
                    data = result["data"]
                    phases_data = data.get("phases", {})
                    logger.info("[POLLING] ✅ Datos recibidos: %d fases", len(phases_data))

                    # Actualizar subfases con los datos reales
                    async with self:
                        for phase_key, phase_info in phases_data.items():
                            for subfase_key, subfase_info in phase_info.get("subfases", {}).items():
                                self.ent_evo_update_subfase(
                                    phase_key=phase_key,
                                    subfase_key=subfase_key,
                                    status=subfase_info["status"],
                                    tiempo=subfase_info.get("elapsed_time", ""),
                                )
                    logger.info("[POLLING] 🔄 UI actualizada, esperando 2s...")
                    yield
                else:
                    logger.warning("[POLLING] ⚠️  No success or no data in result: %s", result)

            except Exception as exc:
                # Log error pero continuar polling
                import logging
                logger = logging.getLogger("backoffice")
                logger.error("[POLLING] Error consultando progreso: %s", exc)

            # Esperar 2 segundos antes del siguiente poll
            await asyncio.sleep(2)

    async def ent_cancel_training(self):
        """Cancela un entrenamiento en progreso."""
        from adapters.api_client import cancel_entrenamiento_training

        if not self.ent_evo_id_entrenamiento:
            yield rx.toast.error(
                "No hay entrenamiento activo para cancelar",
                position="bottom-right",
                duration=3000,
            )
            return

        if self.ent_evo_cancelling:
            # Ya está en proceso de cancelación
            return

        # Marcar como cancelando
        self.ent_evo_cancelling = True
        self.ent_evo_can_cancel = False
        yield

        try:
            # Llamar al middleware para cancelar
            payload = {
                "id_entrenamiento": self.ent_evo_id_entrenamiento,
                "motivo": "Cancelado por usuario desde backoffice",
            }

            response = cancel_entrenamiento_training(
                payload=payload,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if response.get("success"):
                yield rx.toast.success(
                    "Entrenamiento cancelado exitosamente",
                    position="bottom-right",
                    duration=3000,
                )
                # Resetear el panel de evolución
                self.ent_evo_reset()
            else:
                yield rx.toast.error(
                    f"Error al cancelar: {response.get('message', 'Error desconocido')}",
                    position="bottom-right",
                    duration=5000,
                )
                self.ent_evo_cancelling = False
                self.ent_evo_can_cancel = True

        except Exception as exc:
            yield rx.toast.error(
                f"Error al cancelar entrenamiento: {str(exc)}",
                position="bottom-right",
                duration=5000,
            )
            self.ent_evo_cancelling = False
            self.ent_evo_can_cancel = True

    def ent_open_autonomous_modal(self):
        """Abre el modal de confirmación para entrenamiento autónomo.

        Lee el training_mode desde .envglobal y lo muestra en el modal.
        """
        import os
        import yaml
        from pathlib import Path

        # Leer training_mode desde .envglobal (en raíz del proyecto)
        envglobal_path = Path(__file__).parent.parent.parent.parent.parent / ".envglobal"
        training_mode = "simulation"  # Valor por defecto si no se puede leer

        try:
            if envglobal_path.exists():
                with open(envglobal_path, "r", encoding="utf-8") as f:
                    envglobal_data = yaml.safe_load(f)
                    training_mode = envglobal_data.get("training_mode", "simulation")
        except Exception as exc:
            print(f"[WARNING] No se pudo leer training_mode: {exc}")
            training_mode = "simulation"

        self.ent_auto_modal_training_mode = training_mode
        self.ent_auto_modal_open = True

    def ent_close_autonomous_modal(self):
        """Cierra el modal de confirmación de entrenamiento autónomo."""
        self.ent_auto_modal_open = False

    def ent_confirm_autonomous_training(self) -> list[rx.EventHandler]:
        """Confirma y envía el entrenamiento autónomo.

        Este método se ejecuta al confirmar el modal y llama al handler
        ent_send_autonomous_training con los datos del entrenamiento RAG completado.
        """
        # Usar datos completos almacenados durante el entrenamiento RAG
        entrenamiento_data = self.ent_evo_version_data.copy()

        # Cerrar modal
        self.ent_auto_modal_open = False

        # Llamar al handler de envío autónomo
        return self.ent_send_autonomous_training(entrenamiento_data)

    def ent_send_autonomous_training(self, entrenamiento_data: dict) -> list[rx.EventHandler]:
        """Envía solicitud de entrenamiento autónomo (Fases 6-9).

        Este método se llama cuando el usuario hace clic en el botón
        "Entrenar Modelo Autónomo" después de completar un RAG.

        Args:
            entrenamiento_data: Dict con id_entrenamiento, collection_name, etc.

        Returns:
            Lista con evento de polling si el envío fue exitoso.
        """
        from adapters.api_client import send_autonomous_training_to_trainer

        # Construir payload
        payload = {
            "id_organizacion": entrenamiento_data.get("id_organizacion", 0),
            "id_proyecto": entrenamiento_data.get("id_proyecto", 0),
            "id_version": entrenamiento_data.get("id_version", 0),
            "id_entrenamiento": entrenamiento_data.get("id_entrenamiento", 0),
            "pat_version": entrenamiento_data.get("pat_version", ""),
            "collection_name": entrenamiento_data.get("collection_name", ""),
        }

        print(f"[AUTONOMOUS] Enviando entrenamiento autónomo: {payload}")

        try:
            result = send_autonomous_training_to_trainer(
                payload=payload,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if result.get("success"):
                print(f"[AUTONOMOUS] ✅ Entrenamiento autónomo iniciado")
                print(f"[AUTONOMOUS] training_mode: {result.get('training_mode')}")
                print(f"[AUTONOMOUS] id_entrenamiento: {result.get('id_entrenamiento')}")

                # Inicializar panel de evolución para entrenamiento autónomo
                self._ent_evo_init_autonomous(entrenamiento_data, result.get("training_mode", "simulation"))

                print(f"[AUTONOMOUS] Panel de evolución autónomo inicializado")
                print(f"[AUTONOMOUS] 🔄 Iniciando polling...")

                # Iniciar polling automático para evoluciones autónomas
                return [type(self).ent_poll_autonomous_progress]
            else:
                print(f"[AUTONOMOUS] ❌ Error: {result.get('message')}")
                self.ent_send_error = result.get("message", "Error desconocido")
        except Exception as exc:
            print(f"[AUTONOMOUS] ❌ Excepción: {exc}")
            self.ent_send_error = f"Error de comunicación: {str(exc)}"

        return []

    def _ent_evo_init_autonomous(self, entrenamiento_data: dict, training_mode: str):
        """Inicializa el panel de evolución para entrenamiento autónomo.

        Define las 20 subfases autónomas (6.1-9.5) según el training_mode.

        Args:
            entrenamiento_data: Datos del entrenamiento RAG previo
            training_mode: simulation, test o production
        """
        self.ent_evo_active = True
        self.ent_evo_org_name = entrenamiento_data.get("organization_name", "")
        self.ent_evo_project_name = entrenamiento_data.get("proyecto_nombre", "")
        self.ent_evo_version_label = entrenamiento_data.get("version_display", "")
        self.ent_evo_id_entrenamiento = entrenamiento_data.get("id_entrenamiento", 0)
        self.ent_evo_can_cancel = False  # No se puede cancelar el autónomo
        self.ent_evo_cancelling = False
        self.ent_evo_current_phase = "6.1"
        self.ent_evo_current_phase_name = "Analizar chunks disponibles"
        self.ent_evo_is_autonomous = True  # Flag para distinguir de RAG normal
        self.ent_evo_training_mode = training_mode

        # Estructura de fases autónomas (6-9)
        phases = [
            {
                "key": "6",
                "nombre": "Dataset",
                "emoji": "📝",
                "color": "#ec4899",
                "status": "in_progress",
                "tiempo": "",
                "descripcion": "Generación de dataset para fine-tuning",
                "subfases": [
                    {"key": "6.1", "nombre": "Analizar chunks disponibles", "status": "in_progress", "tiempo": ""},
                    {"key": "6.2", "nombre": "Generar plantillas de preguntas", "status": "pending", "tiempo": ""},
                    {"key": "6.3", "nombre": "Generar Q&A con LLM", "status": "pending", "tiempo": ""},
                    {"key": "6.4", "nombre": "Validar y formatear dataset", "status": "pending", "tiempo": ""},
                    {"key": "6.5", "nombre": "Guardar dataset", "status": "pending", "tiempo": ""},
                ]
            },
        ]

        # Agregar fases 7-8-9 solo si NO es simulation
        if training_mode != "simulation":
            phases.extend([
                {
                    "key": "7",
                    "nombre": "Preparación LoRA",
                    "emoji": "🔧",
                    "color": "#f59e0b",
                    "status": "pending",
                    "tiempo": "",
                    "descripcion": "Preparación del entorno para fine-tuning",
                    "subfases": [
                        {"key": "7.1", "nombre": "Verificar dependencias", "status": "pending", "tiempo": ""},
                        {"key": "7.2", "nombre": "Obtener modelo base", "status": "pending", "tiempo": ""},
                        {"key": "7.3", "nombre": "Configurar parámetros LoRA", "status": "pending", "tiempo": ""},
                        {"key": "7.4", "nombre": "Preparar entorno", "status": "pending", "tiempo": ""},
                    ]
                },
                {
                    "key": "8",
                    "nombre": "Entrenamiento LoRA",
                    "emoji": "🏋️",
                    "color": "#10b981",
                    "status": "pending",
                    "tiempo": "",
                    "descripcion": "Fine-tuning del modelo con LoRA",
                    "subfases": [
                        {"key": "8.1", "nombre": "Inicializar trainer", "status": "pending", "tiempo": ""},
                        {"key": "8.2", "nombre": "Entrenamiento en progreso", "status": "pending", "tiempo": ""},
                        {"key": "8.3", "nombre": "Finalizar entrenamiento", "status": "pending", "tiempo": ""},
                        {"key": "8.4", "nombre": "Evaluar modelo", "status": "pending", "tiempo": ""},
                        {"key": "8.5", "nombre": "Guardar adaptadores LoRA", "status": "pending", "tiempo": ""},
                        {"key": "8.6", "nombre": "Validar resultados", "status": "pending", "tiempo": ""},
                    ]
                },
                {
                    "key": "9",
                    "nombre": "Exportación GGUF",
                    "emoji": "📦",
                    "color": "#8b5cf6",
                    "status": "pending",
                    "tiempo": "",
                    "descripcion": "Exportación y empaquetado del modelo",
                    "subfases": [
                        {"key": "9.1", "nombre": "Merge LoRA con modelo base", "status": "pending", "tiempo": ""},
                        {"key": "9.2", "nombre": "Convertir a GGUF", "status": "pending", "tiempo": ""},
                        {"key": "9.3", "nombre": "Crear Modelfile", "status": "pending", "tiempo": ""},
                        {"key": "9.4", "nombre": "Generar README", "status": "pending", "tiempo": ""},
                        {"key": "9.5", "nombre": "Empaquetar entregable", "status": "pending", "tiempo": ""},
                    ]
                },
            ])

        self.ent_evo_phases = phases

    async def ent_poll_autonomous_progress(self) -> AsyncGenerator[None, None]:
        """Polling de progreso para entrenamiento autónomo.

        Consulta las evoluciones autónomas (subfases 6.1-9.5) cada 2 segundos.
        """
        import asyncio
        from adapters.api_client import get_autonomous_training_progress

        if not self.ent_evo_id_entrenamiento or not self.ent_evo_active:
            return

        print(f"[AUTONOMOUS POLLING] Iniciando polling para entrenamiento {self.ent_evo_id_entrenamiento}")

        max_iterations = 18000  # 10 horas máximo (18000 * 2s = 36000s = 10h)
        iteration = 0

        while iteration < max_iterations and self.ent_evo_active:
            try:
                # Consultar progreso de subfases autónomas
                result = get_autonomous_training_progress(
                    id_entrenamiento=self.ent_evo_id_entrenamiento,
                    access_token=self.access_token,
                    session_token=self.session_token,
                )

                if result.get("success"):
                    subfases = result.get("data", {}).get("subfases", [])

                    # Actualizar cada subfase
                    for subfase in subfases:
                        subfase_key = subfase.get("subfase_key", "")
                        status = subfase.get("status", "pending")
                        duracion = subfase.get("duracion_segundos", 0)

                        # Formatear tiempo
                        if duracion > 0:
                            if duracion < 60:
                                tiempo = f"{duracion}s"
                            else:
                                mins = duracion // 60
                                secs = duracion % 60
                                tiempo = f"{mins}m {secs}s"
                        else:
                            tiempo = ""

                        # Extraer phase_key y actualizar
                        phase_key = subfase_key.split(".")[0]
                        self.ent_evo_update_subfase(phase_key, subfase_key, status, tiempo)

                        # Actualizar fase actual si está in_progress
                        if status == "in_progress":
                            self.ent_evo_current_phase = subfase_key
                            self.ent_evo_current_phase_name = subfase.get("subfase_name", "")

                    # Verificar si todas las subfases están completadas
                    all_completed = all(sf.get("status") == "completed" for sf in subfases)
                    if all_completed and subfases:
                        print(f"[AUTONOMOUS POLLING] ✅ Todas las subfases completadas")
                        self.ent_evo_complete_all()
                        self.ent_evo_active = False
                        yield
                        break

                    yield

            except Exception as exc:
                print(f"[AUTONOMOUS POLLING] ❌ Error: {exc}")

            await asyncio.sleep(2)
            iteration += 1

        if iteration >= max_iterations:
            print(f"[AUTONOMOUS POLLING] ⚠️ Timeout alcanzado")

    def ent_download_autonomous_package(self):
        """Descarga el paquete ZIP del modelo autónomo generado.

        Este método inicia la descarga del archivo ZIP desde el navegador.
        """
        from adapters.api_client import download_autonomous_package
        import base64

        print(f"[DOWNLOAD] Iniciando descarga para entrenamiento {self.ent_evo_id_entrenamiento}")

        try:
            # Descargar paquete desde la API
            package_bytes = download_autonomous_package(
                id_entrenamiento=self.ent_evo_id_entrenamiento,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if package_bytes:
                # Convertir a base64 para trigger download en navegador
                package_b64 = base64.b64encode(package_bytes).decode('utf-8')
                filename = f"ENT{self.ent_evo_id_entrenamiento}_modelo_autonomo.zip"

                print(f"[DOWNLOAD] Paquete descargado: {len(package_bytes)} bytes")
                print(f"[DOWNLOAD] Filename: {filename}")

                # Usar rx.download para trigger la descarga
                return rx.download(
                    data=package_b64,
                    filename=filename,
                )
            else:
                print(f"[DOWNLOAD] ❌ Error: No se pudo obtener el paquete")
                return rx.toast.error(
                    "No se pudo descargar el paquete",
                    position="bottom-right",
                    duration=5000,
                )

        except Exception as exc:
            print(f"[DOWNLOAD] ❌ Excepción: {exc}")
            return rx.toast.error(
                f"Error descargando paquete: {str(exc)}",
                position="bottom-right",
                duration=5000,
            )

    # ========================================================================
    # PÁGINA DE DESCARGAS - Gestión de descargas de paquetes GGUF
    # ========================================================================

    def dl_set_otp_code(self, code: str):
        """Establece el código OTP ingresado."""
        self.dl_otp_code = code

    def dl_request_otp(self):
        """Solicita código OTP para validar identidad."""
        from adapters.api_client import request_login_otp

        self.dl_otp_loading = True
        self.dl_otp_error = ""

        # Usar el username y password de la sesión actual
        # Para simplificar, reutilizamos el sistema de login
        response = request_login_otp(self.user_email, "")  # El password no es necesario aquí

        self.dl_otp_loading = False

        if response.get("success"):
            yield rx.toast.success(
                "Código OTP enviado por SMS",
                position="bottom-right",
                duration=3000,
            )
        else:
            self.dl_otp_error = "No se pudo enviar el código OTP"
            yield rx.toast.error(
                "No se pudo enviar el código OTP",
                position="bottom-right",
                duration=5000,
            )

    def dl_validate_otp(self):
        """Valida el código OTP ingresado."""
        from adapters.api_client import validate_login_otp

        if not self.dl_otp_code:
            self.dl_otp_error = "Debe ingresar el código OTP"
            return

        self.dl_otp_loading = True
        self.dl_otp_error = ""

        # Validar OTP con el backend
        response = validate_login_otp(self.user_email, self.dl_otp_code)

        self.dl_otp_loading = False

        if response.get("success"):
            self.dl_otp_validated = True
            self.dl_otp_code = ""

            # Cargar organizaciones disponibles según asignaciones
            yield self.dl_load_organizations()

            yield rx.toast.success(
                "Código OTP validado correctamente",
                position="bottom-right",
                duration=3000,
            )
        else:
            self.dl_otp_error = "Código OTP inválido"
            yield rx.toast.error(
                "Código OTP inválido",
                position="bottom-right",
                duration=5000,
            )

    def dl_init_page(self):
        """Inicializa la página de Descargas cargando organizaciones si es necesario."""
        print(f"[DL] dl_init_page called, dl_organizations len={len(self.dl_organizations)}, user_id={self.user_id}")
        # En backoffice siempre cargar organizaciones (sin OTP requerido)
        if len(self.dl_organizations) == 0:
            self.dl_load_organizations()

    def dl_load_organizations(self):
        """Carga las organizaciones disponibles según asignaciones del usuario."""
        print(f"[DL] dl_load_organizations user_id={self.user_id} identity_type_id={self.identity_type_id} session_org_id={self.organization_id}")
        try:
            orgs, default_id = load_organizations_for_selector(
                user_id=self.user_id,
                identity_type_id=self.identity_type_id,
                session_org_id=self.organization_id,
            )
            self.dl_organizations = orgs
            print(f"[DL] orgs loaded: {len(orgs)}, default_id={default_id}")
            for o in orgs:
                print(f"[DL]   org: {o}")

            # Auto-seleccionar si solo hay una organización
            if len(self.dl_organizations) == 1:
                self.dl_selected_org_id = self.dl_organizations[0]["id"]
                self.dl_selected_org_name = self.dl_organizations[0].get("name", "")
                print(f"[DL] auto-select single org: id={self.dl_selected_org_id} name={self.dl_selected_org_name}")
                self.dl_load_projects()
            elif default_id > 0:
                for org in self.dl_organizations:
                    if org.get("id") == default_id:
                        self.dl_selected_org_id = default_id
                        self.dl_selected_org_name = org.get("name", "")
                        print(f"[DL] auto-select default org: id={self.dl_selected_org_id} name={self.dl_selected_org_name}")
                        self.dl_load_projects()
                        break
            else:
                print(f"[DL] no auto-select (orgs={len(self.dl_organizations)}, default_id={default_id})")

        except Exception as exc:
            print(f"[DL] ERROR cargando orgs: {exc}")
            import traceback
            traceback.print_exc()
            self.dl_error = "Error cargando organizaciones"

    def dl_set_selected_org(self, org_name: str):
        """Establece la organización seleccionada por nombre y carga sus proyectos."""
        print(f"[DL] dl_set_selected_org org_name={org_name}")
        self.dl_selected_org_name = org_name
        self.dl_selected_project_name = ""
        self.dl_selected_version_name = ""

        # Buscar el ID correspondiente al nombre
        org_id = 0
        for org in self.dl_organizations:
            if org.get("name") == org_name:
                org_id = org.get("id", 0)
                break

        self.dl_selected_org_id = org_id
        self.dl_selected_project_id = 0
        self.dl_selected_version_id = 0
        self.dl_projects = []
        self.dl_versions = []
        self.dl_packages = []
        print(f"[DL] org_id={org_id}, calling dl_load_projects")

        if self.dl_selected_org_id > 0:
            self.dl_load_projects()

    def dl_load_projects(self):
        """Carga los proyectos de la organización seleccionada."""
        print(f"[DL] dl_load_projects org_id={self.dl_selected_org_id}")
        if self.dl_selected_org_id == 0:
            return

        try:
            projects, default_id = load_projects_for_selector(
                user_id=self.user_id,
                identity_type_id=self.identity_type_id,
                organization_id=self.dl_selected_org_id,
            )
            self.dl_projects = projects
            print(f"[DL] projects loaded: {len(projects)}, default_id={default_id}")
            for p in projects:
                print(f"[DL]   project: {p}")

            # Auto-seleccionar si solo hay un proyecto
            if len(self.dl_projects) == 1:
                self.dl_selected_project_id = self.dl_projects[0]["id"]
                self.dl_selected_project_name = self.dl_projects[0].get("name", "")
                self.dl_load_versions()
            elif default_id > 0:
                for prj in self.dl_projects:
                    if prj.get("id") == default_id:
                        self.dl_selected_project_id = default_id
                        self.dl_selected_project_name = prj.get("name", "")
                        self.dl_load_versions()
                        break

        except Exception as exc:
            print(f"[DL] ERROR cargando proyectos: {exc}")
            import traceback
            traceback.print_exc()
            self.dl_error = "Error cargando proyectos"

    def dl_set_selected_project(self, project_name: str):
        """Establece el proyecto seleccionado por nombre y carga sus versiones."""
        print(f"[DL] dl_set_selected_project project_name={project_name}")
        self.dl_selected_project_name = project_name
        self.dl_selected_version_name = ""

        # Buscar el ID correspondiente al nombre
        project_id = 0
        for proj in self.dl_projects:
            if proj.get("name") == project_name:
                project_id = proj.get("id", 0)
                break

        self.dl_selected_project_id = project_id
        self.dl_selected_version_id = 0
        self.dl_versions = []
        self.dl_packages = []

        if self.dl_selected_project_id > 0:
            return self.dl_load_versions()

    def dl_load_versions(self):
        """Carga las versiones del proyecto seleccionado."""
        print(f"[DL] dl_load_versions project_id={self.dl_selected_project_id} org_id={self.dl_selected_org_id}")
        if self.dl_selected_project_id == 0:
            return

        try:
            versions, default_id = load_versions_for_selector(
                organization_id=self.dl_selected_org_id,
                project_id=self.dl_selected_project_id,
            )
            # Mapear al formato esperado por dl_version_options (clave "nombre") y dl_set_selected_version (clave "id")
            self.dl_versions = [
                {
                    "id": v.get("version_id", 0),
                    "nombre": f"v{v.get('version_id', 0):03d}",
                }
                for v in versions
                if v.get("version_id", 0) > 0
            ]

        except Exception as exc:
            print(f"[DOWNLOAD] Error cargando versiones: {exc}")
            self.dl_error = "Error cargando versiones"

    def dl_set_selected_version(self, version_name: str):
        """Establece la versión seleccionada por nombre y carga sus paquetes."""
        self.dl_selected_version_name = version_name

        # Buscar el ID correspondiente al nombre
        version_id = 0
        for ver in self.dl_versions:
            if ver.get("nombre") == version_name:
                version_id = ver.get("id", 0)
                break

        self.dl_selected_version_id = version_id
        self.dl_packages = []

        if self.dl_selected_version_id > 0:
            return self.dl_load_packages()

    def dl_load_packages(self):
        """Carga los paquetes disponibles escaneando el sistema de archivos.

        Usa el endpoint /models/list del middleware que escanea las carpetas
        internal/ORG*/PRJ*/v*/*.zip y filtra por proyecto y versión seleccionados.
        """
        from adapters.api_client import list_models_from_filesystem
        from datetime import datetime

        self.dl_loading_packages = True
        self.dl_error = ""
        self.dl_packages = []

        try:
            response = list_models_from_filesystem(
                organization_id=self.dl_selected_org_id if self.dl_selected_org_id > 0 else None,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            self.dl_loading_packages = False

            if response.get("success"):
                models = response.get("models", [])

                # Filtrar por proyecto y versión seleccionados
                filtered = []
                for m in models:
                    if self.dl_selected_project_id > 0:
                        if m.get("project_id", 0) != self.dl_selected_project_id:
                            continue
                    if self.dl_selected_version_id > 0:
                        if m.get("version_id", 0) != self.dl_selected_version_id:
                            continue
                    filtered.append(m)

                # Mapear al formato PackageDict esperado por la UI
                packages = []
                for idx, m in enumerate(filtered):
                    created_ts = m.get("created_at", 0)
                    if isinstance(created_ts, (int, float)) and created_ts > 0:
                        gen_date = datetime.fromtimestamp(created_ts).strftime("%Y-%m-%d %H:%M")
                    else:
                        gen_date = "—"

                    size_mb = 0.0
                    raw_size = m.get("file_size_mb", "0")
                    try:
                        size_mb = float(raw_size)
                    except (ValueError, TypeError):
                        size_mb = 0.0

                    packages.append({
                        "id_entrenamiento": idx + 1,
                        "package_filename": m.get("filename", "modelo.zip"),
                        "training_mode": "production",
                        "created_at": gen_date,
                        "file_size_mb": size_mb,
                        "ollama_model_name": m.get("filename", "").replace(".zip", ""),
                        "gguf_quantization": "n/a",
                        "package_size_mb": size_mb,
                        "dataset_size": 0,
                        "package_generated_at": gen_date,
                        # Campos extra para la descarga por fichero
                        "_relative_path": m.get("relative_path", ""),
                        "_organization_id": m.get("organization_id", 0),
                        "_project_id": m.get("project_id", 0),
                        "_version_id": m.get("version_id", 0),
                    })

                self.dl_packages = packages

                if len(self.dl_packages) == 0:
                    yield rx.toast.info(
                        "No se encontraron paquetes disponibles",
                        position="bottom-right",
                        duration=3000,
                    )
            else:
                self.dl_error = response.get("detail", response.get("error", "Error cargando paquetes"))
                yield rx.toast.error(
                    f"Error cargando paquetes: {self.dl_error}",
                    position="bottom-right",
                    duration=5000,
                )

        except Exception as exc:
            print(f"[DOWNLOAD] Error cargando paquetes: {exc}")
            self.dl_loading_packages = False
            self.dl_error = f"Error: {str(exc)}"
            yield rx.toast.error(
                f"Error cargando paquetes: {str(exc)}",
                position="bottom-right",
                duration=5000,
            )

    def dl_download_package(self, id_entrenamiento: int):
        """Abre el modal OTP para verificar identidad antes de descargar.

        Solo accesible para SuperAdmin (1) y Admin Organización (2).
        """
        # Validación de seguridad
        if self.identity_type_id not in (1, 2):
            return rx.toast.error(
                "No tiene permisos para descargar modelos",
                position="bottom-right",
                duration=5000,
            )

        # Buscar paquete
        pkg = None
        for p in self.dl_packages:
            if p.get("id_entrenamiento") == id_entrenamiento:
                pkg = p
                break

        if not pkg:
            return rx.toast.error(
                "Paquete no encontrado en la lista",
                position="bottom-right",
                duration=5000,
            )

        # Guardar el ID del paquete y abrir modal OTP
        self.dl_otp_pkg_id = id_entrenamiento
        self.dl_otp_code = ""
        self.dl_otp_requested = False
        self.dl_otp_error = ""
        self.dl_otp_phone = ""
        self.dl_show_otp_modal = True

    def dl_close_otp_modal(self):
        """Cierra el modal OTP de descarga."""
        self.dl_show_otp_modal = False
        self.dl_otp_code = ""
        self.dl_otp_requested = False
        self.dl_otp_error = ""
        self.dl_otp_phone = ""
        self.dl_otp_pkg_id = 0

    def dl_request_otp(self):
        """Solicita OTP vía SMS para autorizar la descarga del modelo.

        Flujo:
        1. Llama al middleware para obtener OTP y teléfono del usuario
        2. Envía el SMS directamente a Infobip con el OTP
        3. Muestra confirmación al usuario
        """
        from adapters.api_client import request_model_download_otp

        self.dl_otp_error = ""

        org_id = self.dl_selected_org_id
        prj_id = self.dl_selected_project_id
        ver_id = self.dl_selected_version_id

        try:
            # Paso 1: Obtener OTP y teléfono del middleware
            result = request_model_download_otp(
                organization_id=org_id,
                project_id=prj_id,
                version_id=ver_id,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if not result.get("success"):
                self.dl_otp_error = result.get("message", "Error al solicitar OTP")
                return

            otp = result.get("otp", "")
            phone_number = result.get("phone_number", "")
            phone_masked = result.get("phone_masked", "")

            if not otp or not phone_number:
                self.dl_otp_error = "No se pudieron obtener los datos de OTP"
                return

            # Paso 2: Enviar SMS directamente a Infobip
            if _send_message_by_sms is None:
                self.dl_otp_error = "Función de envío de SMS no disponible"
                return

            sms_sent = _send_message_by_sms(otp, phone_number)
            if sms_sent:
                self.dl_otp_requested = True
                self.dl_otp_phone = phone_masked or ("***" + phone_number[-3:] if len(phone_number) >= 3 else "***")
                return rx.toast.success(
                    f"Código OTP enviado a {self.dl_otp_phone}",
                    position="bottom-right",
                    duration=5000,
                )
            else:
                self.dl_otp_error = "No se pudo enviar el SMS. Intente de nuevo."

        except Exception as exc:
            self.dl_otp_error = f"Error: {str(exc)}"

    def dl_validate_otp_and_download(self):
        """Valida el OTP y descarga el modelo si es correcto."""
        import base64
        from adapters.api_client import (
            download_model_direct,
            validate_model_download_otp,
        )

        self.dl_otp_error = ""

        if not self.dl_otp_code or len(self.dl_otp_code.strip()) < 4:
            self.dl_otp_error = "Introduzca el código OTP recibido"
            return

        org_id = self.dl_selected_org_id
        prj_id = self.dl_selected_project_id
        ver_id = self.dl_selected_version_id

        try:
            # Validar OTP en el middleware
            result = validate_model_download_otp(
                organization_id=org_id,
                project_id=prj_id,
                version_id=ver_id,
                otp=self.dl_otp_code.strip(),
                access_token=self.access_token,
                session_token=self.session_token,
            )

            if not result.get("success"):
                self.dl_otp_error = result.get("message", "OTP incorrecto")
                return

            # Extraer download_token de la validación
            download_token = result.get("download_token", "")
            if not download_token:
                self.dl_otp_error = "No se obtuvo token de descarga"
                return

            # OTP validado - proceder con la descarga
            self.dl_downloading = True

            # Buscar paquete
            pkg = None
            for p in self.dl_packages:
                if p.get("id_entrenamiento") == self.dl_otp_pkg_id:
                    pkg = p
                    break

            if not pkg:
                self.dl_downloading = False
                self.dl_otp_error = "Paquete no encontrado"
                return

            filename = pkg.get("package_filename", "modelo.zip")

            package_bytes = download_model_direct(
                download_token=download_token,
                filename=filename,
                access_token=self.access_token,
                session_token=self.session_token,
            )

            self.dl_downloading = False
            self.dl_show_otp_modal = False

            if package_bytes:
                file_b64 = base64.b64encode(package_bytes).decode("utf-8")
                return rx.download(
                    data=file_b64,
                    filename=filename,
                )
            else:
                return rx.toast.error(
                    "No se pudo descargar el paquete",
                    position="bottom-right",
                    duration=5000,
                )

        except Exception as exc:
            self.dl_downloading = False
            self.dl_otp_error = f"Error: {str(exc)}"

    # ========================================================================
    # MODAL DE JOB - Prompt Builder para Análisis de Documentación
    # ========================================================================

    @rx.var
    def ad_identidad_names(self) -> list[str]:
        """Nombres de prompts de identidades para el selector."""
        return [p["name"] for p in self.ad_prompts_identidades]

    @rx.var
    def ad_contexto_names(self) -> list[str]:
        """Nombres de prompts de contexto para el selector."""
        return [p["name"] for p in self.ad_prompts_contexto]

    @rx.var
    def ad_solicitud_names(self) -> list[str]:
        """Nombres de prompts de solicitudes para el selector."""
        return [p["name"] for p in self.ad_prompts_solicitudes]

    @rx.var
    def ad_modalidad_names(self) -> list[str]:
        """Nombres de prompts de modalidad para el selector."""
        return [p["name"] for p in self.ad_prompts_modalidad]

    def ad_open_job_modal(self, job_id: int):
        """Abre el modal con los datos del job y carga los 4 tipos de prompts.

        Si el job tiene selecciones de prompts guardadas (en configuracion),
        las restaura en los selectores y reconstruye el prompt final.
        """
        # Buscar el job
        for j in self.ad_jobs:
            if j["id"] == job_id:
                self.ad_modal_job = j
                break
        else:
            return

        # Cargar las 4 categorías de prompts
        from adapters.api_client import get_prompts

        for category, attr in [
            ("identidades", "ad_prompts_identidades"),
            ("contexto", "ad_prompts_contexto"),
            ("solicitudes", "ad_prompts_solicitudes"),
            ("modalidad", "ad_prompts_modalidad"),
        ]:
            try:
                prompts = get_prompts(
                    category=category,
                    access_token=self.access_token,
                    session_token=self.session_token,
                )
                setattr(self, attr, prompts if isinstance(prompts, list) else [])
            except Exception as e:
                print(f"[ERROR AD MODAL] cargando prompts {category}: {e}")
                setattr(self, attr, [])

        # Restaurar selecciones guardadas del job (si existen)
        saved_identidad = self.ad_modal_job.get("sel_identidad", "")
        saved_contexto = self.ad_modal_job.get("sel_contexto", "")
        saved_solicitud = self.ad_modal_job.get("sel_solicitud", "")
        saved_modalidad = self.ad_modal_job.get("sel_modalidad", "")

        # Validar que los nombres guardados existen en las listas cargadas
        identidad_names = [p.get("name", "") for p in self.ad_prompts_identidades]
        contexto_names = [p.get("name", "") for p in self.ad_prompts_contexto]
        solicitud_names = [p.get("name", "") for p in self.ad_prompts_solicitudes]
        modalidad_names = [p.get("name", "") for p in self.ad_prompts_modalidad]

        self.ad_sel_identidad = saved_identidad if saved_identidad in identidad_names else ""
        self.ad_sel_contexto = saved_contexto if saved_contexto in contexto_names else ""
        self.ad_sel_solicitud = saved_solicitud if saved_solicitud in solicitud_names else ""
        self.ad_sel_modalidad = saved_modalidad if saved_modalidad in modalidad_names else ""

        # Restaurar prompt final guardado o recomponer con las selecciones
        saved_prompt = self.ad_modal_job.get("prompt_final_guardado", "")
        if saved_prompt and (self.ad_sel_identidad or self.ad_sel_contexto
                            or self.ad_sel_solicitud or self.ad_sel_modalidad):
            self.ad_prompt_final = saved_prompt
        elif self.ad_sel_identidad or self.ad_sel_contexto or self.ad_sel_solicitud or self.ad_sel_modalidad:
            self._ad_compose_prompt()
        else:
            self.ad_prompt_final = ""

        self.ad_trainer_ack = False
        self.ad_trainer_sending = False
        self.ad_trainer_error = ""
        self.ad_modal_open = True

    def ad_close_modal(self):
        """Cierra el modal de job."""
        self.ad_modal_open = False
        self.ad_modal_job = {}
        self.ad_prompt_final = ""
        self.ad_trainer_ack = False
        self.ad_trainer_sending = False
        self.ad_trainer_error = ""

    def _ad_find_prompt_text(self, prompts_list: list[dict], name: str) -> str:
        """Busca el texto del prompt por nombre en una lista."""
        for p in prompts_list:
            if p.get("name") == name:
                return p.get("prompt", "")
        return ""

    def _ad_build_work_path(self) -> str:
        """Construye la ruta de trabajo: base_storage/ORG.../PRJ.../v..."""
        base = get_env_value(
            "backend_ia_base_storage",
            "~/data/anewhope/files/trainer_server/external",
        )
        org_folder = get_folder_by_id_organization(self.ad_org_id)
        prj_folder = get_folder_by_id_project(self.ad_project_id)
        ver_folder = get_folder_by_id_version(self.ad_version_id)
        return f"{base}/{org_folder}/{prj_folder}/{ver_folder}"

    def _ad_compose_prompt(self):
        """Compone el prompt final concatenando los 4 prompts seleccionados."""
        parts: list[str] = []

        # 1. Identidad
        if self.ad_sel_identidad:
            txt = self._ad_find_prompt_text(self.ad_prompts_identidades, self.ad_sel_identidad)
            if txt:
                parts.append(txt)

        # 2. Contexto + ruta de trabajo
        if self.ad_sel_contexto:
            txt = self._ad_find_prompt_text(self.ad_prompts_contexto, self.ad_sel_contexto)
            if txt:
                work_path = self._ad_build_work_path()
                parts.append(f"{txt} .Teniendo en cuenta que la ruta de trabajo es {work_path} .")

        # 3. Solicitudes
        if self.ad_sel_solicitud:
            txt = self._ad_find_prompt_text(self.ad_prompts_solicitudes, self.ad_sel_solicitud)
            if txt:
                parts.append(txt)

        # 4. Modalidad
        if self.ad_sel_modalidad:
            txt = self._ad_find_prompt_text(self.ad_prompts_modalidad, self.ad_sel_modalidad)
            if txt:
                parts.append(txt)

        self.ad_prompt_final = "\n".join(parts)

    def ad_set_sel_identidad(self, name: str):
        """Selecciona un prompt de identidades y recompone."""
        self.ad_sel_identidad = name
        self._ad_compose_prompt()

    def ad_set_sel_contexto(self, name: str):
        """Selecciona un prompt de contexto y recompone."""
        self.ad_sel_contexto = name
        self._ad_compose_prompt()

    def ad_set_sel_solicitud(self, name: str):
        """Selecciona un prompt de solicitudes y recompone."""
        self.ad_sel_solicitud = name
        self._ad_compose_prompt()

    def ad_set_sel_modalidad(self, name: str):
        """Selecciona un prompt de modalidad y recompone."""
        self.ad_sel_modalidad = name
        self._ad_compose_prompt()

    def _is_metadatos_job(self) -> bool:
        """Detecta si el job actual es de análisis de metadatos.

        Condiciones: el nombre del job contiene "metadatos" (case-insensitive)
        Y el prompt final contiene múltiples referencias a "metadatos".

        Returns:
            True si el job es de metadatos, False si es de documentación
        """
        nombre_job = self.ad_modal_job.get("nombre", "").lower()
        prompt_lower = self.ad_prompt_final.lower()

        nombre_tiene_metadatos = "metadatos" in nombre_job
        # Consideramos "múltiples referencias" como 2 o más ocurrencias en el prompt
        prompt_menciones = prompt_lower.count("metadatos")

        return nombre_tiene_metadatos and prompt_menciones >= 2

    def _ad_save_prompt_config(self):
        """Persiste las selecciones de prompts y el prompt final en el campo configuracion del job."""
        import json as _json

        job_id = self.ad_modal_job.get("id", 0)
        if job_id <= 0:
            return

        config_data = {
            "sel_identidad": self.ad_sel_identidad,
            "sel_contexto": self.ad_sel_contexto,
            "sel_solicitud": self.ad_sel_solicitud,
            "sel_modalidad": self.ad_sel_modalidad,
            "prompt_final": self.ad_prompt_final,
        }
        try:
            engine = self._get_projects_writer_engine()
            with engine.begin() as conn:
                conn.execute(text(
                    "UPDATE jobs SET configuracion = :config WHERE id = :job_id"
                ), {"config": _json.dumps(config_data, ensure_ascii=False), "job_id": job_id})
        except Exception as e:
            print(f"[ERROR AD] Guardando configuracion de prompts: {e}")

    def ad_send_to_trainer(self):
        """Envía los datos del modal al endpoint apropiado del trainer.

        Detecta automáticamente si el job es de metadatos o documentación
        y enruta al endpoint correspondiente:
        - /metadatos: si el nombre del job contiene "metadatos" y el prompt
          tiene múltiples referencias a "metadatos"
        - /documentacion: para el resto de jobs de análisis documental
        """
        from adapters.api_client import (
            send_documentacion_to_trainer,
            send_metadatos_to_trainer,
        )

        if not self.ad_prompt_final.strip():
            self.ad_trainer_error = "El prompt final está vacío. Seleccione al menos un prompt."
            return

        self.ad_trainer_sending = True
        self.ad_trainer_error = ""
        self.ad_trainer_ack = False

        # Persistir selecciones de prompts en la BD antes de enviar
        self._ad_save_prompt_config()

        payload = {
            "id_job": self.ad_modal_job.get("id", 0),
            "id_organizacion": self.ad_org_id,
            "id_proyecto": self.ad_project_id,
            "id_version": self.ad_version_id,
            "nombre_job": self.ad_modal_job.get("nombre", ""),
            "descripcion_job": self.ad_modal_job.get("descripcion", ""),
            "id_template": self.ad_modal_job.get("id_template", 0),
            "template_nombre": self.ad_modal_job.get("template_nombre", ""),
            "modelo_nombre": self.ad_modal_job.get("modelo_nombre", ""),
            "salida_nombre": self.ad_modal_job.get("salida_nombre", ""),
            "estado_nombre": self.ad_modal_job.get("estado_nombre", ""),
            "prompt_final": self.ad_prompt_final,
        }

        try:
            # Detección automática: metadatos vs documentación
            if self._is_metadatos_job():
                result = send_metadatos_to_trainer(
                    payload=payload,
                    access_token=self.access_token,
                    session_token=self.session_token,
                )
            else:
                result = send_documentacion_to_trainer(
                    payload=payload,
                    access_token=self.access_token,
                    session_token=self.session_token,
                )
            if result.get("success"):
                self.ad_trainer_ack = True
                self.ad_trainer_error = ""
            else:
                self.ad_trainer_error = result.get("message", "Error desconocido del trainer")
        except Exception as e:
            self.ad_trainer_error = f"Error de comunicación: {str(e)}"
        finally:
            self.ad_trainer_sending = False


def load_presentation_content() -> str:
    """Carga el contenido de presentación desde un archivo markdown externo."""
    try:
        # Obtiene la ruta de presentation.md relativa a este archivo
        current_dir = Path(__file__).parent.parent
        presentation_file = current_dir / "presentation.md"
        with open(presentation_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    except (FileNotFoundError, IOError):
        # Fallback al archivo .txt si no existe el .md
        try:
            current_dir = Path(__file__).parent.parent
            presentation_file = current_dir / "presentation.txt"
            with open(presentation_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        except (FileNotFoundError, IOError):
            # Contenido por defecto si ninguno existe
            return (
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
                "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."
            )


def load_menu_content(filename: str, fallback_text: str) -> str:
    """Carga contenido de un archivo .md o .txt del menú con fallback.
    
    Intenta cargar primero la versión .md, luego .txt.
    """

    try:
        current_dir = Path(__file__).parent.parent
        
        # Intentar cargar versión .md primero
        md_filename = filename.replace(".txt", ".md")
        md_file = current_dir / md_filename
        if md_file.exists():
            with open(md_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        
        # Fallback a .txt
        content_file = current_dir / filename
        with open(content_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    except (FileNotFoundError, IOError):
        # Contenido por defecto si el archivo no existe
        return fallback_text


def logo() -> rx.Component:
    """Logo component."""
    return rx.hstack(
        rx.text("MY", font_weight="bold", font_size="1.8em", color=COLORS["primary"]),
        rx.text("llm", font_size="1.8em", color=COLORS["foreground"]),
        spacing="1",
    )


def login_panel() -> rx.Component:
    """Login panel for user portal."""
    return rx.vstack(
            rx.text("Acceso de Usuario", font_size="1.3em", font_weight="bold", color=COLORS["foreground"]),
            rx.vstack(
                rx.vstack(
                    rx.text("Usuario", font_size="1.1em", color=COLORS["muted_foreground"]),
                    rx.input(
                        placeholder="Ingrese su usuario",
                        on_change=State.set_user_username,
                        value=State.user_username,
                        background_color=COLORS["input"],
                        border_color=COLORS["border"],
                        color=COLORS["foreground"],
                        font_size="1.05em",
                        width="100%",
                        border_radius="5px",
                    ),
                    spacing="1",
                ),
                rx.vstack(
                    rx.text("Contraseña", font_size="1.1em", color=COLORS["muted_foreground"]),
                    rx.input(
                        placeholder="Ingrese su contraseña",
                        type_="password",
                        on_change=State.set_user_password,
                        value=State.user_password,
                        background_color=COLORS["input"],
                        border_color=COLORS["border"],
                        color=COLORS["foreground"],
                        font_size="1.05em",
                        width="100%",
                        border_radius="5px",
                    ),
                    spacing="1",
                ),
                rx.text(
                    "Solicitar código OTP",
                    on_click=State.request_login_otp,
                    color=COLORS["primary"],
                    width="100%",
                    text_align="left",
                    font_size="1.1em",
                    cursor="pointer",
                    _hover={"text_decoration": "underline"},
                ),
                rx.vstack(
                    rx.text("OTP", font_size="1.1em", color=COLORS["muted_foreground"]),
                    rx.input(
                        placeholder="Ingrese su OTP",
                        on_change=State.set_user_otp,
                        value=State.user_otp,
                        background_color=COLORS["input"],
                        border_color=COLORS["border"],
                        color=COLORS["foreground"],
                        font_size="1.05em",
                        width="100%",
                        border_radius="5px",
                    ),
                    spacing="1",
                ),
                spacing="2",
            ),
            rx.box(
                "Iniciar Sesión",
                on_click=State.user_login,
                background_color=COLORS["primary"],
                color="black",
                width="100%",
                font_weight="bold",
                font_size="1.1em",
                padding="0.6em",
                border_radius="0.5em",
                text_align="center",
                cursor="pointer",
                _hover={"opacity": "0.9"},
            ),
            rx.text(
                State.login_error,
                color="red",
                font_size="1.0em",
                display=rx.cond(State.login_error != "", "block", "none"),
            ),
            rx.text(
                State.otp_request_message,
                color=COLORS["muted_foreground"],
                font_size="1.0em",
                display=rx.cond(State.otp_request_message != "", "block", "none"),
            ),
            rx.vstack(
                rx.link(
                    "Crear nuevo usuario",
                    color=COLORS["primary"],
                    href="/user_creation?from=main",
                    font_size="1.1em",
                ),
                rx.link("Recordar contraseña", color=COLORS["primary"], href="/change_password?from=main", font_size="1.1em"),
                spacing="1",
            ),
            spacing="2",
            padding="1.5em",
            background_color=COLORS["card"],
            border=f"1px solid {COLORS['border']}",
            border_radius="0.5em",
            width="100%",
        )


def sidebar_menu(is_logged_in: bool) -> rx.Component:
    """Sidebar menu for navigation."""
    menu_items = rx.cond(
        is_logged_in,
        [
            "organizacion",
            "tecnologias",
            "proyecciones",
            "seguimiento",
            "informes",
            "flujos",
            "descargas",
        ],
        ["inicio", "servicios", "proyectos", "soporte", "contacto"],
    )
    
    return rx.vstack(
            rx.text("Menú", font_size="1.3em", font_weight="bold", color=COLORS["foreground"], margin_bottom="1em"),
            rx.vstack(
                rx.foreach(
                    menu_items,
                    lambda item: rx.box(
                        item.title(),
                        on_click=lambda _, i=item: State.set_user_menu(i),
                        background_color=rx.cond(
                            (State.user_active_menu == item) & (State.internal_active_menu == ""),
                            COLORS["primary"],
                            "transparent"
                        ),
                        color=rx.cond(
                            (State.user_active_menu == item) & (State.internal_active_menu == ""),
                            "white",
                            COLORS["foreground"]
                        ),
                        width="100%",
                        padding="0.75em",
                        border_radius="0.5em",
                        cursor="pointer",
                        text_align="left",
                        font_size="1.1em",
                        font_weight="bold",
                        _hover={"opacity": "0.8"},
                    ),
                ),
                spacing="1",
                align_items="flex-start",
                width="100%",
            ),
            align_items="flex-start",
            width="100%",
        )


def internal_menu(is_logged_in: bool) -> rx.Component:
    """Internal tools menu (only visible when logged in)."""
    internal_items = [
        "asignaciones",
        "estado_proyectos",
        "analisis_documentacion",
        "entrenamientos",
        "analisis_resultados",
        "crear_llm",
        "asistente",
    ]

    return rx.cond(
        is_logged_in,
        rx.vstack(
            rx.text(
                "Internal",
                font_size="1.3em",
                font_weight="bold",
                color=COLORS["foreground"],
                margin_top="2em",
                margin_bottom="1em"
            ),
            rx.vstack(
                rx.foreach(
                    internal_items,
                    lambda item: rx.cond(
                        # Si es "asignaciones", solo mostrar si identity_type_id == 1
                        item == "asignaciones",
                        rx.cond(
                            State.identity_type_id == 1,
                            rx.box(
                                rx.match(
                                    item,
                                    ("crear_llm", "Sistema"),
                                    item.replace("_", " ").title(),
                                ),
                                on_click=lambda _, i=item: State.set_internal_menu(i),
                                background_color=rx.cond(
                                    State.internal_active_menu == item,
                                    COLORS["primary"],
                                    "transparent"
                                ),
                                color=rx.cond(
                                    State.internal_active_menu == item,
                                    "white",
                                    COLORS["foreground"]
                                ),
                                width="100%",
                                padding="0.75em",
                                border_radius="0.5em",
                                cursor="pointer",
                                text_align="left",
                                font_size="1.1em",
                                font_weight="bold",
                                _hover={"opacity": "0.8"},
                            ),
                            rx.fragment(),  # No mostrar nada si no es super admin
                        ),
                        # Para cualquier otro item, siempre mostrar
                        rx.box(
                            rx.match(
                                item,
                                ("crear_llm", "Sistema"),
                                item.replace("_", " ").title(),
                            ),
                            on_click=lambda _, i=item: State.set_internal_menu(i),
                            background_color=rx.cond(
                                State.internal_active_menu == item,
                                COLORS["primary"],
                                "transparent"
                            ),
                            color=rx.cond(
                                State.internal_active_menu == item,
                                "white",
                                COLORS["foreground"]
                            ),
                            width="100%",
                            padding="0.75em",
                            border_radius="0.5em",
                            cursor="pointer",
                            text_align="left",
                            font_size="1.1em",
                            font_weight="bold",
                            _hover={"opacity": "0.8"},
                        ),
                    ),
                ),
                spacing="1",
                align_items="flex-start",
                width="100%",
            ),
            align_items="flex-start",
            width="100%",
        ),
        rx.fragment(),
    )


def user_action_button(icon: str, tooltip: str, on_click, color: str = COLORS["muted_foreground"]) -> rx.Component:
    """Botón de acción con icono y tooltip."""
    return rx.tooltip(
        rx.icon_button(
            rx.icon(icon, size=22),
            variant="ghost",
            size="2",
            color_scheme="yellow",
            cursor="pointer",
            on_click=on_click,
            _hover={"color": COLORS["primary"], "background_color": COLORS["border"]},
        ),
        content=tooltip,
    )


def user_row(user: dict) -> rx.Component:
    """Fila de usuario con acciones.
    
    Muestra solo el user_name pero usa user_id internamente para las acciones.
    Estructura esperada: {"user_id": int, "user_name": str, "active": bool}
    
    Nota: En Reflex, para pasar argumentos dinámicos desde rx.foreach,
    se usa el formato State.method(var) sin lambda.
    
    SEGURIDAD: Los botones de acción solo se muestran si el usuario actual
    tiene permisos de gestión (identity_type_id in 1, 2, 10).
    Ver: State.can_manage_org_users
    """
    return rx.hstack(
        # Información del usuario a la izquierda (solo muestra user_name)
        rx.hstack(
            rx.text(user["user_name"], font_weight="bold", font_size="1.1em", color=COLORS["foreground"]),
            # Badge de estado (Activo/Inactivo)
            rx.cond(
                user["active"],
                rx.badge("Activo", color_scheme="green", variant="soft", size="3"),
                rx.badge("Inactivo", color_scheme="red", variant="soft", size="3"),
            ),
            # Badge de "Staff" si es usuario interno
            rx.cond(
                user.get("is_internal", False),
                rx.badge("Staff", color_scheme="blue", variant="solid", size="3"),
                rx.fragment(),
            ),
            spacing="3",
            align="center",
        ),
        # Acciones a la derecha (usan user_id internamente)
        # SEGURIDAD: Solo se muestran si el usuario tiene permisos de gestión
        # (identity_type_id in 1, 2, 10 - SuperAdmin, Admin Org, Agente Admin)
        # Para usuarios internos (Staff), solo se muestran botones de asignación
        rx.cond(
            State.can_manage_org_users,
            rx.hstack(
                # Botones de gestión (enable/disable/delete) solo para usuarios NO internos
                rx.cond(
                    ~user.get("is_internal", False),
                    rx.hstack(
                        rx.tooltip(
                            rx.icon_button(
                                rx.icon("user-round-check", size=22),
                                variant="ghost",
                                size="2",
                                color_scheme="green",
                                cursor="pointer",
                                on_click=State.enable_user(user["user_id"]),
                                _hover={"color": "#22c55e", "background_color": COLORS["border"]},
                            ),
                            content="Habilitar usuario",
                        ),
                        rx.tooltip(
                            rx.icon_button(
                                rx.icon("user-round-x", size=22),
                                variant="ghost",
                                size="2",
                                color_scheme="red",
                                cursor="pointer",
                                on_click=State.disable_user(user["user_id"]),
                                _hover={"color": "#ef4444", "background_color": COLORS["border"]},
                            ),
                            content="Deshabilitar usuario",
                        ),
                        rx.tooltip(
                            rx.icon_button(
                                rx.icon("trash-2", size=22),
                                variant="ghost",
                                size="2",
                                color_scheme="yellow",
                                cursor="pointer",
                                on_click=State.delete_user(user["user_id"]),
                                _hover={"color": COLORS["primary"], "background_color": COLORS["border"]},
                            ),
                            content="Borrar usuario",
                        ),
                        spacing="1",
                    ),
                    rx.fragment(),
                ),
                # Botones de asignación de proyectos (siempre visibles para todos los usuarios)
                rx.tooltip(
                    rx.icon_button(
                        rx.icon("folder-plus", size=22),
                        variant="ghost",
                        size="2",
                        color_scheme="yellow",
                        cursor="pointer",
                        on_click=State.assign_user_to_projects(user["user_id"]),
                        _hover={"color": COLORS["primary"], "background_color": COLORS["border"]},
                    ),
                    content="Asignar usuario a proyectos",
                ),
                rx.tooltip(
                    rx.icon_button(
                        rx.icon("folder-minus", size=22),
                        variant="ghost",
                        size="2",
                        color_scheme="yellow",
                        cursor="pointer",
                        on_click=State.remove_user_from_projects(user["user_id"]),
                        _hover={"color": COLORS["primary"], "background_color": COLORS["border"]},
                    ),
                    content="Quitar usuario de proyectos",
                ),
                spacing="1",
            ),
            rx.fragment(),  # No mostrar botones si no tiene permisos
        ),
        justify="between",
        align="center",
        width="100%",
        padding="0.75em",
        background_color=COLORS["card"],
        border=f"1px solid {COLORS['border']}",
        border_radius="0.5em",
    )


def create_user_modal() -> rx.Component:
    """Modal para crear un nuevo usuario de la organización."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                rx.hstack(
                    rx.icon("user-plus", size=24, color=COLORS["primary"]),
                    rx.text("Crear Nuevo Usuario", font_weight="bold", font_size="1.3em"),
                    spacing="3",
                    align="center",
                ),
            ),
            rx.dialog.description(
                rx.text(
                    "Complete los datos del nuevo usuario de la organización.",
                    color=COLORS["muted_foreground"],
                    font_size="0.95em",
                ),
            ),
            rx.vstack(
                # Campo: Nombre de usuario
                rx.vstack(
                    rx.text("Nombre de usuario", font_weight="bold", color=COLORS["foreground"]),
                    rx.input(
                        placeholder="Ingrese el nombre de usuario",
                        value=State.new_user_name,
                        on_change=State.set_new_user_name,
                        width="100%",
                        background_color=COLORS["input"],
                        color=COLORS["foreground"],
                        border=f"1px solid {COLORS['border']}",
                    ),
                    width="100%",
                    spacing="1",
                    align_items="flex-start",
                ),
                # Campo: Correo electrónico
                rx.vstack(
                    rx.text("Correo electrónico", font_weight="bold", color=COLORS["foreground"]),
                    rx.input(
                        placeholder="correo@ejemplo.com",
                        value=State.new_user_email,
                        on_change=State.set_new_user_email,
                        type="email",
                        width="100%",
                        background_color=COLORS["input"],
                        color=COLORS["foreground"],
                        border=f"1px solid {COLORS['border']}",
                    ),
                    width="100%",
                    spacing="1",
                    align_items="flex-start",
                ),
                # Campo: Teléfono
                rx.vstack(
                    rx.text("Teléfono móvil", font_weight="bold", color=COLORS["foreground"]),
                    rx.input(
                        placeholder="+34 600 000 000",
                        value=State.new_user_mobile,
                        on_change=State.set_new_user_mobile,
                        type="tel",
                        width="100%",
                        background_color=COLORS["input"],
                        color=COLORS["foreground"],
                        border=f"1px solid {COLORS['border']}",
                    ),
                    width="100%",
                    spacing="1",
                    align_items="flex-start",
                ),
                # Mensaje de error
                rx.cond(
                    State.create_user_error != "",
                    rx.text(
                        State.create_user_error,
                        color="red",
                        font_size="0.9em",
                    ),
                ),
                # Mensaje de éxito
                rx.cond(
                    State.create_user_success != "",
                    rx.text(
                        State.create_user_success,
                        color=COLORS["primary"],
                        font_size="0.9em",
                        font_weight="bold",
                    ),
                ),
                width="100%",
                spacing="3",
                padding_y="1em",
            ),
            # Botones de acción
            rx.hstack(
                rx.button(
                    rx.icon("x", size=18, color=COLORS["foreground"]),
                    rx.text("Salir", color=COLORS["foreground"]),
                    on_click=State.close_create_user_modal,
                    variant="outline",
                    size="3",
                    color_scheme="gray",
                ),
                rx.button(
                    rx.cond(
                        State.is_creating_user,
                        rx.spinner(size="2"),
                        rx.icon("save", size=18, color="black"),
                    ),
                    rx.text("Guardar", font_weight="bold", color="black"),
                    on_click=State.save_new_user,
                    background_color=COLORS["primary"],
                    size="3",
                    disabled=State.is_creating_user,
                    _hover={"background_color": "#e67e00", "cursor": "pointer"},
                ),
                spacing="3",
                justify="end",
                width="100%",
            ),
            background_color=COLORS["card"],
            border=f"1px solid {COLORS['border']}",
            padding="1.5em",
            max_width="450px",
        ),
        open=State.show_create_user_modal,
    )


def assign_user_to_project_modal() -> rx.Component:
    """Modal para asignar un usuario a un proyecto."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                rx.hstack(
                    rx.icon("user-check", size=24, color=COLORS["primary"]),
                    rx.text("Asignar Usuario a Proyecto", font_weight="bold", font_size="1.3em"),
                    spacing="3",
                    align="center",
                ),
            ),
            rx.dialog.description(
                rx.text(
                    f"Asignar usuario '{State.assign_user_name}' a un proyecto con un rol específico.",
                    color=COLORS["muted_foreground"],
                    font_size="0.95em",
                ),
            ),
            rx.vstack(
                # Selector de proyecto
                rx.vstack(
                    rx.text("Proyecto", font_weight="bold", color=COLORS["foreground"]),
                    rx.select(
                        State.assign_project_names,
                        placeholder="Seleccione un proyecto",
                        on_change=State.set_assign_project,
                        width="100%",
                        size="3",
                        style={
                            "backgroundColor": COLORS["input"],
                            "color": COLORS["foreground"],
                            "borderColor": COLORS["border"],
                        },
                    ),
                    width="100%",
                    spacing="1",
                    align_items="flex-start",
                ),
                # Selector de rol
                rx.vstack(
                    rx.text("Rol", font_weight="bold", color=COLORS["foreground"]),
                    rx.select(
                        State.assign_role_names,
                        placeholder="Seleccione un rol",
                        on_change=State.set_assign_role,
                        width="100%",
                        size="3",
                        style={
                            "backgroundColor": COLORS["input"],
                            "color": COLORS["foreground"],
                            "borderColor": COLORS["border"],
                        },
                    ),
                    width="100%",
                    spacing="1",
                    align_items="flex-start",
                ),
                # Mensaje de error
                rx.cond(
                    State.assign_error != "",
                    rx.text(
                        State.assign_error,
                        color="red",
                        font_size="0.9em",
                    ),
                ),
                # Mensaje de éxito
                rx.cond(
                    State.assign_success != "",
                    rx.text(
                        State.assign_success,
                        color="green",
                        font_size="0.9em",
                    ),
                ),
                # Botones
                rx.hstack(
                    rx.dialog.close(
                        rx.button(
                            "Cancelar",
                            variant="soft",
                            color_scheme="gray",
                            on_click=State.close_assign_user_modal,
                        ),
                    ),
                    rx.button(
                        "Asignar",
                        on_click=State.confirm_assign_user,
                        background_color=COLORS["primary"],
                        color="black",
                        _hover={"background_color": "#e67e00"},
                    ),
                    spacing="3",
                    justify="end",
                    width="100%",
                ),
                spacing="4",
                width="100%",
            ),
            background_color=COLORS["card"],
            border=f"1px solid {COLORS['border']}",
            padding="1.5em",
            max_width="450px",
        ),
        open=State.show_assign_user_modal,
    )


def create_project_modal() -> rx.Component:
    """Modal para crear un nuevo proyecto."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                rx.hstack(
                    rx.icon("folder-plus", size=24, color=COLORS["primary"]),
                    rx.text("Crear Nuevo Proyecto", font_weight="bold", font_size="1.3em"),
                    spacing="3",
                    align="center",
                ),
            ),
            rx.dialog.description(
                rx.text(
                    "Complete los datos del nuevo proyecto. Se creará automáticamente con el estado 'Propuesta Cliente'.",
                    color=COLORS["muted_foreground"],
                    font_size="0.95em",
                ),
            ),
            rx.vstack(
                # Campo: Nombre del proyecto
                rx.vstack(
                    rx.text("Nombre del proyecto", font_weight="bold", color=COLORS["foreground"]),
                    rx.input(
                        placeholder="Ingrese el nombre del proyecto",
                        value=State.new_project_name,
                        on_change=State.set_new_project_name,
                        width="100%",
                        background_color=COLORS["input"],
                        color=COLORS["foreground"],
                        border=f"1px solid {COLORS['border']}",
                    ),
                    width="100%",
                    spacing="1",
                    align_items="flex-start",
                ),
                # Campo: Descripción
                rx.vstack(
                    rx.text("Descripción (opcional)", font_weight="bold", color=COLORS["foreground"]),
                    rx.text_area(
                        placeholder="Descripción del proyecto",
                        value=State.new_project_description,
                        on_change=State.set_new_project_description,
                        width="100%",
                        min_height="100px",
                        background_color=COLORS["input"],
                        color=COLORS["foreground"],
                        border=f"1px solid {COLORS['border']}",
                    ),
                    width="100%",
                    spacing="1",
                    align_items="flex-start",
                ),
                # Mensaje de error
                rx.cond(
                    State.create_project_error != "",
                    rx.text(
                        State.create_project_error,
                        color="red",
                        font_size="0.9em",
                    ),
                ),
                # Mensaje de éxito
                rx.cond(
                    State.create_project_success != "",
                    rx.text(
                        State.create_project_success,
                        color=COLORS["primary"],
                        font_size="0.9em",
                        font_weight="bold",
                    ),
                ),
                width="100%",
                spacing="3",
                padding_y="1em",
            ),
            # Botones de acción
            rx.hstack(
                rx.button(
                    rx.icon("x", size=18, color=COLORS["foreground"]),
                    rx.text("Cancelar", color=COLORS["foreground"]),
                    on_click=State.close_create_project_modal,
                    variant="outline",
                    size="3",
                    color_scheme="gray",
                ),
                rx.button(
                    rx.cond(
                        State.is_creating_project,
                        rx.spinner(size="2"),
                        rx.icon("save", size=18, color="black"),
                    ),
                    rx.text("Guardar", font_weight="bold", color="black"),
                    on_click=State.save_new_project,
                    background_color=COLORS["primary"],
                    size="3",
                    disabled=State.is_creating_project,
                    _hover={"background_color": "#e67e00", "cursor": "pointer"},
                ),
                spacing="3",
                justify="end",
                width="100%",
            ),
            background_color=COLORS["card"],
            border=f"1px solid {COLORS['border']}",
            padding="1.5em",
            max_width="500px",
        ),
        open=State.show_create_project_modal,
    )


def users_management_panel() -> rx.Component:
    """Panel de gestión de usuarios de la organización."""
    return rx.vstack(
        # Modal de creación de usuario
        create_user_modal(),
        # Modal de asignación de usuario a proyecto
        assign_user_to_project_modal(),
        rx.hstack(
            rx.icon("users", size=28, color=COLORS["primary"]),
            rx.heading("Gestión de Usuarios", size="6", color=COLORS["primary"]),
            spacing="3",
            align="center",
        ),
        # SEGURIDAD: Solo mostrar si el usuario tiene permiso user_create
        rx.cond(
            State.can_user_create,
            rx.button(
                rx.icon("user-plus", size=20, color="black"),
                rx.text("Crear usuario", font_weight="bold", color="black"),
                on_click=State.create_user,
                background_color=COLORS["primary"],
                size="3",
                _hover={"background_color": "#e67e00", "cursor": "pointer"},
            ),
            rx.fragment(),
        ),
        rx.vstack(
            rx.foreach(
                State.org_users,
                user_row,
            ),
            width="100%",
            spacing="2",
        ),
        width="100%",
        padding="1.5em",
        background_color=COLORS["card"],
        border=f"1px solid {COLORS['border']}",
        border_radius="0.5em",
        spacing="3",
        align_items="flex-start",
    )


def project_row(project: dict) -> rx.Component:
    """Fila de proyecto con acciones.
    
    Estados del proyecto:
    - existe=False: Borrado (rojo) - máxima prioridad visual
    - active=False: Bloqueado (naranja)
    - active=True y existe=True: Activo (verde)
    """
    return rx.hstack(
        # Información del proyecto a la izquierda
        rx.hstack(
            rx.text(project["name"], font_weight="bold", font_size="1.1em", color=COLORS["foreground"]),
            # Badge de estado: Borrado > Bloqueado > Activo
            rx.cond(
                ~project["existe"],  # Si existe=False → Borrado
                rx.badge("Borrado", color_scheme="red", variant="soft", size="3"),
                rx.cond(
                    project["active"],  # Si active=True → Activo
                    rx.badge("Activo", color_scheme="green", variant="soft", size="3"),
                    rx.badge("Bloqueado", color_scheme="orange", variant="soft", size="3"),
                ),
            ),
            spacing="3",
            align="center",
        ),
        # Acciones a la derecha
        rx.hstack(
            # Recuperar proyecto (verde) - solo para proyectos borrados
            rx.tooltip(
                rx.icon_button(
                    rx.icon("archive-restore", size=22),
                    variant="ghost",
                    size="2",
                    color_scheme="green",
                    cursor="pointer",
                    on_click=State.restore_project(project["id"]),
                    _hover={"color": "#22c55e", "background_color": COLORS["border"]},
                ),
                content="Recuperar proyecto",
            ),
            # Desbloquear proyecto (verde) - activa el proyecto
            rx.tooltip(
                rx.icon_button(
                    rx.icon("lock-open", size=22),
                    variant="ghost",
                    size="2",
                    color_scheme="green",
                    cursor="pointer",
                    on_click=State.unlock_project(project["id"]),
                    _hover={"color": "#22c55e", "background_color": COLORS["border"]},
                ),
                content="Desbloquear proyecto",
            ),
            # Bloquear proyecto (naranja) - desactiva el proyecto
            rx.tooltip(
                rx.icon_button(
                    rx.icon("lock", size=22),
                    variant="ghost",
                    size="2",
                    color_scheme="orange",
                    cursor="pointer",
                    on_click=State.lock_project(project["id"]),
                    _hover={"color": "#f97316", "background_color": COLORS["border"]},
                ),
                content="Bloquear proyecto",
            ),
            # Borrar proyecto (rojo) - borrado lógico
            rx.tooltip(
                rx.icon_button(
                    rx.icon("trash-2", size=22),
                    variant="ghost",
                    size="2",
                    color_scheme="red",
                    cursor="pointer",
                    on_click=State.delete_project(project["id"]),
                    _hover={"color": "#ef4444", "background_color": COLORS["border"]},
                ),
                content="Borrar proyecto",
            ),
            # Solicitud de soporte
            rx.tooltip(
                rx.icon_button(
                    rx.icon("headset", size=22),
                    variant="ghost",
                    size="2",
                    color_scheme="yellow",
                    cursor="pointer",
                    on_click=State.request_project_support(project["id"]),
                    _hover={"color": COLORS["primary"], "background_color": COLORS["border"]},
                ),
                content="Solicitud de soporte",
            ),
            spacing="1",
        ),
        justify="between",
        align="center",
        width="100%",
        padding="0.75em",
        background_color=COLORS["card"],
        border=f"1px solid {COLORS['border']}",
        border_radius="0.5em",
    )


def support_ticket_modal() -> rx.Component:
    """Modal para crear un ticket de soporte desde un proyecto."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                rx.hstack(
                    rx.icon("headset", size=24, color=COLORS["primary"]),
                    rx.text("Solicitud de Soporte", font_weight="bold", font_size="1.3em"),
                    spacing="3",
                    align="center",
                ),
            ),
            rx.dialog.description(
                rx.text(
                    "Crear ticket de soporte",
                    color=COLORS["muted_foreground"],
                    font_size="0.9em",
                ),
            ),
            rx.vstack(
                # Proyecto asociado (informativo)
                rx.cond(
                    State.support_project_name != "",
                    rx.hstack(
                        rx.text("Proyecto:", font_weight="bold", color=COLORS["foreground"]),
                        rx.badge(State.support_project_name, color_scheme="blue", variant="soft"),
                        spacing="2",
                        align="center",
                    ),
                ),
                # Campo motivo
                rx.vstack(
                    rx.text("Motivo *", font_weight="bold", color=COLORS["foreground"]),
                    rx.input(
                        value=State.support_titulo,
                        on_change=State.set_support_titulo,
                        placeholder="Describe brevemente el motivo de la consulta",
                        width="100%",
                        background_color=COLORS["input"],
                        color=COLORS["foreground"],
                        border=f"1px solid {COLORS['border']}",
                    ),
                    width="100%",
                    spacing="1",
                    align_items="flex-start",
                ),
                # Campo consulta
                rx.vstack(
                    rx.text("Consulta *", font_weight="bold", color=COLORS["foreground"]),
                    rx.text_area(
                        value=State.support_consulta,
                        on_change=State.set_support_consulta,
                        placeholder="Describe detalladamente tu consulta o problema...",
                        width="100%",
                        min_height="120px",
                        background_color=COLORS["input"],
                        color=COLORS["foreground"],
                        border=f"1px solid {COLORS['border']}",
                    ),
                    width="100%",
                    spacing="1",
                    align_items="flex-start",
                ),
                # Info: Estado y prioridad automáticos
                rx.hstack(
                    rx.badge("Estado: Abierto", color_scheme="green", variant="soft"),
                    rx.badge("Prioridad: Media", color_scheme="yellow", variant="soft"),
                    spacing="2",
                    align="center",
                ),
                rx.text(
                    "El equipo de soporte revisará tu consulta lo antes posible.",
                    color=COLORS["muted_foreground"],
                    font_size="0.85em",
                    font_style="italic",
                ),
                # Mensaje de error
                rx.cond(
                    State.support_error != "",
                    rx.text(State.support_error, color="red", font_size="0.9em"),
                ),
                # Mensaje de éxito
                rx.cond(
                    State.support_success != "",
                    rx.text(State.support_success, color=COLORS["primary"], font_size="0.9em", font_weight="bold"),
                ),
                width="100%",
                spacing="3",
                padding_y="1em",
            ),
            # Botones de acción
            rx.hstack(
                rx.button(
                    rx.icon("x", size=18, color=COLORS["foreground"]),
                    rx.text("Cancelar", color=COLORS["foreground"]),
                    on_click=State.close_support_modal,
                    variant="outline",
                    size="3",
                    color_scheme="gray",
                ),
                rx.button(
                    rx.cond(
                        State.is_creating_support,
                        rx.spinner(size="2"),
                        rx.icon("send", size=18, color="black"),
                    ),
                    rx.text("Enviar", font_weight="bold", color="black"),
                    on_click=State.save_support_ticket,
                    disabled=State.is_creating_support,
                    color_scheme="green",
                    variant="solid",
                    size="3",
                ),
                spacing="3",
                justify="end",
                width="100%",
            ),
            background_color=COLORS["card"],
            border=f"1px solid {COLORS['border']}",
            padding="1.5em",
            max_width="550px",
        ),
        open=State.show_support_modal,
    )


def projects_management_panel() -> rx.Component:
    """Panel de gestión de proyectos de la organización."""
    return rx.vstack(
        # Modal de creación de proyecto
        create_project_modal(),
        # Modal de solicitud de soporte
        support_ticket_modal(),
        rx.hstack(
            rx.icon("folder-kanban", size=28, color=COLORS["primary"]),
            rx.heading("Gestión de Proyectos", size="6", color=COLORS["primary"]),
            spacing="3",
            align="center",
        ),
        # SEGURIDAD: Solo mostrar si el usuario tiene permiso project_create
        rx.cond(
            State.can_project_create,
            rx.button(
                rx.icon("folder-plus", size=20, color="black"),
                rx.text("Crear proyecto", font_weight="bold", color="black"),
                on_click=State.create_project,
                color_scheme="orange",
                variant="solid",
                size="3",
            ),
            rx.fragment(),
        ),
        rx.vstack(
            rx.foreach(
                State.org_projects,
                project_row,
            ),
            width="100%",
            spacing="2",
        ),
        width="100%",
        padding="1.5em",
        background_color=COLORS["card"],
        border=f"1px solid {COLORS['border']}",
        border_radius="0.5em",
        spacing="3",
        align_items="flex-start",
    )


def ticket_row(ticket: dict) -> rx.Component:
    """Fila de ticket con acciones."""
    return rx.hstack(
        # Información del ticket a la izquierda
        rx.vstack(
            rx.hstack(
                rx.text(f"#{ticket['id']}", font_weight="bold", color=COLORS["muted_foreground"]),
                rx.text(ticket["titulo"], font_weight="bold", font_size="1.05em", color=COLORS["foreground"]),
                spacing="2",
            ),
            rx.hstack(
                rx.badge(
                    ticket["estado"],
                    color_scheme=rx.match(
                        ticket["estado"],
                        ("abierto", "blue"),
                        ("en_espera", "amber"),
                        ("resuelto", "green"),
                        ("cerrado", "gray"),
                        "gray",
                    ),
                    variant="solid",
                    size="2",
                    style={"fontSize": "14px", "padding": "6px 12px", "fontWeight": "600", "color": "black"},
                ),
                rx.badge(
                    ticket["prioridad"],
                    color_scheme=rx.match(
                        ticket["prioridad"],
                        ("baja", "gray"),
                        ("media", "cyan"),
                        ("alta", "orange"),
                        ("urgente", "red"),
                        "gray",
                    ),
                    variant="solid",
                    size="2",
                    style={"fontSize": "14px", "padding": "6px 12px", "fontWeight": "600", "color": "black"},
                ),
                rx.cond(
                    ticket.get("respuesta", "") != "",
                    rx.badge("Con respuesta", color_scheme="blue", variant="outline", size="2"),
                    rx.badge("Sin respuesta", color_scheme="gray", variant="outline", size="2"),
                ),
                spacing="2",
            ),
            spacing="1",
            align_items="flex-start",
        ),
        # Botón gestionar a la derecha
        rx.tooltip(
            rx.icon_button(
                rx.icon("pencil", size=20),
                variant="ghost",
                size="2",
                color_scheme="blue",
                cursor="pointer",
                on_click=State.open_ticket_modal(ticket["id"]),
                _hover={"color": COLORS["primary"], "background_color": COLORS["border"]},
            ),
            content="Gestionar ticket",
        ),
        justify="between",
        align="center",
        width="100%",
        padding="0.75em",
        background_color=COLORS["card"],
        border=f"1px solid {COLORS['border']}",
        border_radius="0.5em",
    )


def ticket_management_modal() -> rx.Component:
    """Modal para gestionar un ticket de soporte."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                rx.hstack(
                    rx.icon("headset", size=24, color=COLORS["primary"]),
                    rx.text("Gestión de Ticket", font_weight="bold", font_size="1.3em"),
                    spacing="3",
                    align="center",
                ),
            ),
            # Información del ticket
            rx.vstack(
                # Título
                rx.hstack(
                    rx.text("Motivo:", font_weight="bold", color=COLORS["muted_foreground"]),
                    rx.text(State.selected_ticket_titulo, color=COLORS["foreground"]),
                    spacing="2",
                ),
                # Consulta (solo lectura)
                rx.vstack(
                    rx.text("Consulta del cliente:", font_weight="bold", color=COLORS["muted_foreground"]),
                    rx.box(
                        rx.text(State.selected_ticket_consulta, color=COLORS["foreground"]),
                        padding="0.75em",
                        background_color=COLORS["input"],
                        border=f"1px solid {COLORS['border']}",
                        border_radius="0.25em",
                        width="100%",
                        max_height="100px",
                        overflow_y="auto",
                    ),
                    width="100%",
                    spacing="1",
                    align_items="flex-start",
                ),
                # Selectores de estado y prioridad
                rx.hstack(
                    rx.vstack(
                        rx.text("Estado", font_weight="bold", color=COLORS["primary"], font_size="1.1em"),
                        rx.select(
                            ["abierto", "en_espera", "resuelto", "cerrado"],
                            value=State.selected_ticket_estado,
                            on_change=State.set_ticket_estado,
                            width="150px",
                            size="3",
                            background_color=COLORS["input"],
                            color=COLORS["foreground"],
                            border_color=COLORS["border"],
                        ),
                        spacing="1",
                        align_items="flex-start",
                    ),
                    rx.vstack(
                        rx.text("Prioridad", font_weight="bold", color=COLORS["primary"], font_size="1.1em"),
                        rx.select(
                            ["baja", "media", "alta", "urgente"],
                            value=State.selected_ticket_prioridad,
                            on_change=State.set_ticket_prioridad,
                            width="150px",
                            size="3",
                            background_color=COLORS["input"],
                            color=COLORS["foreground"],
                            border_color=COLORS["border"],
                        ),
                        spacing="1",
                        align_items="flex-start",
                    ),
                    spacing="4",
                ),
                # Campo de respuesta
                rx.vstack(
                    rx.text("Respuesta", font_weight="bold", color=COLORS["foreground"]),
                    rx.text_area(
                        value=State.selected_ticket_respuesta,
                        on_change=State.set_ticket_respuesta,
                        placeholder="Escribe tu respuesta al cliente...",
                        width="100%",
                        min_height="100px",
                        background_color=COLORS["input"],
                        color=COLORS["foreground"],
                        border=f"1px solid {COLORS['border']}",
                    ),
                    width="100%",
                    spacing="1",
                    align_items="flex-start",
                ),
                # Mensajes de error/éxito
                rx.cond(
                    State.ticket_modal_error != "",
                    rx.text(State.ticket_modal_error, color="red", font_size="0.9em"),
                ),
                rx.cond(
                    State.ticket_modal_success != "",
                    rx.text(State.ticket_modal_success, color="green", font_size="0.9em"),
                ),
                # Botones
                rx.hstack(
                    rx.button(
                        "Cancelar",
                        on_click=State.close_ticket_modal,
                        color_scheme="gray",
                        variant="outline",
                    ),
                    rx.button(
                        "Guardar Estado",
                        on_click=State.save_ticket_changes,
                        color_scheme="blue",
                        disabled=State.is_updating_ticket,
                    ),
                    rx.button(
                        "Enviar Respuesta",
                        on_click=State.save_ticket_response,
                        color_scheme="green",
                        style={"font_weight": "bold", "color": "black"},
                        disabled=State.is_updating_ticket,
                    ),
                    spacing="2",
                    justify="end",
                    width="100%",
                ),
                width="100%",
                spacing="3",
                padding="1em",
            ),
            max_width="500px",
            background_color=COLORS["card"],
        ),
        open=State.show_ticket_modal,
    )


def tickets_management_panel() -> rx.Component:
    """Panel de gestión de tickets de soporte."""
    return rx.vstack(
        rx.hstack(
            rx.icon("headset", size=28, color=COLORS["primary"]),
            rx.heading("Gestión de Tickets", size="6", color=COLORS["primary"]),
            spacing="3",
            align="center",
        ),
        rx.text(
            "Tickets de soporte de la organización",
            color=COLORS["muted_foreground"],
            font_size="0.9em",
        ),
        # Modal de gestión de ticket
        ticket_management_modal(),
        # Lista de tickets
        rx.cond(
            State.org_tickets.length() > 0,
            rx.vstack(
                rx.foreach(
                    State.org_tickets,
                    ticket_row,
                ),
                width="100%",
                spacing="2",
            ),
            rx.text(
                "No hay tickets de soporte",
                color=COLORS["muted_foreground"],
                font_style="italic",
                padding="1em",
            ),
        ),
        width="100%",
        padding="1.5em",
        background_color=COLORS["card"],
        border=f"1px solid {COLORS['border']}",
        border_radius="0.5em",
        spacing="3",
        align_items="flex-start",
    )


def org_project_assignment_row(assignment: dict) -> rx.Component:
    """Fila de asignación de proyecto (solo lectura)."""
    return rx.hstack(
        rx.hstack(
            rx.icon("folder", size=18, color=COLORS["primary"]),
            rx.text(
                assignment["proyecto_nombre"],
                font_weight="bold",
                color=COLORS["foreground"],
                font_size="1em",
            ),
            spacing="2",
            align="center",
            width="35%",
        ),
        rx.hstack(
            rx.icon("user", size=18, color=COLORS["muted_foreground"]),
            rx.text(
                assignment["usuario_nombre"],
                color=COLORS["foreground"],
                font_size="0.95em",
            ),
            spacing="2",
            align="center",
            width="35%",
        ),
        rx.badge(
            assignment["rol_nombre"],
            color_scheme=rx.cond(
                assignment["rol_nombre"] == "Editor",
                "blue",
                rx.cond(
                    assignment["rol_nombre"] == "Lector",
                    "green",
                    "orange",
                ),
            ),
            size="2",
        ),
        width="100%",
        padding="0.75em 1em",
        background_color=COLORS["input"],
        border_radius="0.5em",
        justify="between",
        align="center",
    )


def org_project_assignments_panel() -> rx.Component:
    """Panel de asignaciones de usuarios a proyectos (solo lectura)."""
    return rx.vstack(
        rx.hstack(
            rx.icon("users-round", size=28, color=COLORS["primary"]),
            rx.heading("Asignaciones de Proyectos", size="6", color=COLORS["primary"]),
            rx.spacer(),
            rx.button(
                rx.hstack(
                    rx.icon("refresh-cw", size=16),
                    rx.text("Actualizar"),
                    spacing="2",
                ),
                on_click=State.load_org_project_assignments,
                size="2",
                variant="outline",
                color=COLORS["primary"],
                border_color=COLORS["primary"],
            ),
            spacing="3",
            align="center",
            width="100%",
        ),
        rx.text(
            "Vista de solo lectura - Se actualiza al asignar usuarios",
            color=COLORS["muted_foreground"],
            font_size="0.85em",
            font_style="italic",
        ),
        rx.cond(
            State.org_project_assignments.length() > 0,
            rx.vstack(
                rx.hstack(
                    rx.text("Proyecto", font_weight="bold", color=COLORS["muted_foreground"], width="35%"),
                    rx.text("Usuario", font_weight="bold", color=COLORS["muted_foreground"], width="35%"),
                    rx.text("Rol", font_weight="bold", color=COLORS["muted_foreground"]),
                    width="100%",
                    padding="0.5em 1em",
                ),
                rx.foreach(
                    State.org_project_assignments,
                    org_project_assignment_row,
                ),
                width="100%",
                spacing="2",
            ),
            rx.text(
                "No hay asignaciones de usuarios a proyectos",
                color=COLORS["muted_foreground"],
                font_style="italic",
                padding="1em",
            ),
        ),
        width="100%",
        padding="1.5em",
        background_color=COLORS["card"],
        border=f"1px solid {COLORS['border']}",
        border_radius="0.5em",
        spacing="3",
        align_items="flex-start",
    )


def organization_management_panels() -> rx.Component:
    """Paneles de gestión de usuarios, proyectos y tickets para la sección Organización."""
    return rx.vstack(
        # Selector de organización (filtrado por asignaciones)
        org_selector_bar(
            org_names=State.bo_organization_names,
            selected_org_display=State.bo_selected_org_display,
            on_org_change=State.bo_set_organization,
        ),
        users_management_panel(),
        projects_management_panel(),
        org_project_assignments_panel(),
        tickets_management_panel(),
        width="100%",
        spacing="4",
        margin_top="1.5em",
    )


def tecnologia_item(tech: dict) -> rx.Component:
    """Componente para mostrar una tecnología en la lista.
    
    En backoffice se puede cambiar la asignación en cualquier momento.
    """
    tech_id = tech.get("id", 0)
    tech_name = tech.get("name", "Sin nombre")
    tech_descripcion = tech.get("descripcion", "")
    is_active = tech.get("active", True)
    is_selected = State.selected_tecnologia_id == tech_id
    
    return rx.box(
        rx.hstack(
            # Indicador de selección (círculo naranja)
            rx.box(
                rx.cond(
                    is_selected,
                    rx.icon("check", size=20, color="white"),
                    rx.fragment(),
                ),
                width="32px",
                height="32px",
                border_radius="50%",
                border=rx.cond(
                    is_selected,
                    f"3px solid {COLORS['primary']}",
                    f"3px solid {COLORS['border']}",
                ),
                background_color=rx.cond(is_selected, COLORS["primary"], "transparent"),
                display="flex",
                align_items="center",
                justify_content="center",
                flex_shrink="0",
            ),
            rx.vstack(
                rx.text(
                    tech_name,
                    font_weight="bold",
                    font_size="1.25em",
                    color=rx.cond(is_active, COLORS["foreground"], COLORS["muted_foreground"]),
                ),
                rx.text(
                    tech_descripcion,
                    font_size="1.05em",
                    color=COLORS["muted_foreground"],
                    opacity=rx.cond(is_active, "1", "0.6"),
                ),
                spacing="2",
                align_items="flex-start",
                flex="1",
            ),
            rx.cond(
                ~is_active,
                rx.badge("Inactiva", color_scheme="gray", size="2"),
                rx.fragment(),
            ),
            spacing="4",
            align="center",
            width="100%",
        ),
        padding="1.25em",
        background=rx.cond(
            is_selected,
            f"{COLORS['primary']}20",
            COLORS["card"],
        ),
        border=rx.cond(
            is_selected,
            f"3px solid {COLORS['primary']}",
            f"2px solid {COLORS['border']}",
        ),
        border_radius="0.75em",
        opacity=rx.cond(is_active, "1", "0.5"),
        cursor=rx.cond(is_active, "pointer", "not-allowed"),
        on_click=State.select_tecnologia(tech),
        _hover=rx.cond(
            is_active,
            {"background": f"{COLORS['primary']}15"},
            {},
        ),
        width="100%",
    )


def tecnologia_asignada_row(item: dict) -> rx.Component:
    """Fila que muestra un proyecto y su tecnología asignada."""
    return rx.hstack(
        rx.text(
            item["project_name"],
            font_weight="medium",
            color=COLORS["foreground"],
            font_size="1em",
            flex="1",
        ),
        rx.cond(
            item["tecnologia_name"],
            rx.badge(
                item["tecnologia_name"],
                color_scheme="orange",
                variant="soft",
                size="2",
            ),
            rx.badge(
                "(sin asignar)",
                color_scheme="gray",
                variant="soft",
                size="2",
            ),
        ),
        width="100%",
        padding="0.75em 1em",
        background_color=COLORS["card"],
        border=f"1px solid {COLORS['border']}",
        border_radius="0.5em",
        justify="between",
        align="center",
    )


def tecnologias_asignadas_panel() -> rx.Component:
    """Panel informativo que muestra proyectos con sus tecnologías asignadas."""
    return rx.vstack(
        rx.hstack(
            rx.icon("list", size=28, color=COLORS["primary"]),
            rx.heading(
                "Tecnologías asignadas a proyecto",
                size="6",
                color=COLORS["primary"],
            ),
            spacing="3",
            align="center",
        ),
        rx.cond(
            State.tecnologias_asignadas_list.length() > 0,
            rx.vstack(
                rx.foreach(
                    State.tecnologias_asignadas_list,
                    tecnologia_asignada_row,
                ),
                width="100%",
                spacing="2",
            ),
            rx.text(
                "No hay proyectos en la organización",
                color=COLORS["muted_foreground"],
                font_size="0.95em",
            ),
        ),
        width="100%",
        padding="1.5em",
        background_color=COLORS["card"],
        border=f"1px solid {COLORS['border']}",
        border_radius="0.5em",
        spacing="3",
        align_items="flex-start",
        margin_top="1em",
    )


def tecnologias_management_panel() -> rx.Component:
    """Panel de gestión de tecnologías por proyecto.
    
    En backoffice permite cambiar la tecnología asignada en cualquier momento.
    """
    return rx.vstack(
        rx.hstack(
            rx.icon("cpu", size=36, color=COLORS["primary"]),
            rx.heading("Gestión de Tecnología", size="6", color=COLORS["primary"]),
            spacing="4",
            align_items="center",
        ),
        rx.text(
            "Selecciona un proyecto y asigna o cambia la tecnología asociada.",
            color=COLORS["muted_foreground"],
            font_size="1.1em",
        ),
        # Selector de organización (filtrado por asignaciones)
        org_selector_bar(
            org_names=State.bo_organization_names,
            selected_org_display=State.bo_selected_org_display,
            on_org_change=State.bo_set_organization,
        ),
        # Selector de proyecto
        rx.hstack(
            rx.text("Proyecto:", font_weight="bold", color=COLORS["primary"], font_size="1.1em"),
            rx.select(
                State.projects_for_tech_select,
                placeholder="Selecciona un proyecto",
                value=State.selected_tech_project_name,
                on_change=State.select_tech_project,
                width="350px",
                size="3",
                background_color=COLORS["input"],
                color=COLORS["foreground"],
                border_color=COLORS["border"],
            ),
            spacing="4",
            align_items="center",
            margin_top="1em",
        ),
        # Lista de tecnologías
        rx.cond(
            State.selected_tech_project_id > 0,
            rx.vstack(
                rx.text(
                    "Selecciona la tecnología:",
                    font_weight="bold",
                    color=COLORS["foreground"],
                    font_size="1.15em",
                    margin_top="1em",
                ),
                rx.vstack(
                    rx.foreach(
                        State.tecnologias_list,
                        tecnologia_item,
                    ),
                    width="100%",
                    spacing="3",
                ),
                # Mostrar asignación actual
                rx.cond(
                    State.proyecto_tecnologia_asignada.length() > 0,
                    rx.hstack(
                        rx.icon("circle-check", size=24, color=COLORS["primary"]),
                        rx.text(
                            "Tecnología actualmente asignada",
                            color=COLORS["primary"],
                            font_size="1.05em",
                            font_weight="500",
                        ),
                        margin_top="0.75em",
                    ),
                    rx.fragment(),
                ),
                # Botón para cambiar asignación
                rx.button(
                    rx.icon("save", size=16),
                    "Guardar cambios",
                    on_click=State.asignar_tecnologia_proyecto,
                    color_scheme="blue",
                    margin_top="1em",
                    disabled=State.selected_tecnologia_id <= 0,
                ),
                # Mensajes de estado
                rx.cond(
                    State.tech_assign_success != "",
                    rx.callout(
                        State.tech_assign_success,
                        icon="check",
                        color_scheme="green",
                        margin_top="0.5em",
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    State.tech_assign_error != "",
                    rx.callout(
                        State.tech_assign_error,
                        icon="triangle-alert",
                        color_scheme="red",
                        margin_top="0.5em",
                    ),
                    rx.fragment(),
                ),
                width="100%",
                align_items="flex-start",
            ),
            rx.text(
                "Selecciona un proyecto para ver las tecnologías disponibles.",
                color=COLORS["muted_foreground"],
                font_style="italic",
                margin_top="1em",
            ),
        ),
        width="100%",
        padding="1.5em",
        background=COLORS["card"],
        border_radius="12px",
        border=f"1px solid {COLORS['border']}",
        margin_top="1.5em",
    )


def asistente_panel() -> rx.Component:
    """Panel del Asistente IA con integración Ollama."""
    return rx.vstack(
        # Estado de Ollama
        rx.hstack(
            rx.icon("activity", size=20, color=COLORS["primary"]),
            rx.text("Estado de Ollama:", font_weight="bold", font_size="1.1em", color=COLORS["primary"]),
            rx.text(
                State.asistente_ollama_status,
                color=rx.cond(
                    State.asistente_ollama_available,
                    "#22c55e",  # Verde
                    "#ef4444",  # Rojo
                ),
                font_weight="bold",
            ),
            rx.button(
                rx.icon("refresh-cw", size=16),
                on_click=[State.check_ollama_health, State.load_ollama_models],
                size="1",
                variant="soft",
                background_color=COLORS["primary"],
                color="black",
                font_weight="bold",
                _hover={"opacity": "0.9"},
            ),
            spacing="3",
            align_items="center",
            padding="1em",
            background_color=COLORS["card"],
            border_radius="0.5em",
            border=f"2px solid {COLORS['primary']}",
            width="100%",
        ),
        # Selector de modelo
        rx.vstack(
            rx.hstack(
                rx.icon("cpu", size=20, color=COLORS["primary"]),
                rx.text("Modelo:", font_weight="bold", font_size="1.1em", color=COLORS["primary"]),
                spacing="2",
            ),
            rx.cond(
                (State.asistente_models.length() > 0) & (State.asistente_selected_model != ""),
                rx.select(
                    State.asistente_models,
                    value=State.asistente_selected_model,
                    on_change=State.set_asistente_model,
                    placeholder="Selecciona un modelo...",
                    size="3",
                    width="100%",
                ),
                rx.cond(
                    State.asistente_models.length() > 0,
                    rx.text(
                        "Cargando modelos...",
                        color=COLORS["muted_foreground"],
                        font_style="italic",
                    ),
                    rx.text(
                        "No hay modelos disponibles",
                        color=COLORS["muted_foreground"],
                        font_style="italic",
                    ),
                ),
            ),
            spacing="2",
            padding="1em",
            background_color=COLORS["card"],
            border_radius="0.5em",
            border=f"2px solid {COLORS['primary']}",
            width="100%",
        ),
        # Panel de consulta
        rx.vstack(
            rx.hstack(
                rx.icon("message-square", size=20, color=COLORS["primary"]),
                rx.text("Consulta", font_weight="bold", font_size="1.1em", color=COLORS["primary"]),
                spacing="2",
            ),
            rx.text_area(
                value=State.asistente_prompt,
                on_change=State.set_asistente_prompt,
                placeholder="Escribe tu consulta aquí...",
                size="3",
                rows="8",
                width="100%",
                style={"font-size": "1.1em", "line-height": "1.6"},
            ),
            rx.button(
                rx.cond(
                    State.asistente_is_loading,
                    rx.hstack(
                        rx.spinner(size="2"),
                        rx.text("Procesando..."),
                        spacing="2",
                    ),
                    rx.hstack(
                        rx.icon("send", size=16),
                        rx.text("Enviar consulta"),
                        spacing="2",
                    ),
                ),
                on_click=State.submit_asistente_prompt,
                disabled=State.asistente_is_loading,
                size="3",
                background_color=COLORS["primary"],
                color="white",
                width="100%",
                _hover={"opacity": "0.9"},
            ),
            spacing="2",
            padding="1em",
            background_color=COLORS["card"],
            border_radius="0.5em",
            border=f"1px solid {COLORS['border']}",
            width="100%",
        ),
        # Error (si existe)
        rx.cond(
            State.asistente_error != "",
            rx.box(
                rx.hstack(
                    rx.icon("circle-alert", size=20, color="#ef4444"),
                    rx.text(State.asistente_error, color="#ef4444"),
                    spacing="2",
                ),
                padding="1em",
                background_color="#fef2f2",
                border_radius="0.5em",
                border="1px solid #fecaca",
                width="100%",
            ),
            rx.fragment(),
        ),
        # Panel de respuesta
        rx.vstack(
            rx.hstack(
                rx.icon("message-circle", size=20, color=COLORS["primary"]),
                rx.text("Respuesta", font_weight="bold", font_size="1.1em", color=COLORS["primary"]),
                spacing="2",
            ),
            rx.cond(
                State.asistente_response != "",
                rx.box(
                    rx.markdown(State.asistente_response),
                    padding="1em",
                    background_color=COLORS["background"],
                    border_radius="0.5em",
                    width="100%",
                    min_height="200px",
                    max_height="600px",
                    overflow_y="auto",
                    style={"font-size": "1.1em", "line-height": "1.6"},
                ),
                rx.box(
                    rx.text(
                        "La respuesta aparecerá aquí...",
                        color=COLORS["muted_foreground"],
                        font_style="italic",
                        font_size="1.1em",
                    ),
                    padding="2em",
                    background_color=COLORS["background"],
                    border_radius="0.5em",
                    width="100%",
                    min_height="200px",
                ),
            ),
            spacing="2",
            padding="1em",
            background_color=COLORS["card"],
            border_radius="0.5em",
            border=f"1px solid {COLORS['border']}",
            width="100%",
        ),
        spacing="4",
        width="100%",
        align_items="flex-start",
    )


def sistema_panel() -> rx.Component:
    """Panel de Sistema con monitoreo de servicios."""

    def service_check_item(label: str, status_var, available_var, check_func) -> rx.Component:
        """Componente reutilizable para cada check de servicio."""
        return rx.hstack(
            rx.icon("activity", size=20, color=COLORS["primary"]),
            rx.text(f"{label}:", font_weight="bold", font_size="1em", color=COLORS["foreground"], min_width="180px"),
            rx.text(
                status_var,
                color=rx.cond(
                    available_var,
                    "#22c55e",  # Verde
                    "#ef4444",  # Rojo
                ),
                font_weight="bold",
                min_width="150px",
            ),
            rx.button(
                rx.icon("refresh-cw", size=16),
                on_click=check_func,
                size="1",
                variant="soft",
                background_color=COLORS["primary"],
                color="black",
                font_weight="bold",
                _hover={"opacity": "0.9"},
            ),
            spacing="3",
            align_items="center",
            padding="0.75em",
            background_color=COLORS["background"],
            border_radius="0.5em",
            width="100%",
        )

    return rx.vstack(
        # Botón para verificar todos los servicios
        rx.hstack(
            rx.text("Estado del Sistema", font_size="1.5em", font_weight="bold", color=COLORS["foreground"]),
            rx.button(
                rx.icon("refresh-cw", size=18, margin_right="0.5em"),
                "Verificar Todos",
                on_click=State.check_all_services,
                size="2",
                background_color=COLORS["primary"],
                color="black",
                font_weight="bold",
                _hover={"opacity": "0.9"},
            ),
            spacing="4",
            align_items="center",
            justify="between",
            width="100%",
            margin_bottom="1em",
        ),

        # ===== PANEL FRONTEND =====
        rx.vstack(
            rx.hstack(
                rx.icon("monitor", size=24, color=COLORS["primary"]),
                rx.text("Frontend", font_weight="bold", font_size="1.3em", color=COLORS["primary"]),
                spacing="3",
            ),
            service_check_item("Aplicación Frontend", State.sys_frontend_status, State.sys_frontend_available, State.check_frontend_service),
            service_check_item("Backoffice", State.sys_backoffice_status, State.sys_backoffice_available, State.check_backoffice_service),
            service_check_item("Middleware", State.sys_middleware_status, State.sys_middleware_available, State.check_middleware_service),
            service_check_item("Redis", State.sys_redis_status, State.sys_redis_available, State.check_redis_service),
            service_check_item("API SMS", State.sys_sms_api_status, State.sys_sms_api_available, State.check_sms_api_service),
            spacing="2",
            padding="1.5em",
            background_color=COLORS["card"],
            border_radius="0.5em",
            border=f"2px solid {COLORS['primary']}",
            width="100%",
        ),

        # ===== PANEL BACKEND =====
        rx.vstack(
            rx.hstack(
                rx.icon("server", size=24, color=COLORS["primary"]),
                rx.text("Backend", font_weight="bold", font_size="1.3em", color=COLORS["primary"]),
                spacing="3",
            ),
            service_check_item("Broker", State.sys_broker_status, State.sys_broker_available, State.check_broker_service),
            service_check_item("Backend Core", State.sys_backend_core_status, State.sys_backend_core_available, State.check_backend_core_service),
            service_check_item("fmanagement", State.sys_fmanagement_status, State.sys_fmanagement_available, State.check_fmanagement_service),
            service_check_item("MariaDB", State.sys_mariadb_status, State.sys_mariadb_available, State.check_mariadb_service),
            spacing="2",
            padding="1.5em",
            background_color=COLORS["card"],
            border_radius="0.5em",
            border=f"2px solid {COLORS['primary']}",
            width="100%",
        ),

        # ===== PANEL TRAINER =====
        rx.vstack(
            rx.hstack(
                rx.icon("cpu", size=24, color=COLORS["primary"]),
                rx.text("Trainer", font_weight="bold", font_size="1.3em", color=COLORS["primary"]),
                spacing="3",
            ),
            service_check_item("Backend IA", State.sys_trainer_status, State.sys_trainer_available, State.check_trainer_service),
            service_check_item("ChromaDB", State.sys_chromadb_status, State.sys_chromadb_available, State.check_chromadb_service),
            service_check_item("Ollama", State.sys_ollama_status, State.sys_ollama_available, State.check_ollama_service),
            spacing="2",
            padding="1.5em",
            background_color=COLORS["card"],
            border_radius="0.5em",
            border=f"2px solid {COLORS['primary']}",
            width="100%",
        ),

        spacing="3",
        width="100%",
        align_items="flex-start",
    )


def _prompts_management_tab() -> rx.Component:
    """Prompts management tab content (SuperAdmin only)."""
    return rx.vstack(
        # Category selector
        rx.text("Categoría de Prompts", font_weight="bold", color=COLORS["primary"], font_size="1.7em"),
        rx.select.root(
            rx.select.trigger(
                placeholder="Selecciona categoría...",
                style={"backgroundColor": COLORS["input"], "color": COLORS["foreground"], "borderColor": COLORS["border"]},
            ),
            rx.select.content(
                rx.select.item("Identidades", value="identidades"),
                rx.select.item("Contexto", value="contexto"),
                rx.select.item("Solicitudes", value="solicitudes"),
                rx.select.item("Modalidad", value="modalidad"),
            ),
            value=State.prompts_category,
            on_change=State.set_prompts_category,
            size="3",
            width="300px",
        ),

        # Horizontal layout: Form on left (38%), List on right (58%)
        rx.hstack(
            # Form panel (left side)
            rx.box(
                rx.vstack(
                    rx.text(
                        rx.cond(State.form_mode == "create", "Crear Nuevo Prompt", "Editar Prompt"),
                        font_weight="bold", color=COLORS["primary"], font_size="1.5em",
                    ),
                    rx.text("Nombre", color=COLORS["primary"], font_weight="bold", font_size="1.1em"),
                    rx.input(
                        placeholder="Nombre único del prompt...",
                        value=State.form_name,
                        on_change=State.set_form_name,
                        width="100%",
                    ),
                    rx.text("Descripción", color=COLORS["primary"], font_weight="bold", font_size="1.1em", margin_top="0.5em"),
                    rx.text_area(
                        placeholder="Descripción breve...",
                        value=State.form_description,
                        on_change=State.set_form_description,
                        width="100%",
                        rows="2",
                    ),
                    rx.text("Prompt", color=COLORS["primary"], font_weight="bold", font_size="1.1em", margin_top="0.5em"),
                    rx.text_area(
                        placeholder="Contenido del prompt...",
                        value=State.form_prompt,
                        on_change=State.set_form_prompt,
                        width="100%",
                        rows="10",
                    ),
                    rx.hstack(
                        rx.button(
                            rx.cond(State.form_mode == "create", "Crear", "Actualizar"),
                            on_click=State.save_prompt,
                            background_color=COLORS["primary"],
                            color="black",
                            font_weight="bold",
                        ),
                        rx.button(
                            "Cancelar",
                            on_click=State.clear_prompts_form,
                            variant="outline",
                            color="white",
                            font_weight="bold",
                        ),
                        spacing="2",
                        margin_top="1em",
                    ),
                    rx.cond(State.form_error != "", rx.callout(State.form_error, icon="circle-alert", color_scheme="red")),
                    rx.cond(State.form_success != "", rx.callout(State.form_success, icon="circle-check", color_scheme="green")),
                    spacing="2",
                ),
                padding="1.5em",
                background_color=COLORS["card"],
                border_radius="0.5em",
                border=f"1px solid {COLORS['border']}",
                width="38%",
            ),

            # Prompts list panel (right side)
            rx.box(
                rx.vstack(
                    rx.text("Prompts Guardados", font_weight="bold", color=COLORS["primary"], font_size="1.5em"),
                    rx.cond(
                        State.prompts_list.length() > 0,
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell(rx.text("Nombre", color=COLORS["primary"], font_weight="bold")),
                                    rx.table.column_header_cell(rx.text("Descripción", color=COLORS["primary"], font_weight="bold")),
                                    rx.table.column_header_cell(rx.text("Estado", color=COLORS["primary"], font_weight="bold")),
                                    rx.table.column_header_cell(rx.text("Acciones", color=COLORS["primary"], font_weight="bold")),
                                ),
                            ),
                            rx.table.body(
                                rx.foreach(
                                    State.prompts_list,
                                    lambda p: rx.table.row(
                                        rx.table.cell(rx.text(p["name"], color="white")),
                                        rx.table.cell(rx.text(p.get("description", "-"), color="white")),
                                        rx.table.cell(
                                            rx.cond(p["active"], rx.badge("Activo", color_scheme="green"), rx.badge("Inactivo", color_scheme="gray")),
                                        ),
                                        rx.table.cell(
                                            rx.hstack(
                                                rx.button("Editar", on_click=lambda: State.select_prompt(p["id_prompt"]), size="1", color="white", font_weight="bold"),
                                                rx.button(
                                                    rx.cond(p["active"], "Deshabilitar", "Habilitar"),
                                                    on_click=lambda: State.toggle_prompt_status(p["id_prompt"], p["active"]),
                                                    size="1",
                                                    color="white",
                                                    font_weight="bold",
                                                ),
                                                spacing="1",
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                        rx.text("No hay prompts. Crea uno nuevo.", color=COLORS["muted_foreground"], font_style="italic"),
                    ),
                    spacing="2",
                ),
                padding="1.5em",
                background_color=COLORS["card"],
                border_radius="0.5em",
                border=f"1px solid {COLORS['border']}",
                width="58%",
            ),

            spacing="4",
            width="100%",
            align_items="flex-start",
        ),

        spacing="3",
        width="100%",
    )


def _ad_job_row(job: rx.Var) -> rx.Component:
    """Fila de la tabla de jobs de análisis de documentación."""
    _cell_color = "white"
    return rx.table.row(
        rx.table.cell(rx.text(job["id"], color=_cell_color)),
        rx.table.cell(
            rx.text(job["nombre"], font_weight="bold", color=_cell_color),
        ),
        rx.table.cell(rx.text(job["template_nombre"], color=_cell_color)),
        rx.table.cell(
            rx.badge(
                job["estado_nombre"],
                variant="solid",
                size="1",
                style={"color": "black", "backgroundColor": job["estado_color"]},
            ),
        ),
        rx.table.cell(rx.text(job["modelo_nombre"], color=_cell_color)),
        rx.table.cell(rx.text(job["salida_nombre"], color=_cell_color)),
        rx.table.cell(rx.text(job["programado_para"], color=_cell_color)),
        rx.table.cell(rx.text(job["created_at"], color=_cell_color)),
        rx.table.cell(
            rx.hstack(
                rx.cond(
                    job["error"] != "",
                    rx.tooltip(
                        rx.icon("triangle-alert", size=16, color="red"),
                        content=job["error"],
                    ),
                    rx.icon("circle-check", size=16, color="green"),
                ),
                rx.button(
                    rx.icon("eye", size=14),
                    on_click=State.ad_open_job_modal(job["id"]),
                    size="1",
                    variant="ghost",
                    color=COLORS["primary"],
                    cursor="pointer",
                    title="Abrir detalle del job",
                ),
                spacing="2",
            ),
        ),
    )


def _ad_job_modal() -> rx.Component:
    """Modal de detalle de job con prompt builder."""
    return rx.dialog.root(
        rx.dialog.content(
            # Título
            rx.dialog.title(
                rx.hstack(
                    rx.icon("file-search", size=22, color=COLORS["primary"]),
                    rx.text("Detalle del Job", font_size="1.3em", font_weight="bold",
                            color=COLORS["primary"]),
                    spacing="2",
                    align_items="center",
                ),
            ),

            # Datos del job
            rx.separator(margin_y="0.5em"),
            rx.hstack(
                rx.vstack(
                    rx.text("Nombre", font_weight="bold", color=COLORS["primary"], font_size="0.9em"),
                    rx.text(State.ad_modal_job["nombre"], color=COLORS["foreground"]),
                    spacing="0",
                    width="50%",
                ),
                rx.vstack(
                    rx.text("Plantilla", font_weight="bold", color=COLORS["primary"], font_size="0.9em"),
                    rx.text(State.ad_modal_job["template_nombre"], color=COLORS["foreground"]),
                    spacing="0",
                    width="50%",
                ),
                width="100%",
            ),
            rx.hstack(
                rx.vstack(
                    rx.text("Estado", font_weight="bold", color=COLORS["primary"], font_size="0.9em"),
                    rx.badge(
                        State.ad_modal_job["estado_nombre"],
                        variant="solid", size="1",
                        style={"color": "black", "backgroundColor": State.ad_modal_job["estado_color"]},
                    ),
                    spacing="1",
                    width="25%",
                ),
                rx.vstack(
                    rx.text("Modelo", font_weight="bold", color=COLORS["primary"], font_size="0.9em"),
                    rx.text(State.ad_modal_job["modelo_nombre"], color=COLORS["foreground"]),
                    spacing="0",
                    width="25%",
                ),
                rx.vstack(
                    rx.text("Salida", font_weight="bold", color=COLORS["primary"], font_size="0.9em"),
                    rx.text(State.ad_modal_job["salida_nombre"], color=COLORS["foreground"]),
                    spacing="0",
                    width="25%",
                ),
                rx.vstack(
                    rx.text("Creado", font_weight="bold", color=COLORS["primary"], font_size="0.9em"),
                    rx.text(State.ad_modal_job["created_at"], color=COLORS["foreground"], font_size="0.85em"),
                    spacing="0",
                    width="25%",
                ),
                width="100%",
                margin_top="0.5em",
            ),
            # Contexto: Organización, Proyecto, Versión
            rx.hstack(
                rx.badge("Org", color_scheme="cyan", variant="solid", size="1",
                         style={"color": "black"}),
                rx.text(State.ad_selected_org_display, font_size="0.85em",
                        color=COLORS["muted_foreground"]),
                rx.badge("Proyecto", color_scheme="amber", variant="solid", size="1",
                         style={"color": "black"}),
                rx.text(State.ad_selected_project_display, font_size="0.85em",
                        color=COLORS["muted_foreground"]),
                rx.badge("Versión", color_scheme="blue", variant="solid", size="1",
                         style={"color": "black"}),
                rx.text(State.ad_selected_version_display, font_size="0.85em",
                        color=COLORS["muted_foreground"]),
                spacing="2",
                margin_top="0.5em",
            ),

            # Sección de Prompt Builder
            rx.separator(margin_y="0.8em"),
            rx.text("Construir Prompt", font_weight="bold", color=COLORS["primary"],
                    font_size="1.1em"),

            # 4 selectores de prompts en grid 2x2
            rx.hstack(
                rx.vstack(
                    rx.text("Identidad", font_weight="bold", color=COLORS["primary"],
                            font_size="0.9em"),
                    rx.select(
                        State.ad_identidad_names,
                        value=State.ad_sel_identidad,
                        on_change=State.ad_set_sel_identidad,
                        placeholder="Seleccionar identidad...",
                        width="100%",
                        size="2",
                        style={"backgroundColor": COLORS["input"],
                               "color": COLORS["foreground"],
                               "borderColor": COLORS["border"]},
                    ),
                    spacing="1",
                    width="50%",
                ),
                rx.vstack(
                    rx.text("Contexto", font_weight="bold", color=COLORS["primary"],
                            font_size="0.9em"),
                    rx.select(
                        State.ad_contexto_names,
                        value=State.ad_sel_contexto,
                        on_change=State.ad_set_sel_contexto,
                        placeholder="Seleccionar contexto...",
                        width="100%",
                        size="2",
                        style={"backgroundColor": COLORS["input"],
                               "color": COLORS["foreground"],
                               "borderColor": COLORS["border"]},
                    ),
                    spacing="1",
                    width="50%",
                ),
                spacing="3",
                width="100%",
            ),
            rx.hstack(
                rx.vstack(
                    rx.text("Solicitud", font_weight="bold", color=COLORS["primary"],
                            font_size="0.9em"),
                    rx.select(
                        State.ad_solicitud_names,
                        value=State.ad_sel_solicitud,
                        on_change=State.ad_set_sel_solicitud,
                        placeholder="Seleccionar solicitud...",
                        width="100%",
                        size="2",
                        style={"backgroundColor": COLORS["input"],
                               "color": COLORS["foreground"],
                               "borderColor": COLORS["border"]},
                    ),
                    spacing="1",
                    width="50%",
                ),
                rx.vstack(
                    rx.text("Modalidad", font_weight="bold", color=COLORS["primary"],
                            font_size="0.9em"),
                    rx.select(
                        State.ad_modalidad_names,
                        value=State.ad_sel_modalidad,
                        on_change=State.ad_set_sel_modalidad,
                        placeholder="Seleccionar modalidad...",
                        width="100%",
                        size="2",
                        style={"backgroundColor": COLORS["input"],
                               "color": COLORS["foreground"],
                               "borderColor": COLORS["border"]},
                    ),
                    spacing="1",
                    width="50%",
                ),
                spacing="3",
                width="100%",
                margin_top="0.3em",
            ),

            # Prompt final compuesto
            rx.text("Prompt Final", font_weight="bold", color=COLORS["primary"],
                    font_size="1em", margin_top="0.8em"),
            rx.text_area(
                value=State.ad_prompt_final,
                is_read_only=True,
                width="100%",
                min_height="180px",
                style={
                    "backgroundColor": "#1a1a2e",
                    "color": "#e0e0e0",
                    "borderColor": COLORS["border"],
                    "fontFamily": "monospace",
                    "fontSize": "0.85em",
                    "whiteSpace": "pre-wrap",
                },
            ),

            # Error del trainer
            rx.cond(
                State.ad_trainer_error != "",
                rx.callout(
                    State.ad_trainer_error,
                    icon="triangle-alert",
                    color_scheme="red",
                    size="1",
                    width="100%",
                    margin_top="0.5em",
                ),
            ),

            # Botones y ACK
            rx.separator(margin_y="0.5em"),
            rx.hstack(
                rx.button(
                    rx.cond(
                        State.ad_trainer_sending,
                        rx.hstack(
                            rx.icon("loader", size=16),
                            rx.text("Enviando..."),
                            spacing="1",
                        ),
                        rx.hstack(
                            rx.icon("send", size=16),
                            rx.text("Enviar al Trainer"),
                            spacing="1",
                        ),
                    ),
                    on_click=State.ad_send_to_trainer,
                    color_scheme="orange",
                    size="3",
                    style={"font_weight": "bold", "color": "black"},
                    disabled=State.ad_trainer_sending,
                ),
                # Etiqueta ACK
                rx.cond(
                    State.ad_trainer_ack,
                    rx.badge(
                        rx.hstack(
                            rx.icon("circle-check", size=14),
                            rx.text("Recibido en Trainer"),
                            spacing="1",
                            align_items="center",
                        ),
                        color_scheme="green",
                        variant="solid",
                        size="2",
                        style={"color": "black"},
                    ),
                ),
                rx.spacer(),
                rx.button(
                    "Salir",
                    on_click=State.ad_close_modal,
                    color_scheme="orange",
                    size="3",
                    variant="outline",
                    style={"color": COLORS["primary"]},
                ),
                width="100%",
                align_items="center",
            ),

            style={
                "backgroundColor": "#1e1e2e",
                "border": f"1px solid {COLORS['border']}",
                "maxWidth": "750px",
                "maxHeight": "90vh",
                "overflowY": "auto",
            },
        ),
        open=State.ad_modal_open,
    )


def _ent_version_row(item: dict) -> rx.Component:
    """Fila de la tabla de versiones pendientes de entrenamiento."""
    return rx.table.row(
        rx.table.cell(
            rx.text(item["organization_name"], font_weight="500", color="white"),
        ),
        rx.table.cell(
            rx.text(item["proyecto_nombre"], color="white"),
        ),
        rx.table.cell(
            rx.badge(
                item["version_display"],
                color_scheme="orange",
                variant="solid",
                size="2",
            ),
        ),
        rx.table.cell(
            rx.hstack(
                # Botón "Enviar al Trainer" - oculto si ya se recibió ACK
                rx.cond(
                    item["ack"],
                    rx.fragment(),
                    rx.button(
                        rx.cond(
                            State.ent_sending_state_id == item["state_id"],
                            rx.spinner(size="1"),
                            rx.icon("play", size=14),
                        ),
                        on_click=State.ent_open_params_modal(item["state_id"]),
                        size="1",
                        variant="ghost",
                        color=COLORS["primary"],
                        cursor="pointer",
                        title="Abrir parámetros de entrenamiento",
                        disabled=State.ent_sending_state_id > 0,
                    ),
                ),
                # Etiqueta ACK
                rx.cond(
                    item["ack"],
                    rx.badge(
                        rx.hstack(
                            rx.icon("circle-check", size=14),
                            rx.text("Solicitud recibida"),
                            spacing="1",
                            align_items="center",
                        ),
                        color_scheme="green",
                        size="2",
                    ),
                    rx.fragment(),
                ),
                spacing="2",
                align_items="center",
            ),
        ),
        _hover={"background_color": "rgba(255, 140, 0, 0.08)"},
    )


def _ent_param_field(
    label: str,
    value: rx.Var,
    on_change,
    hint: str = "",
) -> rx.Component:
    """Campo individual para el modal de parámetros de entrenamiento."""
    return rx.vstack(
        rx.text(label, font_weight="bold", font_size="0.85em", color=COLORS["primary"]),
        rx.input(
            value=value,
            on_change=on_change,
            size="2",
            width="100%",
            style={
                "background_color": COLORS["input"],
                "color": COLORS["foreground"],
                "border_color": COLORS["border"],
            },
        ),
        rx.cond(
            hint != "",
            rx.text(hint, font_size="0.7em", color=COLORS["muted_foreground"]),
            rx.fragment(),
        ),
        spacing="1",
        width="100%",
    )


def _ent_params_modal() -> rx.Component:
    """Modal de parámetros de entrenamiento con 3 grupos conceptuales."""
    return rx.dialog.root(
        rx.dialog.content(
            # Título
            rx.dialog.title(
                rx.hstack(
                    rx.icon("settings-2", size=22, color=COLORS["primary"]),
                    rx.text(
                        "Parámetros de Entrenamiento",
                        font_size="1.3em",
                        font_weight="bold",
                        color=COLORS["primary"],
                    ),
                    spacing="2",
                    align_items="center",
                ),
            ),

            # Indicador de carga
            rx.cond(
                State.ent_modal_loading,
                rx.center(
                    rx.spinner(size="3"),
                    padding="2em",
                ),
                rx.vstack(
                    # Cabecera: info de versión + flags
                    rx.separator(margin_y="0.5em"),
                    rx.hstack(
                        rx.badge("Org", color_scheme="cyan", variant="solid", size="1",
                                 style={"color": "black"}),
                        rx.text(
                            State.ent_modal_version_data["organization_name"],
                            font_size="0.85em",
                            color=COLORS["muted_foreground"],
                        ),
                        rx.badge("Proyecto", color_scheme="amber", variant="solid", size="1",
                                 style={"color": "black"}),
                        rx.text(
                            State.ent_modal_version_data["proyecto_nombre"],
                            font_size="0.85em",
                            color=COLORS["muted_foreground"],
                        ),
                        rx.badge("Versión", color_scheme="blue", variant="solid", size="1",
                                 style={"color": "black"}),
                        rx.text(
                            State.ent_modal_version_data["version_display"],
                            font_size="0.85em",
                            color=COLORS["muted_foreground"],
                        ),
                        spacing="2",
                        flex_wrap="wrap",
                    ),

                    # Checks informativos (solo lectura)
                    rx.hstack(
                        rx.hstack(
                            rx.checkbox(
                                checked=State.ent_modal_es_primer,
                                disabled=True,
                                color_scheme="green",
                            ),
                            rx.text("Primer Entrenamiento", font_size="0.9em",
                                    color=COLORS["foreground"]),
                            spacing="1",
                            align_items="center",
                        ),
                        rx.hstack(
                            rx.checkbox(
                                checked=State.ent_modal_es_reentrenamiento,
                                disabled=True,
                                color_scheme="orange",
                            ),
                            rx.text("Reentrenamiento", font_size="0.9em",
                                    color=COLORS["foreground"]),
                            spacing="1",
                            align_items="center",
                        ),
                        spacing="4",
                        margin_y="0.5em",
                    ),

                    # ====== GRUPO 1: Preparación de Datos ======
                    rx.separator(margin_y="0.5em"),
                    rx.hstack(
                        rx.icon("database", size=16, color=COLORS["primary"]),
                        rx.text(
                            "Preparación de Datos",
                            font_weight="bold",
                            font_size="1em",
                            color=COLORS["primary"],
                        ),
                        spacing="2",
                        align_items="center",
                    ),
                    rx.hstack(
                        _ent_param_field(
                            "Chunk Size",
                            State.ent_modal_chunk_size,
                            State.set_ent_modal_chunk_size,
                            "Rec: 100-5000",
                        ),
                        _ent_param_field(
                            "Chunk Overlap",
                            State.ent_modal_chunk_overlap,
                            State.set_ent_modal_chunk_overlap,
                            "Rec: 0-chunk/2",
                        ),
                        _ent_param_field(
                            "Embedding Dim",
                            State.ent_modal_embedding_dimension,
                            State.set_ent_modal_embedding_dimension,
                            "Rec: 128-2048",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    rx.hstack(
                        _ent_param_field(
                            "Sequence Length",
                            State.ent_modal_sequence_length,
                            State.set_ent_modal_sequence_length,
                            "Rec: 64-4096",
                        ),
                        _ent_param_field(
                            "Distance Metric",
                            State.ent_modal_distance_metric,
                            State.set_ent_modal_distance_metric,
                            "cosine, l2, ip",
                        ),
                        rx.box(width="100%"),  # Spacer
                        spacing="3",
                        width="100%",
                    ),

                    # ====== GRUPO 2: Modelo y Generación ======
                    rx.separator(margin_y="0.5em"),
                    rx.hstack(
                        rx.icon("brain", size=16, color=COLORS["primary"]),
                        rx.text(
                            "Modelo y Generación",
                            font_weight="bold",
                            font_size="1em",
                            color=COLORS["primary"],
                        ),
                        spacing="2",
                        align_items="center",
                    ),
                    rx.hstack(
                        rx.vstack(
                            rx.text(
                                "Modelo Base",
                                font_weight="bold",
                                font_size="0.85em",
                                color=COLORS["primary"],
                            ),
                            rx.select(
                                State.ent_modal_modelos_disponibles,
                                value=State.ent_modal_model_type,
                                on_change=State.set_ent_modal_model_type,
                                size="2",
                                width="100%",
                            ),
                            spacing="1",
                            width="100%",
                        ),
                        _ent_param_field(
                            "Temperature",
                            State.ent_modal_temperature,
                            State.set_ent_modal_temperature,
                            "Rec: 0.0-1.0",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    rx.hstack(
                        _ent_param_field(
                            "Max Tokens",
                            State.ent_modal_max_tokens,
                            State.set_ent_modal_max_tokens,
                            "Rec: 256-32768",
                        ),
                        _ent_param_field(
                            "Top K",
                            State.ent_modal_top_k,
                            State.set_ent_modal_top_k,
                            "Rec: 1-100",
                        ),
                        rx.box(width="100%"),  # Spacer
                        spacing="3",
                        width="100%",
                    ),

                    # ====== GRUPO 3: Optimización ======
                    rx.separator(margin_y="0.5em"),
                    rx.hstack(
                        rx.icon("gauge", size=16, color=COLORS["primary"]),
                        rx.text(
                            "Optimización",
                            font_weight="bold",
                            font_size="1em",
                            color=COLORS["primary"],
                        ),
                        spacing="2",
                        align_items="center",
                    ),
                    rx.hstack(
                        _ent_param_field(
                            "Learning Rate",
                            State.ent_modal_learning_rate,
                            State.set_ent_modal_learning_rate,
                            "Rec: 0.00001-0.1",
                        ),
                        _ent_param_field(
                            "Batch Size",
                            State.ent_modal_batch_size,
                            State.set_ent_modal_batch_size,
                            "Rec: 1-256",
                        ),
                        _ent_param_field(
                            "Epochs",
                            State.ent_modal_epochs,
                            State.set_ent_modal_epochs,
                            "Rec: 1-100",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    rx.hstack(
                        _ent_param_field(
                            "Hidden Units",
                            State.ent_modal_hidden_units,
                            State.set_ent_modal_hidden_units,
                            "Rec: 32-2048",
                        ),
                        _ent_param_field(
                            "Dropout Rate",
                            State.ent_modal_dropout_rate,
                            State.set_ent_modal_dropout_rate,
                            "Rec: 0.0-0.5",
                        ),
                        _ent_param_field(
                            "Loss Function",
                            State.ent_modal_loss_function,
                            State.set_ent_modal_loss_function,
                            "cross_entropy",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    rx.hstack(
                        _ent_param_field(
                            "Optimizer",
                            State.ent_modal_optimizer,
                            State.set_ent_modal_optimizer,
                            "adam, sgd, rmsprop",
                        ),
                        rx.box(width="100%"),
                        rx.box(width="100%"),
                        spacing="3",
                        width="100%",
                    ),

                    # ====== ZONA DE WARNINGS ======
                    rx.cond(
                        State.ent_modal_warnings.length() > 0,
                        rx.vstack(
                            rx.separator(margin_y="0.5em"),
                            rx.foreach(
                                State.ent_modal_warnings,
                                lambda w: rx.callout(
                                    w,
                                    icon="triangle-alert",
                                    color_scheme="yellow",
                                    width="100%",
                                    size="1",
                                ),
                            ),
                            spacing="1",
                            width="100%",
                        ),
                        rx.fragment(),
                    ),

                    # ====== ERROR DE ENVÍO ======
                    rx.cond(
                        State.ent_send_error != "",
                        rx.callout(
                            State.ent_send_error,
                            icon="triangle-alert",
                            color_scheme="red",
                            width="100%",
                        ),
                        rx.fragment(),
                    ),

                    # ====== PIE: Botones ======
                    rx.separator(margin_y="0.5em"),
                    rx.hstack(
                        rx.dialog.close(
                            rx.button(
                                "Cancelar",
                                color_scheme="orange",
                                size="2",
                                variant="soft",
                                style={"font_weight": "bold", "color": COLORS["primary"]},
                            ),
                        ),
                        rx.button(
                            rx.cond(
                                State.ent_sending_state_id > 0,
                                rx.hstack(
                                    rx.spinner(size="1"),
                                    rx.text("Enviando..."),
                                    spacing="1",
                                ),
                                rx.hstack(
                                    rx.icon("send", size=14),
                                    rx.text("Enviar al Trainer"),
                                    spacing="1",
                                ),
                            ),
                            on_click=State.ent_send_to_trainer_from_modal,
                            color_scheme="orange",
                            size="2",
                            style={"font_weight": "bold", "color": "black"},
                            disabled=State.ent_sending_state_id > 0,
                        ),
                        justify="end",
                        spacing="2",
                        width="100%",
                    ),

                    spacing="2",
                    width="100%",
                ),
            ),

            style={
                "background_color": COLORS["card"],
                "border": f"1px solid {COLORS['border']}",
                "max_width": "750px",
                "max_height": "85vh",
                "overflow_y": "auto",
            },
        ),
        open=State.ent_modal_open,
        on_open_change=lambda val: State.ent_close_params_modal(),
    )


def entrenamientos_panel() -> rx.Component:
    """Panel de entrenamientos - visor de versiones pendientes."""
    return rx.vstack(
        # Botón para cargar/recargar datos
        rx.button(
            rx.hstack(
                rx.icon("refresh-cw", size=16),
                rx.text("Cargar versiones pendientes", font_weight="bold"),
                spacing="2",
            ),
            on_click=State.ent_load_pending_versions,
            size="2",
            color_scheme="orange",
            style={"font_weight": "bold", "color": "black"},
            margin_bottom="1em",
        ),

        # Indicador de carga
        rx.cond(
            State.ent_loading,
            rx.hstack(
                rx.spinner(size="3"),
                rx.text("Cargando versiones...", color=COLORS["muted_foreground"]),
                spacing="2",
            ),
            rx.fragment(),
        ),

        # Mensaje de error de carga
        rx.cond(
            State.ent_error != "",
            rx.callout(
                State.ent_error,
                icon="triangle-alert",
                color_scheme="red",
                width="100%",
            ),
            rx.fragment(),
        ),

        # Mensaje de error de envío al trainer
        rx.cond(
            State.ent_send_error != "",
            rx.callout(
                State.ent_send_error,
                icon="triangle-alert",
                color_scheme="red",
                width="100%",
            ),
            rx.fragment(),
        ),

        # Tabla de versiones pendientes
        rx.cond(
            State.ent_pending_versions.length() > 0,
            rx.vstack(
                rx.text(
                    rx.text.strong("Versiones preparadas para entrenamiento inicial"),
                    font_size="1.1em",
                    color=COLORS["primary"],
                    margin_bottom="0.5em",
                ),
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(
                                rx.text("Organización", font_weight="bold", color=COLORS["primary"]),
                            ),
                            rx.table.column_header_cell(
                                rx.text("Proyecto", font_weight="bold", color=COLORS["primary"]),
                            ),
                            rx.table.column_header_cell(
                                rx.text("Versión", font_weight="bold", color=COLORS["primary"]),
                            ),
                            rx.table.column_header_cell(
                                rx.text("Acción", font_weight="bold", color=COLORS["primary"]),
                            ),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            State.ent_pending_versions,
                            _ent_version_row,
                        ),
                    ),
                    width="100%",
                    size="2",
                ),
                width="100%",
            ),
            # Sin versiones pendientes
            rx.cond(
                ~State.ent_loading,
                rx.callout(
                    "No hay versiones pendientes de entrenamiento inicial.",
                    icon="info",
                    color_scheme="blue",
                    width="100%",
                ),
                rx.fragment(),
            ),
        ),
        width="100%",
        spacing="3",
    )


# ============================================================================
# Panel: Evolución del Entrenamiento (fases secuenciales)
# ============================================================================

# Mapeo de estados a colores e iconos para las fases
_EVO_STATUS_COLORS = {
    "completed": "#22c55e",
    "in_progress": "#f59e0b",
    "pending": "#94a3b8",
    "error": "#ef4444",
}

_EVO_STATUS_ICONS = {
    "completed": "circle-check",
    "in_progress": "loader",
    "pending": "circle",
    "error": "circle-x",
}

_EVO_STATUS_LABELS = {
    "completed": "Completado",
    "in_progress": "En progreso",
    "pending": "Pendiente",
    "error": "Error",
}


def _ent_evo_subfase_row(subfase: dict) -> rx.Component:
    """Fila individual de una subfase dentro de una fase.

    Args:
        subfase: Diccionario con key, nombre, status, tiempo
    """
    is_completed = subfase["status"] == "completed"
    is_active = subfase["status"] == "in_progress"
    is_error = subfase["status"] == "error"
    is_pending = subfase["status"] == "pending"

    return rx.hstack(
        # Mini indicador de estado
        rx.cond(
            is_completed,
            rx.icon("check", size=14, color="#22c55e"),
            rx.cond(
                is_active,
                rx.spinner(size="1", color="#f59e0b"),
                rx.cond(
                    is_error,
                    rx.icon("x", size=14, color="#ef4444"),
                    rx.icon("circle", size=8, color="#64748b"),
                ),
            ),
        ),
        # Nombre de la subfase
        rx.text(
            subfase["nombre"],
            font_size="0.85em",
            color=rx.cond(
                is_pending,
                "#64748b",
                rx.cond(
                    is_active,
                    "#f59e0b",
                    rx.cond(
                        is_error,
                        "#ef4444",
                        "#94a3b8",
                    ),
                ),
            ),
        ),
        rx.spacer(),
        # Tiempo empleado (si está disponible)
        rx.cond(
            subfase["tiempo"] != "",
            rx.text(
                subfase["tiempo"],
                font_size="0.75em",
                color="#64748b",
                font_family="monospace",
            ),
            rx.fragment(),
        ),
        spacing="2",
        align_items="center",
        padding="0.4em 0.6em",
        border_radius="4px",
        background=rx.cond(
            is_active,
            "rgba(245, 158, 11, 0.08)",
            "transparent",
        ),
        width="100%",
    )


def _ent_evo_phase_card(phase: dict) -> rx.Component:
    """Tarjeta individual de una fase del entrenamiento con subfases expandibles.

    Estilo visual inspirado en la página de flujos: opacidad diferenciada,
    bordes coloreados y transiciones suaves.
    """
    is_completed = phase["status"] == "completed"
    is_active = phase["status"] == "in_progress"
    is_error = phase["status"] == "error"
    is_pending = phase["status"] == "pending"
    is_expanded = State.ent_evo_expanded_phase == phase["key"]

    return rx.vstack(
        # Tarjeta principal de la fase
        rx.hstack(
            # Indicador visual (línea + círculo)
            rx.vstack(
                # Icono de estado
                rx.cond(
                    is_completed,
                    rx.icon("circle-check", size=22, color="#22c55e"),
                    rx.cond(
                        is_active,
                        rx.icon("loader", size=22, color="#f59e0b"),
                        rx.cond(
                            is_error,
                            rx.icon("circle-x", size=22, color="#ef4444"),
                            rx.icon("circle", size=22, color="#64748b"),
                        ),
                    ),
                ),
                align="center",
                width="30px",
                min_width="30px",
            ),

            # Contenido de la fase
            rx.box(
                rx.hstack(
                    # Emoji
                    rx.text(phase["emoji"], font_size="1.4em"),
                    # Nombre y descripción
                    rx.vstack(
                        rx.text(
                            phase["nombre"],
                            font_weight="bold",
                            font_size="0.95em",
                            color=rx.cond(
                                is_pending,
                                "#94a3b8",
                                "#e2e8f0",
                            ),
                        ),
                        rx.text(
                            phase["descripcion"],
                            font_size="0.8em",
                            color=rx.cond(
                                is_pending,
                                "#64748b",
                                "#94a3b8",
                            ),
                        ),
                        spacing="0",
                    ),
                    # Badge de estado
                    rx.spacer(),
                    rx.cond(
                        is_completed,
                        rx.badge("Completado", color_scheme="green", size="1", variant="surface"),
                        rx.cond(
                            is_active,
                            rx.badge(
                                rx.hstack(
                                    rx.spinner(size="1"),
                                    rx.text("En progreso"),
                                    spacing="1",
                                    align_items="center",
                                ),
                                color_scheme="yellow",
                                size="1",
                                variant="surface",
                            ),
                            rx.cond(
                                is_error,
                                rx.badge("Error", color_scheme="red", size="1", variant="surface"),
                                rx.badge("Pendiente", color_scheme="gray", size="1", variant="surface"),
                            ),
                        ),
                    ),
                    # Icono de expansión
                    rx.icon(
                        rx.cond(
                            is_expanded,
                            "chevron-down",
                            "chevron-right",
                        ),
                        size=18,
                        color="#94a3b8",
                    ),
                    spacing="3",
                    align_items="center",
                    width="100%",
                ),
                border_left=rx.cond(
                    is_completed,
                    "3px solid #22c55e",
                    rx.cond(
                        is_active,
                        "3px solid #f59e0b",
                        rx.cond(
                            is_error,
                            "3px solid #ef4444",
                            "3px solid #334155",
                        ),
                    ),
                ),
                opacity=rx.cond(is_pending, "0.45", "1"),
                box_shadow=rx.cond(
                    is_active,
                    "0 0 12px rgba(245, 158, 11, 0.25)",
                    "none",
                ),
                transition="all 0.5s ease-in-out",
                padding="0.75em 1em",
                border_radius="8px",
                background=rx.cond(
                    is_active,
                    "rgba(245, 158, 11, 0.08)",
                    rx.cond(
                        is_completed,
                        "rgba(34, 197, 94, 0.05)",
                        rx.cond(
                            is_error,
                            "rgba(239, 68, 68, 0.08)",
                            "#1e293b",
                        ),
                    ),
                ),
                width="100%",
                cursor="pointer",
                on_click=State.ent_evo_toggle_phase(phase["key"]),
                _hover={"opacity": "0.85"},
            ),
            spacing="3",
            align_items="flex_start",
            width="100%",
        ),

        # Subfases (expandibles)
        rx.cond(
            is_expanded,
            rx.vstack(
                rx.foreach(
                    phase["subfases"],
                    _ent_evo_subfase_row,
                ),
                padding_left="3.5em",
                spacing="1",
                width="100%",
                margin_top="0.5em",
            ),
            rx.fragment(),
        ),

        spacing="0",
        width="100%",
    )


def _ent_evo_connector() -> rx.Component:
    """Línea conectora vertical entre fases."""
    return rx.box(
        width="2px",
        height="12px",
        background="#334155",
        margin_left="14px",
    )


def evolucion_entrenamiento_panel() -> rx.Component:
    """Panel de evolución del entrenamiento - fases secuenciales."""
    return rx.cond(
        State.ent_evo_active,
        rx.vstack(
            rx.separator(margin_y="1.5em"),

            # Título del panel
            rx.hstack(
                rx.icon("activity", size=20, color=COLORS["primary"]),
                rx.text(
                    rx.text.strong("Evolución del entrenamiento"),
                    font_size="1.1em",
                    color=COLORS["foreground"],
                ),
                spacing="2",
                align_items="center",
            ),

            # Información de la versión en entrenamiento
            rx.hstack(
                rx.badge(
                    rx.hstack(
                        rx.text("Organización:", font_weight="bold"),
                        rx.text(State.ent_evo_org_name),
                        spacing="1",
                    ),
                    color_scheme="blue",
                    size="2",
                    variant="surface",
                ),
                rx.badge(
                    rx.hstack(
                        rx.text("Proyecto:", font_weight="bold"),
                        rx.text(State.ent_evo_project_name),
                        spacing="1",
                    ),
                    color_scheme="purple",
                    size="2",
                    variant="surface",
                ),
                rx.badge(
                    rx.hstack(
                        rx.text("Versión:", font_weight="bold"),
                        rx.text(State.ent_evo_version_label),
                        spacing="1",
                    ),
                    color_scheme="orange",
                    size="2",
                    variant="surface",
                ),
                spacing="2",
                flex_wrap="wrap",
            ),

            # Botón de cancelar entrenamiento
            rx.cond(
                State.ent_evo_can_cancel & ~State.ent_evo_cancelling,
                rx.button(
                    rx.hstack(
                        rx.icon("circle-x", size=16),
                        rx.text("Cancelar Entrenamiento", font_weight="bold"),
                        spacing="2",
                    ),
                    on_click=State.ent_cancel_training,
                    size="2",
                    color_scheme="red",
                    variant="soft",
                    style={"font_weight": "bold"},
                ),
                rx.cond(
                    State.ent_evo_cancelling,
                    rx.hstack(
                        rx.spinner(size="2"),
                        rx.text("Cancelando...", color="#ef4444"),
                        spacing="2",
                    ),
                    rx.fragment(),
                ),
            ),

            # Botón de Entrenar Modelo Autónomo (solo si RAG completado)
            rx.cond(
                State.ent_evo_rag_completed,
                rx.vstack(
                    rx.separator(margin_y="1em"),
                    rx.callout(
                        rx.vstack(
                            rx.hstack(
                                rx.icon("check-circle", size=20, color="#10b981"),
                                rx.text(
                                    "Entrenamiento RAG completado exitosamente",
                                    font_weight="bold",
                                ),
                                spacing="2",
                                align_items="center",
                            ),
                            rx.text(
                                "Ahora puedes iniciar el entrenamiento autónomo para generar un modelo fine-tuned.",
                                color=COLORS["muted"],
                            ),
                            rx.button(
                                rx.hstack(
                                    rx.icon("rocket", size=18),
                                    rx.text("Entrenar Modelo Autónomo", font_weight="bold"),
                                    spacing="2",
                                ),
                                on_click=State.ent_open_autonomous_modal,
                                size="3",
                                color_scheme="orange",
                                variant="solid",
                                style={"font_weight": "bold", "margin_top": "0.5em"},
                            ),
                            spacing="2",
                            width="100%",
                        ),
                        icon="zap",
                        color_scheme="green",
                        size="2",
                    ),
                    spacing="2",
                    width="100%",
                ),
                rx.fragment(),
            ),

            # Botón de Descargar Modelo (solo si autónomo completado)
            rx.cond(
                State.ent_evo_autonomous_completed,
                rx.vstack(
                    rx.separator(margin_y="1em"),
                    rx.callout(
                        rx.vstack(
                            rx.hstack(
                                rx.icon("check-circle", size=20, color="#10b981"),
                                rx.text(
                                    "Modelo autónomo generado exitosamente",
                                    font_weight="bold",
                                ),
                                spacing="2",
                                align_items="center",
                            ),
                            rx.text(
                                "El modelo GGUF está listo para descargar. El paquete incluye el modelo cuantizado, Modelfile e instrucciones de uso.",
                                color=COLORS["muted"],
                            ),
                            rx.hstack(
                                rx.button(
                                    rx.hstack(
                                        rx.icon("download", size=18),
                                        rx.text("Descargar Modelo GGUF", font_weight="bold"),
                                        spacing="2",
                                    ),
                                    on_click=State.ent_download_autonomous_package,
                                    size="3",
                                    color_scheme="green",
                                    variant="solid",
                                    style={"font_weight": "bold"},
                                ),
                                rx.badge(
                                    rx.hstack(
                                        rx.icon("package", size=14),
                                        rx.text("ZIP Package", font_size="0.85em"),
                                        spacing="1",
                                    ),
                                    color_scheme="blue",
                                    variant="surface",
                                ),
                                spacing="2",
                                margin_top="0.5em",
                                align_items="center",
                            ),
                            spacing="2",
                            width="100%",
                        ),
                        icon="package-check",
                        color_scheme="green",
                        size="2",
                    ),
                    spacing="2",
                    width="100%",
                ),
                rx.fragment(),
            ),

            # Timeline de fases
            rx.box(
                rx.foreach(
                    State.ent_evo_phases,
                    lambda phase, idx: rx.fragment(
                        rx.cond(
                            idx > 0,
                            _ent_evo_connector(),
                            rx.fragment(),
                        ),
                        _ent_evo_phase_card(phase),
                    ),
                ),
                width="100%",
                padding="0.5em 0",
            ),

            width="100%",
            spacing="3",
        ),
        rx.fragment(),
    )


def _ent_autonomous_confirmation_modal() -> rx.Component:
    """Modal de confirmación para iniciar entrenamiento autónomo."""
    return rx.dialog.root(
        rx.dialog.content(
            # Título
            rx.dialog.title(
                rx.hstack(
                    rx.icon("zap", size=24, color="#f59e0b"),
                    rx.text("Iniciar Entrenamiento Autónomo", font_weight="bold"),
                    spacing="2",
                    align_items="center",
                ),
            ),

            # Contenido
            rx.vstack(
                # Descripción
                rx.text(
                    "El entrenamiento autónomo procesará las fases 6-9:",
                    font_weight="bold",
                    margin_top="1em",
                ),
                rx.vstack(
                    rx.hstack(
                        rx.icon("check-circle", size=16, color="#10b981"),
                        rx.text("Fase 6: Generación de Dataset"),
                        spacing="2",
                    ),
                    rx.hstack(
                        rx.icon("check-circle", size=16, color="#10b981"),
                        rx.text("Fases 7-8: Fine-tuning con LoRA"),
                        spacing="2",
                    ),
                    rx.hstack(
                        rx.icon("check-circle", size=16, color="#10b981"),
                        rx.text("Fase 9: Exportación a GGUF"),
                        spacing="2",
                    ),
                    spacing="1",
                    padding_left="0.5em",
                ),

                # Training mode
                rx.separator(margin_y="1em"),
                rx.hstack(
                    rx.text("Modo actual:", font_weight="bold"),
                    rx.badge(
                        State.ent_auto_modal_training_mode.upper(),
                        color_scheme=rx.cond(
                            State.ent_auto_modal_training_mode == "simulation",
                            "blue",
                            rx.cond(
                                State.ent_auto_modal_training_mode == "test",
                                "orange",
                                "red",
                            ),
                        ),
                        variant="solid",
                        size="2",
                    ),
                    spacing="2",
                    align_items="center",
                ),

                # Advertencias según modo
                rx.cond(
                    State.ent_auto_modal_training_mode == "simulation",
                    rx.callout(
                        rx.vstack(
                            rx.text("Modo simulación:", font_weight="bold"),
                            rx.text("Solo se generará el dataset (Fase 6). Las fases 7-9 se omitirán."),
                            spacing="1",
                        ),
                        icon="info",
                        color_scheme="blue",
                        size="1",
                    ),
                    rx.cond(
                        State.ent_auto_modal_training_mode == "test",
                        rx.callout(
                            rx.vstack(
                                rx.text("Modo prueba:", font_weight="bold"),
                                rx.text("Se ejecutará un entrenamiento ligero (~20-40 min)."),
                                spacing="1",
                            ),
                            icon="alert-triangle",
                            color_scheme="orange",
                            size="1",
                        ),
                        rx.callout(
                            rx.vstack(
                                rx.text("Modo producción:", font_weight="bold"),
                                rx.text("Se ejecutará un entrenamiento completo (~1-2 horas)."),
                                spacing="1",
                            ),
                            icon="alert-circle",
                            color_scheme="red",
                            size="1",
                        ),
                    ),
                ),

                spacing="2",
                width="100%",
            ),

            # Botones
            rx.flex(
                rx.dialog.close(
                    rx.button(
                        "Cancelar",
                        on_click=State.ent_close_autonomous_modal,
                        color_scheme="gray",
                        variant="soft",
                    ),
                ),
                rx.button(
                    rx.hstack(
                        rx.icon("rocket", size=16),
                        rx.text("Iniciar Entrenamiento"),
                        spacing="2",
                    ),
                    on_click=State.ent_confirm_autonomous_training,
                    color_scheme="orange",
                    style={"font_weight": "bold"},
                ),
                spacing="3",
                margin_top="1.5em",
                justify="end",
            ),

            style={
                "max_width": "500px",
                "padding": "1.5em",
            },
        ),
        open=State.ent_auto_modal_open,
    )


def entrenamientos_full_panel() -> rx.Component:
    """Panel completo de Entrenamientos: visor + evolución."""
    return rx.vstack(
        entrenamientos_panel(),
        evolucion_entrenamiento_panel(),
        _ent_params_modal(),
        _ent_autonomous_confirmation_modal(),
        width="100%",
        spacing="2",
    )


def descargas_panel() -> rx.Component:
    """Panel de Descargas de modelos GGUF entrenados."""
    # Colores oscuros para contraste en paneles gris claro
    _heading_color = "#c2410c"   # Naranja oscuro - headings
    _text_color = "#2d3748"      # Gris oscuro - texto principal
    _label_color = "#9a3412"     # Naranja más oscuro - labels

    return rx.vstack(
        # Título
        rx.heading(
            "Descargas de Modelos",
            size="7",
            color=_heading_color,
            margin_bottom="1em",
        ),

        # Barra de selectores horizontal (Organización → Proyecto → Versión)
        org_project_version_selector_bar(
            org_names=State.dl_organization_options,
            selected_org_display=State.dl_selected_org_name,
            on_org_change=State.dl_set_selected_org,
            project_names=State.dl_project_options,
            selected_project_display=State.dl_selected_project_name,
            on_project_change=State.dl_set_selected_project,
            version_numbers=State.dl_version_options,
            selected_version_display=State.dl_selected_version_name,
            on_version_change=State.dl_set_selected_version,
            org_placeholder="Seleccione organización",
            project_placeholder="Seleccione proyecto",
            version_placeholder="Seleccione versión",
        ),

        # DEBUG: Estado de selectores (temporal)
        rx.box(
            rx.text(
                State.dl_debug_info,
                color="#ff6600",
                font_size="0.8em",
            ),
            padding="0.5em",
            border="1px dashed #ff6600",
            border_radius="0.3em",
            margin_bottom="1em",
            width="100%",
        ),

        # Lista de paquetes disponibles
        rx.cond(
            State.dl_loading_packages,
            rx.card(
                rx.hstack(
                    rx.spinner(size="3"),
                    rx.text(
                        "Cargando paquetes disponibles...",
                        color=_text_color,
                    ),
                    spacing="3",
                    align_items="center",
                    padding="2em",
                ),
                size="2",
            ),
            rx.cond(
                State.dl_packages.length() > 0,
                rx.vstack(
                    rx.hstack(
                        rx.icon("package", size=20, color=_heading_color),
                        rx.heading(
                            "Paquetes Disponibles",
                            size="4",
                            color=_heading_color,
                        ),
                        rx.badge(
                            f"{State.dl_packages.length()} paquetes",
                            color_scheme="orange",
                        ),
                        spacing="2",
                        align_items="center",
                    ),

                    # Lista de paquetes
                    rx.foreach(
                        State.dl_packages,
                        lambda pkg: rx.card(
                            rx.vstack(
                                # Información del paquete
                                rx.hstack(
                                    rx.icon("file-archive", size=24, color="#c2410c"),
                                    rx.vstack(
                                        rx.text(
                                            pkg["package_filename"],
                                            font_weight="bold",
                                            font_size="1.1em",
                                            color=_text_color,
                                        ),
                                        rx.hstack(
                                            rx.badge(
                                                "Modelo LLM",
                                                color_scheme="orange",
                                                variant="surface",
                                            ),
                                            spacing="2",
                                        ),
                                        spacing="1",
                                        align_items="start",
                                    ),
                                    spacing="3",
                                    align_items="center",
                                    flex="1",
                                ),

                                # Información adicional
                                rx.grid(
                                    rx.vstack(
                                        rx.text(
                                            "Tamaño:",
                                            font_size="0.85em",
                                            color=_label_color,
                                            font_weight="bold",
                                        ),
                                        rx.text(
                                            f"{pkg['package_size_mb']:.2f} MB",
                                            font_weight="bold",
                                            color=_text_color,
                                        ),
                                        spacing="0",
                                    ),
                                    rx.vstack(
                                        rx.text(
                                            "Generado:",
                                            font_size="0.85em",
                                            color=_label_color,
                                            font_weight="bold",
                                        ),
                                        rx.text(
                                            pkg["package_generated_at"],
                                            font_weight="bold",
                                            color=_text_color,
                                        ),
                                        spacing="0",
                                    ),
                                    columns="2",
                                    spacing="4",
                                    width="100%",
                                ),

                                rx.separator(margin_y="0.5em"),

                                # Botón de descarga (solo SuperAdmin y Admin Org)
                                rx.cond(
                                    State.can_download_models,
                                    rx.button(
                                        rx.hstack(
                                            rx.icon("shield-check", size=16),
                                            rx.text("Descargar con OTP", font_weight="bold"),
                                            spacing="2",
                                        ),
                                        on_click=lambda: State.dl_download_package(pkg["id_entrenamiento"]),
                                        loading=State.dl_downloading,
                                        color_scheme="orange",
                                        size="3",
                                        width="100%",
                                        style={"font_weight": "bold", "color": "black"},
                                    ),
                                    rx.text(
                                        "Solo administradores pueden descargar modelos",
                                        color="#9a3412",
                                        font_size="0.85em",
                                        font_style="italic",
                                        text_align="center",
                                        width="100%",
                                    ),
                                ),

                                spacing="3",
                                width="100%",
                            ),
                            size="2",
                            margin_bottom="1em",
                        ),
                    ),

                    spacing="3",
                    width="100%",
                ),
                # No hay paquetes
                rx.cond(
                    State.dl_selected_version_id > 0,
                    rx.card(
                        rx.vstack(
                            rx.icon("inbox", size=48, color=_label_color),
                            rx.text(
                                "No se encontraron paquetes disponibles",
                                font_size="1.1em",
                                color=_text_color,
                                font_weight="bold",
                            ),
                            rx.text(
                                "Seleccione otra versión o complete un entrenamiento autónomo primero.",
                                font_size="0.9em",
                                color=_label_color,
                            ),
                            spacing="2",
                            align_items="center",
                            padding="3em",
                        ),
                        size="2",
                    ),
                    rx.card(
                        rx.vstack(
                            rx.icon("filter", size=48, color=_label_color),
                            rx.text(
                                "Seleccione los filtros para ver paquetes disponibles",
                                font_size="1.1em",
                                color=_text_color,
                                font_weight="bold",
                            ),
                            spacing="2",
                            align_items="center",
                            padding="3em",
                        ),
                        size="2",
                    ),
                ),
            ),
        ),

        # Modal OTP para validación de descarga
        rx.dialog.root(
            rx.dialog.content(
                rx.dialog.title(
                    rx.hstack(
                        rx.icon("shield-check", size=24, color="#c2410c"),
                        rx.text(
                            "Verificación OTP para Descarga",
                            font_weight="bold",
                            color="#c2410c",
                        ),
                        spacing="2",
                        align_items="center",
                    ),
                ),
                rx.dialog.description(
                    rx.text(
                        "Se requiere verificación OTP para autorizar la descarga del modelo.",
                        color="#2d3748",
                        size="2",
                    ),
                ),

                rx.vstack(
                    # Paso 1: Solicitar OTP
                    rx.cond(
                        ~State.dl_otp_requested,
                        rx.vstack(
                            rx.text(
                                "Pulse el botón para recibir un código de verificación por SMS.",
                                color="#2d3748",
                                size="2",
                            ),
                            rx.button(
                                rx.hstack(
                                    rx.icon("smartphone", size=16),
                                    rx.text("Solicitar Código OTP", font_weight="bold"),
                                    spacing="2",
                                ),
                                on_click=State.dl_request_otp,
                                color_scheme="orange",
                                size="3",
                                width="100%",
                                style={"font_weight": "bold", "color": "black"},
                            ),
                            spacing="3",
                            width="100%",
                        ),
                        # Paso 2: Introducir OTP y validar
                        rx.vstack(
                            rx.text(
                                rx.text.strong("Código enviado a: "),
                                State.dl_otp_phone,
                                color="#2d3748",
                                size="2",
                            ),
                            rx.input(
                                placeholder="Introduzca el código OTP",
                                value=State.dl_otp_code,
                                on_change=State.set_dl_otp_code,
                                type="text",
                                max_length=8,
                                size="3",
                                width="100%",
                                style={
                                    "text_align": "center",
                                    "font_size": "1.2em",
                                    "letter_spacing": "0.3em",
                                },
                            ),
                            rx.button(
                                rx.hstack(
                                    rx.icon("download", size=16),
                                    rx.text("Validar y Descargar", font_weight="bold"),
                                    spacing="2",
                                ),
                                on_click=State.dl_validate_otp_and_download,
                                loading=State.dl_downloading,
                                color_scheme="orange",
                                size="3",
                                width="100%",
                                style={"font_weight": "bold", "color": "black"},
                            ),
                            rx.button(
                                "Reenviar código",
                                on_click=State.dl_request_otp,
                                variant="ghost",
                                size="2",
                                color="#9a3412",
                            ),
                            spacing="3",
                            width="100%",
                        ),
                    ),

                    # Mensaje de error
                    rx.cond(
                        State.dl_otp_error != "",
                        rx.callout(
                            State.dl_otp_error,
                            icon="alert_triangle",
                            color_scheme="red",
                            size="1",
                            width="100%",
                        ),
                        rx.fragment(),
                    ),

                    spacing="4",
                    width="100%",
                    padding_top="1em",
                ),

                rx.dialog.close(
                    rx.button(
                        "Cancelar",
                        variant="soft",
                        color_scheme="gray",
                        size="2",
                        on_click=State.dl_close_otp_modal,
                    ),
                ),

                style={"max_width": "450px"},
            ),
            open=State.dl_show_otp_modal,
        ),

        # Modal OTP para autorizar descarga
        _otp_modal(),

        spacing="4",
        width="100%",
        padding="2em",
        on_mount=State.dl_init_page,
    )


def _otp_modal() -> rx.Component:
    """Modal de validación OTP para autorizar descarga de modelos."""
    _heading_color = "#c2410c"
    _text_color = "#2d3748"
    _label_color = "#9a3412"

    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                rx.hstack(
                    rx.icon("shield-check", size=24, color=_heading_color),
                    rx.text(
                        "Verificación de Seguridad",
                        font_weight="bold",
                        color=_heading_color,
                    ),
                    spacing="2",
                    align_items="center",
                ),
            ),
            rx.dialog.description(
                rx.text(
                    "Para descargar el modelo es necesario verificar su identidad mediante código OTP enviado por SMS.",
                    color=_text_color,
                    font_size="0.95em",
                ),
            ),
            rx.separator(margin_y="1em"),

            # Paso 1: Solicitar OTP
            rx.cond(
                ~State.dl_otp_requested,
                rx.vstack(
                    rx.text(
                        "Pulse el botón para recibir un código de verificación en su teléfono móvil registrado.",
                        color=_text_color,
                        font_size="0.9em",
                    ),
                    rx.button(
                        rx.hstack(
                            rx.icon("smartphone", size=16),
                            rx.text("Solicitar código OTP", font_weight="bold"),
                            spacing="2",
                        ),
                        on_click=State.dl_request_otp,
                        color_scheme="orange",
                        size="3",
                        width="100%",
                        style={"font_weight": "bold", "color": "black"},
                    ),
                    spacing="3",
                    width="100%",
                ),
                # Paso 2: Introducir OTP recibido
                rx.vstack(
                    rx.hstack(
                        rx.icon("check-circle", size=18, color="#16a34a"),
                        rx.text(
                            rx.cond(
                                State.dl_otp_phone != "",
                                f"Código enviado a {State.dl_otp_phone}",
                                "Código OTP enviado por SMS",
                            ),
                            color="#16a34a",
                            font_weight="bold",
                            font_size="0.9em",
                        ),
                        spacing="2",
                        align_items="center",
                    ),
                    rx.text(
                        "Introduzca el código recibido:",
                        color=_label_color,
                        font_weight="bold",
                        font_size="0.9em",
                    ),
                    rx.input(
                        placeholder="Código OTP",
                        value=State.dl_otp_code,
                        on_change=State.set_dl_otp_code,
                        type="text",
                        max_length=8,
                        size="3",
                        width="100%",
                        style={"text_align": "center", "font_size": "1.2em", "letter_spacing": "0.3em"},
                    ),
                    rx.button(
                        rx.hstack(
                            rx.icon("download", size=16),
                            rx.text("Validar y Descargar", font_weight="bold"),
                            spacing="2",
                        ),
                        on_click=State.dl_validate_otp_and_download,
                        loading=State.dl_downloading,
                        color_scheme="orange",
                        size="3",
                        width="100%",
                        style={"font_weight": "bold", "color": "black"},
                    ),
                    rx.button(
                        "Reenviar código",
                        on_click=State.dl_request_otp,
                        variant="ghost",
                        size="2",
                        color=_label_color,
                    ),
                    spacing="3",
                    width="100%",
                ),
            ),

            # Mensaje de error
            rx.cond(
                State.dl_otp_error != "",
                rx.callout(
                    State.dl_otp_error,
                    icon="alert_triangle",
                    color_scheme="red",
                    margin_top="1em",
                ),
                rx.fragment(),
            ),

            rx.separator(margin_y="1em"),

            # Botón cerrar
            rx.dialog.close(
                rx.button(
                    "Cancelar",
                    variant="soft",
                    color_scheme="gray",
                    size="2",
                    on_click=State.dl_close_otp_modal,
                    style={"font_weight": "bold", "color": "black"},
                ),
            ),

            max_width="450px",
        ),
        open=State.dl_show_otp_modal,
    )


def analisis_documentacion_panel() -> rx.Component:
    """Panel principal de Análisis de Documentación con creación de jobs."""
    return rx.vstack(
        # Botón para inicializar/recargar datos
        rx.button(
            rx.hstack(
                rx.icon("refresh-cw", size=16),
                rx.text("Cargar datos", font_weight="bold"),
                spacing="2",
            ),
            on_click=State.ad_init_page,
            size="2",
            color_scheme="orange",
            style={"font_weight": "bold", "color": "black"},
            margin_bottom="1em",
        ),

        # Selector Organización → Proyecto → Versión
        org_project_version_selector_bar(
            org_names=State.ad_org_names,
            selected_org_display=State.ad_selected_org_display,
            on_org_change=State.ad_set_organization,
            project_names=State.ad_project_names,
            selected_project_display=State.ad_selected_project_display,
            on_project_change=State.ad_set_project,
            version_numbers=State.ad_version_names,
            selected_version_display=State.ad_selected_version_display,
            on_version_change=State.ad_set_version,
        ),

        # Mensajes de error/éxito
        rx.cond(
            State.ad_error != "",
            rx.callout(State.ad_error, icon="triangle-alert", color_scheme="red", width="100%"),
            rx.fragment(),
        ),
        rx.cond(
            State.ad_success != "",
            rx.callout(State.ad_success, icon="check", color_scheme="green", width="100%"),
            rx.fragment(),
        ),

        # Solo mostrar si hay versión seleccionada
        rx.cond(
            State.ad_version_id > 0,
            rx.vstack(
                # Selector de plantilla
                rx.text(
                    "Seleccionar Plantilla de Job",
                    font_weight="bold", color=COLORS["primary"], font_size="1.3em",
                ),
                rx.select(
                    State.ad_template_names,
                    value=State.ad_selected_template_display,
                    on_change=State.ad_select_template,
                    placeholder="Seleccione una plantilla de análisis...",
                    width="100%",
                    size="3",
                    style={
                        "backgroundColor": COLORS["input"],
                        "color": COLORS["foreground"],
                        "borderColor": COLORS["border"],
                    },
                ),

                # Formulario desplegable (solo si hay plantilla seleccionada)
                rx.cond(
                    State.ad_show_form,
                    rx.box(
                        rx.vstack(
                            rx.text(
                                "Crear Job de Análisis de Documentación",
                                font_weight="bold", color=COLORS["primary"],
                                font_size="1.3em",
                            ),
                            rx.separator(margin_y="0.5em"),

                            # Nombre del job
                            rx.text("Nombre del Job *", color=COLORS["primary"],
                                    font_weight="bold", font_size="1.1em"),
                            rx.input(
                                placeholder="Nombre descriptivo del job...",
                                value=State.ad_job_nombre,
                                on_change=State.set_ad_job_nombre,
                                width="100%",
                            ),

                            # Descripción
                            rx.text("Descripción", color=COLORS["primary"],
                                    font_weight="bold", font_size="1.1em",
                                    margin_top="0.3em"),
                            rx.text_area(
                                placeholder="Descripción del job...",
                                value=State.ad_job_descripcion,
                                on_change=State.set_ad_job_descripcion,
                                width="100%",
                                min_height="60px",
                            ),

                            # Fila de selectores: Modelo | Salida | Estado
                            rx.hstack(
                                # Modelo
                                rx.vstack(
                                    rx.text("Modelo LLM", color=COLORS["primary"],
                                            font_weight="bold", font_size="1em"),
                                    rx.select.root(
                                        rx.select.trigger(
                                            placeholder="Modelo...",
                                            style={"backgroundColor": COLORS["input"],
                                                   "color": COLORS["foreground"],
                                                   "borderColor": COLORS["border"]},
                                        ),
                                        rx.select.content(
                                            rx.foreach(
                                                State.ad_modelos,
                                                lambda m: rx.select.item(
                                                    m["nombre"], value=m["id"].to(str)
                                                ),
                                            ),
                                        ),
                                        value=rx.cond(
                                            State.ad_job_id_modelo > 0,
                                            State.ad_job_id_modelo.to(str), ""
                                        ),
                                        on_change=State.ad_set_job_modelo_from_str,
                                        size="3",
                                        width="100%",
                                    ),
                                    spacing="1",
                                    width="33%",
                                ),
                                # Salida
                                rx.vstack(
                                    rx.text("Tipo de Salida", color=COLORS["primary"],
                                            font_weight="bold", font_size="1em"),
                                    rx.select.root(
                                        rx.select.trigger(
                                            placeholder="Salida...",
                                            style={"backgroundColor": COLORS["input"],
                                                   "color": COLORS["foreground"],
                                                   "borderColor": COLORS["border"]},
                                        ),
                                        rx.select.content(
                                            rx.foreach(
                                                State.ad_salidas,
                                                lambda s: rx.select.item(
                                                    s["nombre"], value=s["id"].to(str)
                                                ),
                                            ),
                                        ),
                                        value=rx.cond(
                                            State.ad_job_id_salida > 0,
                                            State.ad_job_id_salida.to(str), ""
                                        ),
                                        on_change=State.ad_set_job_salida_from_str,
                                        size="3",
                                        width="100%",
                                    ),
                                    spacing="1",
                                    width="33%",
                                ),
                                # Estado inicial
                                rx.vstack(
                                    rx.text("Estado Inicial", color=COLORS["primary"],
                                            font_weight="bold", font_size="1em"),
                                    rx.select.root(
                                        rx.select.trigger(
                                            placeholder="Estado...",
                                            style={"backgroundColor": COLORS["input"],
                                                   "color": COLORS["foreground"],
                                                   "borderColor": COLORS["border"]},
                                        ),
                                        rx.select.content(
                                            rx.foreach(
                                                State.ad_estados,
                                                lambda e: rx.select.item(
                                                    e["nombre"], value=e["id"].to(str)
                                                ),
                                            ),
                                        ),
                                        value=rx.cond(
                                            State.ad_job_id_estado > 0,
                                            State.ad_job_id_estado.to(str), ""
                                        ),
                                        on_change=State.ad_set_job_estado_from_str,
                                        size="3",
                                        width="100%",
                                    ),
                                    spacing="1",
                                    width="33%",
                                ),
                                spacing="3",
                                width="100%",
                            ),

                            # Programar para (opcional)
                            rx.text("Programar para (opcional)", color=COLORS["primary"],
                                    font_weight="bold", font_size="1em",
                                    margin_top="0.3em"),
                            rx.input(
                                type="datetime-local",
                                value=State.ad_job_programado_para,
                                on_change=State.set_ad_job_programado_para,
                                width="300px",
                            ),

                            # Información de contexto
                            rx.hstack(
                                rx.badge("Org", color_scheme="cyan", variant="solid",
                                         size="1", style={"color": "black"}),
                                rx.text(State.ad_selected_org_display, font_size="0.9em",
                                        color=COLORS["muted_foreground"]),
                                rx.badge("Proyecto", color_scheme="amber", variant="solid",
                                         size="1", style={"color": "black"}),
                                rx.text(State.ad_selected_project_display, font_size="0.9em",
                                        color=COLORS["muted_foreground"]),
                                rx.badge("Versión", color_scheme="blue", variant="solid",
                                         size="1", style={"color": "black"}),
                                rx.text(State.ad_selected_version_display, font_size="0.9em",
                                        color=COLORS["muted_foreground"]),
                                spacing="2",
                                margin_top="0.5em",
                            ),

                            # Botón crear
                            rx.separator(margin_y="0.5em"),
                            rx.button(
                                rx.icon("play", size=18),
                                "Crear Job",
                                on_click=State.ad_create_job,
                                color_scheme="orange",
                                size="3",
                                style={"font_weight": "bold", "color": "black"},
                            ),

                            spacing="2",
                            width="100%",
                        ),
                        width="100%",
                        padding="1.5em",
                        border=f"1px solid {COLORS['border']}",
                        border_radius="0.5em",
                        margin_top="1em",
                    ),
                    rx.fragment(),
                ),

                # Visor de jobs existentes
                rx.separator(margin_y="1em"),
                rx.text(
                    "Jobs de Análisis de Documentación",
                    font_weight="bold", color=COLORS["primary"], font_size="1.3em",
                ),
                rx.cond(
                    State.ad_jobs.length() > 0,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("ID", style={"color": "white"}),
                                rx.table.column_header_cell("Nombre", style={"color": "white"}),
                                rx.table.column_header_cell("Plantilla", style={"color": "white"}),
                                rx.table.column_header_cell("Estado", style={"color": "white"}),
                                rx.table.column_header_cell("Modelo", style={"color": "white"}),
                                rx.table.column_header_cell("Salida", style={"color": "white"}),
                                rx.table.column_header_cell("Programado", style={"color": "white"}),
                                rx.table.column_header_cell("Creado", style={"color": "white"}),
                                rx.table.column_header_cell(""),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(State.ad_jobs, _ad_job_row),
                        ),
                        width="100%",
                        size="1",
                    ),
                    rx.text(
                        "No hay jobs de análisis para esta versión. Seleccione una plantilla para crear uno.",
                        color=COLORS["muted_foreground"],
                        font_style="italic",
                        padding="1em",
                    ),
                ),

                spacing="3",
                width="100%",
            ),
            rx.text(
                "Seleccione una organización, proyecto y versión para gestionar jobs de análisis.",
                color=COLORS["muted_foreground"],
                font_style="italic",
                padding="2em",
                text_align="center",
            ),
        ),

        # Modal de detalle del job con prompt builder
        _ad_job_modal(),

        spacing="4",
        width="100%",
    )


def _jt_template_row(template: rx.Var) -> rx.Component:
    """Fila de la tabla de plantillas de jobs."""
    return rx.table.row(
        rx.table.cell(template["id"]),
        rx.table.cell(
            rx.text(template["nombre"], font_weight="bold", color=COLORS["foreground"]),
        ),
        rx.table.cell(template["tipo_nombre"]),
        rx.table.cell(template["pagina"]),
        rx.table.cell(template["modelo_nombre"]),
        rx.table.cell(template["salida_nombre"]),
        rx.table.cell(template["estado_nombre"]),
        rx.table.cell(
            rx.hstack(
                rx.cond(
                    template["es_programable"],
                    rx.badge("Prog", color_scheme="cyan", variant="solid", size="1", style={"color": "black"}),
                    rx.fragment(),
                ),
                rx.cond(
                    template["acepta_entrada"],
                    rx.badge("Hijo", color_scheme="amber", variant="solid", size="1", style={"color": "black"}),
                    rx.fragment(),
                ),
                rx.cond(
                    template["permite_hijos"],
                    rx.badge("Padre", color_scheme="blue", variant="solid", size="1", style={"color": "black"}),
                    rx.fragment(),
                ),
                spacing="1",
            ),
        ),
        rx.table.cell(
            rx.cond(
                template["activo"],
                rx.badge("Activa", color_scheme="green", variant="solid", size="1", style={"color": "black"}),
                rx.badge("Inactiva", color_scheme="red", variant="solid", size="1", style={"color": "black"}),
            ),
        ),
        rx.table.cell(
            rx.hstack(
                rx.button(
                    rx.icon("pencil", size=14),
                    on_click=State.jt_select_template(template["id"]),
                    size="1",
                    variant="ghost",
                    color=COLORS["primary"],
                    cursor="pointer",
                ),
                rx.button(
                    rx.icon("power", size=14),
                    on_click=State.jt_toggle_active(template["id"]),
                    size="1",
                    variant="ghost",
                    color=rx.cond(template["activo"], "red", "green"),
                    cursor="pointer",
                ),
                spacing="1",
            ),
        ),
    )


def _job_templates_tab() -> rx.Component:
    """Tab de gestión de plantillas de jobs (SuperAdmin only)."""
    return rx.vstack(
        # Mensajes de error/éxito
        rx.cond(
            State.jt_error != "",
            rx.callout(State.jt_error, icon="triangle-alert", color_scheme="red", width="100%"),
            rx.fragment(),
        ),
        rx.cond(
            State.jt_success != "",
            rx.callout(State.jt_success, icon="check", color_scheme="green", width="100%"),
            rx.fragment(),
        ),

        # Layout horizontal: Formulario (38%) | Tabla (58%)
        rx.hstack(
            # Formulario (izquierda)
            rx.box(
                rx.vstack(
                    rx.text(
                        rx.cond(State.jt_form_mode == "create", "Crear Plantilla", "Editar Plantilla"),
                        font_weight="bold", color=COLORS["primary"], font_size="1.5em",
                    ),

                    # Nombre
                    rx.text("Nombre *", color=COLORS["primary"], font_weight="bold", font_size="1.1em"),
                    rx.input(
                        placeholder="Nombre de la plantilla...",
                        value=State.jt_nombre,
                        on_change=State.set_jt_nombre,
                        width="100%",
                    ),

                    # Descripción
                    rx.text("Descripción", color=COLORS["primary"], font_weight="bold", font_size="1.1em",
                            margin_top="0.3em"),
                    rx.text_area(
                        placeholder="Descripción detallada...",
                        value=State.jt_descripcion,
                        on_change=State.set_jt_descripcion,
                        width="100%",
                        min_height="60px",
                    ),

                    # Tipo de Job
                    rx.text("Tipo de Job *", color=COLORS["primary"], font_weight="bold", font_size="1.1em",
                            margin_top="0.3em"),
                    rx.select.root(
                        rx.select.trigger(
                            placeholder="Seleccionar tipo...",
                            style={"backgroundColor": COLORS["input"], "color": COLORS["foreground"],
                                   "borderColor": COLORS["border"]},
                        ),
                        rx.select.content(
                            rx.foreach(
                                State.jt_tipos,
                                lambda t: rx.select.item(t["nombre"], value=t["id"].to(str)),
                            ),
                        ),
                        value=rx.cond(State.jt_id_tipo > 0, State.jt_id_tipo.to(str), ""),
                        on_change=State.jt_set_id_tipo_from_str,
                        size="3",
                        width="100%",
                    ),

                    # Modelo LLM
                    rx.text("Modelo LLM", color=COLORS["primary"], font_weight="bold", font_size="1.1em",
                            margin_top="0.3em"),
                    rx.select.root(
                        rx.select.trigger(
                            placeholder="Modelo por defecto (opcional)...",
                            style={"backgroundColor": COLORS["input"], "color": COLORS["foreground"],
                                   "borderColor": COLORS["border"]},
                        ),
                        rx.select.content(
                            rx.foreach(
                                State.jt_modelos,
                                lambda m: rx.select.item(m["nombre"], value=m["id"].to(str)),
                            ),
                        ),
                        value=rx.cond(State.jt_id_modelo > 0, State.jt_id_modelo.to(str), ""),
                        on_change=State.jt_set_id_modelo_from_str,
                        size="3",
                        width="100%",
                    ),

                    # Tipo de salida
                    rx.text("Tipo de Salida", color=COLORS["primary"], font_weight="bold", font_size="1.1em",
                            margin_top="0.3em"),
                    rx.select.root(
                        rx.select.trigger(
                            placeholder="Salida por defecto (opcional)...",
                            style={"backgroundColor": COLORS["input"], "color": COLORS["foreground"],
                                   "borderColor": COLORS["border"]},
                        ),
                        rx.select.content(
                            rx.foreach(
                                State.jt_salidas,
                                lambda s: rx.select.item(s["nombre"], value=s["id"].to(str)),
                            ),
                        ),
                        value=rx.cond(State.jt_id_salida > 0, State.jt_id_salida.to(str), ""),
                        on_change=State.jt_set_id_salida_from_str,
                        size="3",
                        width="100%",
                    ),

                    # Estado inicial
                    rx.text("Estado Inicial", color=COLORS["primary"], font_weight="bold", font_size="1.1em",
                            margin_top="0.3em"),
                    rx.select.root(
                        rx.select.trigger(
                            placeholder="Estado al crear job (opcional)...",
                            style={"backgroundColor": COLORS["input"], "color": COLORS["foreground"],
                                   "borderColor": COLORS["border"]},
                        ),
                        rx.select.content(
                            rx.foreach(
                                State.jt_estados,
                                lambda e: rx.select.item(e["nombre"], value=e["id"].to(str)),
                            ),
                        ),
                        value=rx.cond(State.jt_id_estado_inicial > 0, State.jt_id_estado_inicial.to(str), ""),
                        on_change=State.jt_set_id_estado_from_str,
                        size="3",
                        width="100%",
                    ),

                    # Toggles (switches)
                    rx.separator(margin_y="0.5em"),
                    rx.hstack(
                        rx.switch(
                            checked=State.jt_es_programable,
                            on_change=State.set_jt_es_programable,
                        ),
                        rx.text("Programable", color=COLORS["foreground"], font_size="0.95em"),
                        spacing="2",
                        align_items="center",
                    ),
                    rx.hstack(
                        rx.switch(
                            checked=State.jt_acepta_entrada,
                            on_change=State.set_jt_acepta_entrada,
                        ),
                        rx.text("Acepta entrada (puede ser job hijo)", color=COLORS["foreground"],
                                font_size="0.95em"),
                        spacing="2",
                        align_items="center",
                    ),
                    rx.hstack(
                        rx.switch(
                            checked=State.jt_permite_hijos,
                            on_change=State.set_jt_permite_hijos,
                        ),
                        rx.text("Permite hijos (puede ser job padre)", color=COLORS["foreground"],
                                font_size="0.95em"),
                        spacing="2",
                        align_items="center",
                    ),

                    # Botones
                    rx.separator(margin_y="0.5em"),
                    rx.hstack(
                        rx.button(
                            rx.cond(State.jt_form_mode == "create", "Crear Plantilla", "Guardar Cambios"),
                            on_click=State.jt_save_template,
                            color_scheme="orange",
                            size="3",
                            style={"font_weight": "bold", "color": "black"},
                        ),
                        rx.cond(
                            State.jt_form_mode == "edit",
                            rx.button(
                                "Cancelar",
                                on_click=State.jt_clear_form,
                                color_scheme="gray",
                                size="3",
                                variant="outline",
                            ),
                            rx.fragment(),
                        ),
                        spacing="2",
                    ),

                    spacing="2",
                    width="100%",
                ),
                width="38%",
                padding="1em",
                border=f"1px solid {COLORS['border']}",
                border_radius="0.5em",
            ),

            # Tabla de plantillas (derecha)
            rx.box(
                rx.vstack(
                    rx.text("Plantillas Registradas", font_weight="bold", color=COLORS["primary"],
                            font_size="1.5em"),
                    rx.cond(
                        State.jt_list.length() > 0,
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell("ID"),
                                    rx.table.column_header_cell("Nombre"),
                                    rx.table.column_header_cell("Tipo"),
                                    rx.table.column_header_cell("Página"),
                                    rx.table.column_header_cell("Modelo"),
                                    rx.table.column_header_cell("Salida"),
                                    rx.table.column_header_cell("Estado Ini."),
                                    rx.table.column_header_cell("Flags"),
                                    rx.table.column_header_cell("Estado"),
                                    rx.table.column_header_cell("Acciones"),
                                ),
                            ),
                            rx.table.body(
                                rx.foreach(State.jt_list, _jt_template_row),
                            ),
                            width="100%",
                            size="1",
                        ),
                        rx.text(
                            "No hay plantillas registradas. Cree una usando el formulario.",
                            color=COLORS["muted_foreground"],
                            font_style="italic",
                            padding="2em",
                        ),
                    ),
                    spacing="3",
                    width="100%",
                ),
                width="58%",
                padding="1em",
                border=f"1px solid {COLORS['border']}",
                border_radius="0.5em",
                overflow_x="auto",
            ),

            spacing="4",
            width="100%",
            align_items="flex-start",
        ),

        spacing="3",
        width="100%",
    )


def asignaciones_panel() -> rx.Component:
    """Panel de Gestor de Asignaciones (SuperAdmin only)."""
    return rx.vstack(
        # Header
        rx.heading(
            "Gestor de Asignaciones",
            size="6",
            color=COLORS["primary"],  # Cambiado a naranja
            margin_bottom="0.5em",
        ),
        rx.text(
            "Gestión de asignaciones de usuarios internos a organizaciones y proyectos",
            color=COLORS["muted_foreground"],
            font_size="0.9em",
            margin_bottom="1em",
        ),

        # Botón para cargar datos
        rx.button(
            rx.hstack(
                rx.icon("refresh-cw", size=16),
                rx.text("Cargar Datos", font_weight="bold"),
                spacing="2",
            ),
            on_click=State.load_assignments_data,
            size="2",
            background_color=COLORS["primary"],
            color="black",  # Cambiado a negro
            margin_bottom="1em",
        ),

        # Custom Tabs
        rx.hstack(
            rx.button(
                "Roles por Organización",
                on_click=lambda: State.set_assignments_tab("organizaciones"),
                background_color=rx.cond(
                    State.assignments_active_tab == "organizaciones",
                    COLORS["primary"],
                    "transparent",
                ),
                color=rx.cond(
                    State.assignments_active_tab == "organizaciones",
                    "black",  # Cambiado a negro
                    COLORS["foreground"],
                ),
                border=f"1px solid {COLORS['border']}",
                padding="0.75em 1.5em",
                border_radius="0.5em",
                cursor="pointer",
                _hover={"opacity": "0.8"},
                font_weight="bold",
            ),
            rx.button(
                "Roles por Proyecto",
                on_click=lambda: State.set_assignments_tab("proyectos"),
                background_color=rx.cond(
                    State.assignments_active_tab == "proyectos",
                    COLORS["primary"],
                    "transparent",
                ),
                color=rx.cond(
                    State.assignments_active_tab == "proyectos",
                    "black",  # Cambiado a negro
                    COLORS["foreground"],
                ),
                border=f"1px solid {COLORS['border']}",
                padding="0.75em 1.5em",
                border_radius="0.5em",
                cursor="pointer",
                _hover={"opacity": "0.8"},
                font_weight="bold",
            ),
            rx.button(
                "Gestión de Prompts",
                on_click=lambda: State.set_assignments_tab("prompts"),
                background_color=rx.cond(
                    State.assignments_active_tab == "prompts",
                    COLORS["primary"],
                    "transparent",
                ),
                color=rx.cond(
                    State.assignments_active_tab == "prompts",
                    "black",
                    COLORS["foreground"],
                ),
                border=f"1px solid {COLORS['border']}",
                padding="0.75em 1.5em",
                border_radius="0.5em",
                cursor="pointer",
                _hover={"opacity": "0.8"},
                font_weight="bold",
            ),
            rx.button(
                "Plantillas de Jobs",
                on_click=lambda: State.set_assignments_tab("job_templates"),
                background_color=rx.cond(
                    State.assignments_active_tab == "job_templates",
                    COLORS["primary"],
                    "transparent",
                ),
                color=rx.cond(
                    State.assignments_active_tab == "job_templates",
                    "black",
                    COLORS["foreground"],
                ),
                border=f"1px solid {COLORS['border']}",
                padding="0.75em 1.5em",
                border_radius="0.5em",
                cursor="pointer",
                _hover={"opacity": "0.8"},
                font_weight="bold",
            ),
            spacing="2",
            padding="1em",
            border_bottom=f"1px solid {COLORS['border']}",
            width="100%",
        ),

        # Tab Content
        rx.cond(
            State.assignments_active_tab == "organizaciones",
            _org_assignments_tab(),
            rx.cond(
                State.assignments_active_tab == "proyectos",
                _project_assignments_tab(),
                rx.cond(
                    State.assignments_active_tab == "prompts",
                    _prompts_management_tab(),
                    _job_templates_tab(),
                ),
            ),
        ),

        spacing="4",
        width="100%",
    )


def _org_assignments_tab() -> rx.Component:
    """Organization assignments tab content."""
    return rx.hstack(
        # Left column: Form
        rx.box(
            rx.vstack(
                rx.text(
                    "Asignar Usuario a Organización",
                    font_weight="bold",
                    color=COLORS["primary"],
                    font_size="1.7em",  # Aumentado a 1.7em para mayor visibilidad
                ),

                # User selector
                rx.text("Usuario Interno", color=COLORS["primary"], font_size="1.1em", font_weight="bold"),
                rx.cond(
                    State.assignments_internal_users.length() > 0,
                    rx.select.root(
                        rx.select.trigger(
                            placeholder="Selecciona usuario...",
                            style={"backgroundColor": COLORS["input"], "color": COLORS["foreground"], "borderColor": COLORS["border"]},
                        ),
                        rx.select.content(
                            rx.foreach(
                                State.assignments_internal_users,
                                lambda user: rx.select.item(
                                    user["user_name"],
                                    value=user["user_id"].to_string(),
                                ),
                            ),
                        ),
                        on_change=State.set_selected_user_org_from_str,
                        size="3",
                        width="100%",
                    ),
                    rx.text("No hay usuarios internos cargados", color=COLORS["muted_foreground"], font_style="italic"),
                ),

                # Organization selector
                rx.text("Organización", color=COLORS["primary"], font_size="1.1em", font_weight="bold", margin_top="0.5em"),
                rx.cond(
                    State.assignments_organizations.length() > 0,
                    rx.select.root(
                        rx.select.trigger(
                            placeholder="Selecciona organización...",
                            style={"backgroundColor": COLORS["input"], "color": COLORS["foreground"], "borderColor": COLORS["border"]},
                        ),
                        rx.select.content(
                            rx.foreach(
                                State.assignments_organizations,
                                lambda org: rx.select.item(
                                    org["organization_name"],
                                    value=org["organization_id"].to_string(),
                                ),
                            ),
                        ),
                        on_change=State.set_selected_organization_assign_from_str,
                        size="3",
                        width="100%",
                    ),
                    rx.text("No hay organizaciones cargadas", color=COLORS["muted_foreground"], font_style="italic"),
                ),

                # Role selector (filtered: only roles 2-5)
                rx.text("Rol", color=COLORS["primary"], font_size="1.1em", font_weight="bold", margin_top="0.5em"),
                rx.select.root(
                    rx.select.trigger(
                        placeholder="Selecciona rol...",
                        style={"backgroundColor": COLORS["input"], "color": COLORS["foreground"], "borderColor": COLORS["border"]},
                    ),
                    rx.select.content(
                        rx.foreach(
                            State.filtered_org_roles,
                            lambda role: rx.select.item(
                                role["identity_type_name"],
                                value=role["identity_type_id"].to_string(),
                            ),
                        ),
                    ),
                    on_change=State.set_selected_org_role_from_str,
                    size="3",
                    width="100%",
                ),

                # Action buttons
                rx.hstack(
                    rx.button(
                        "Asignar",
                        on_click=State.create_org_assignment,
                        background_color=COLORS["primary"],
                        color="black",  # Cambiado a negro
                        font_weight="bold",  # Agregado negrita
                        size="2",
                    ),
                    rx.button(
                        "Ver Asignaciones",
                        on_click=State.load_org_assignments,
                        variant="outline",
                        size="2",
                        font_weight="bold",
                        color="white",  # Cambiado a blanco para más contraste
                    ),
                    spacing="2",
                    margin_top="1em",
                ),

                # Messages
                rx.cond(
                    State.org_assignment_error != "",
                    rx.callout(
                        State.org_assignment_error,
                        icon="circle-alert",
                        color_scheme="red",
                        size="1",
                        margin_top="0.5em",
                    ),
                ),
                rx.cond(
                    State.org_assignment_success != "",
                    rx.callout(
                        State.org_assignment_success,
                        icon="circle-check",
                        color_scheme="green",
                        size="1",
                        margin_top="0.5em",
                    ),
                ),

                spacing="3",
            ),
            padding="1.5em",
            background_color=COLORS["card"],
            border_radius="0.5em",
            border=f"1px solid {COLORS['border']}",
            width="38%",  # Reducido de 48% a 38%
            flex_shrink="0",
        ),

        # Right column: Assignments table
        rx.box(
            rx.vstack(
                rx.text(
                    "Asignaciones Actuales",
                    font_weight="bold",
                    color=COLORS["primary"],
                    font_size="1.7em",  # Aumentado a 1.7em para mayor visibilidad
                ),

                rx.cond(
                    State.org_assignments_list.length() > 0,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("Usuario"),
                                rx.table.column_header_cell("Organización"),
                                rx.table.column_header_cell("Rol"),
                                rx.table.column_header_cell("Estado"),
                                rx.table.column_header_cell("Acciones"),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                State.org_assignments_list,
                                lambda assignment: rx.table.row(
                                    rx.table.cell(assignment["user_name"]),
                                    rx.table.cell(assignment["organization_name"]),
                                    rx.table.cell(assignment["role_name"]),
                                    rx.table.cell(
                                        rx.cond(
                                            assignment["active"],
                                            rx.badge("Activo", color_scheme="green"),
                                            rx.badge("Inactivo", color_scheme="gray"),
                                        ),
                                    ),
                                    rx.table.cell(
                                        rx.hstack(
                                            rx.button(
                                                rx.cond(
                                                    assignment["active"],
                                                    "Deshabilitar",
                                                    "Habilitar",
                                                ),
                                                on_click=State.toggle_org_assignment(assignment["id"]),
                                                size="1",
                                                variant="soft",
                                                color="white",  # Cambiado a blanco para más contraste
                                                font_weight="bold",
                                            ),
                                            rx.button(
                                                "Eliminar",
                                                on_click=State.delete_org_assignment(assignment["id"]),
                                                color_scheme="red",
                                                size="1",
                                                variant="soft",
                                                color="white",  # Cambiado a blanco para más contraste
                                                font_weight="bold",
                                            ),
                                            spacing="1",
                                        ),
                                    ),
                                ),
                            ),
                        ),
                        size="2",
                        variant="surface",
                    ),
                    rx.text(
                        "No hay asignaciones para mostrar. Selecciona una organización y haz clic en 'Ver Asignaciones'.",
                        color=COLORS["muted_foreground"],
                        font_style="italic",
                        text_align="center",
                        padding="2em",
                    ),
                ),

                spacing="3",
            ),
            padding="1.5em",
            background_color=COLORS["card"],
            border_radius="0.5em",
            border=f"1px solid {COLORS['border']}",
            width="58%",  # Aumentado de 48% a 58%
            flex_shrink="0",
        ),

        spacing="4",
        width="100%",
        align_items="flex-start",
    )


def _project_assignments_tab() -> rx.Component:
    """Project assignments tab content."""
    return rx.hstack(  # Cambiado de vstack a hstack para layout horizontal
        # Left column: Form
        rx.box(
            rx.vstack(
                rx.text(
                    "Asignar Usuario a Proyecto",
                    font_weight="bold",
                    color=COLORS["primary"],
                    font_size="1.7em",  # Aumentado de 1.1em a 1.7em
                ),

                # User selector
                rx.text("Usuario Interno", color=COLORS["primary"], font_size="1.1em", font_weight="bold"),
                rx.cond(
                    State.assignments_internal_users.length() > 0,
                    rx.select.root(
                        rx.select.trigger(
                            placeholder="Selecciona usuario...",
                            style={"backgroundColor": COLORS["input"], "color": COLORS["foreground"], "borderColor": COLORS["border"]},
                        ),
                        rx.select.content(
                            rx.foreach(
                                State.assignments_internal_users,
                                lambda user: rx.select.item(
                                    user["user_name"],
                                    value=user["user_id"].to_string(),
                                ),
                            ),
                        ),
                        on_change=State.set_selected_user_project_from_str,
                        size="3",
                        width="100%",
                    ),
                    rx.text("No hay usuarios internos cargados", color=COLORS["muted_foreground"], font_style="italic"),
                ),

                # Organization selector for project
                rx.text("Organización", color=COLORS["primary"], font_size="1.1em", font_weight="bold", margin_top="0.5em"),
                rx.cond(
                    State.assignments_organizations.length() > 0,
                    rx.select.root(
                        rx.select.trigger(
                            placeholder="Selecciona organización...",
                            style={"backgroundColor": COLORS["input"], "color": COLORS["foreground"], "borderColor": COLORS["border"]},
                        ),
                        rx.select.content(
                            rx.foreach(
                                State.assignments_organizations,
                                lambda org: rx.select.item(
                                    org["organization_name"],
                                    value=org["organization_id"].to_string(),
                                ),
                            ),
                        ),
                        on_change=State.set_selected_org_for_project_from_str,
                        size="3",
                        width="100%",
                    ),
                    rx.text("No hay organizaciones cargadas", color=COLORS["muted_foreground"], font_style="italic"),
                ),

                # Project selector (filtered by organization)
                rx.text("Proyecto", color=COLORS["primary"], font_size="1.1em", font_weight="bold", margin_top="0.5em"),
                rx.cond(
                    State.assignments_projects.length() > 0,
                    rx.select.root(
                        rx.select.trigger(
                            placeholder="Selecciona proyecto...",
                            style={"backgroundColor": COLORS["input"], "color": COLORS["foreground"], "borderColor": COLORS["border"]},
                        ),
                        rx.select.content(
                            rx.foreach(
                                State.assignments_projects,
                                lambda proj: rx.select.item(
                                    proj["nombre"],
                                    value=proj["id_proyecto"].to_string(),
                                ),
                            ),
                        ),
                        on_change=State.set_selected_project_assign_from_str,
                        size="3",
                        width="100%",
                    ),
                    rx.text(
                        rx.cond(
                            State.selected_org_for_project > 0,
                            "No hay proyectos en esta organización",
                            "Selecciona una organización primero"
                        ),
                        color=COLORS["muted_foreground"],
                        font_style="italic"
                    ),
                ),

                # Role selector
                rx.text("Rol en Proyecto", color=COLORS["primary"], font_size="1.1em", font_weight="bold", margin_top="0.5em"),
                rx.select.root(
                    rx.select.trigger(
                        placeholder="Selecciona rol...",
                        style={"backgroundColor": COLORS["input"], "color": COLORS["foreground"], "borderColor": COLORS["border"]},
                    ),
                    rx.select.content(
                        rx.foreach(
                            State.assignments_project_roles,
                            lambda role: rx.select.item(
                                role["nombre_rol"],
                                value=role["id"].to_string(),
                            ),
                        ),
                    ),
                    on_change=State.set_selected_project_role_from_str,
                    size="3",
                    width="100%",
                ),

                # Prerequisite warning
                rx.cond(
                    State.prerequisite_validation_error != "",
                    rx.callout(
                        State.prerequisite_validation_error,
                        icon="triangle-alert",
                        color_scheme="orange",
                        size="1",
                        margin_top="0.5em",
                    ),
                ),

                # Action buttons
                rx.hstack(
                    rx.button(
                        "Asignar",
                        on_click=State.create_project_assignment,
                        background_color=COLORS["primary"],
                        color="black",  # Cambiado a negro
                        font_weight="bold",  # Agregado negrita
                        size="2",
                    ),
                    rx.button(
                        "Ver Asignaciones",
                        on_click=State.load_project_assignments,
                        variant="outline",
                        size="2",
                        font_weight="bold",  # Agregado negrita
                        color="white",  # Agregado color blanco
                    ),
                    spacing="2",
                    margin_top="1em",
                ),

                # Messages
                rx.cond(
                    State.project_assignment_error != "",
                    rx.callout(
                        State.project_assignment_error,
                        icon="circle-alert",
                        color_scheme="red",
                        size="1",
                        margin_top="0.5em",
                    ),
                ),
                rx.cond(
                    State.project_assignment_success != "",
                    rx.callout(
                        State.project_assignment_success,
                        icon="circle-check",
                        color_scheme="green",
                        size="1",
                        margin_top="0.5em",
                    ),
                ),

                spacing="3",
            ),
            padding="1.5em",
            background_color=COLORS["card"],
            border_radius="0.5em",
            border=f"1px solid {COLORS['border']}",
            width="38%",  # Ancho del panel izquierdo
            flex_shrink="0",
        ),

        # Right column: Assignments table
        rx.box(
            rx.vstack(
                rx.text(
                    "Asignaciones Actuales",
                    font_weight="bold",
                    color=COLORS["primary"],
                    font_size="1.7em",  # Aumentado de 1.1em a 1.7em
                ),

                rx.cond(
                    State.project_assignments_list.length() > 0,

                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("Usuario"),
                                rx.table.column_header_cell("Proyecto"),
                                rx.table.column_header_cell("Rol"),
                                rx.table.column_header_cell("Estado"),
                                rx.table.column_header_cell("Acciones"),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                State.project_assignments_list,
                                lambda assignment: rx.table.row(
                                    rx.table.cell(assignment["user_name"]),
                                    rx.table.cell(assignment["project_name"]),
                                    rx.table.cell(assignment["role_name"]),
                                    rx.table.cell(
                                        rx.cond(
                                            assignment["active"],
                                            rx.badge("Activo", color_scheme="green"),
                                            rx.badge("Inactivo", color_scheme="gray"),
                                        ),
                                    ),
                                    rx.table.cell(
                                        rx.hstack(
                                            rx.button(
                                                rx.cond(
                                                    assignment["active"],
                                                    "Deshabilitar",
                                                    "Habilitar",
                                                ),
                                                on_click=State.toggle_project_assignment(assignment["id"]),
                                                size="1",
                                                variant="soft",
                                                color="white",  # Agregado color blanco
                                                font_weight="bold",  # Agregado negrita
                                            ),
                                            rx.button(
                                                "Eliminar",
                                                on_click=State.delete_project_assignment(assignment["id"]),
                                                color_scheme="red",
                                                size="1",
                                                variant="soft",
                                                color="white",  # Agregado color blanco
                                                font_weight="bold",  # Agregado negrita
                                            ),
                                            spacing="1",
                                        ),
                                    ),
                                ),
                            ),
                        ),
                        size="2",
                        variant="surface",
                    ),
                    rx.text(
                        "No hay asignaciones para mostrar. Selecciona un proyecto y haz clic en 'Ver Asignaciones'.",
                        color=COLORS["muted_foreground"],
                        font_style="italic",
                        text_align="center",
                        padding="2em",
                    ),
                ),

                spacing="3",
            ),
            padding="1.5em",
            background_color=COLORS["card"],
            border_radius="0.5em",
            border=f"1px solid {COLORS['border']}",
            width="58%",  # Ancho del panel derecho
            flex_shrink="0",
        ),

        spacing="4",
        width="100%",
        align_items="flex-start",  # Alinear desde arriba
    )


def internal_panel(active_item: str) -> rx.Component:
    """Panel for internal tools menu items."""
    heading_text = rx.match(
        active_item,
        ("asignaciones", "Asignaciones"),
        ("estado_proyectos", "Estado de Proyectos"),
        ("analisis_documentacion", "Análisis de Documentación"),
        ("entrenamientos", "Entrenamientos"),
        ("descargas", "Descargas"),
        ("analisis_resultados", "Análisis de Resultados"),
        ("crear_llm", "Sistema"),
        ("asistente", "Asistente"),
        "Internal Tools",
    )

    # Contenido para cada sección (usando rx.cond para lazy loading)
    content = rx.cond(
        active_item == "asignaciones",
        asignaciones_panel(),
        rx.cond(
            active_item == "estado_proyectos",
            estado_proyectos_panel(),
            rx.cond(
                active_item == "analisis_documentacion",
                analisis_documentacion_panel(),
                rx.cond(
                    active_item == "entrenamientos",
                    entrenamientos_full_panel(),
                    rx.cond(
                        active_item == "descargas",
                        model_downloads_panel(),
                        rx.cond(
                            active_item == "analisis_resultados",
                            analisis_resultados_page(),
                            rx.cond(
                                active_item == "crear_llm",
                                sistema_panel(),
                                rx.cond(
                                    active_item == "asistente",
                                    asistente_panel(),
                                    rx.text("Selecciona una opción del menú Internal.", color=COLORS["muted_foreground"]),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )

    # Para asistente y asignaciones, mostrar sin el box contenedor extra
    return rx.cond(
        (active_item == "asistente") | (active_item == "asignaciones"),
        rx.vstack(
            rx.heading(heading_text, size="8", color=COLORS["primary"], margin_bottom="0.5em"),
            content,
            padding="2em",
            width="100%",
            align_items="flex-start",
        ),
        rx.vstack(
            rx.heading(heading_text, size="8", color=COLORS["primary"], margin_bottom="0.5em"),
            rx.box(
                content,
                padding="2em",
                background_color=COLORS["card"],
                border_radius="0.5em",
                border=f"1px solid {COLORS['border']}",
            ),
            padding="2em",
            width="100%",
            align_items="flex-start",
        ),
    )


def info_panel(active_item: str, is_logged_in: bool) -> rx.Component:
    """Info panel displaying content based on active menu item."""
    presentation_text = load_presentation_content()
    services_text = load_menu_content(
        "services.txt", "Servicios especializados para impulsar sus proyectos de IA."
    )
    projects_text = load_menu_content(
        "proyectos.txt", "Proyectos y entregas en progreso."
    )
    support_text = load_menu_content(
        "soporte.txt", "Soporte técnico y acompañamiento."
    )
    contact_text = load_menu_content(
        "contacto.txt", "Canales de contacto y atención al cliente."
    )
    organization_text = load_organizacion_content()
    technologies_text = load_tecnologias_content()
    projections_text = load_proyecciones_content()
    tracking_text = load_menu_content(
        "seguimiento.txt", "Seguimiento de avances, entregas y validaciones."
    )
    flows_text = load_flujos_content()
    downloads_text = load_menu_content(
        "descargas.txt", "Recursos, informes y entregables para descargar."
    )

    heading_text = rx.cond(
        is_logged_in,
        rx.match(
            active_item,
            ("organizacion", "Organizacion"),
            ("tecnologias", "Tecnologias"),
            ("proyecciones", "Proyecciones"),
            ("seguimiento", "Seguimiento"),
            ("informes", "Informes"),
            ("flujos", "Flujos"),
            ("descargas", "Descargas"),
            "Organizacion",
        ),
        rx.match(
            active_item,
            ("servicios", "Servicios"),
            ("proyectos", "Proyectos"),
            ("soporte", "Soporte"),
            ("contacto", "Contacto"),
            "Inicio",
        ),
    )
    content_text = rx.cond(
        is_logged_in,
        rx.match(
            active_item,
            ("organizacion", organization_text),
            ("tecnologias", technologies_text),
            ("proyecciones", projections_text),
            ("seguimiento", ""),  # Sin contenido markdown para seguimiento
            ("informes", ""),  # Sin contenido markdown para informes
            ("flujos", flows_text),
            ("descargas", downloads_text),
            presentation_text,
        ),
        rx.match(
            active_item,
            ("servicios", services_text),
            ("proyectos", projects_text),
            ("soporte", support_text),
            ("contacto", contact_text),
            presentation_text,
        ),
    )
    
    return rx.vstack(
        # No mostrar heading para informes (lo incluye el propio componente)
        rx.cond(
            active_item != "informes",
            rx.heading(heading_text, size="8", color=COLORS["primary"], margin_bottom="0.5em"),
            rx.box(height="0"),
        ),
        rx.cond(
            rx.cond(is_logged_in, False, active_item == "inicio"),
            rx.box(
                rx.image(
                    src="/logo.jpg",
                    alt="Myllm Logo",
                    width="150px",
                    max_width="100%",
                    height="auto",
                ),
                width="100%",
                display="flex",
                justify_content="center",
                align_items="center",
                margin_y="1em",
            ),
            rx.box(height="0"),
        ),
        # Contenido: markdown para todas las secciones (públicas e internas)
        # Backoffice usa tamaños aumentados para legibilidad de textos y emojis
        rx.cond(
            content_text != "",
            rx.markdown(
                content_text,
                component_map={
                    "h1": lambda text: rx.heading(text, size="8", color=COLORS["primary"], margin_bottom="0.5em"),
                    "h2": lambda text: rx.heading(text, size="6", color=COLORS["primary"], margin_top="1em", margin_bottom="0.5em"),
                    "h3": lambda text: rx.heading(text, size="5", color=COLORS["primary"], margin_top="0.8em", margin_bottom="0.4em"),
                    "p": lambda text: rx.text(text, color=COLORS["muted_foreground"], font_size="1.15em", line_height="1.6", margin_bottom="0.6em"),
                    "li": lambda text: rx.list_item(rx.text(text, color=COLORS["muted_foreground"], font_size="1.15em", line_height="1.5")),
                    "strong": lambda text: rx.text(text, font_weight="bold", color=COLORS["foreground"], as_="span"),
                    "em": lambda text: rx.text(text, font_style="italic", as_="span"),
                    "blockquote": lambda text: rx.box(
                        rx.text(text, color=COLORS["primary"], font_style="italic", font_size="1.15em"),
                        border_left=f"4px solid {COLORS['primary']}",
                        padding_left="1em",
                        margin_y="1em",
                        background_color=f"{COLORS['primary']}10",
                        padding="0.8em",
                        border_radius="0.3em",
                    ),
                    "table": lambda children: rx.box(
                        children,
                        width="100%",
                        overflow_x="auto",
                        margin_y="1em",
                    ),
                    "th": lambda text: rx.table.column_header_cell(
                        rx.text(text, font_weight="bold", color=COLORS["foreground"], font_size="1em"),
                    ),
                    "td": lambda text: rx.table.cell(
                        rx.text(text, color=COLORS["muted_foreground"], font_size="1em"),
                    ),
                },
            ),
            rx.box(height="0"),
        ),
        rx.cond(
            rx.cond(is_logged_in, active_item == "flujos", False),
            flujos_diagram(),
            rx.box(height="0"),
        ),
        # Paneles de gestión de usuarios y proyectos: visibles solo en menú "organizacion"
        rx.cond(
            rx.cond(is_logged_in, active_item == "organizacion", False),
            organization_management_panels(),
            rx.box(height="0"),
        ),
        # Panel de gestión de tecnologías: visible solo en menú "tecnologias"
        rx.cond(
            rx.cond(is_logged_in, active_item == "tecnologias", False),
            rx.vstack(
                tecnologias_management_panel(),
                tecnologias_asignadas_panel(),
                width="100%",
                spacing="4",
            ),
            rx.box(height="0"),
        ),
        # Panel de gestión de proyecciones: visible solo en menú "proyecciones"
        rx.cond(
            rx.cond(is_logged_in, active_item == "proyecciones", False),
            proyecciones_management_panel(),
            rx.box(height="0"),
        ),
        # Panel de seguimiento: visible solo en menú "seguimiento"
        rx.cond(
            rx.cond(is_logged_in, active_item == "seguimiento", False),
            seguimiento_panel(),
            rx.box(height="0"),
        ),
        # Panel de informes: visible solo en menú "informes"
        rx.cond(
            rx.cond(is_logged_in, active_item == "informes", False),
            informes_panel(),
            rx.box(height="0"),
        ),
        # Panel de descargas con selectores de organización, proyecto y versión
        rx.cond(
            rx.cond(is_logged_in, active_item == "descargas", False),
            model_downloads_panel(),
            rx.box(height="0"),
        ),
        rx.cond(
            rx.cond(
                is_logged_in,
                rx.cond(active_item != "flujos", active_item != "organizacion", False),
                False,
            ),
            rx.flex(
            rx.box(
                rx.vstack(
                    rx.text("Perplejidad", color=COLORS["muted_foreground"], font_size="0.9em"),
                    rx.text("≈30", font_size="2em", font_weight="bold", color=COLORS["foreground"]),
                    spacing="1",
                ),
                padding="1.5em",
                background_color=COLORS["card"],
                border=f"1px solid {COLORS['border']}",
                border_radius="0.5em",
                flex="1",
            ),
            rx.box(
                rx.vstack(
                    rx.text("BLEU Score", color=COLORS["muted_foreground"], font_size="0.9em"),
                    rx.text("0.5+", font_size="2em", font_weight="bold", color=COLORS["foreground"]),
                    spacing="1",
                ),
                padding="1.5em",
                background_color=COLORS["card"],
                border=f"1px solid {COLORS['border']}",
                border_radius="0.5em",
                flex="1",
            ),
            rx.box(
                rx.vstack(
                    rx.text("F1 Score", color=COLORS["muted_foreground"], font_size="0.9em"),
                    rx.text("≈70−80", font_size="2em", font_weight="bold", color=COLORS["foreground"]),
                    spacing="1",
                ),
                padding="1.5em",
                background_color=COLORS["card"],
                border=f"1px solid {COLORS['border']}",
                border_radius="0.5em",
                flex="1",
            ),
            direction="row",
            spacing="4",
            width="100%",
            ),
            rx.box(height="0"),
        ),
        spacing=rx.cond(active_item == "seguimiento", "1", "4"),
        padding=rx.cond(active_item == "seguimiento", "0.5em 2em", "2em"),
        width="100%",
    )


def proyecciones_management_panel() -> rx.Component:
    """Panel de gestión de versiones de proyecto (3 capas) - Versión avanzada backoffice."""
    return rx.vstack(
        # ===== CAPA 1: Selector de organización y proyecto =====
        rx.vstack(
            rx.hstack(
                rx.icon("folder-git-2", size=36, color=COLORS["primary"]),
                rx.heading("Gestión de Versiones", size="6", color=COLORS["primary"]),
                spacing="4",
                align="center",
            ),
            rx.text(
                "Administra las versiones de los proyectos y sus contenidos (versión avanzada)",
                color=COLORS["muted_foreground"],
                font_size="1.1em",
            ),
            # Selector de organización (filtrado por asignaciones)
            org_selector_bar(
                org_names=State.bo_organization_names,
                selected_org_display=State.bo_selected_org_display,
                on_org_change=State.bo_set_organization,
            ),
            rx.hstack(
                rx.text("Proyecto:", font_weight="bold", color=COLORS["primary"], font_size="1.1em"),
                rx.select(
                    State.proyecciones_projects_select,
                    placeholder="Seleccionar proyecto...",
                    value=State.proyecciones_project_name,
                    on_change=State.set_proyecciones_project,
                    width="350px",
                    size="3",
                    background_color=COLORS["input"],
                    color=COLORS["foreground"],
                    border_color=COLORS["border"],
                ),
                spacing="4",
                align="center",
            ),
            width="100%",
            spacing="3",
            padding="1.5em",
            background_color=COLORS["card"],
            border=f"1px solid {COLORS['border']}",
            border_radius="0.5em",
        ),
        # ===== CAPA 2: Botón crear nueva versión =====
        rx.cond(
            State.proyecciones_project_id > 0,
            rx.vstack(
                rx.hstack(
                    rx.icon("git-branch", size=28, color=COLORS["primary"]),
                    rx.heading("Gestión de Versiones", size="6", color=COLORS["primary"]),
                    rx.spacer(),
                    rx.button(
                        rx.icon("plus", size=18),
                        "Crear nueva versión",
                        on_click=State.create_new_version,
                        color_scheme="orange",
                        size="3",
                        disabled=State.is_loading_versions,
                        style={"font_weight": "bold", "color": "black"},
                    ),
                    spacing="3",
                    align="center",
                    width="100%",
                ),
                rx.cond(
                    State.proyecciones_error != "",
                    rx.text(State.proyecciones_error, color="red", font_size="0.95em"),
                ),
                rx.cond(
                    State.proyecciones_success != "",
                    rx.text(State.proyecciones_success, color="green", font_size="0.95em"),
                ),
                width="100%",
                spacing="3",
                padding="1.5em",
                background_color=COLORS["card"],
                border=f"1px solid {COLORS['border']}",
                border_radius="0.5em",
            ),
            rx.fragment(),
        ),
        # ===== CAPA 3: Explorador de archivos (INTEGRADO) =====
        # Muestra todas las versiones del proyecto seleccionado
        rx.cond(
            State.proyecciones_project_id > 0,
            rx.vstack(
                explorador_panel(
                    ExploradorState,
                ),
                width="100%",
                spacing="3",
                padding="1.5em",
                background_color=COLORS["card"],
                border=f"1px solid {COLORS['border']}",
                border_radius="0.5em",
            ),
            rx.fragment(),
        ),
        width="100%",
        spacing="4",
    )


def dashboard_tabs() -> rx.Component:
    """Dashboard with tabs for user portal."""
    tabs_config = [
        ("resumen", "Resumen"),
        ("proyectos", "Proyectos"),
        ("tareas", "Tareas"),
        ("reportes", "Reportes"),
        ("documentos", "Documentos"),
        ("configuracion", "Configuración"),
    ]
    
    active_tab = State.user_active_tab
    set_tab = State.set_user_tab
    
    return rx.vstack(
        rx.hstack(
            *[
                rx.button(
                    label,
                    on_click=lambda _, t=tab_id: set_tab(t),
                    background_color=rx.cond(
                        active_tab == tab_id,
                        COLORS["primary"],
                        "transparent"
                    ),
                    color=rx.cond(
                        active_tab == tab_id,
                        "black",
                        COLORS["foreground"]
                    ),
                    border="none",
                    padding="0.75em 1.5em",
                    border_radius="0.5em",
                    cursor="pointer",
                    font_weight="bold",
                    _hover={"opacity": "0.8"},
                )
                for tab_id, label in tabs_config
            ],
            spacing="2",
            padding="1.5em",
            border_bottom=f"1px solid {COLORS['border']}",
            width="100%",
        ),
        rx.cond(
            active_tab == "resumen",
            rx.vstack(
                rx.heading("Resumen General", size="6", color=COLORS["primary"]),
                rx.flex(
                    rx.box(
                        rx.vstack(
                            rx.text("Proyectos Activos", color=COLORS["muted_foreground"], font_size="0.9em"),
                            rx.text("12", font_size="2.5em", font_weight="bold", color=COLORS["foreground"]),
                            spacing="1",
                        ),
                        padding="1.5em",
                        background_color=COLORS["card"],
                        border=f"1px solid {COLORS['border']}",
                        border_radius="0.5em",
                        flex="1",
                    ),
                    rx.box(
                        rx.vstack(
                            rx.text("Tareas Pendientes", color=COLORS["muted_foreground"], font_size="0.9em"),
                            rx.text("24", font_size="2.5em", font_weight="bold", color=COLORS["foreground"]),
                            spacing="1",
                        ),
                        padding="1.5em",
                        background_color=COLORS["card"],
                        border=f"1px solid {COLORS['border']}",
                        border_radius="0.5em",
                        flex="1",
                    ),
                    rx.box(
                        rx.vstack(
                            rx.text("Reportes Nuevos", color=COLORS["muted_foreground"], font_size="0.9em"),
                            rx.text("36", font_size="2.5em", font_weight="bold", color=COLORS["foreground"]),
                            spacing="1",
                        ),
                        padding="1.5em",
                        background_color=COLORS["card"],
                        border=f"1px solid {COLORS['border']}",
                        border_radius="0.5em",
                        flex="1",
                    ),
                    direction="row",
                    spacing="4",
                    width="100%",
                ),
                spacing="4",
                padding="1.5em",
            ),
        ),
        rx.cond(
            active_tab == "proyectos",
            rx.vstack(
                rx.heading("Proyectos", size="6", color=COLORS["primary"]),
                *[
                    rx.hstack(
                        rx.vstack(
                            rx.text(f"Proyecto {chr(65+i)}", font_weight="bold", color=COLORS["foreground"]),
                            rx.text("En progreso", color=COLORS["muted_foreground"], font_size="0.9em"),
                            spacing="1",
                        ),
                        rx.text(f"{75 - i*15}% completado", color=COLORS["primary"], font_size="0.9em"),
                        padding="1em",
                        background_color=COLORS["card"],
                        border=f"1px solid {COLORS['border']}",
                        border_radius="0.5em",
                        width="100%",
                        justify_content="space-between",
                    )
                    for i in range(3)
                ],
                spacing="2",
                padding="1.5em",
            ),
        ),
        rx.cond(
            active_tab == "tareas",
            rx.vstack(
                rx.heading("Tareas", size="6", color=COLORS["primary"]),
                *[
                    rx.hstack(
                        rx.checkbox(checked=False),
                        rx.text(task, color=COLORS["foreground"]),
                        padding="1em",
                        background_color=COLORS["card"],
                        border=f"1px solid {COLORS['border']}",
                        border_radius="0.5em",
                        width="100%",
                        align_items="center",
                    )
                    for task in [
                        "Revisar documentación",
                        "Actualizar sistema",
                        "Reunión con equipo",
                        "Preparar presentación",
                    ]
                ],
                spacing="2",
                padding="1.5em",
            ),
        ),
        rx.cond(
            active_tab == "reportes",
            rx.vstack(
                rx.heading("Reportes", size="6", color=COLORS["primary"]),
                rx.flex(
                    *[
                        rx.box(
                            rx.vstack(
                                rx.text(report, font_weight="bold", color=COLORS["foreground"]),
                                rx.text("Generado: Nov 2026", color=COLORS["muted_foreground"], font_size="0.9em"),
                                spacing="1",
                            ),
                            padding="1.5em",
                            background_color=COLORS["card"],
                            border=f"1px solid {COLORS['border']}",
                            border_radius="0.5em",
                            flex="1",
                        )
                        for report in [
                            "Reporte Mensual",
                            "Análisis de Rendimiento",
                            "Estadísticas de Uso",
                            "Informe Financiero",
                        ]
                    ],
                    direction="row",
                    spacing="4",
                    width="100%",
                ),
                spacing="4",
                padding="1.5em",
            ),
        ),
        rx.cond(
            active_tab == "documentos",
            rx.vstack(
                rx.heading("Documentos", size="6", color=COLORS["primary"]),
                *[
                    rx.hstack(
                        rx.text(doc, color=COLORS["foreground"]),
                        rx.link("Descargar", color=COLORS["primary"], href="#", font_size="0.9em"),
                        padding="1em",
                        background_color=COLORS["card"],
                        border=f"1px solid {COLORS['border']}",
                        border_radius="0.5em",
                        width="100%",
                        justify_content="space-between",
                    )
                    for doc in [
                        "Manual de Usuario.pdf",
                        "Guía de Inicio.docx",
                        "Especificaciones Técnicas.pdf",
                        "Contrato de Servicio.pdf",
                    ]
                ],
                spacing="2",
                padding="1.5em",
            ),
        ),
        rx.cond(
            active_tab == "configuracion",
            rx.vstack(
                rx.heading("Configuración", size="6", color=COLORS["primary"]),
                rx.vstack(
                    rx.vstack(
                        rx.text("Notificaciones por email", color=COLORS["muted_foreground"], font_size="0.9em"),
                        rx.hstack(
                            rx.checkbox(checked=True),
                            rx.text("Activadas", color=COLORS["foreground"]),
                        ),
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("Idioma", color=COLORS["muted_foreground"], font_size="0.9em"),
                        rx.select(
                            ["Español", "English"],
                            value="Español",
                            background_color=COLORS["input"],
                            border_color=COLORS["border"],
                            color=COLORS["foreground"],
                            width="100%",
                        ),
                        spacing="1",
                    ),
                    spacing="3",
                    padding="1.5em",
                    background_color=COLORS["card"],
                    border=f"1px solid {COLORS['border']}",
                    border_radius="0.5em",
                ),
                spacing="3",
                padding="1.5em",
            ),
        ),
        spacing="0",
        width="100%",
        background_color=COLORS["background"],
        padding="0",
    )


def footer() -> rx.Component:
    """Footer component."""
    return rx.vstack(
        rx.hstack(
            rx.vstack(
                rx.text("Servicios", font_weight="bold", color=COLORS["foreground"], font_size="1.4em"),
                rx.link("Características", color=COLORS["primary"], href="/backoffice/show-md?file=caracteristicas", is_external=True, font_size="1.3em"),
                rx.link("Precios", color=COLORS["primary"], href="/backoffice/show-md?file=precios", is_external=True, font_size="1.3em"),
                rx.link("Seguridad", color=COLORS["primary"], href="/backoffice/show-md?file=seguridad", is_external=True, font_size="1.3em"),
                spacing="2",
            ),
            rx.vstack(
                rx.text("Empresa", font_weight="bold", color=COLORS["foreground"], font_size="1.4em"),
                rx.link("Nosotros", color=COLORS["primary"], href="/backoffice/show-md?file=nosotros", is_external=True, font_size="1.3em"),
                rx.link("Blog", color=COLORS["primary"], href="/backoffice/show-md?file=blog", is_external=True, font_size="1.3em"),
                rx.link("Estado", color=COLORS["primary"], href="/backoffice/show-md?file=estado", is_external=True, font_size="1.3em"),
                spacing="2",
            ),
            rx.vstack(
                rx.text("Recursos", font_weight="bold", color=COLORS["foreground"], font_size="1.4em"),
                rx.link("Documentación", color=COLORS["primary"], href="/backoffice/show-md?file=documentacion", is_external=True, font_size="1.3em"),
                rx.link("Comunidad", color=COLORS["primary"], href="/backoffice/show-md?file=comunidad", is_external=True, font_size="1.3em"),
                rx.link("Soporte", color=COLORS["primary"], href="/backoffice/show-md?file=soporte", is_external=True, font_size="1.3em"),
                spacing="2",
            ),
            rx.vstack(
                rx.text("Legal", font_weight="bold", color=COLORS["foreground"], font_size="1.4em"),
                rx.link("Privacidad", color=COLORS["primary"], href="/backoffice/show-md?file=privacidad", is_external=True, font_size="1.3em"),
                rx.link("Términos", color=COLORS["primary"], href="/backoffice/show-md?file=terminos", is_external=True, font_size="1.3em"),
                rx.link("Contratos", color=COLORS["primary"], href="/backoffice/show-md?file=contratos", is_external=True, font_size="1.3em"),
                spacing="2",
            ),
            spacing="6",
            width="100%",
            padding="2em",
            justify_content="center",
            align="center",
        ),
        rx.divider(margin_y="1em"),
        rx.box(
            rx.hstack(
                # Versión en la esquina inferior izquierda
                rx.text(
                    f"Version: {APP_VERSION}",
                    color=COLORS["muted_foreground"],
                    font_size="1.1em",
                ),
                rx.spacer(),
                # Copyright en el centro
                rx.text(
                    "© 2025 Myllm. Todos los derechos reservados.",
                    color=COLORS["muted_foreground"],
                    font_size="1.25em",
                ),
                rx.spacer(),
                width="100%",
                align_items="center",
            ),
            width="100%",
            padding="1em",
        ),
        background_color=COLORS["card"],
        border_top=f"1px solid {COLORS['border']}",
        width="100%",
        spacing="0",
    )


def user_portal() -> rx.Component:
    """User portal main page."""
    return rx.cond(
        State.is_logged_in,
        rx.vstack(
            rx.hstack(
                logo(),
                rx.box(flex_grow="1"),
                # Botón Volver al Frontend
                rx.button(
                    "Volver al Frontend",
                    on_click=State.go_to_frontend,
                    background_color="#22c55e",  # Verde del frontend
                    color="black",
                    font_weight="bold",
                    font_size="1.1em",
                    _hover={"background_color": "#1ea34d"},
                ),
                rx.button(
                    "Desconectar",
                    on_click=State.user_logout,
                    background_color="#FF8C00",  # Naranja
                    color="black",
                    font_weight="bold",
                    font_size="1.1em",
                    _hover={"background_color": "#FF7000"},
                ),
                width="100%",
                padding="1em",
                background_color=COLORS["card"],
                border_bottom=f"1px solid {COLORS['border']}",
                align_items="center",
            ),
            rx.hstack(
                rx.box(
                    rx.vstack(
                        sidebar_menu(State.is_logged_in),
                        internal_menu(State.is_logged_in),
                        spacing="4",
                        padding="1.5em",
                    ),
                    width="25%",
                    padding="1em",
                    background_color=COLORS["card"],
                    border_right=f"1px solid {COLORS['border']}",
                    height="100%",
                    overflow_y="auto",
                ),
                rx.box(
                    rx.cond(
                        State.internal_active_menu != "",
                        internal_panel(State.internal_active_menu),
                        info_panel(State.user_active_menu, State.is_logged_in),
                    ),
                    width="75%",
                    background_color=COLORS["background"],
                    padding="0",
                    height="100%",
                ),
                width="100%",
                spacing="0",
                flex="1",
                align_items="stretch",
                background_color=COLORS["card"],
            ),
            footer(),
            background_color=COLORS["background"],
            width="100%",
            min_height="100vh",
            spacing="0",
        ),
        rx.vstack(
            rx.hstack(
                logo(),
                rx.box(flex_grow="1"),
                rx.text(
                    "Pagina principal",
                    color=COLORS["muted_foreground"],
                    font_size="1.1em",
                ),
                width="100%",
                padding="1em",
                background_color=COLORS["card"],
                border_bottom=f"1px solid {COLORS['border']}",
                align_items="center",
            ),
            rx.hstack(
                rx.box(
                    rx.vstack(
                        # Sin login_panel - el usuario ya está logado desde el frontend
                        sidebar_menu(State.is_logged_in),
                        spacing="4",
                        padding="1.5em",
                    ),
                    width="25%",
                    padding="1em",
                    background_color=COLORS["card"],
                    border_right=f"1px solid {COLORS['border']}",
                    height="100%",
                ),
                rx.box(
                    info_panel(State.user_active_menu, State.is_logged_in),
                    width="75%",
                    background_color=COLORS["background"],
                    padding="0",
                    height="100%",
                ),
                width="100%",
                spacing="0",
                flex="1",
                align_items="stretch",
                background_color=COLORS["card"],
            ),
            footer(),
            background_color=COLORS["background"],
            width="100%",
            min_height="100vh",
            spacing="0",
        ),
    )


# Crear la aplicación
app = rx.App(
    theme=rx.theme(
        appearance="dark",
        accent_color="orange",
    ),
    style={
        "font_family": "Inter, system-ui, sans-serif",
    },
)

# User portal route
app.add_page(
    user_portal,
    route="/",
    title="Myllm - Pagina principal",
    on_load=State.on_page_load,
)

# User creation route
# NOTA: sys.path ya está configurado al inicio del archivo
try:
    from pages.user_creation import user_creation_page
    app.add_page(user_creation_page, route="/user_creation", title="Myllm - Crear Usuario")
    print("✅ Ruta /user_creation registrada exitosamente")
except ImportError as e:
    print(f"⚠️ Warning: Could not import user_creation_page: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"❌ Error al registrar ruta /user_creation: {e}")
    import traceback
    traceback.print_exc()

try:
    from pages.change_password import change_password_page
    app.add_page(change_password_page, route="/change_password", title="Myllm - Recordar Contraseña")
    print("✅ Ruta /change_password registrada exitosamente")
except ImportError as e:
    print(f"⚠️ Warning: Could not import change_password_page: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"❌ Error al registrar ruta /change_password: {e}")

try:
    from pages.model_downloads import model_downloads_page
    app.add_page(model_downloads_page, route="/model_downloads", title="Myllm - Descargas de Modelos")
    print("✅ Ruta /model_downloads registrada exitosamente")
except ImportError as e:
    print(f"⚠️ Warning: Could not import model_downloads_page: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"❌ Error al registrar ruta /model_downloads: {e}")

try:
    from pages.analisis_resultados import analisis_resultados_page
    app.add_page(analisis_resultados_page, route="/analisis_resultados", title="Myllm - Análisis de Resultados")
    print("✅ Ruta /analisis_resultados registrada exitosamente")
except ImportError as e:
    print(f"⚠️ Warning: Could not import analisis_resultados_page: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"❌ Error al registrar ruta /model_downloads: {e}")
    import traceback
    traceback.print_exc()
    import traceback
    traceback.print_exc()
