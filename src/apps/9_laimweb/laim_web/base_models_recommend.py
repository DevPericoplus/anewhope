"""Mini-guía «Modelo recomendado para mi equipo».

Cifras alineadas con el cliente: ~1 GB de VRAM por 1B de parámetros en Q4
(`library.dat`), con margen para KV-cache y warmup (dos modelos). A 12 GB
el techo es 9b, como pide esta página.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MemorySizeRow:
    """Una fila de la tabla memoria → tamaño máximo de modelo."""

    memory_gb: int
    max_params: str
    typical_range: str
    examples: str


# Techos Q4: más memoria → modelos más grandes; menos memoria recorta el máximo.
MEMORY_SIZE_ROWS: tuple[MemorySizeRow, ...] = (
    MemorySizeRow(6, "2b", "1.5b–2b", "qwen3.5:2b, qwen2.5-coder:1.5b-base"),
    MemorySizeRow(12, "9b", "2b–9b", "gemma3:4b, qwen3.5:4b, llama3.1:8b, qwen3.5:9b"),
    MemorySizeRow(20, "14b", "4b–14b", "gemma4:12b, qwen3:14b"),
    MemorySizeRow(24, "16b", "8b–16b", "gemma4:12b, deepseek-coder-v2:16b"),
    MemorySizeRow(36, "27b", "9b–27b", "qwen3.8:27b"),
    MemorySizeRow(48, "32b", "14b–32b", "qwen3:32b (Q4)"),
    MemorySizeRow(64, "70b (Q4)", "27b–70b", "70b Q4; varios 9b–27b a la vez"),
    MemorySizeRow(128, "70b+", "varios grandes", "70b Q5 / 72b + warmup de varios tiers"),
)


def memory_table_markdown() -> str:
    """Tabla Markdown memoria → techo de parámetros."""
    lines = [
        "| Memoria GPU / unificada | Tamaño máximo (Q4) | Rango habitual | Ejemplos |",
        "|-------------------------|--------------------|----------------|----------|",
    ]
    for row in MEMORY_SIZE_ROWS:
        lines.append(
            f"| {row.memory_gb} GB | {row.max_params} | {row.typical_range} | `{row.examples}` |"
        )
    return "\n".join(lines)


def recommend_guide_markdown() -> str:
    """Cuerpo de la mini-guía (markdown CRT)."""
    return "\n".join(
        (
            "Mire **cores de GPU** y **memoria** de *este* equipo. Los cores "
            "permiten más inferencias a la vez **si la memoria llega**. La "
            "memoria fija el **tamaño máximo** del modelo.",
            "",
            "### Cómo ver cores y memoria",
            "",
            "En el cliente: **`laim info`** (CPU, GPU, VRAM o RAM unificada). "
            "También Config › Modelos IA › **🧭 Asesor** (puntúa contra ese hardware).",
            "",
            "| Sistema | Cores de GPU | Memoria |",
            "|---------|--------------|---------|",
            "| **Windows / Linux (NVIDIA)** | `nvidia-smi` (nombre y recuento) | `nvidia-smi --query-gpu=memory.total --format=csv` |",
            "| **Linux (AMD)** | `rocm-smi` | misma herramienta, VRAM |",
            "| **macOS Apple Silicon** | Acerca de este Mac / `system_profiler SPDisplaysDataType` (p. ej. «40-core GPU») | RAM **unificada** (CPU+GPU), no VRAM PCIe. LAIM la trata como el techo de modelo |",
            "| **Mac Intel** | suele ser CPU | no dimensione como si hubiera VRAM NVIDIA |",
            "",
            "En chat, el caso **gpu** / **vram_usage** lee esos mismos datos en vivo.",
            "",
            "### Cores: concurrencia de inferencias",
            "",
            "Más cores (o una GPU holgada) permiten **más inferencias en paralelo**. "
            "Solo súbalas si **queda memoria** para el modelo, el KV-cache y, si "
            "usa warmup, un segundo modelo.",
            "",
            "En el cliente: **Internal › Local → Paralelismo Ollama** "
            "(`OllamaSlotManager`, slots, workers) y las pistas "
            "`OLLAMA_NUM_PARALLEL` / `OLLAMA_MAX_LOADED_MODELS` del demonio. "
            "Regla del Core: capacidad LAIM ≤ `OLLAMA_NUM_PARALLEL`.",
            "",
            "- GPU infrautilizada y latencia alta → subir slots/`NUM_PARALLEL` **con margen de memoria**.",
            "- OOM o descargas constantes → bajar slots y tamaño de modelo; no suba concurrencia.",
            "- Apple Silicon: el adaptador ya recorta (p. ej. 8 GB → 1 slot; 24 GB → 2 slots / 3 modelos).",
            "",
            "### Memoria: el techo del tamaño",
            "",
            "La memoria (VRAM dedicada o RAM unificada) **limita el tamaño**. "
            "Orientación Q4: ~1 GB por 1B de parámetros, dejando hueco a contexto "
            "y warmup. A **12 GB** el máximo razonable es **9b**. Menos memoria "
            "recorta el techo; más memoria abre 14b, 27b, 70b…",
            "",
            memory_table_markdown(),
            "",
            "Los ejemplos son tamaños de referencia (mismas familias que el "
            "catálogo de desarrollo). Una cuantización más baja cabe en menos "
            "memoria; Q8 o FP16 pide el doble o más.",
            "",
            "### Warmup: varios modelos en memoria, a propósito",
            "",
            "El **precalentamiento** (Config › Modelos IA › Precalentamiento) "
            "carga de forma **predictiva** los tiers que LAIM va a usar: al "
            "abrir chat, **Rápido** y **Medio**; el **Lento** justo antes del "
            "reproceso (F6). Descarga los que no hacen falta (`keep_alive`) y "
            "deja en GPU los útiles para la actividad en curso.",
            "",
            "Por eso la tabla es un techo **por modelo**, no la suma de todos "
            "los tiers. Si quiere warmup de dos modelos a la vez, cada uno debe "
            "caber **con el otro**. **⚡ Memoria** (panel Herramientas) y "
            "`ollama ps` muestran qué hay cargado y cuánta VRAM ocupa.",
            "",
            "### Comprobar que el modelo sirve al tier",
            "",
            "Que quepa en memoria no basta. Verifique capacidades con las "
            "herramientas del cliente:",
            "",
            "1. **🔍 Capacidades** — thinking (no en Traductor/Rápido), tools "
            "(Medio/Lento), embedding (no es un tier de chat), visión/audio/coder "
            "para Imágenes / Sonido / Desarrollo.",
            "2. **🧭 Asesor** — *soportados* (caben) vs *recomendados* (encajan "
            "en el uso del slot). Un 4b puede ser recomendado en Rápido y solo "
            "soportado en Lento.",
            "3. **`laim eval`** o Evaluar en Inferencia directa, y **`laim compare`** "
            "/ Comparar — el benchmark público no sustituye su hardware.",
            "4. **📊 Analizar** y **⚡ Memoria** — scoring y VRAM real; VRAM=0 "
            "significa que corre en CPU.",
            "",
            "Así confirma que otro tamaño o versión (más pequeño si hay poca "
            "memoria, más grande si sobra) sigue cubriendo la función de cada tier.",
        )
    )
