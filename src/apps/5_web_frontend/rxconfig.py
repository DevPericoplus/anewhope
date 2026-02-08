"""
Configuración de Reflex para la aplicación web frontend
Con soporte para sesión compartida mediante Redis
"""
import reflex as rx
import sys
import importlib.util
from pathlib import Path

# Cargar env_settings dinámicamente (evita SyntaxError con nombres numéricos)
env_settings_path = Path(__file__).resolve().parent.parent.parent / "2_shared_application" / "config" / "env_settings.py"
spec = importlib.util.spec_from_file_location("env_settings", env_settings_path)
env_settings = importlib.util.module_from_spec(spec)
sys.modules["env_settings"] = env_settings
spec.loader.exec_module(env_settings)

# Leer configuración de Redis
REDIS_HOST = env_settings.get_env_value("redis_host", "localhost")
REDIS_PORT = int(env_settings.get_env_value("redis_port", "6379"))
REDIS_PASSWORD = env_settings.get_protected_value("redis_password", None)
REDIS_DB = int(env_settings.get_env_value("redis_db", "0"))

# Construir URL de Redis
# Para Redis 6+ con ACL, usar formato: redis://username:password@host:port/db
if REDIS_PASSWORD:
    redis_url = f"redis://default:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
else:
    redis_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

config = rx.Config(
    app_name="web_frontend",
    db_url="sqlite:///reflex.db",
    
    # Configuración de Redis para sesión compartida
    # Reflex 0.8.25 usa automáticamente Redis cuando se proporciona redis_url
    redis_url=redis_url,
    
    # Configuración de servidor
    env=rx.Env.PROD,
    frontend_port=3100,  # Puerto estático fijo para frontend (evita conflictos con nginx)
    backend_port=8005,
    api_url="https://tfmmyllm.ai",
    backend_host="0.0.0.0",
    
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
)

