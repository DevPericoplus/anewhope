"""Guion de la guía gráfica de escenarios LAIM."""

from __future__ import annotations

from typing import Any

ESCENARIO_DEFAULT_ID = "share_multi"
ESCENARIO_STEP_SECONDS = 2.8
PACKET_REV_LABELS = frozenset({"TOKENS"})

GPU_IDLE = "idle"
GPU_INFER = "infer"
GPU_QUEUE = "queue"
GPU_HOT = "hot"

_SCENARIOS: list[dict[str, Any]] = [
    {
        "id": ESCENARIO_DEFAULT_ID,
        "number": 1,
        "title": "Varios Connect, un Share",
        "summary": "Clientes ligeros usan la IA de un único equipo con GPU.",
        "command": "laim connect   ·   laim share",
        "show_queue": True,
        "nodes": [
            {"id": "share", "label": "LAIM Share", "role": "share", "left": "50%", "top": "22%", "gpu": True},
            {"id": "c1", "label": "Connect A", "role": "connect", "left": "16%", "top": "78%", "gpu": False},
            {"id": "c2", "label": "Connect B", "role": "connect", "left": "50%", "top": "84%", "gpu": False},
            {"id": "c3", "label": "Connect C", "role": "connect", "left": "84%", "top": "78%", "gpu": False},
        ],
        "edges": [
            {"id": "c1-share", "x1": 16, "y1": 78, "x2": 50, "y2": 22, "kind": "ai", "mx": 33, "my": 50},
            {"id": "c2-share", "x1": 50, "y1": 84, "x2": 50, "y2": 22, "kind": "ai", "mx": 50, "my": 53},
            {"id": "c3-share", "x1": 84, "y1": 78, "x2": 50, "y2": 22, "kind": "ai", "mx": 67, "my": 50},
        ],
        "steps": [
            {
                "caption": "Share en reposo. Cola GPU vacía: 2 slots Ollama libres. Nada preemptivo.",
                "gpu": GPU_IDLE,
                "active_edges": [],
                "lit_nodes": ["share"],
                "packet_edge": "",
                "packet_label": "",
                "queue_slots": "0/2",
                "queue_note": "ClaimNextQueuedByGroup · grupo GPU",
                "queue_jobs": [],
            },
            {
                "caption": "Connect A hace queue_submit(chat, P2). El job entra en la cola del Share.",
                "gpu": GPU_IDLE,
                "active_edges": ["c1-share"],
                "lit_nodes": ["c1", "share"],
                "packet_edge": "c1-share",
                "packet_label": "SUBMIT",
                "queue_slots": "0/2",
                "queue_note": "chat/direct = P2 por defecto",
                "queue_jobs": [
                    {"client": "A", "kind": "chat", "prio": "P2", "status": "queued", "detail": "created_at"},
                ],
            },
            {
                "caption": "Un worker reclama el job (claim atómico) y toma el slot 1. GPU en inferencia.",
                "gpu": GPU_INFER,
                "active_edges": ["c1-share"],
                "lit_nodes": ["share"],
                "packet_edge": "c1-share",
                "packet_label": "CLAIM",
                "queue_slots": "1/2",
                "queue_note": "AcquireOllamaSlot · el job en curso no se corta",
                "queue_jobs": [
                    {"client": "A", "kind": "chat", "prio": "P2", "status": "running", "detail": "slot 1"},
                ],
            },
            {
                "caption": "Tokens hacia A. El slot sigue ocupado hasta que el stream termina.",
                "gpu": GPU_INFER,
                "active_edges": ["c1-share"],
                "lit_nodes": ["c1", "share"],
                "packet_edge": "c1-share",
                "packet_label": "TOKENS",
                "queue_slots": "1/2",
                "queue_note": "slot 2 aún libre",
                "queue_jobs": [
                    {"client": "A", "kind": "chat", "prio": "P2", "status": "running", "detail": "slot 1"},
                ],
            },
            {
                "caption": "B envía chat P2 y C envía teacher P3. A no se interrumpe: quedan en cola.",
                "gpu": GPU_QUEUE,
                "active_edges": ["c1-share", "c2-share", "c3-share"],
                "lit_nodes": ["c1", "c2", "c3", "share"],
                "packet_edge": "c2-share",
                "packet_label": "ENQUEUE",
                "queue_slots": "1/2",
                "queue_note": "P2 antes que P3 · FIFO a igualdad",
                "queue_jobs": [
                    {"client": "A", "kind": "chat", "prio": "P2", "status": "running", "detail": "slot 1"},
                    {"client": "B", "kind": "chat", "prio": "P2", "status": "queued", "detail": "espera slot"},
                    {"client": "C", "kind": "teacher", "prio": "P3", "status": "queued", "detail": "prioridad baja"},
                ],
            },
            {
                "caption": "Slot 2 libre: claim de B (P2). C (P3) sigue esperando. Cola saturada (2/2).",
                "gpu": GPU_HOT,
                "active_edges": ["c1-share", "c2-share", "c3-share"],
                "lit_nodes": ["c1", "c2", "c3", "share"],
                "packet_edge": "c2-share",
                "packet_label": "CLAIM",
                "queue_slots": "2/2",
                "queue_note": "OLLAMA_NUM_PARALLEL=2 · sin preempción",
                "queue_jobs": [
                    {"client": "A", "kind": "chat", "prio": "P2", "status": "running", "detail": "slot 1"},
                    {"client": "B", "kind": "chat", "prio": "P2", "status": "running", "detail": "slot 2"},
                    {"client": "C", "kind": "teacher", "prio": "P3", "status": "queued", "detail": "espera hueco"},
                ],
            },
            {
                "caption": "A termina y libera el slot. Claim de C (teacher). B sigue en su slot.",
                "gpu": GPU_QUEUE,
                "active_edges": ["c2-share", "c3-share"],
                "lit_nodes": ["c2", "c3", "share"],
                "packet_edge": "c3-share",
                "packet_label": "CLAIM",
                "queue_slots": "2/2",
                "queue_note": "A done → C claimed",
                "queue_jobs": [
                    {"client": "B", "kind": "chat", "prio": "P2", "status": "running", "detail": "slot 2"},
                    {"client": "C", "kind": "teacher", "prio": "P3", "status": "running", "detail": "slot 1"},
                    {"client": "A", "kind": "chat", "prio": "P2", "status": "done", "detail": "liberado"},
                ],
            },
        ],
    },
    {
        "id": "remote_ssh",
        "number": 2,
        "title": "Un Connect, varias máquinas",
        "summary": "Desde un LAIM se abre SSH a varios hosts y la IA acompaña cada sesión.",
        "command": "laim remote   ·   laim connect",
        "nodes": [
            {"id": "connect", "label": "LAIM Connect", "role": "connect", "left": "24%", "top": "50%", "gpu": False},
            {"id": "h1", "label": "Host Linux", "role": "host", "left": "78%", "top": "20%", "gpu": False},
            {"id": "h2", "label": "Host Windows", "role": "host", "left": "84%", "top": "50%", "gpu": False},
            {"id": "h3", "label": "Host macOS", "role": "host", "left": "78%", "top": "80%", "gpu": False},
        ],
        "edges": [
            {"id": "ssh1", "x1": 24, "y1": 50, "x2": 78, "y2": 20, "kind": "ssh", "mx": 51, "my": 35},
            {"id": "ssh2", "x1": 24, "y1": 50, "x2": 84, "y2": 50, "kind": "ssh", "mx": 54, "my": 50},
            {"id": "ssh3", "x1": 24, "y1": 50, "x2": 78, "y2": 80, "kind": "ssh", "mx": 51, "my": 65},
        ],
        "steps": [
            {
                "caption": "Un operador con LAIM Connect. Las máquinas remotas están en espera.",
                "gpu": GPU_IDLE,
                "active_edges": [],
                "lit_nodes": ["connect"],
                "packet_edge": "",
                "packet_label": "",
            },
            {
                "caption": "Se abre la sesión SSH al host Linux (`laim remote`).",
                "gpu": GPU_IDLE,
                "active_edges": ["ssh1"],
                "lit_nodes": ["connect", "h1"],
                "packet_edge": "ssh1",
                "packet_label": "SSH",
            },
            {
                "caption": "Segunda consola: Windows por SSH/WinRM. Cada sesión es independiente.",
                "gpu": GPU_IDLE,
                "active_edges": ["ssh1", "ssh2"],
                "lit_nodes": ["connect", "h1", "h2"],
                "packet_edge": "ssh2",
                "packet_label": "SSH",
            },
            {
                "caption": "Tercer host (macOS). Un solo LAIM, tres terminales.",
                "gpu": GPU_IDLE,
                "active_edges": ["ssh1", "ssh2", "ssh3"],
                "lit_nodes": ["connect", "h1", "h2", "h3"],
                "packet_edge": "ssh3",
                "packet_label": "SSH",
            },
            {
                "caption": "La IA de soporte se engancha a la sesión Linux (diagnóstico en contexto).",
                "gpu": GPU_INFER,
                "active_edges": ["ssh1"],
                "lit_nodes": ["connect", "h1"],
                "packet_edge": "ssh1",
                "packet_label": "IA",
            },
            {
                "caption": "Misma IA, otra máquina: el chat no mezcla las consolas.",
                "gpu": GPU_INFER,
                "active_edges": ["ssh2"],
                "lit_nodes": ["connect", "h2"],
                "packet_edge": "ssh2",
                "packet_label": "IA",
            },
        ],
    },
    {
        "id": "combo_bastion",
        "number": 3,
        "title": "Varios Share + Remote bastión",
        "summary": "Clientes eligen GPU y, desde el Share, saltan a máquinas que no ven.",
        "command": "laim connect   ·   laim share   ·   laim remote",
        "show_queue": True,
        "nodes": [
            {"id": "sa", "label": "Share GPU-A", "role": "share", "left": "32%", "top": "18%", "gpu": True},
            {"id": "sb", "label": "Share GPU-B", "role": "share", "left": "68%", "top": "18%", "gpu": True},
            {"id": "c1", "label": "Connect 1", "role": "connect", "left": "20%", "top": "82%", "gpu": False},
            {"id": "c2", "label": "Connect 2", "role": "connect", "left": "50%", "top": "86%", "gpu": False},
            {"id": "ha", "label": "Host A", "role": "host", "left": "14%", "top": "40%", "gpu": False},
            {"id": "hb", "label": "Host B", "role": "host", "left": "86%", "top": "40%", "gpu": False},
        ],
        "edges": [
            {"id": "c1-sa", "x1": 20, "y1": 82, "x2": 32, "y2": 18, "kind": "ai", "mx": 26, "my": 50},
            {"id": "c2-sb", "x1": 50, "y1": 86, "x2": 68, "y2": 18, "kind": "ai", "mx": 59, "my": 52},
            {"id": "sa-ha", "x1": 32, "y1": 18, "x2": 14, "y2": 40, "kind": "ssh", "mx": 23, "my": 29},
            {"id": "sb-hb", "x1": 68, "y1": 18, "x2": 86, "y2": 40, "kind": "ssh", "mx": 77, "my": 29},
        ],
        "steps": [
            {
                "caption": "Dos Share con GPU distintas. Los Connect aún no eligen destino.",
                "gpu": GPU_IDLE,
                "active_edges": [],
                "lit_nodes": ["sa", "sb"],
                "packet_edge": "",
                "packet_label": "",
                "queue_slots": "0/2",
                "queue_note": "cada Share tiene su cola GPU",
                "queue_jobs": [],
            },
            {
                "caption": "Connect 1 apunta al Share GPU-A (cliente ligero).",
                "gpu": GPU_INFER,
                "active_edges": ["c1-sa"],
                "lit_nodes": ["c1", "sa"],
                "packet_edge": "c1-sa",
                "packet_label": "SUBMIT",
                "queue_slots": "1/2",
                "queue_note": "GPU-A · cola propia",
                "queue_jobs": [
                    {"client": "1", "kind": "chat", "prio": "P2", "status": "running", "detail": "GPU-A slot 1"},
                ],
            },
            {
                "caption": "Connect 2 usa GPU-B. Cada Share tiene su propia cola GPU.",
                "gpu": GPU_QUEUE,
                "active_edges": ["c1-sa", "c2-sb"],
                "lit_nodes": ["c1", "c2", "sa", "sb"],
                "packet_edge": "c2-sb",
                "packet_label": "SUBMIT",
                "queue_slots": "1/2",
                "queue_note": "dos masters · dos colas",
                "queue_jobs": [
                    {"client": "1", "kind": "chat", "prio": "P2", "status": "running", "detail": "GPU-A slot 1"},
                    {"client": "2", "kind": "chat", "prio": "P2", "status": "running", "detail": "GPU-B slot 1"},
                ],
            },
            {
                "caption": "Desde GPU-A se abre Remote al Host A: el Share es bastión.",
                "gpu": GPU_INFER,
                "active_edges": ["c1-sa", "sa-ha"],
                "lit_nodes": ["c1", "sa", "ha"],
                "packet_edge": "sa-ha",
                "packet_label": "SSH",
                "queue_slots": "1/2",
                "queue_note": "SSH no ocupa slot GPU; el chat de A sigue",
                "queue_jobs": [
                    {"client": "1", "kind": "chat", "prio": "P2", "status": "running", "detail": "GPU-A slot 1"},
                ],
            },
            {
                "caption": "GPU-B hace lo mismo hacia Host B. El portátil no ve esas redes.",
                "gpu": GPU_QUEUE,
                "active_edges": ["c2-sb", "sb-hb"],
                "lit_nodes": ["c2", "sb", "hb"],
                "packet_edge": "sb-hb",
                "packet_label": "SSH",
                "queue_slots": "1/2",
                "queue_note": "GPU-B · SSH no corta el chat",
                "queue_jobs": [
                    {"client": "2", "kind": "chat", "prio": "P2", "status": "running", "detail": "GPU-B slot 1"},
                ],
            },
            {
                "caption": "Suma: varias GPU + salto Remote. El Share es cerebro y puerta.",
                "gpu": GPU_HOT,
                "active_edges": ["c1-sa", "c2-sb", "sa-ha", "sb-hb"],
                "lit_nodes": ["c1", "c2", "sa", "sb", "ha", "hb"],
                "packet_edge": "",
                "packet_label": "",
                "queue_slots": "2/2",
                "queue_note": "dos masters · colas independientes",
                "queue_jobs": [
                    {"client": "1", "kind": "chat", "prio": "P2", "status": "running", "detail": "GPU-A slot 1"},
                    {"client": "2", "kind": "chat", "prio": "P2", "status": "running", "detail": "GPU-B slot 1"},
                ],
            },
        ],
    },
    {
        "id": "mesh_headscale",
        "number": 4,
        "title": "Malla Headscale + Tailscale",
        "summary": "Un LAIM con Headscale une nodos remotos; el cliente Tailscale entra a la mesh.",
        "command": "laim   ·   headscale   ·   tailscale",
        "nodes": [
            {"id": "hs", "label": "LAIM + Headscale", "role": "mesh", "left": "50%", "top": "48%", "gpu": False},
            {"id": "n1", "label": "Nodo remoto 1", "role": "remote", "left": "18%", "top": "18%", "gpu": False},
            {"id": "n2", "label": "Nodo remoto 2", "role": "remote", "left": "82%", "top": "18%", "gpu": False},
            {"id": "n3", "label": "Nodo remoto 3", "role": "remote", "left": "18%", "top": "82%", "gpu": False},
            {"id": "ts", "label": "Cliente Tailscale", "role": "connect", "left": "82%", "top": "82%", "gpu": False},
        ],
        "edges": [
            {"id": "hs-n1", "x1": 50, "y1": 48, "x2": 18, "y2": 18, "kind": "mesh", "mx": 34, "my": 33},
            {"id": "hs-n2", "x1": 50, "y1": 48, "x2": 82, "y2": 18, "kind": "mesh", "mx": 66, "my": 33},
            {"id": "hs-n3", "x1": 50, "y1": 48, "x2": 18, "y2": 82, "kind": "mesh", "mx": 34, "my": 65},
            {"id": "hs-ts", "x1": 50, "y1": 48, "x2": 82, "y2": 82, "kind": "mesh", "mx": 66, "my": 65},
        ],
        "steps": [
            {
                "caption": "El LAIM publica Headscale: plano de control de la malla.",
                "gpu": GPU_IDLE,
                "active_edges": [],
                "lit_nodes": ["hs"],
                "packet_edge": "",
                "packet_label": "",
            },
            {
                "caption": "El nodo remoto 1 se registra en la mesh.",
                "gpu": GPU_IDLE,
                "active_edges": ["hs-n1"],
                "lit_nodes": ["hs", "n1"],
                "packet_edge": "hs-n1",
                "packet_label": "JOIN",
            },
            {
                "caption": "Nodos 2 y 3 se unen. Los cables de malla no son SSH clásico.",
                "gpu": GPU_IDLE,
                "active_edges": ["hs-n1", "hs-n2", "hs-n3"],
                "lit_nodes": ["hs", "n1", "n2", "n3"],
                "packet_edge": "hs-n2",
                "packet_label": "JOIN",
            },
            {
                "caption": "Un cliente Tailscale entra como un peer más de la red.",
                "gpu": GPU_IDLE,
                "active_edges": ["hs-n1", "hs-n2", "hs-n3", "hs-ts"],
                "lit_nodes": ["hs", "ts"],
                "packet_edge": "hs-ts",
                "packet_label": "PEER",
            },
            {
                "caption": "Tráfico mesh: LAIM no sustituye la VPN, la orquesta.",
                "gpu": GPU_INFER,
                "active_edges": ["hs-n1", "hs-n2", "hs-n3", "hs-ts"],
                "lit_nodes": ["hs", "n1", "n2", "n3", "ts"],
                "packet_edge": "hs-n3",
                "packet_label": "MESH",
            },
            {
                "caption": "Acceso a la malla con LAIM y el cliente Tailscale a la vez.",
                "gpu": GPU_INFER,
                "active_edges": ["hs-ts", "hs-n1"],
                "lit_nodes": ["hs", "ts", "n1"],
                "packet_edge": "hs-ts",
                "packet_label": "OK",
            },
        ],
    },
    {
        "id": "perimetro",
        "number": 5,
        "title": "Internet → LAN de empresa",
        "summary": "Un LAIM en la red local es el único hueco: mesh, Remote y Share internos.",
        "command": "laim connect   ·   laim remote   ·   laim share",
        "show_queue": True,
        "nodes": [
            {"id": "wan", "label": "Equipo en Internet", "role": "connect", "left": "12%", "top": "50%", "gpu": False},
            {"id": "bastion", "label": "LAIM bastión", "role": "bastion", "left": "42%", "top": "50%", "gpu": False},
            {"id": "share", "label": "Share interno", "role": "share", "left": "80%", "top": "24%", "gpu": True},
            {"id": "files", "label": "Servidor ficheros", "role": "host", "left": "82%", "top": "52%", "gpu": False},
            {"id": "pc", "label": "PC interno", "role": "host", "left": "80%", "top": "80%", "gpu": False},
        ],
        "edges": [
            {"id": "wan-bas", "x1": 12, "y1": 50, "x2": 42, "y2": 50, "kind": "wan", "mx": 27, "my": 50},
            {"id": "bas-share", "x1": 42, "y1": 50, "x2": 80, "y2": 24, "kind": "ai", "mx": 61, "my": 37},
            {"id": "bas-files", "x1": 42, "y1": 50, "x2": 82, "y2": 52, "kind": "ssh", "mx": 62, "my": 51},
            {"id": "bas-pc", "x1": 42, "y1": 50, "x2": 80, "y2": 80, "kind": "ssh", "mx": 61, "my": 65},
        ],
        "steps": [
            {
                "caption": "Fuera de la empresa: un portátil en Internet. La LAN no está expuesta.",
                "gpu": GPU_IDLE,
                "active_edges": [],
                "lit_nodes": ["wan"],
                "packet_edge": "",
                "packet_label": "",
            },
            {
                "caption": "El tráfico entra solo por el LAIM bastión (perímetro).",
                "gpu": GPU_IDLE,
                "active_edges": ["wan-bas"],
                "lit_nodes": ["wan", "bastion"],
                "packet_edge": "wan-bas",
                "packet_label": "WAN",
            },
            {
                "caption": "El bastión gestiona la mesh hacia recursos internos.",
                "gpu": GPU_IDLE,
                "active_edges": ["wan-bas", "bas-pc"],
                "lit_nodes": ["bastion", "pc"],
                "packet_edge": "bas-pc",
                "packet_label": "MESH",
            },
            {
                "caption": "`laim remote` al servidor de ficheros: salto interno, no DNAT público.",
                "gpu": GPU_IDLE,
                "active_edges": ["wan-bas", "bas-files"],
                "lit_nodes": ["bastion", "files"],
                "packet_edge": "bas-files",
                "packet_label": "SSH",
            },
            {
                "caption": "O bien se usa el Share interno: la GPU de empresa sirve la IA.",
                "gpu": GPU_INFER,
                "active_edges": ["wan-bas", "bas-share"],
                "lit_nodes": ["wan", "bastion", "share"],
                "packet_edge": "bas-share",
                "packet_label": "SUBMIT",
                "queue_slots": "1/2",
                "queue_note": "Share interno · queue_submit P2",
                "queue_jobs": [
                    {"client": "WAN", "kind": "chat", "prio": "P2", "status": "running", "detail": "slot 1"},
                ],
            },
            {
                "caption": "Un solo punto de entrada. Remote y Share no se publican a Internet.",
                "gpu": GPU_QUEUE,
                "active_edges": ["wan-bas", "bas-share", "bas-files", "bas-pc"],
                "lit_nodes": ["wan", "bastion", "share", "files", "pc"],
                "packet_edge": "bas-share",
                "packet_label": "TOKENS",
                "queue_slots": "1/2",
                "queue_note": "tokens por el bastión · slot aún ocupado",
                "queue_jobs": [
                    {"client": "WAN", "kind": "chat", "prio": "P2", "status": "running", "detail": "slot 1"},
                ],
            },
        ],
    },
]


def list_escenario_ids() -> list[str]:
    """Identificadores en orden de menú."""
    return [str(item["id"]) for item in _SCENARIOS]


def get_escenario(escenario_id: str) -> dict[str, Any]:
    """Devuelve el escenario o el primero si el id no existe."""
    for item in _SCENARIOS:
        if item["id"] == escenario_id:
            return item
    return _SCENARIOS[0]


def escenario_step_count(escenario_id: str) -> int:
    """Número de fases del escenario."""
    return len(get_escenario(escenario_id)["steps"])


def list_escenario_cards() -> list[dict[str, Any]]:
    """Tarjetas del selector (sin geometría)."""
    cards: list[dict[str, Any]] = []
    for item in _SCENARIOS:
        cards.append(
            {
                "id": item["id"],
                "number": item["number"],
                "heading": f"{item['number']}. {item['title']}",
                "title": item["title"],
                "summary": item["summary"],
            }
        )
    return cards


def wire_curve_d(x1: float, y1: float, x2: float, y2: float) -> str:
    """Curva Bézier del cable, mismo criterio que el Network Monitor de LAIM."""
    dx = (x2 - x1) * 0.35
    dy = (y2 - y1) * 0.35
    return (
        f"M{x1:g},{y1:g} "
        f"C{x1 + dx:g},{y1 + dy * 0.5:g} "
        f"{x2 - dx:g},{y2 - dy * 0.5:g} "
        f"{x2:g},{y2:g}"
    )


def infer_packet_dir(label: str) -> str:
    """TOKENS vuelve al cliente; el resto viaja hacia el destino del cable."""
    return "rev" if label in PACKET_REV_LABELS else "fwd"


def _packet_position(scenario: dict[str, Any], edge_id: str) -> tuple[str, str]:
    """Punto medio del cable activo para el paquete."""
    for edge in scenario["edges"]:
        if edge["id"] == edge_id:
            return f"{edge['mx']}%", f"{edge['my']}%"
    return "50%", "50%"


def _edge_kind_map(scenario: dict[str, Any]) -> dict[str, str]:
    """Tipo de cable (ai/ssh/mesh/wan) por id."""
    return {str(edge["id"]): str(edge["kind"]) for edge in scenario["edges"]}


def _traffic_packets(
    scenario: dict[str, Any],
    step: dict[str, Any],
    packet_dir: str,
) -> list[dict[str, Any]]:
    """Paquetes de la fase: el principal lleva etiqueta; el resto solo la flecha."""
    kinds = _edge_kind_map(scenario)
    packet_edge = str(step["packet_edge"])
    packets: list[dict[str, Any]] = []
    if packet_edge:
        packets.append(
            {
                "edge": packet_edge,
                "label": str(step["packet_label"]),
                "reverse": packet_dir == "rev",
                "kind": kinds.get(packet_edge, "ai"),
                "primary": True,
            }
        )
    for edge_id in step["active_edges"]:
        if edge_id == packet_edge:
            continue
        packets.append(
            {
                "edge": str(edge_id),
                "label": "",
                "reverse": False,
                "kind": kinds.get(str(edge_id), "ai"),
                "primary": False,
            }
        )
    return packets


def build_escenario_view(escenario_id: str, step_index: int) -> dict[str, Any]:
    """Vista lista para la UI: nodos, cables, paquete y textos de la fase."""
    scenario = get_escenario(escenario_id)
    steps: list[dict[str, Any]] = scenario["steps"]
    total = len(steps)
    safe_index = min(max(step_index, 0), total - 1)
    step = steps[safe_index]
    active = set(step["active_edges"])
    lit = set(step["lit_nodes"])
    gpu = str(step["gpu"])
    packet_edge = str(step["packet_edge"])
    packet_label = str(step["packet_label"])
    packet_dir = infer_packet_dir(packet_label)
    packet_x, packet_y = _packet_position(scenario, packet_edge)
    traffic = _traffic_packets(scenario, step, packet_dir)
    queue_jobs = [
        {
            "client": str(job.get("client", "")),
            "kind": str(job.get("kind", "")),
            "prio": str(job.get("prio", "P2")),
            "status": str(job.get("status", "queued")),
            "detail": str(job.get("detail", "")),
        }
        for job in step.get("queue_jobs", [])
        if isinstance(job, dict)
    ]
    show_queue = bool(scenario.get("show_queue"))

    nodes: list[dict[str, Any]] = []
    for node in scenario["nodes"]:
        node_id = str(node["id"])
        classes = ["esc-node", f"esc-role-{node['role']}"]
        if node.get("gpu"):
            classes.append(f"esc-gpu-{gpu}")
        if node_id in lit:
            classes.append("esc-lit")
        nodes.append(
            {
                "id": node_id,
                "label": node["label"],
                "role": str(node["role"]).upper(),
                "left": node["left"],
                "top": node["top"],
                "class_name": " ".join(classes),
            }
        )

    edges: list[dict[str, Any]] = []
    for edge in scenario["edges"]:
        wire_class = f"esc-wire esc-wire-{edge['kind']}"
        if edge["id"] in active:
            wire_class += " esc-wire-active"
        edges.append(
            {
                "id": edge["id"],
                "x1": edge["x1"],
                "y1": edge["y1"],
                "x2": edge["x2"],
                "y2": edge["y2"],
                "class_name": wire_class,
            }
        )

    return {
        "id": scenario["id"],
        "number": scenario["number"],
        "title": scenario["title"],
        "summary": scenario["summary"],
        "command": scenario["command"],
        "step_label": f"{safe_index + 1}/{total}",
        "caption": step["caption"],
        "gpu": gpu,
        "lit_csv": "|" + "|".join(step["lit_nodes"]) + "|",
        "active_csv": "|" + "|".join(step["active_edges"]) + "|",
        "nodes": nodes,
        "edges": edges,
        "packet_visible": bool(packet_edge),
        "packet_x": packet_x,
        "packet_y": packet_y,
        "packet_label": packet_label,
        "packet_dir": packet_dir,
        "packet_edge": packet_edge,
        "traffic": traffic,
        "show_queue": show_queue,
        "queue_slots": str(step.get("queue_slots", "0/2")),
        "queue_note": str(step.get("queue_note", "")),
        "queue_jobs": queue_jobs,
        "last_step": safe_index >= total - 1,
    }
