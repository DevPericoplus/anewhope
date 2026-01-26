"""Contenido del panel de Organizacion."""

from pathlib import Path


def load_organizacion_content() -> str:
    """Carga el contenido del panel Organizacion desde el archivo organizacion.txt."""

    try:
        current_dir = Path(__file__).parent.parent
        content_file = current_dir / "organizacion.txt"
        with content_file.open("r", encoding="utf-8") as file_handler:
            return file_handler.read().strip()
    except OSError:
        return "Gestión y visión general de tu organización."
