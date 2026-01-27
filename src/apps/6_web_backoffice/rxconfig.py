"""
Configuración de Reflex para la aplicación backoffice
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

# Leer configuración de Redis (MISMA configuración que frontend)
REDIS_HOST = env_settings.get_env_value("redis_host", "localhost")
REDIS_PORT = int(env_settings.get_env_value("redis_port", "6379"))
REDIS_PASSWORD = env_settings.get_protected_value("redis_password", None)
REDIS_DB = int(env_settings.get_env_value("redis_db", "0"))  # ⚠️ DEBE SER LA MISMA DB que frontend

# Construir URL de Redis
if REDIS_PASSWORD:
    redis_url = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
else:
    redis_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

config = rx.Config(
    app_name="web_backoffice",
    db_url="sqlite:///backoffice.db",
    
    # Configuración de Redis para sesión compartida (MISMA que frontend)
    # Reflex detecta automáticamente Redis y lo usa como state manager
    redis_url=redis_url,
    
    # Configuración de servidor
    env=rx.Env.PROD,
    frontend_port=3200,  # Puerto estático fijo para backoffice (evita conflictos con nginx)
    backend_port=8006,
    api_url="https://tfmmyllm.ai:8443",
    deploy_url="https://tfmmyllm.ai:8443",
    backend_host="0.0.0.0",
    
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
)
