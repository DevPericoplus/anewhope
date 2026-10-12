"""Comparativa de requisitos: monopuesto vs Share/Connect + Headscale.

Cifras orientativas (cores y memoria mínima). La memoria fija cuántos
modelos caben a la vez; los cores, cuántas inferencias en paralelo.
El Share concentra la GPU; el cliente ligero no infiere.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RequirementRow:
    """Una fila de cores + memoria mínima estimada."""

    profile: str
    gpu_cores: str
    memory: str
    notes: str


# Monopuesto: un operador, inferencia en este equipo (tabla 12 GB → 9b).
MONO_ROWS: tuple[RequirementRow, ...] = (
    RequirementRow(
        "Esencial",
        "6–10 / iGPU",
        "6 GB",
        "Solo 2b, 1 slot, contexto 4k",
    ),
    RequirementRow(
        "Dedicado (día a día)",
        "16–24",
        "12 GB",
        "Hasta 9b, 2 slots, contexto 8k–16k",
    ),
    RequirementRow(
        "Holgado",
        "30+",
        "24 GB",
        "12b–16b y warmup de dos tiers",
    ),
)

# Share: la GPU del master atiende chat/Direct/STT/editor de los Connect.
SHARE_ROWS: tuple[RequirementRow, ...] = (
    RequirementRow(
        "1–2 clientes ligeros",
        "20+",
        "16–20 GB",
        "2 slots; Rápido+Medio calientes",
    ),
    RequirementRow(
        "3–5 clientes",
        "30+",
        "24–36 GB",
        "2–3 slots; varios tiers en VRAM",
    ),
    RequirementRow(
        "6 o más",
        "40+",
        "48 GB+",
        "3 slots; programar eval y descargas",
    ),
)


def _rows_table(
    rows: tuple[RequirementRow, ...],
    first_col: str,
) -> str:
    lines = [
        f"| {first_col} | Cores GPU (orient.) | Memoria GPU mín. | Qué esperar |",
        "|--------------|---------------------|------------------|---------------|",
    ]
    for row in rows:
        lines.append(
            f"| {row.profile} | {row.gpu_cores} | {row.memory} | {row.notes} |"
        )
    return "\n".join(lines)


def compare_guide_markdown() -> str:
    """Cuerpo de la comparativa (markdown CRT)."""
    return "\n".join(
        (
            "Dos formas de usar la misma GPU: **solo en este equipo** "
            "(monopuesto) o **Share** para varios LAIM ligeros (Connect). "
            "Los cores permiten más inferencias a la vez; la **memoria** "
            "fija el tamaño y cuántos modelos pueden quedar calientes. "
            "Cifras **estimadas** (Q4); mida con `laim info` y ⚡ Memoria.",
            "",
            "### 1. Monopuesto dedicado",
            "",
            "Un operador. Chat, Direct y warmup viven en **esta** GPU. "
            "Basta con dimensionar un modelo (o dos si hay warmup) y 1–2 slots.",
            "",
            _rows_table(MONO_ROWS, "Perfil"),
            "",
            "En Apple Silicon la memoria es **unificada**: use la RAM del Mac "
            "como techo, no una VRAM PCIe. El cliente ligero **sin** Ollama "
            "local no necesita esta tabla: apunta la ruta IA a un Share.",
            "",
            "### 2. Share + varios Connect",
            "",
            "El **master** (`laim share`, `share_api` **:4322**) ejecuta la "
            "inferencia de los clientes: chat, Direct, Suggestions, STT, "
            "editor y traducción. F6 de «este equipo» sigue en cada cliente. "
            "Más usuarios concurrentes = más slots y más VRAM (varios tiers "
            "calientes). Los ligeros casi no gastan GPU.",
            "",
            _rows_table(SHARE_ROWS, "Carga en el Share"),
            "",
            "Regla: capacidad LAIM (slots) ≤ `OLLAMA_NUM_PARALLEL` del demonio. "
            "Si el Share se queda corto, baje tamaño de modelo o suba memoria; "
            "no suba concurrencia a costa de OOM.",
            "",
            "### Headscale y `laim remote`: reserve más",
            "",
            "La malla (Headscale coordinador + cliente Tailscale, IPs `100.x`) "
            "permite clientes ligeros **remotos** (otra LAN, 4G, hotel) y, "
            "desde un monopuesto, **`laim remote`** / Suggestions hacia "
            "máquinas unidas a ese coordinador. El plano de control "
            "(`mesh_api` **:4324**) es ligero; la **carga extra** aparece "
            "cuando el mismo host es Share + coordinador + destino SSH, o "
            "cuando varios Connect remotos disparan inferencia a la vez "
            "(incluido relé DERP si no hay P2P).",
            "",
            "En esos casos **suba un escalón** de la tabla Share (memoria y "
            "cores): LAIM trabaja más (inferencia + malla + SSH). Un "
            "monopuesto que solo *usa* `laim remote` hacia otros hosts "
            "puede quedarse en su fila; si además es el Share, dimensione "
            "como Share.",
            "",
            "### Colas y horarios de poco impacto",
            "",
            "LAIM no tiene que hacerlo todo a la vez. El **Gestor de colas** "
            "(Config › Internal) y las **tareas programadas** (Asesor → "
            "Programar, descargas `model_download`, `laim eval`) permiten "
            "dejar pulls, evaluaciones y comparativas en **valle** (noche, "
            "fin de semana). Así un Share con poca holgura atiende el chat "
            "de día y reserva GPU para trabajo pesado cuando no hay "
            "clientes. Si el hardware no da para un tier, `init` **no lo "
            "encola**.",
            "",
            "### Reutilizar memoria: KV-cache y ajustes internos",
            "",
            "El cliente ya adapta LAIM al hardware. Ejemplos que conviene "
            "tocar **antes** de comprar más GPU:",
            "",
            "| Ajuste | Dónde | Qué gana |",
            "|--------|-------|----------|",
            "| **`num_ctx` / límite de contexto** | Internal › Local → Ventana de contexto | Menos KV-cache: 8B a 4k ≈ 6 GB; a 16k pide ~12 GB. En 6–8 GB deje 4096–8192 |",
            "| **Chat Context Summarized** | misma sección (umbral 85 %) | Comprime historial con el tier medio; libera VRAM sin cortar el chat |",
            "| **`keep_alive`** | misma sección / adaptador | Minutos en VRAM. Silicon ≥16 GB usa `-1` (no recargar). En poca memoria, 5 min o 0 |",
            "| **Warmup** | Modelos IA → Precalentamiento | Precarga Rápido+Medio; Lento antes de F6; descarga el resto |",
            "| **Slots / `OLLAMA_NUM_PARALLEL`** | Internal › Local → Paralelismo | Más cores útiles solo si hay VRAM. Silicon 8 GB → 1 slot; 24 GB → 2/3 modelos |",
            "| **`OLLAMA_MAX_LOADED_MODELS`** | pista del adaptador | Cuántos tiers pueden quedar calientes |",
            "| **Flash Attention + KV `q8_0`** | adaptador Apple Silicon | Menos VRAM en contextos largos (`OLLAMA_FLASH_ATTENTION=1`) |",
            "| **Familias blue/green** | Modelos IA → Familias | Cambiar de juego de modelos sin redimensionar el host |",
            "| **Cuantización Q4** | `laim catalog` | ~1 GB VRAM por 1B de parámetros; Q8/FP16 pide el doble o más |",
            "",
            "Mida después con **⚡ Memoria** / `ollama ps` y el **Asesor**. "
            "Si VRAM=0, el modelo corre en CPU: baje tamaño o contexto, no "
            "suba slots.",
        )
    )
