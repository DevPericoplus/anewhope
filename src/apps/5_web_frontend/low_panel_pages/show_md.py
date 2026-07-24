"""Visor de archivos Markdown para el panel inferior del frontend."""

from pathlib import Path

import reflex as rx

from branding import APP_BRAND_NAME, MSG_COPYRIGHT

from portal_crt import COLORS, MARKDOWN_COMPONENT_MAP, SELECT_STYLE


def load_markdown_content(filename: str) -> str:
    """
    Carga el contenido de un archivo Markdown desde low_panel_pages.
    
    Args:
        filename: Nombre del archivo sin extensión.
    
    Returns:
        Contenido del archivo o mensaje de error.
    """
    base_path = Path(__file__).parent
    md_file = base_path / f"{filename}.md"
    
    if md_file.exists():
        try:
            return md_file.read_text(encoding="utf-8")
        except Exception as e:
            return f"Error al leer el archivo: {e}"
    else:
        return f"# Contenido no disponible\n\nEl archivo `{filename}.md` no se encontró."


class ShowMdState(rx.State):
    """Estado para el visor de Markdown."""
    
    content: str = ""
    title: str = ""
    
    def on_page_load(self):
        """Carga el contenido cuando la página se carga."""
        # Obtener el parámetro 'file' de la URL
        params = self.router.page.params
        filename = params.get("file", "default") if params else "default"
        
        self.title = filename.replace("_", " ").title()
        self.content = load_markdown_content(filename)


def markdown_viewer() -> rx.Component:
    """Componente visor de Markdown con estilos del tema (tamaños aumentados)."""
    return rx.box(
        rx.vstack(
            # Header
            rx.hstack(
                rx.icon("file-text", size=42, color=COLORS["primary"]),
                rx.heading(
                    ShowMdState.title,
                    size="9",
                    color=COLORS["foreground"],
                    font_size="2.2em",
                ),
                spacing="4",
                align="center",
            ),
            rx.divider(color=COLORS["border"]),
            # Contenido Markdown
            rx.box(
                rx.markdown(
                    ShowMdState.content,
                    component_map={
                        "h1": lambda text: rx.heading(
                            text, 
                            size="9", 
                            color=COLORS["primary"], 
                            margin_y="0.6em",
                            font_size="2.4em",
                        ),
                        "h2": lambda text: rx.heading(
                            text, 
                            size="8", 
                            color=COLORS["foreground"], 
                            margin_y="0.5em",
                            font_size="1.9em",
                        ),
                        "h3": lambda text: rx.heading(
                            text, 
                            size="7", 
                            color=COLORS["foreground"], 
                            margin_y="0.4em",
                            font_size="1.6em",
                        ),
                        "p": lambda text: rx.text(
                            text, 
                            color=COLORS["foreground"], 
                            font_size="1.35em", 
                            line_height="1.7",
                        ),
                        "li": lambda text: rx.list_item(
                            rx.text(
                                text, 
                                color=COLORS["foreground"], 
                                font_size="1.3em",
                                line_height="1.6",
                            )
                        ),
                        "a": lambda text, **props: rx.link(
                            text, 
                            color=COLORS["primary"], 
                            font_size="1.3em",
                            **props,
                        ),
                        "code": lambda text: rx.code(
                            text, 
                            color=COLORS["primary"],
                            font_size="1.2em",
                        ),
                        "blockquote": lambda text: rx.box(
                            rx.text(
                                text, 
                                color=COLORS["muted_foreground"], 
                                font_style="italic",
                                font_size="1.25em",
                            ),
                            border_left=f"5px solid {COLORS['primary']}",
                            padding_left="1.2em",
                            margin_y="1.2em",
                        ),
                        "strong": lambda text: rx.text(
                            text,
                            as_="b",
                            font_weight="bold",
                            font_size="1.35em",
                        ),
                        "em": lambda text: rx.text(
                            text,
                            as_="i",
                            font_style="italic",
                            font_size="1.35em",
                        ),
                        "table": lambda children: rx.box(
                            children,
                            overflow_x="auto",
                            font_size="1.2em",
                            width="100%",
                        ),
                        "th": lambda text: rx.table.column_header_cell(
                            text,
                            font_size="1.25em",
                            font_weight="bold",
                            color=COLORS["primary"],
                            padding="0.8em",
                        ),
                        "td": lambda text: rx.table.cell(
                            text,
                            font_size="1.2em",
                            color=COLORS["foreground"],
                            padding="0.7em",
                        ),
                    },
                ),
                padding="1.5em",
                width="100%",
            ),
            # Footer con botón para cerrar
            rx.divider(color=COLORS["border"]),
            rx.hstack(
                rx.text(
                    f"© 2025 {APP_BRAND_NAME} - Contenido informativo",
                    color=COLORS["muted_foreground"],
                    font_size="1.1em",
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("x", size=20),
                    "Cerrar pestaña",
                    on_click=rx.call_script("window.close()"),
                    color_scheme="gray",
                    variant="outline",
                    size="3",
                    font_size="1.1em",
                ),
                width="100%",
                padding="1.2em",
                align="center",
            ),
            spacing="5",
            width="100%",
            max_width="1100px",
            margin="0 auto",
        ),
        background=COLORS["background"],
        min_height="100vh",
        padding="2.5em",
    )


# Ruta de la página
@rx.page(route="/show-md", title="Visor de Contenido", on_load=ShowMdState.on_page_load)
def show_md() -> rx.Component:
    """Página del visor de Markdown accesible por URL."""
    return markdown_viewer()
