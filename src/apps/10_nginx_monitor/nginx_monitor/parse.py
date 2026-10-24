"""Clasifica una línea del access_log JSON de nginx.

La base se llama nginx. Cada petición va a la tabla de una sola
aplicación: laimweb, frontend (web_frontend) o backoffice. El puerto
8443 es el backoffice aunque comparta el hostname público con el
frontend. Un host con «laim» es laimweb. El resto del tráfico publicado
es frontend. Artifactory y el resto no se guardan.
"""

from __future__ import annotations

import hashlib
import json

APPS = ("laimweb", "frontend", "backoffice")


def classify(host: str, port: int) -> str:
    host = (host or "").lower()
    if port == 8443 or "backoffice" in host:
        return "backoffice"
    if "laim" in host:
        return "laimweb"
    if "artifactory" in host:
        return ""
    return "frontend"


def feature_of(path: str) -> str:
    path = (path or "/").split("?", 1)[0]
    name = path.rsplit("/", 1)[-1]
    if "." in name or path.startswith(("/_next", "/static", "/assets")):
        return "estático"
    parts = [p for p in path.split("/") if p]
    if not parts:
        return "inicio"
    return "/" + parts[0][:48]


def visitor_of(ip: str) -> str:
    return hashlib.sha256((ip or "").encode()).hexdigest()[:16]


def _ms(value) -> int:
    if value in (None, "", "-"):
        return 0
    text = str(value).split(",", 1)[0].strip()
    try:
        return max(0, int(float(text) * 1000))
    except ValueError:
        return 0


def parse_line(line: str) -> dict | None:
    line = line.strip()
    if not line:
        return None
    try:
        raw = json.loads(line)
    except json.JSONDecodeError:
        return None
    try:
        port = int(raw.get("port") or 0)
    except (TypeError, ValueError):
        port = 0
    app = classify(str(raw.get("host") or ""), port)
    if app not in APPS:
        return None
    try:
        status = int(raw.get("status") or 0)
    except (TypeError, ValueError):
        status = 0
    try:
        nbytes = int(raw.get("bytes") or 0)
    except (TypeError, ValueError):
        nbytes = 0
    path = str(raw.get("path") or "/").split("?", 1)[0][:256]
    return {
        "app": app,
        "ts": str(raw.get("ts") or ""),
        "visitor": visitor_of(str(raw.get("ip") or "")),
        "method": str(raw.get("method") or "GET")[:8],
        "path": path,
        "feature": feature_of(path),
        "status": status,
        "bytes": max(0, nbytes),
        "request_ms": _ms(raw.get("rt")),
        "upstream_ms": _ms(raw.get("urt")),
    }


def parse_stub(text: str) -> dict | None:
    """Texto de stub_status. Devuelve None si no es esa página."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) < 4 or not lines[0].lower().startswith("active connections"):
        return None
    try:
        active = int(lines[0].split(":")[1])
        accepts, handled, requests = (int(x) for x in lines[2].split())
        tokens = lines[3].replace(":", " ").split()
        parts = {
            tokens[i].lower(): int(tokens[i + 1])
            for i in range(0, len(tokens) - 1, 2)
        }
    except (IndexError, ValueError):
        return None
    return {
        "active": active,
        "accepts": accepts,
        "handled": handled,
        "requests": requests,
        "reading": parts.get("reading", 0),
        "writing": parts.get("writing", 0),
        "waiting": parts.get("waiting", 0),
    }
