"""
Configuración de Reflex para la aplicación web frontend
"""
import reflex as rx

config = rx.Config(
    app_name="web_frontend",
    db_url="sqlite:///reflex.db",
    env=rx.Env.DEV,
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
)

