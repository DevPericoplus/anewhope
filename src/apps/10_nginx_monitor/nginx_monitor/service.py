"""Proceso único: sigue el log JSON, consulta stub_status y sirve la API.

Pensado para copiarse a otro proyecto que publique con nginx: un
contenedor, un volumen /data/nginx_monitor y el log monitor.json.
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOCK = threading.Lock()
PROC = os.environ.get("NGINX_MONITOR_PROC", "/proc")

from nginx_monitor.parse import APPS, parse_line, parse_stub
from nginx_monitor.store import connect, insert_requests, insert_status, list_errors, purge, stats

DB = os.environ.get("NGINX_MONITOR_DB", "/data/nginx_monitor/nginx.db")
LOG = os.environ.get("NGINX_MONITOR_LOG", "/var/log/nginx/monitor.json")
STATUS_URL = os.environ.get("NGINX_STATUS_URL", "http://nginx:8088/nginx_status")
LISTEN = os.environ.get("NGINX_MONITOR_LISTEN", "0.0.0.0:8096")
OFFSET = os.environ.get("NGINX_MONITOR_OFFSET", "")


def _offset_path() -> str:
    if OFFSET:
        return OFFSET
    return os.path.join(os.path.dirname(DB) or ".", "monitor.offset")


def read_host() -> tuple[float, float]:
    """CPU y RAM del host si /proc está montado. Si no, ceros."""
    try:
        with open(os.path.join(PROC, "meminfo"), encoding="utf-8") as fh:
            mem = {}
            for line in fh:
                key, _, rest = line.partition(":")
                mem[key] = int(rest.strip().split()[0])
        total = mem.get("MemTotal", 0)
        avail = mem.get("MemAvailable", total)
        mem_pct = round(100 * (total - avail) / total, 1) if total else 0.0
    except OSError:
        mem_pct = 0.0
    try:
        def snap():
            with open(os.path.join(PROC, "stat"), encoding="utf-8") as fh:
                parts = fh.readline().split()[1:]
            nums = [int(x) for x in parts]
            idle = nums[3] + (nums[4] if len(nums) > 4 else 0)
            return sum(nums), idle
        a, b = snap(), None
        time.sleep(0.2)
        b = snap()
        total = b[0] - a[0]
        idle = b[1] - a[1]
        cpu = round(100 * (total - idle) / total, 1) if total else 0.0
    except OSError:
        cpu = 0.0
    return cpu, mem_pct


def follow(conn) -> None:
    path = _offset_path()
    pos = 0
    if os.path.exists(path):
        try:
            pos = int(open(path, encoding="utf-8").read().strip() or "0")
        except ValueError:
            pos = 0
    pending: list[dict] = []
    last_flush = time.time()
    last_status = 0.0
    last_purge = 0.0
    while True:
        if os.path.exists(LOG):
            size = os.path.getsize(LOG)
            if pos > size:
                pos = 0
            with open(LOG, encoding="utf-8", errors="replace") as fh:
                fh.seek(pos)
                for line in fh:
                    row = parse_line(line)
                    if row:
                        pending.append(row)
                pos = fh.tell()
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(str(pos))
        now = time.time()
        if pending and now - last_flush >= 2:
            with LOCK:
                insert_requests(conn, pending)
            pending.clear()
            last_flush = now
        if now - last_status >= 15:
            sample_status(conn)
            last_status = now
        if now - last_purge >= 3600:
            with LOCK:
                purge(conn)
            last_purge = now
        time.sleep(1)


def sample_status(conn) -> None:
    body = ""
    try:
        with urllib.request.urlopen(STATUS_URL, timeout=3) as resp:
            body = resp.read().decode("utf-8", "replace")
    except OSError:
        body = ""
    parsed = parse_stub(body) if body else None
    cpu, mem = read_host()
    row = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "active": 0, "reading": 0, "writing": 0, "waiting": 0,
        "accepts": 0, "handled": 0, "requests": 0,
        "cpu_pct": cpu, "mem_pct": mem,
    }
    if parsed:
        row.update(parsed)
    with LOCK:
        insert_status(conn, row)


class Handler(BaseHTTPRequestHandler):
    conn = None

    def log_message(self, fmt, *args):
        return

    def _send(self, code: int, payload: dict) -> None:
        raw = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/health":
            self._send(200, {"ok": True, "database": "nginx"})
            return
        query = self.path.split("?", 1)[1] if "?" in self.path else ""
        app = _app_from_query(query)
        if path == "/api/v1/errors":
            if app not in APPS:
                self._send(400, {"error": "aplicación desconocida"})
                return
            with LOCK:
                payload = {"errors": list_errors(self.conn, app)}
            self._send(200, payload)
            return
        if path != "/api/v1/stats":
            self._send(404, {"error": "no encontrado"})
            return
        if app not in APPS:
            self._send(400, {"error": "aplicación desconocida"})
            return
        with LOCK:
            payload = stats(self.conn, app)
        self._send(200, payload)


def _app_from_query(query: str) -> str:
    app = "laimweb"
    for part in query.split("&"):
        if part.startswith("app="):
            app = part.split("=", 1)[1]
    return app


def main() -> None:
    conn = connect(DB)
    Handler.conn = conn
    threading.Thread(target=follow, args=(conn,), daemon=True).start()
    host, _, port = LISTEN.rpartition(":")
    server = ThreadingHTTPServer((host or "0.0.0.0", int(port or "8096")), Handler)
    server.serve_forever()
