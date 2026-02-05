"""
Entidad de dominio para eventos del calendario basados en cambios.
Domain-Driven Design: representa un evento del calendario con su tipo y color asociado.
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional


# Mapeo automático de colores para tipos de cambio
COLOR_MAPPING = {
    "VERSION_CREADA": "#4CAF50",  # Verde - creación
    "Asignación usuario": "#2196F3",  # Azul - asignaciones
    "Respuesta soporte proyecto": "#9C27B0",  # Púrpura - respuestas
    "Quitar usuario": "#F44336",  # Rojo - eliminaciones
    "Solicitud soporte proyecto": "#FF9800",  # Naranja - solicitudes
    "Actualización soporte proyecto": "#00BCD4",  # Cyan - actualizaciones
}

# Color especial para días con eventos mixtos (cliente + interno)
COLOR_MIXTO = "#FFD700"  # Dorado


@dataclass
class CambioEvento:
    """
    Representa un evento del calendario basado en un cambio en el sistema.
    """
    id: int
    fecha_cambio: date
    tipo_cambio: str
    descripcion: str
    id_organizacion: int
    id_proyecto: Optional[int]
    id_version: Optional[int]
    tipo_usuario: Optional[str] = None  # 'cliente' o 'interno'

    def get_color(self) -> str:
        """
        Retorna el color asociado al tipo de cambio.
        Si no existe mapeo, retorna un color por defecto.
        """
        return COLOR_MAPPING.get(self.tipo_cambio, "#757575")  # Gris por defecto

    def get_tooltip_text(self) -> str:
        """
        Genera el texto del tooltip para mostrar en el calendario.
        """
        return f"{self.tipo_cambio}: {self.descripcion}"

    def to_calendar_event(self) -> dict:
        """
        Convierte la entidad a formato de evento del calendario.
        """
        return {
            "id": self.id,
            "date": self.fecha_cambio.isoformat(),
            "tipo_cambio": self.tipo_cambio,
            "descripcion": self.descripcion,
            "color": self.get_color(),
            "tooltip": self.get_tooltip_text(),
            "id_organizacion": self.id_organizacion,
            "id_proyecto": self.id_proyecto,
            "tipo_usuario": self.tipo_usuario,
        }


@dataclass
class EventosDia:
    """
    Agrupa todos los eventos de un día específico.
    Permite determinar si hay mezcla de eventos cliente/interno.
    """
    fecha: date
    eventos: list[CambioEvento]

    def tiene_eventos_mixtos(self) -> bool:
        """
        Verifica si hay eventos tanto de clientes como de internos en el mismo día.
        """
        tipos_usuario = {e.tipo_usuario for e in self.eventos if e.tipo_usuario}
        return "cliente" in tipos_usuario and "interno" in tipos_usuario

    def get_color(self) -> str:
        """
        Retorna el color para este día.
        Si hay eventos mixtos, retorna el color especial.
        Si no, retorna el color del primer evento.
        """
        if self.tiene_eventos_mixtos():
            return COLOR_MIXTO

        if self.eventos:
            return self.eventos[0].get_color()

        return "#757575"

    def get_tooltip_text(self) -> str:
        """
        Genera el texto del tooltip combinando todos los eventos del día.
        """
        if not self.eventos:
            return ""

        if len(self.eventos) == 1:
            return self.eventos[0].get_tooltip_text()

        tooltips = [e.get_tooltip_text() for e in self.eventos]
        return "\n".join(f"• {t}" for t in tooltips)

    def to_calendar_event(self) -> dict:
        """
        Convierte el grupo de eventos a formato del calendario.
        """
        return {
            "date": self.fecha.isoformat(),
            "color": self.get_color(),
            "tooltip": self.get_tooltip_text(),
            "count": len(self.eventos),
            "has_mixed": self.tiene_eventos_mixtos(),
        }


def agrupar_eventos_por_dia(eventos: list[CambioEvento]) -> list[EventosDia]:
    """
    Agrupa eventos por fecha para facilitar la visualización en el calendario.
    """
    eventos_por_fecha = {}

    for evento in eventos:
        fecha = evento.fecha_cambio
        if fecha not in eventos_por_fecha:
            eventos_por_fecha[fecha] = []
        eventos_por_fecha[fecha].append(evento)

    return [
        EventosDia(fecha=fecha, eventos=evs)
        for fecha, evs in eventos_por_fecha.items()
    ]
