"""Módulo para la página de Proyecciones."""

from pathlib import Path


def load_proyecciones_content() -> str:
    """Carga el contenido del panel Proyecciones desde el archivo proyecciones.md."""

    try:
        current_dir = Path(__file__).parent.parent
        content_file = current_dir / "proyecciones.md"
        with content_file.open("r", encoding="utf-8") as file_handler:
            return file_handler.read().strip()
    except OSError:
        return "# Administrador de Versiones\n\nGestiona las versiones de tu proyecto y el repositorio de contenidos."
