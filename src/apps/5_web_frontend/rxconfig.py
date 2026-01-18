"""
Configuración de Reflex para la aplicación web frontend
"""
import reflex as rx

config = rx.Config(
    app_name="web_frontend",
    db_url="sqlite:///reflex.db",
    env=rx.Env.DEV,
    backend_port=8005,
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
)

