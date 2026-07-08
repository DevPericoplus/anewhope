"""Generación de avatares del foro LAIM con iconos pixel-art distintivos."""

from __future__ import annotations

import struct
import zlib
from typing import Callable

AvatarAccent = tuple[int, int, int]

DEFAULT_AVATAR_SPECS: list[tuple[str, AvatarAccent, bool]] = [
    ("Terminal", (125, 255, 125), True),
    ("Cipher", (100, 220, 180), False),
    ("Node", (80, 200, 140), False),
    ("Pulse", (140, 255, 160), False),
    ("Signal", (90, 230, 120), False),
    ("Vector", (110, 240, 150), False),
    ("Matrix", (70, 190, 110), False),
    ("Proxy", (130, 255, 170), False),
]

_BG = (8, 12, 8)
_RING = (40, 90, 40)
_SYMBOL = (248, 255, 248)
_SYMBOL_STROKE = (10, 32, 10)


class _AvatarCanvas:
    """Lienzo cuadrado para dibujar iconos dentro del disco del avatar."""

    def __init__(self, size: int, accent: AvatarAccent) -> None:
        self.size = size
        self.accent = accent
        self.dim = (
            max(0, accent[0] - 45),
            max(0, accent[1] - 55),
            max(0, accent[2] - 45),
        )
        self.mid = (
            min(255, accent[0] - 20),
            min(255, accent[1] - 30),
            min(255, accent[2] - 20),
        )
        self._pixels: list[list[tuple[int, int, int]]] = [
            [_BG for _ in range(size)] for _ in range(size)
        ]

    def _in_circle(self, x: int, y: int, cx: int, cy: int, radius: int) -> bool:
        dx, dy = x - cx, y - cy
        return dx * dx + dy * dy <= radius * radius

    def draw_base_disc(self) -> None:
        """Fondo oscuro con disco y borde."""
        cx = cy = self.size // 2
        radius = self.size // 2 - 6
        for y in range(self.size):
            for x in range(self.size):
                dx, dy = x - cx, y - cy
                dist_sq = dx * dx + dy * dy
                if dist_sq <= radius * radius:
                    self._pixels[y][x] = self.accent
                elif dist_sq <= (radius + 2) * (radius + 2):
                    self._pixels[y][x] = _RING

    def set_px(self, x: int, y: int, color: tuple[int, int, int]) -> None:
        if 0 <= x < self.size and 0 <= y < self.size:
            self._pixels[y][x] = color

    def fill_rect(
        self,
        x0: int,
        y0: int,
        width: int,
        height: int,
        color: tuple[int, int, int],
    ) -> None:
        for y in range(y0, y0 + height):
            for x in range(x0, x0 + width):
                self.set_px(x, y, color)

    def stroke_rect(
        self,
        x0: int,
        y0: int,
        width: int,
        height: int,
        color: tuple[int, int, int],
        thickness: int = 1,
    ) -> None:
        for t in range(thickness):
            for x in range(x0, x0 + width):
                self.set_px(x, y0 + t, color)
                self.set_px(x, y0 + height - 1 - t, color)
            for y in range(y0, y0 + height):
                self.set_px(x0 + t, y, color)
                self.set_px(x0 + width - 1 - t, y, color)

    def draw_line(
        self,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        color: tuple[int, int, int],
        thickness: int = 1,
    ) -> None:
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            for ox in range(-(thickness // 2), thickness // 2 + 1):
                for oy in range(-(thickness // 2), thickness // 2 + 1):
                    self.set_px(x + ox, y + oy, color)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def draw_glyph(self, rows: list[str], ox: int, oy: int, scale: int = 2) -> None:
        """Dibuja un patrón '#' sobre fondo '.' en escala pixel."""
        for row_index, row in enumerate(rows):
            for col_index, char in enumerate(row):
                if char != "#":
                    continue
                for sy in range(scale):
                    for sx in range(scale):
                        self.set_px(
                            ox + col_index * scale + sx,
                            oy + row_index * scale + sy,
                            _SYMBOL,
                        )

    def to_png_bytes(self) -> bytes:
        """Serializa el lienzo a PNG RGB."""
        size = self.size
        raw = bytearray()
        for y in range(size):
            row = bytearray([0])
            for x in range(size):
                row.extend(self._pixels[y][x])
            raw.extend(row)
        compressed = zlib.compress(bytes(raw), 9)
        ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
        return (
            b"\x89PNG\r\n\x1a\n"
            + _png_chunk(b"IHDR", ihdr)
            + _png_chunk(b"IDAT", compressed)
            + _png_chunk(b"IEND", b"")
        )


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)


def _draw_terminal(canvas: _AvatarCanvas) -> None:
    canvas.fill_rect(16, 20, 32, 22, _SYMBOL_STROKE)
    canvas.stroke_rect(16, 20, 32, 22, _SYMBOL, thickness=2)
    canvas.draw_glyph(
        [
            "....",
            ".>>.",
            ".__.",
            "....",
        ],
        24,
        28,
        scale=2,
    )


def _draw_cipher(canvas: _AvatarCanvas) -> None:
    canvas.fill_rect(24, 30, 16, 14, _SYMBOL_STROKE)
    canvas.stroke_rect(24, 30, 16, 14, _SYMBOL, thickness=2)
    for x in range(26, 38):
        canvas.set_px(x, 26, _SYMBOL)
        canvas.set_px(x, 27, _SYMBOL)
    canvas.fill_rect(30, 36, 4, 4, canvas.accent)


def _draw_node(canvas: _AvatarCanvas) -> None:
    nodes = [(32, 22), (22, 38), (42, 38)]
    for x0, y0 in nodes:
        canvas.fill_rect(x0 - 3, y0 - 3, 7, 7, _SYMBOL_STROKE)
        canvas.stroke_rect(x0 - 3, y0 - 3, 7, 7, _SYMBOL, thickness=1)
    canvas.draw_line(32, 25, 25, 35, _SYMBOL, thickness=2)
    canvas.draw_line(32, 25, 39, 35, _SYMBOL, thickness=2)
    canvas.draw_line(25, 38, 39, 38, _SYMBOL, thickness=2)


def _draw_pulse(canvas: _AvatarCanvas) -> None:
    points = [
        (14, 32),
        (20, 32),
        (24, 24),
        (28, 40),
        (32, 28),
        (36, 32),
        (50, 32),
    ]
    for index in range(len(points) - 1):
        x0, y0 = points[index]
        x1, y1 = points[index + 1]
        canvas.draw_line(x0, y0, x1, y1, _SYMBOL, thickness=2)


def _draw_signal(canvas: _AvatarCanvas) -> None:
    canvas.fill_rect(30, 40, 4, 4, _SYMBOL)
    for y, width in ((34, 10), (30, 18), (26, 26)):
        x0 = 32 - width // 2
        canvas.draw_line(x0, y, x0 + width, y, _SYMBOL, thickness=2)


def _draw_vector(canvas: _AvatarCanvas) -> None:
    canvas.draw_line(20, 44, 44, 20, _SYMBOL, thickness=3)
    canvas.fill_rect(36, 18, 10, 4, _SYMBOL)
    canvas.fill_rect(40, 18, 4, 10, _SYMBOL)


def _draw_matrix(canvas: _AvatarCanvas) -> None:
    for row in range(3):
        for col in range(3):
            x0 = 20 + col * 10
            y0 = 22 + row * 10
            canvas.fill_rect(x0, y0, 7, 7, _SYMBOL_STROKE)
            canvas.stroke_rect(x0, y0, 7, 7, _SYMBOL, thickness=1)


def _draw_proxy(canvas: _AvatarCanvas) -> None:
    canvas.fill_rect(16, 26, 12, 14, _SYMBOL_STROKE)
    canvas.stroke_rect(16, 26, 12, 14, _SYMBOL, thickness=2)
    canvas.fill_rect(36, 26, 12, 14, _SYMBOL_STROKE)
    canvas.stroke_rect(36, 26, 12, 14, _SYMBOL, thickness=2)
    canvas.draw_line(30, 33, 34, 33, _SYMBOL, thickness=2)
    canvas.draw_glyph([".#", ".."], 34, 29, scale=2)


_SYMBOL_DRAWERS: dict[str, Callable[[_AvatarCanvas], None]] = {
    "Terminal": _draw_terminal,
    "Cipher": _draw_cipher,
    "Node": _draw_node,
    "Pulse": _draw_pulse,
    "Signal": _draw_signal,
    "Vector": _draw_vector,
    "Matrix": _draw_matrix,
    "Proxy": _draw_proxy,
}


def build_avatar_png(
    label: str,
    accent: AvatarAccent,
    *,
    size: int = 64,
) -> bytes:
    """Genera PNG de avatar con icono interior según la etiqueta del catálogo."""
    canvas = _AvatarCanvas(size, accent)
    canvas.draw_base_disc()
    drawer = _SYMBOL_DRAWERS.get(label)
    if drawer is not None:
        drawer(canvas)
    return canvas.to_png_bytes()
