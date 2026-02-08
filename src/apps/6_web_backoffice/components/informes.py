"""
Componente de Informes para el backoffice.
Muestra informes y estadísticas del sistema.
"""
import reflex as rx
import importlib.util
import re
from pathlib import Path
from sqlalchemy import create_engine
from adapters.api_client import get_project_versions

# Colores del tema
COLORS = {
    "primary": "#FF8C00",
    "background": "#1A1A1A",
    "foreground": "#FFFFFF",
    "card": "#2A2A2A",
    "border": "#3A3A3A",
    "muted_foreground": "#A0A0A0",
}


def _load_cambios_adapter():
    """Carga dinámicamente el adaptador de cambios."""
    adapter_path = (
        Path(__file__).resolve().parents[3]
        / "2_shared_application/adapters/cambios_adapter.py"
    )
    spec = importlib.util.spec_from_file_location("cambios_adapter", adapter_path)
    if spec is None or spec.loader is None:
        raise ImportError("No se pudo cargar el módulo cambios_adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_storage_structure():
    """Carga dinámicamente el módulo storage_access_structure."""
    storage_path = (
        Path(__file__).resolve().parents[3]
        / "2_shared_application/storage_access_structure.py"
    )
    spec = importlib.util.spec_from_file_location("storage_access_structure", storage_path)
    if spec is None or spec.loader is None:
        raise ImportError("No se pudo cargar el módulo storage_access_structure")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_informes_manager():
    """Carga dinámicamente el módulo informes_manager."""
    manager_path = (
        Path(__file__).resolve().parents[3]
        / "2_shared_application/informes_manager.py"
    )
    spec = importlib.util.spec_from_file_location("informes_manager", manager_path)
    if spec is None or spec.loader is None:
        raise ImportError("No se pudo cargar el módulo informes_manager")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InformesState(rx.State):
    """Estado para el componente de Informes."""

    # Selector de organizaciones
    organizaciones: list[dict] = []
    selected_org_id: int = 0
    selected_org_nombre: str = ""

    # Selector de proyectos
    proyectos: list[dict] = []
    selected_proyecto_id: int = 0
    selected_proyecto_nombre: str = "Todos"

    # Selector de versiones
    versiones: list[dict] = []
    selected_version_id: int = 0
    selected_version_nombre: str = "Todas"

    # Selector de archivos markdown
    archivos: list[dict] = []
    selected_archivo_nombre: str = ""
    markdown_content: str = ""

    @rx.var
    def org_names(self) -> list[str]:
        """Nombres de organizaciones para el selector."""
        return [org["nombre"] for org in self.organizaciones]

    @rx.var
    def proyecto_names(self) -> list[str]:
        """Nombres de proyectos para el selector."""
        return ["Todos"] + [p["nombre"] for p in self.proyectos]

    @rx.var
    def version_names(self) -> list[str]:
        """Nombres de versiones con formato vXXX."""
        return ["Todas"] + [v['folder_name'] for v in self.versiones]

    @rx.var
    def archivo_names(self) -> list[str]:
        """Nombres de archivos para el selector."""
        if not self.archivos:
            return ["Sin informes disponibles"]
        return [a["display_name"] for a in self.archivos]

    async def _get_db_engine(self):
        """Crea el engine de la base de datos para myllm_projects_db."""
        try:
            # Crear engine para myllm_projects_db
            DB_USER = "myllm_admin"
            DB_PASS = "Us3r%40dminP%40ss"  # URL-encoded
            DB_HOST = "localhost"
            engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/myllm_projects_db")
            return engine
        except Exception as e:
            print(f"[ERROR INFORMES] Error creando engine: {e}")
            return None

    async def load_organizaciones(self):
        """Carga las organizaciones asignadas al usuario interno."""
        print("[DEBUG INFORMES] load_organizaciones INICIADO")
        engine = await self._get_db_engine()
        if not engine:
            print("[DEBUG INFORMES] No se pudo obtener engine")
            return

        try:
            from web_backoffice.web_backoffice import State as MainState
            cambios_adapter = _load_cambios_adapter()

            main_state = await self.get_state(MainState)
            user_id = main_state.user_id
            print(f"[DEBUG INFORMES] user_id={user_id}")

            # Obtener organizaciones asignadas al usuario interno
            organizaciones = cambios_adapter.obtener_organizaciones_internas_usuario(
                engine=engine,
                id_usuario=user_id
            )

            print(f"[DEBUG INFORMES] Organizaciones obtenidas: {len(organizaciones)}")
            for org in organizaciones:
                print(f"[DEBUG INFORMES]   - {org['nombre']} (ID: {org['id']})")

            self.organizaciones = organizaciones

            # Si hay organizaciones, seleccionar la primera
            if organizaciones:
                self.selected_org_id = organizaciones[0]["id"]
                self.selected_org_nombre = organizaciones[0]["nombre"]
                print(f"[DEBUG INFORMES] Organización seleccionada: {self.selected_org_nombre}")
            else:
                print("[DEBUG INFORMES] No se encontraron organizaciones asignadas")

        except Exception as e:
            print(f"[ERROR INFORMES] Error al cargar organizaciones: {e}")
            import traceback
            traceback.print_exc()

    async def load_proyectos(self):
        """Carga los proyectos de la organización seleccionada."""
        if self.selected_org_id == 0:
            self.proyectos = []
            return

        engine = await self._get_db_engine()
        if not engine:
            return

        try:
            cambios_adapter = _load_cambios_adapter()

            # Obtener proyectos de la organización
            proyectos = cambios_adapter.obtener_proyectos_organizacion(
                engine=engine,
                id_organizacion=self.selected_org_id
            )

            print(f"[DEBUG INFORMES] Proyectos obtenidos: {len(proyectos)}")
            for p in proyectos:
                print(f"[DEBUG INFORMES]   - {p['nombre']} (ID: {p['id']})")

            self.proyectos = proyectos
            # Resetear selección de proyecto
            self.selected_proyecto_id = 0
            self.selected_proyecto_nombre = "Todos"

        except Exception as e:
            print(f"[ERROR INFORMES] Error al cargar proyectos: {e}")
            import traceback
            traceback.print_exc()

    def set_organizacion(self, org_nombre: str):
        """Cambia la organización seleccionada."""
        self.selected_org_nombre = org_nombre
        # Buscar el ID de la organización por nombre
        for org in self.organizaciones:
            if org["nombre"] == org_nombre:
                self.selected_org_id = org["id"]
                break
        return InformesState.load_proyectos

    async def load_versiones(self):
        """Carga las versiones del proyecto seleccionado."""
        if self.selected_proyecto_id == 0:
            self.versiones = []
            return

        try:
            # Obtener tokens de sesión del MainState
            from web_backoffice.web_backoffice import State as MainState
            main_state = await self.get_state(MainState)

            # Llamar a la API para obtener versiones
            response = get_project_versions(
                project_id=self.selected_proyecto_id,
                access_token=main_state.access_token,
                session_token=main_state.session_token,
            )

            # Procesar respuesta
            versiones_data = response.get("versiones", [])
            versiones = []

            for v in versiones_data:
                versiones.append({
                    "id": v.get("id_version"),
                    "folder_name": v.get("version_folder", "")
                })

            print(f"[DEBUG INFORMES] Versiones obtenidas: {len(versiones)}")
            for v in versiones:
                print(f"[DEBUG INFORMES]   - {v['folder_name']} (ID: {v['id']})")

            self.versiones = versiones
            # Resetear selección de versión
            self.selected_version_id = 0
            self.selected_version_nombre = "Todas"

        except Exception as e:
            print(f"[ERROR INFORMES] Error al cargar versiones: {e}")
            import traceback
            traceback.print_exc()

    def set_proyecto(self, proyecto_nombre: str):
        """Cambia el proyecto seleccionado."""
        self.selected_proyecto_nombre = proyecto_nombre
        if proyecto_nombre == "Todos":
            self.selected_proyecto_id = 0
        else:
            # Buscar el ID del proyecto por nombre
            for p in self.proyectos:
                if p["nombre"] == proyecto_nombre:
                    self.selected_proyecto_id = p["id"]
                    break
        return InformesState.load_versiones

    def set_version(self, version_nombre: str):
        """Cambia la versión seleccionada."""
        self.selected_version_nombre = version_nombre
        if version_nombre == "Todas":
            self.selected_version_id = 0
        else:
            # Buscar el ID por folder_name
            for v in self.versiones:
                if v["folder_name"] == version_nombre:
                    self.selected_version_id = v["id"]
                    break
        return InformesState.load_archivos

    async def load_archivos(self):
        """Carga los archivos markdown de la versión seleccionada."""
        if self.selected_version_id == 0:
            self.archivos = []
            self.selected_archivo_nombre = ""
            self.markdown_content = ""
            return

        try:
            informes_manager = _load_informes_manager()

            # Debug: Mostrar IDs que se van a usar
            print(f"[DEBUG INFORMES] Llamando list_markdown_files con:")
            print(f"[DEBUG INFORMES]   org_id={self.selected_org_id}")
            print(f"[DEBUG INFORMES]   project_id={self.selected_proyecto_id}")
            print(f"[DEBUG INFORMES]   version_id={self.selected_version_id}")

            # Listar archivos en la carpeta de versión
            archivos = informes_manager.list_markdown_files(
                org_id=self.selected_org_id,
                project_id=self.selected_proyecto_id,
                version_id=self.selected_version_id
            )

            print(f"[DEBUG INFORMES] Archivos obtenidos: {len(archivos)}")
            for a in archivos:
                print(f"[DEBUG INFORMES]   - {a['display_name']}")

            self.archivos = archivos

            # Si hay archivos, seleccionar el primero automáticamente
            if archivos:
                self.selected_archivo_nombre = archivos[0]["display_name"]
                await self.load_markdown_content()
            else:
                self.selected_archivo_nombre = ""
                self.markdown_content = ""

        except Exception as e:
            print(f"[ERROR INFORMES] Error al cargar archivos: {e}")
            import traceback
            traceback.print_exc()

    async def set_archivo(self, archivo_nombre: str):
        """Cambia el archivo seleccionado y carga su contenido."""
        if archivo_nombre == "Sin informes disponibles":
            return

        self.selected_archivo_nombre = archivo_nombre
        await self.load_markdown_content()

    def _enrich_content_with_emojis(self, content: str) -> str:
        """Enriquece el contenido markdown con emojis técnicos para un aspecto profesional."""
        keyword_emojis = {
            "Presentación": "📄",
            "Metodología": "🔬",
            "Resultados": "📈",
            "Conclusión": "💡",
            "Recomendaciones": "🚀",
            "Referencias": "📚",
            "Evaluación": "📊",
            "Seguridad": "🔒",
            "Latencia": "⚡",
            "Alerta": "⚠️",
            "Error": "❌",
            "Objetivo": "🎯",
        }

        enriched_content = content
        for key, emoji in keyword_emojis.items():
            pattern = re.compile(r'((?:#+|\*\*)\s*(?:\d+\.?\s*)?)' + re.escape(key))
            enriched_content = pattern.sub(r'\1' + f"{emoji} {key}", enriched_content)

        return enriched_content

    async def load_markdown_content(self):
        """Carga el contenido markdown del archivo seleccionado."""
        if not self.selected_archivo_nombre:
            self.markdown_content = ""
            return

        try:
            informes_manager = _load_informes_manager()

            content = informes_manager.get_markdown_content_by_name(
                org_id=self.selected_org_id,
                project_id=self.selected_proyecto_id,
                version_id=self.selected_version_id,
                display_name=self.selected_archivo_nombre
            )

            if content:
                # Enriquecer con emojis
                self.markdown_content = self._enrich_content_with_emojis(content)
                print(f"[DEBUG INFORMES] Contenido cargado: {len(content)} caracteres")
            else:
                self.markdown_content = ""
                print("[ERROR INFORMES] No se pudo cargar el contenido")

        except Exception as e:
            print(f"[ERROR INFORMES] Error al cargar contenido markdown: {e}")
            import traceback
            traceback.print_exc()

    async def on_mount_informes(self):
        """Se ejecuta cuando se monta el componente."""
        await self.load_organizaciones()
        if self.selected_org_id > 0:
            await self.load_proyectos()
            if self.selected_proyecto_id > 0:
                await self.load_versiones()


def markdown_viewer() -> rx.Component:
    """Visor de markdown con estilos personalizados."""
    return rx.box(
        rx.markdown(
            InformesState.markdown_content,
            component_map={
                "h1": lambda text: rx.heading(
                    text,
                    size="9",
                    margin_bottom="0.5em",
                    margin_top="0",
                    color="#2d3748",
                    font_size="2.5em"
                ),
                "h2": lambda text: rx.heading(
                    text,
                    size="8",
                    margin_top="1em",
                    margin_bottom="0.5em",
                    color="#C2410C",
                    border_bottom="2px solid #C2410C",
                    padding_bottom="0.2em",
                    font_size="2em"
                ),
                "h3": lambda text: rx.heading(
                    text,
                    size="6",
                    margin_top="0.8em",
                    margin_bottom="0.4em",
                    color="#4a5568",
                    font_size="1.6em"
                ),
                "p": lambda text: rx.text(
                    text,
                    margin_bottom="0.8em",
                    line_height="1.6",
                    color="#4a5568",
                    font_size="1.3em"
                ),
                "li": lambda text: rx.list_item(
                    rx.text(text, font_size="1.2em", color="#4a5568"),
                    margin_bottom="0.2em"
                ),
                "strong": lambda text: rx.text(
                    text,
                    as_="span",
                    font_weight="bold",
                    color="#C2410C",  # Naranja oscuro para contraste
                    font_size="1.1em"
                ),
                "table": lambda *children, **props: rx.table.root(
                    *children,
                    **props,
                    variant="surface",
                    width="100%",
                    margin_bottom="1em"
                ),
                "thead": lambda *children, **props: rx.table.header(*children, **props),
                "tbody": lambda *children, **props: rx.table.body(*children, **props),
                "tr": lambda *children, **props: rx.table.row(*children, **props),
                "th": lambda *children, **props: rx.table.column_header_cell(
                    *children,
                    **props,
                    color="#2d3748",
                    font_weight="bold",
                    font_size="1.2em"
                ),
                "td": lambda *children, **props: rx.table.cell(
                    *children,
                    **props,
                    color="#4a5568",
                    font_size="1.15em"
                ),
            }
        ),
        padding_top="20px",
        padding_bottom="40px",
        padding_left="40px",
        padding_right="40px",
        bg="linear-gradient(180deg, #FFFDE7 0%, #FFF3E0 100%)",
        width="100%"
    )


def informes_panel() -> rx.Component:
    """Panel principal de Informes."""
    return rx.vstack(
        # Título
        rx.heading("Informes", size="8", color=COLORS["primary"], margin_top="0", margin_bottom="0.3em"),

        # Selectores en línea horizontal
        rx.hstack(
            # Selector de organización
            rx.hstack(
                rx.text(
                    "Organización:",
                    color=COLORS["primary"],
                    font_weight="bold",
                    font_size="1.2em",
                    white_space="nowrap"
                ),
                rx.select(
                    InformesState.org_names,
                    value=InformesState.selected_org_nombre,
                    on_change=InformesState.set_organizacion,
                    placeholder="Seleccione organización",
                    size="3",
                    width="180px",
                ),
                spacing="2",
                align_items="center",
            ),

            # Selector de proyecto
            rx.hstack(
                rx.text(
                    "Proyecto:",
                    color=COLORS["primary"],
                    font_weight="bold",
                    font_size="1.2em",
                    white_space="nowrap"
                ),
                rx.select(
                    InformesState.proyecto_names,
                    value=InformesState.selected_proyecto_nombre,
                    on_change=InformesState.set_proyecto,
                    placeholder="Seleccione proyecto",
                    size="3",
                    width="180px",
                ),
                spacing="2",
                align_items="center",
            ),

            # Selector de versión
            rx.hstack(
                rx.text(
                    "Versión:",
                    color=COLORS["primary"],
                    font_weight="bold",
                    font_size="1.2em",
                    white_space="nowrap"
                ),
                rx.select(
                    InformesState.version_names,
                    value=InformesState.selected_version_nombre,
                    on_change=InformesState.set_version,
                    placeholder="Seleccione versión",
                    size="3",
                    width="100px",
                ),
                spacing="2",
                align_items="center",
            ),

            # Selector de informe
            rx.hstack(
                rx.text(
                    "Informe:",
                    color=COLORS["primary"],
                    font_weight="bold",
                    font_size="1.2em",
                    white_space="nowrap"
                ),
                rx.select(
                    InformesState.archivo_names,
                    value=InformesState.selected_archivo_nombre,
                    on_change=InformesState.set_archivo,
                    placeholder="Seleccione informe",
                    size="3",
                    width="300px",
                ),
                spacing="2",
                align_items="center",
            ),

            spacing="3",
            width="100%",
            padding="0.5em 1em",
            background_color=COLORS["background"],
            align_items="center",
        ),

        # Visor de markdown
        markdown_viewer(),

        width="100%",
        spacing="0",
        margin_top="0",
        on_mount=InformesState.on_mount_informes,
    )
