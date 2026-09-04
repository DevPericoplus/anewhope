"""Avatares SVG deterministas al estilo boring-avatars (MIT).

Port de las utilidades y variantes oficiales:
https://github.com/boringdesigners/boring-avatars

La semilla es el nombre (u otra cadena). Misma entrada → mismo SVG.
"""

from __future__ import annotations

import base64
from typing import Final

VARIANTS: Final[tuple[str, ...]] = (
    "marble",
    "beam",
    "pixel",
    "sunset",
    "ring",
    "bauhaus",
)

VARIANT_LABELS: Final[dict[str, str]] = {
    "marble": "Mármol",
    "beam": "Haz",
    "pixel": "Pixel",
    "sunset": "Atardecer",
    "ring": "Anillo",
    "bauhaus": "Bauhaus",
}

PALETTE_CRT: Final[tuple[str, ...]] = (
    "#0a1a0a",
    "#146a3c",
    "#9dff9d",
    "#7dff7d",
    "#22c55e",
)
PALETTE_CLASSIC: Final[tuple[str, ...]] = (
    "#92A1C6",
    "#146A7C",
    "#F0AB3D",
    "#C271B4",
    "#C20D90",
)
PALETTE_AMBER: Final[tuple[str, ...]] = (
    "#1a1200",
    "#FF8C00",
    "#ffb000",
    "#ffd59a",
    "#8B4513",
)
PALETTE_MIDNIGHT: Final[tuple[str, ...]] = (
    "#0b1220",
    "#1e3a5f",
    "#38bdf8",
    "#818cf8",
    "#22d3ee",
)

PALETTES: Final[dict[str, tuple[str, ...]]] = {
    "crt": PALETTE_CRT,
    "classic": PALETTE_CLASSIC,
    "amber": PALETTE_AMBER,
    "midnight": PALETTE_MIDNIGHT,
}

PALETTE_LABELS: Final[dict[str, str]] = {
    "crt": "Fósforo",
    "classic": "Clásica",
    "amber": "Ámbar",
    "midnight": "Medianoche",
}

DEFAULT_NAME: Final[str] = "LAIM"
DEFAULT_VARIANT: Final[str] = "marble"
DEFAULT_PALETTE_ID: Final[str] = "crt"


def hash_code(name: str) -> int:
    """Hash de 32 bits con signo, equivalente al de boring-avatars."""
    value = 0
    for character in name:
        value = _to_int32(((value << 5) - value) + ord(character))
    return abs(value)


def get_digit(number: int, ntn: int) -> int:
    """Dígito en la posición ntn (desde la derecha, 0-index)."""
    return int((number / (10**ntn)) % 10)


def get_boolean(number: int, ntn: int) -> bool:
    """True si el dígito en ntn es par."""
    return (get_digit(number, ntn) % 2) == 0


def get_unit(number: int, range_value: int, index: int | None = None) -> int:
    """Unidad acotada; puede invertirse según el dígito en ``index``."""
    if range_value == 0:
        return 0
    value = number % range_value
    if index and (get_digit(number, index) % 2) == 0:
        return -value
    return value


def get_random_color(number: int, colors: tuple[str, ...] | list[str]) -> str:
    """Color de la paleta a partir del hash."""
    if not colors:
        return "#000000"
    return colors[number % len(colors)]


def get_contrast(hex_color: str) -> str:
    """Negro o blanco según luminancia YIQ (texto sobre el color)."""
    raw = hex_color.lstrip("#")
    if len(raw) != 6:
        return "#FFFFFF"
    red = int(raw[0:2], 16)
    green = int(raw[2:4], 16)
    blue = int(raw[4:6], 16)
    yiq = ((red * 299) + (green * 587) + (blue * 114)) / 1000
    return "#000000" if yiq >= 128 else "#FFFFFF"


def resolve_palette(palette_id: str) -> tuple[str, ...]:
    """Devuelve la paleta o la CRT por defecto."""
    return PALETTES.get(palette_id, PALETTE_CRT)


def resolve_variant(variant: str) -> str:
    """Normaliza la variante o usa mármol."""
    clean = (variant or "").strip().lower()
    if clean in VARIANTS:
        return clean
    return DEFAULT_VARIANT


def resolve_seed(name: str) -> str:
    """Semilla no vacía para el generador."""
    clean = name.strip()
    return clean if clean else DEFAULT_NAME


def build_avatar_svg(
    name: str,
    *,
    variant: str = DEFAULT_VARIANT,
    colors: tuple[str, ...] | list[str] | None = None,
    palette_id: str = DEFAULT_PALETTE_ID,
    square: bool = False,
    size: int = 80,
) -> str:
    """Genera el SVG de un avatar determinista."""
    seed = resolve_seed(name)
    chosen = resolve_variant(variant)
    palette = tuple(colors) if colors else resolve_palette(palette_id)
    builders = {
        "marble": _svg_marble,
        "beam": _svg_beam,
        "pixel": _svg_pixel,
        "sunset": _svg_sunset,
        "ring": _svg_ring,
        "bauhaus": _svg_bauhaus,
    }
    return builders[chosen](seed, palette, square=square, size=size)


def svg_to_data_url(svg: str) -> str:
    """Convierte SVG a data URL para ``rx.image``."""
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def build_avatar_data_url(
    name: str,
    *,
    variant: str = DEFAULT_VARIANT,
    palette_id: str = DEFAULT_PALETTE_ID,
    square: bool = False,
    size: int = 80,
) -> str:
    """SVG del avatar como data URL."""
    return svg_to_data_url(
        build_avatar_svg(
            name,
            variant=variant,
            palette_id=palette_id,
            square=square,
            size=size,
        )
    )


def build_variant_preview_tiles(
    name: str,
    *,
    palette_id: str = DEFAULT_PALETTE_ID,
    square: bool = False,
    size: int = 80,
) -> list[dict[str, str]]:
    """Una ficha por variante para el selector del perfil."""
    tiles: list[dict[str, str]] = []
    for variant in VARIANTS:
        tiles.append(
            {
                "variant": variant,
                "label": VARIANT_LABELS[variant],
                "preview_url": build_avatar_data_url(
                    name,
                    variant=variant,
                    palette_id=palette_id,
                    square=square,
                    size=size,
                ),
            }
        )
    return tiles


def _to_int32(value: int) -> int:
    truncated = value & 0xFFFFFFFF
    if truncated >= 0x80000000:
        return truncated - 0x100000000
    return truncated


def _mask_id(variant: str, name: str) -> str:
    return f"ba_{variant}_{hash_code(f'{variant}:{name}')}"


def _rx_attr(square: bool, view: int) -> str:
    return "" if square else f' rx="{view}"'


def _svg_open(view: int, size: int, mask_id: str, square: bool) -> str:
    return (
        f'<svg viewBox="0 0 {view} {view}" fill="none" role="img" '
        f'xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}">'
        f'<mask id="{mask_id}" maskUnits="userSpaceOnUse" x="0" y="0" '
        f'width="{view}" height="{view}">'
        f'<rect width="{view}" height="{view}"{_rx_attr(square, view)} '
        f'fill="#FFFFFF"/></mask>'
        f'<g mask="url(#{mask_id})">'
    )


def _svg_close() -> str:
    return "</g></svg>"


def _svg_marble(
    name: str,
    colors: tuple[str, ...],
    *,
    square: bool,
    size: int,
) -> str:
    view = 80
    num = hash_code(name)
    props = []
    for index in range(3):
        props.append(
            {
                "color": get_random_color(num + index, colors),
                "tx": get_unit(num * (index + 1), view // 10, 1),
                "ty": get_unit(num * (index + 1), view // 10, 2),
                "scale": 1.2 + get_unit(num * (index + 1), view // 20) / 10,
                "rotate": get_unit(num * (index + 1), 360, 1),
            }
        )
    mask_id = _mask_id("marble", name)
    filter_id = f"filter_{mask_id}"
    path_one = (
        "M32.414 59.35L50.376 70.5H72.5v-71H33.728L26.5 13.381l19.057 "
        "27.08L32.414 59.35z"
    )
    path_two = (
        "M22.216 24L0 46.75l14.108 38.129L78 86l-3.081-59.276-22.378 "
        "4.005 12.698 15.262 10.118-16.282 24.198 32.07L22.216 24z"
    )
    return (
        f"{_svg_open(view, size, mask_id, square)}"
        f'<rect width="{view}" height="{view}" fill="{props[0]["color"]}"/>'
        f'<path filter="url(#{filter_id})" d="{path_one}" '
        f'fill="{props[1]["color"]}" '
        f'transform="translate({props[1]["tx"]} {props[1]["ty"]}) '
        f'rotate({props[1]["rotate"]} {view / 2} {view / 2}) '
        f'scale({props[1]["scale"]})"/>'
        f'<path filter="url(#{filter_id})" style="mix-blend-mode:overlay" '
        f'd="{path_two}" fill="{props[2]["color"]}" '
        f'transform="translate({props[2]["tx"]} {props[2]["ty"]}) '
        f'rotate({props[2]["rotate"]} {view / 2} {view / 2}) '
        f'scale({props[2]["scale"]})"/>'
        f"</g>"
        f"<defs><filter id=\"{filter_id}\" filterUnits=\"userSpaceOnUse\" "
        f'color-interpolation-filters="sRGB">'
        f'<feFlood flood-opacity="0" result="BackgroundImageFix"/>'
        f'<feBlend in="SourceGraphic" in2="BackgroundImageFix" result="shape"/>'
        f'<feGaussianBlur stdDeviation="7" result="effect1_foregroundBlur"/>'
        f"</filter></defs></svg>"
    )


def _svg_beam(
    name: str,
    colors: tuple[str, ...],
    *,
    square: bool,
    size: int,
) -> str:
    view = 36
    num = hash_code(name)
    wrapper_color = get_random_color(num, colors)
    pre_x = get_unit(num, 10, 1)
    wrapper_x = pre_x + view / 9 if pre_x < 5 else pre_x
    pre_y = get_unit(num, 10, 2)
    wrapper_y = pre_y + view / 9 if pre_y < 5 else pre_y
    wrapper_rotate = get_unit(num, 360)
    wrapper_scale = 1 + get_unit(num, view // 12) / 10
    is_mouth_open = get_boolean(num, 2)
    is_circle = get_boolean(num, 1)
    eye_spread = get_unit(num, 5)
    mouth_spread = get_unit(num, 3)
    face_rotate = get_unit(num, 10, 3)
    face_x = wrapper_x / 2 if wrapper_x > view / 6 else get_unit(num, 8, 1)
    face_y = wrapper_y / 2 if wrapper_y > view / 6 else get_unit(num, 7, 2)
    face_color = get_contrast(wrapper_color)
    background = get_random_color(num + 13, colors)
    wrapper_rx = view if is_circle else view / 6
    mouth_y = 19 + mouth_spread
    if is_mouth_open:
        mouth = (
            f'<path d="M15 {mouth_y}c2 1 4 1 6 0" stroke="{face_color}" '
            f'fill="none" stroke-linecap="round"/>'
        )
    else:
        mouth = (
            f'<path d="M13,{mouth_y}a1,0.75 0 0,0 10,0" fill="{face_color}"/>'
        )
    mask_id = _mask_id("beam", name)
    return (
        f"{_svg_open(view, size, mask_id, square)}"
        f'<rect width="{view}" height="{view}" fill="{background}"/>'
        f'<rect x="0" y="0" width="{view}" height="{view}" '
        f'transform="translate({wrapper_x} {wrapper_y}) '
        f'rotate({wrapper_rotate} {view / 2} {view / 2}) '
        f'scale({wrapper_scale})" fill="{wrapper_color}" rx="{wrapper_rx}"/>'
        f'<g transform="translate({face_x} {face_y}) '
        f'rotate({face_rotate} {view / 2} {view / 2})">'
        f"{mouth}"
        f'<rect x="{14 - eye_spread}" y="14" width="1.5" height="2" rx="1" '
        f'stroke="none" fill="{face_color}"/>'
        f'<rect x="{20 + eye_spread}" y="14" width="1.5" height="2" rx="1" '
        f'stroke="none" fill="{face_color}"/>'
        f"</g>{_svg_close()}"
    )


def _svg_pixel(
    name: str,
    colors: tuple[str, ...],
    *,
    square: bool,
    size: int,
) -> str:
    view = 80
    cell = 10
    num = hash_code(name)
    mask_id = _mask_id("pixel", name)
    rects: list[str] = []
    for index in range(64):
        color = get_random_color(num % (index + 1), colors)
        col = index % 8
        row = index // 8
        rects.append(
            f'<rect width="{cell}" height="{cell}" '
            f'x="{col * cell}" y="{row * cell}" fill="{color}"/>'
        )
    return f"{_svg_open(view, size, mask_id, square)}{''.join(rects)}{_svg_close()}"


def _svg_sunset(
    name: str,
    colors: tuple[str, ...],
    *,
    square: bool,
    size: int,
) -> str:
    view = 80
    num = hash_code(name)
    sunset = [get_random_color(num + index, colors) for index in range(4)]
    mask_id = _mask_id("sunset", name)
    grad_a = f"g0_{mask_id}"
    grad_b = f"g1_{mask_id}"
    return (
        f"{_svg_open(view, size, mask_id, square)}"
        f'<path fill="url(#{grad_a})" d="M0 0h80v40H0z"/>'
        f'<path fill="url(#{grad_b})" d="M0 40h80v40H0z"/>'
        f"</g><defs>"
        f'<linearGradient id="{grad_a}" x1="{view / 2}" y1="0" '
        f'x2="{view / 2}" y2="{view / 2}">'
        f'<stop stop-color="{sunset[0]}"/>'
        f'<stop offset="1" stop-color="{sunset[1]}"/>'
        f"</linearGradient>"
        f'<linearGradient id="{grad_b}" x1="{view / 2}" y1="{view / 2}" '
        f'x2="{view / 2}" y2="{view}">'
        f'<stop stop-color="{sunset[2]}"/>'
        f'<stop offset="1" stop-color="{sunset[3]}"/>'
        f"</linearGradient>"
        f"</defs></svg>"
    )


def _svg_ring(
    name: str,
    colors: tuple[str, ...],
    *,
    square: bool,
    size: int,
) -> str:
    view = 90
    num = hash_code(name)
    shuffled = [get_random_color(num + index, colors) for index in range(5)]
    ring = [
        shuffled[0],
        shuffled[1],
        shuffled[1],
        shuffled[2],
        shuffled[2],
        shuffled[3],
        shuffled[3],
        shuffled[0],
        shuffled[4],
    ]
    mask_id = _mask_id("ring", name)
    return (
        f"{_svg_open(view, size, mask_id, square)}"
        f'<path d="M0 0h90v45H0z" fill="{ring[0]}"/>'
        f'<path d="M0 45h90v45H0z" fill="{ring[1]}"/>'
        f'<path d="M83 45a38 38 0 00-76 0h76z" fill="{ring[2]}"/>'
        f'<path d="M83 45a38 38 0 01-76 0h76z" fill="{ring[3]}"/>'
        f'<path d="M77 45a32 32 0 10-64 0h64z" fill="{ring[4]}"/>'
        f'<path d="M77 45a32 32 0 11-64 0h64z" fill="{ring[5]}"/>'
        f'<path d="M71 45a26 26 0 00-52 0h52z" fill="{ring[6]}"/>'
        f'<path d="M71 45a26 26 0 01-52 0h52z" fill="{ring[7]}"/>'
        f'<circle cx="45" cy="45" r="23" fill="{ring[8]}"/>'
        f"{_svg_close()}"
    )


def _svg_bauhaus(
    name: str,
    colors: tuple[str, ...],
    *,
    square: bool,
    size: int,
) -> str:
    view = 80
    num = hash_code(name)
    props = []
    for index in range(4):
        props.append(
            {
                "color": get_random_color(num + index, colors),
                "tx": get_unit(num * (index + 1), view // 2 - (index + 17), 1),
                "ty": get_unit(num * (index + 1), view // 2 - (index + 17), 2),
                "rotate": get_unit(num * (index + 1), 360),
                "is_square": get_boolean(num, 2),
            }
        )
    mask_id = _mask_id("bauhaus", name)
    bar_height = view if props[1]["is_square"] else view / 8
    return (
        f"{_svg_open(view, size, mask_id, square)}"
        f'<rect width="{view}" height="{view}" fill="{props[0]["color"]}"/>'
        f'<rect x="{(view - 60) / 2}" y="{(view - 20) / 2}" width="{view}" '
        f'height="{bar_height}" fill="{props[1]["color"]}" '
        f'transform="translate({props[1]["tx"]} {props[1]["ty"]}) '
        f'rotate({props[1]["rotate"]} {view / 2} {view / 2})"/>'
        f'<circle cx="{view / 2}" cy="{view / 2}" r="{view / 5}" '
        f'fill="{props[2]["color"]}" '
        f'transform="translate({props[2]["tx"]} {props[2]["ty"]})"/>'
        f'<line x1="0" y1="{view / 2}" x2="{view}" y2="{view / 2}" '
        f'stroke-width="2" stroke="{props[3]["color"]}" '
        f'transform="translate({props[3]["tx"]} {props[3]["ty"]}) '
        f'rotate({props[3]["rotate"]} {view / 2} {view / 2})"/>'
        f"{_svg_close()}"
    )
