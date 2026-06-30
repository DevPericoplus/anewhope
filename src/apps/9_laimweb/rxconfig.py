"""
Configuración de Reflex para la aplicación LAIM Web.
Estilo visual CRT terminal con fuentes Inconsolata.
Puerto: 8010 (asignación dedicada LAIM)
"""

import importlib.util
import sys
from pathlib import Path

import reflex as rx

# Cargar env_settings dinámicamente
env_settings_path = (
    Path(__file__).resolve().parent.parent.parent
    / "2_shared_application"
    / "config"
    / "env_settings.py"
)
spec = importlib.util.spec_from_file_location("env_settings", env_settings_path)
env_settings = importlib.util.module_from_spec(spec)
sys.modules["env_settings"] = env_settings
spec.loader.exec_module(env_settings)

# Redis para sesión compartida
REDIS_HOST = env_settings.get_env_value("redis_host", "localhost")
REDIS_PORT = int(env_settings.get_env_value("redis_port", "6379"))
REDIS_PASSWORD = env_settings.get_protected_value("redis_password", None)
REDIS_DB = int(env_settings.get_env_value("redis_db", "0"))

if REDIS_PASSWORD:
    redis_url = f"redis://default:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
else:
    redis_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

REDIS_LOCK_EXPIRATION = int(
    env_settings.get_env_value("redis_lock_expiration", "30000")
)

config = rx.Config(
    app_name="laim_web",
    db_url="sqlite:///reflex.db",
    redis_url=redis_url,
    redis_lock_expiration=REDIS_LOCK_EXPIRATION,
    env=rx.Env.DEV,
    frontend_port=3110,
    backend_port=8010,
    api_url=env_settings.get_env_value("laimweb_api_url", "http://localhost:8010"),
    backend_host="0.0.0.0",
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
)
