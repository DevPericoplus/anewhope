"""Base de datos sqlite llamada nginx (fichero nginx.db).

Tablas separadas por aplicación, más nginx_status para el proceso
(stub_status y CPU/RAM del host). Las filas crudas duran 14 días; los
agregados por hora, 180.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta, timezone

from nginx_monitor.parse import APPS

RAW_DAYS = 14
HOUR_DAYS = 180


def connect(path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    for app in APPS:
        conn.execute(
            f"""CREATE TABLE IF NOT EXISTS {app}_requests (
                id INTEGER PRIMARY KEY,
                ts TEXT NOT NULL,
                visitor TEXT NOT NULL,
                method TEXT NOT NULL,
                path TEXT NOT NULL,
                feature TEXT NOT NULL,
                status INTEGER NOT NULL,
                bytes INTEGER NOT NULL,
                request_ms INTEGER NOT NULL,
                upstream_ms INTEGER NOT NULL
            )"""
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS {app}_requests_ts ON {app}_requests(ts)"
        )
        conn.execute(
            f"""CREATE TABLE IF NOT EXISTS {app}_hourly (
                hour TEXT PRIMARY KEY,
                requests INTEGER NOT NULL,
                visitors INTEGER NOT NULL,
                bytes INTEGER NOT NULL,
                s2xx INTEGER NOT NULL,
                s3xx INTEGER NOT NULL,
                s4xx INTEGER NOT NULL,
                s5xx INTEGER NOT NULL,
                sum_ms INTEGER NOT NULL,
                sum_upstream INTEGER NOT NULL
            )"""
        )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS nginx_status (
            id INTEGER PRIMARY KEY,
            ts TEXT NOT NULL,
            active INTEGER NOT NULL,
            reading INTEGER NOT NULL,
            writing INTEGER NOT NULL,
            waiting INTEGER NOT NULL,
            accepts INTEGER NOT NULL,
            handled INTEGER NOT NULL,
            requests INTEGER NOT NULL,
            cpu_pct REAL NOT NULL,
            mem_pct REAL NOT NULL
        )"""
    )
    conn.commit()
    return conn


def insert_requests(conn: sqlite3.Connection, rows: list[dict]) -> None:
    if not rows:
        return
    by_app: dict[str, list[dict]] = {app: [] for app in APPS}
    for row in rows:
        by_app[row["app"]].append(row)
    with conn:
        for app, batch in by_app.items():
            if not batch:
                continue
            conn.executemany(
                f"""INSERT INTO {app}_requests
                    (ts, visitor, method, path, feature, status, bytes, request_ms, upstream_ms)
                    VALUES (:ts, :visitor, :method, :path, :feature, :status, :bytes, :request_ms, :upstream_ms)""",
                batch,
            )
            buckets: dict[str, dict] = {}
            for row in batch:
                hour = (row["ts"] or "")[:13]
                if len(hour) < 13:
                    hour = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H")
                b = buckets.setdefault(
                    hour,
                    {
                        "requests": 0, "visitors": set(), "bytes": 0,
                        "s2xx": 0, "s3xx": 0, "s4xx": 0, "s5xx": 0,
                        "sum_ms": 0, "sum_upstream": 0,
                    },
                )
                b["requests"] += 1
                b["visitors"].add(row["visitor"])
                b["bytes"] += row["bytes"]
                b["sum_ms"] += row["request_ms"]
                b["sum_upstream"] += row["upstream_ms"]
                code = row["status"]
                if 200 <= code < 300:
                    b["s2xx"] += 1
                elif 300 <= code < 400:
                    b["s3xx"] += 1
                elif 400 <= code < 500:
                    b["s4xx"] += 1
                elif code >= 500:
                    b["s5xx"] += 1
            for hour, b in buckets.items():
                conn.execute(
                    f"""INSERT INTO {app}_hourly
                        (hour, requests, visitors, bytes, s2xx, s3xx, s4xx, s5xx, sum_ms, sum_upstream)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(hour) DO UPDATE SET
                          requests = requests + excluded.requests,
                          visitors = visitors + excluded.visitors,
                          bytes = bytes + excluded.bytes,
                          s2xx = s2xx + excluded.s2xx,
                          s3xx = s3xx + excluded.s3xx,
                          s4xx = s4xx + excluded.s4xx,
                          s5xx = s5xx + excluded.s5xx,
                          sum_ms = sum_ms + excluded.sum_ms,
                          sum_upstream = sum_upstream + excluded.sum_upstream
                    """,
                    (
                        hour, b["requests"], len(b["visitors"]), b["bytes"],
                        b["s2xx"], b["s3xx"], b["s4xx"], b["s5xx"],
                        b["sum_ms"], b["sum_upstream"],
                    ),
                )


def insert_status(conn: sqlite3.Connection, row: dict) -> None:
    with conn:
        conn.execute(
            """INSERT INTO nginx_status
               (ts, active, reading, writing, waiting, accepts, handled, requests, cpu_pct, mem_pct)
               VALUES (:ts, :active, :reading, :writing, :waiting, :accepts, :handled, :requests, :cpu_pct, :mem_pct)""",
            row,
        )
        conn.execute(
            "DELETE FROM nginx_status WHERE id NOT IN (SELECT id FROM nginx_status ORDER BY id DESC LIMIT 2000)"
        )


def purge(conn: sqlite3.Connection, now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    raw_cut = (now - timedelta(days=RAW_DAYS)).strftime("%Y-%m-%dT%H:%M:%S")
    hour_cut = (now - timedelta(days=HOUR_DAYS)).strftime("%Y-%m-%dT%H")
    with conn:
        for app in APPS:
            conn.execute(f"DELETE FROM {app}_requests WHERE ts < ?", (raw_cut,))
            conn.execute(f"DELETE FROM {app}_hourly WHERE hour < ?", (hour_cut,))


def _p95(values: list[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))
    return ordered[idx]


def stats(conn: sqlite3.Connection, app: str) -> dict:
    if app not in APPS:
        raise ValueError(app)
    hourly = [
        dict(row)
        for row in conn.execute(
            f"SELECT * FROM {app}_hourly ORDER BY hour DESC LIMIT 48"
        )
    ]
    hourly.reverse()
    totals = conn.execute(
        f"""SELECT
              COALESCE(SUM(requests), 0) AS requests,
              COALESCE(SUM(visitors), 0) AS visitors,
              COALESCE(SUM(bytes), 0) AS bytes,
              COALESCE(SUM(s2xx), 0) AS s2xx,
              COALESCE(SUM(s3xx), 0) AS s3xx,
              COALESCE(SUM(s4xx), 0) AS s4xx,
              COALESCE(SUM(s5xx), 0) AS s5xx,
              COALESCE(SUM(sum_ms), 0) AS sum_ms,
              COALESCE(SUM(sum_upstream), 0) AS sum_upstream
            FROM {app}_hourly"""
    ).fetchone()
    requests = int(totals["requests"] or 0)
    distinct_total = conn.execute(
        f"SELECT COUNT(DISTINCT visitor) AS n FROM {app}_requests"
    ).fetchone()["n"]
    distinct_hour = {
        row["hour"]: int(row["n"])
        for row in conn.execute(
            f"""SELECT substr(ts, 1, 13) AS hour, COUNT(DISTINCT visitor) AS n
                FROM {app}_requests GROUP BY 1"""
        )
    }
    times = [
        int(row["request_ms"])
        for row in conn.execute(
            f"SELECT request_ms FROM {app}_requests ORDER BY id DESC LIMIT 5000"
        )
    ]
    features = [
        {"name": row["feature"], "requests": row["n"], "avg_ms": int(row["avg_ms"] or 0)}
        for row in conn.execute(
            f"""SELECT feature, COUNT(*) AS n, AVG(request_ms) AS avg_ms
                FROM {app}_requests GROUP BY feature ORDER BY n DESC LIMIT 8"""
        )
    ]
    methods = [
        {"name": row["method"], "requests": row["n"]}
        for row in conn.execute(
            f"SELECT method, COUNT(*) AS n FROM {app}_requests GROUP BY method ORDER BY n DESC"
        )
    ]
    status = conn.execute(
        "SELECT * FROM nginx_status ORDER BY id DESC LIMIT 1"
    ).fetchone()
    points = []
    for row in hourly:
        n = int(row["requests"] or 0)
        points.append({
            "hour": row["hour"],
            "requests": n,
            "visitors": distinct_hour.get(row["hour"], int(row["visitors"] or 0)),
            "errors": int(row["s4xx"] or 0) + int(row["s5xx"] or 0),
            "avg_ms": int(row["sum_ms"] / n) if n else 0,
            "bytes": int(row["bytes"] or 0),
        })
    nginx = {}
    if status is not None:
        nginx = {
            "active": status["active"],
            "reading": status["reading"],
            "writing": status["writing"],
            "waiting": status["waiting"],
            "accepts": status["accepts"],
            "handled": status["handled"],
            "requests": status["requests"],
            "cpu_pct": status["cpu_pct"],
            "mem_pct": status["mem_pct"],
            "ts": status["ts"],
        }
    return {
        "app": app,
        "requests": requests,
        "visitors": int(distinct_total or 0),
        "bytes": int(totals["bytes"] or 0),
        "s2xx": int(totals["s2xx"] or 0),
        "s3xx": int(totals["s3xx"] or 0),
        "s4xx": int(totals["s4xx"] or 0),
        "s5xx": int(totals["s5xx"] or 0),
        "avg_ms": int(totals["sum_ms"] / requests) if requests else 0,
        "upstream_ms": int(totals["sum_upstream"] / requests) if requests else 0,
        "p95_ms": _p95(times),
        "hourly": points,
        "features": features,
        "methods": methods,
        "nginx": nginx,
    }
