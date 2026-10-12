"""Referencia de modelos base: familias blue/green del LAIM de desarrollo.

Snapshot de las familias de este equipo (export `laim_config_clear` +
slots TTS que el cliente rellena por defecto). No es un catálogo vivo
ni una receta de hardware: otras versiones del mismo modelo pueden
ajustarse mejor a cada instalación.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BaseModelTierRow:
    """Una fila del ejemplo blue/green."""

    tier: str
    blue: str
    green: str


# Orden y etiquetas = AllTierKeys / TierKeyLabel del cliente.
# Blue/green (salvo TTS) = familias de /Users/perico/develop/laim/bin/silicon
# config/laim_config_clear.json. TTS EN/ES = DefaultTTSModel / DefaultTTSSpanishModel.
BASE_MODEL_TIER_ROWS: tuple[BaseModelTierRow, ...] = (
    BaseModelTierRow("Traductor", "gemma3:4b", "gemma3:4b"),
    BaseModelTierRow("Rápido", "qwen3.5:2b", "qwen3.5:2b"),
    BaseModelTierRow("Medio", "parable/qwen3-fable:4b", "gemma3:4b"),
    BaseModelTierRow("Lento", "qwen3:8b", "qwen3.5:4b"),
    BaseModelTierRow("Alternativo", "phi4-mini:3.8b", "phi3:3.8b"),
    BaseModelTierRow("Imágenes", "llama3.2:3b", "qwen3.5:2b"),
    BaseModelTierRow("Vídeo", "qwen3.5:9b", "gemma4:12b"),
    BaseModelTierRow("Sonido", "gemma4:e4b", "gemma4:e2b"),
    BaseModelTierRow("TTS EN", "legraphista/Orpheus:latest", "legraphista/Orpheus:latest"),
    BaseModelTierRow("TTS ES", "sematre/Orpheus:ft-it_es-3b", "sematre/Orpheus:ft-it_es-3b"),
    BaseModelTierRow("Desarrollo", "qwen2.5-coder:1.5b-base", "deepseek-coder:6.7b"),
)

CATALOG_INTRO = (
    "Ejemplo de modelos con los que se ha ejercitado LAIM en el equipo "
    "de desarrollo (familias **blue** y **green**). Sirve de referencia "
    "de modelos **probados**, no de talla única: explore otras versiones "
    "o tamaños de la misma familia que encajen en la CPU, GPU y memoria "
    "del equipo donde instale el cliente (`laim catalog`, Config › Modelos IA)."
)


def catalog_table_markdown() -> str:
    """Tabla Markdown `tier | blue | green` para el visor CRT."""
    lines = [
        "| Tier | Blue | Green |",
        "|------|------|-------|",
    ]
    for row in BASE_MODEL_TIER_ROWS:
        lines.append(f"| {row.tier} | `{row.blue}` | `{row.green}` |")
    return "\n".join(lines)
