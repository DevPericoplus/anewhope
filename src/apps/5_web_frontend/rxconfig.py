"""
Configuración de Reflex para la aplicación web frontend
"""
import reflex as rx

config = rx.Config(
    app_name="web_frontend",
    db_url="sqlite:///reflex.db",
    env=rx.Env.PROD,  # Modo producción para servir todo desde un puerto
    backend_port=8005,
    api_url="https://tfmmyllm.ai",  # URL pública para acceso desde navegador
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
)

