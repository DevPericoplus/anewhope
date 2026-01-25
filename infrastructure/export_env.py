#!/usr/bin/env python3
"""Exporta variables de entorno desde env.yaml."""

from __future__ import annotations

import argparse
from pathlib import Path


def _get_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _parse_yaml_line(raw_line: str) -> tuple[str, str] | None:
    line = raw_line.strip()
    if not line or line.startswith("#"):
        return None
    if ":" not in line:
        return None
    key, value = line.split(":", 1)
    key = key.strip()
    value = value.strip().strip("'").strip('"')
    if not key:
        return None
    return key, value


def load_env_yaml(env_name: str) -> dict[str, str]:
    env_path = (
        _get_repo_root()
        / "infrastructure"
        / "environments"
        / env_name
        / "env.yaml"
    )
    if not env_path.exists():
        raise FileNotFoundError(f"No existe env.yaml en {env_path}")
    payload: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        parsed = _parse_yaml_line(raw_line)
        if parsed is None:
            continue
        key, value = parsed
        payload[key.upper()] = value
    return payload


def build_exports(payload: dict[str, str], fmt: str) -> str:
    if fmt == "envfile":
        lines = [f"{key}={value}" for key, value in sorted(payload.items())]
    else:
        lines = [f'export {key}="{value}"' for key, value in sorted(payload.items())]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Exporta variables de entorno desde env.yaml"
    )
    parser.add_argument(
        "--environment",
        "-e",
        default="macbook",
        help="Nombre del entorno (macbook, dev, pre, pro).",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Ruta de salida (si no se indica, imprime por stdout).",
    )
    parser.add_argument(
        "--format",
        choices=("export", "envfile"),
        default="export",
        help="Formato de salida: export (por defecto) o envfile.",
    )
    args = parser.parse_args()

    exports = build_exports(load_env_yaml(args.environment), args.format)
    if args.output:
        Path(args.output).write_text(exports, encoding="utf-8")
    else:
        print(exports, end="")


if __name__ == "__main__":
    main()
