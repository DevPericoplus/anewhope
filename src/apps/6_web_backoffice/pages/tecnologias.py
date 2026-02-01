"""Módulo para la página de Tecnologías."""

from pathlib import Path


def load_tecnologias_content() -> str:
    """Carga el contenido del panel Tecnologías desde el archivo tecnologias.md."""

    try:
        current_dir = Path(__file__).parent.parent
        content_file = current_dir / "tecnologias.md"
        with content_file.open("r", encoding="utf-8") as file_handler:
            return file_handler.read().strip()
    except OSError:
        return "# Gestión de Stack Tecnológico\n\nPermite definir y gestionar las tecnologías específicas asignadas a cada proyecto."
