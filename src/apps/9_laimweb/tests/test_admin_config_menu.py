"""Tests del menú de configuración administrador LAIM Web."""

from laim_web.static_pages_loader import (
    ADMIN_CONFIG_PAGE_MENUS,
    LAIM_ADMIN_IDENTITY_TYPE_IDS,
    can_access_admin_config_menu,
    is_admin_config_menu,
    load_static_page_markdown,
)


def test_admin_config_menus_defined() -> None:
    """Existen páginas de configuración con markdown."""
    expected = {
        "config_general",
        "config_foro",
    }
    assert expected == ADMIN_CONFIG_PAGE_MENUS
    general = load_static_page_markdown("config_general")
    assert "Usuarios" in general
    assert "Registro" in general
    assert "Foro LAIM" in general
    assert "Visor de logs" in general
    assert "Asignar moderador" in general
    foro = load_static_page_markdown("config_foro")
    assert foro.startswith("# Foro LAIM")
    assert "Categorías" in foro
    assert "Prefijos de hilo" in foro


def test_named_config_pages_keep_public_titles() -> None:
    """Los títulos que ve el administrador coinciden con el menú."""
    assert load_static_page_markdown("config_foro").startswith("# Foro LAIM")
    assert load_static_page_markdown("config_usuarios").startswith("# Página no encontrada")
    assert load_static_page_markdown("config_auditoria").startswith("# Página no encontrada")


def test_is_admin_config_menu() -> None:
    """Solo las claves config_* pertenecen a configuración."""
    assert is_admin_config_menu("config_foro") is True
    assert is_admin_config_menu("config_usuarios") is False
    assert is_admin_config_menu("instaladores") is False


def test_can_access_admin_config_menu_for_admins() -> None:
    """SuperAdmin y Admin org acceden; otros roles no."""
    for admin_id in LAIM_ADMIN_IDENTITY_TYPE_IDS:
        assert can_access_admin_config_menu("config_general", admin_id) is True

    assert can_access_admin_config_menu("config_general", 3) is False
    assert can_access_admin_config_menu("config_general", 4) is False
    assert can_access_admin_config_menu("config_general", 5) is False


def test_can_access_non_config_menu_for_any_role() -> None:
    """Las páginas normales no requieren rol admin."""
    assert can_access_admin_config_menu("instaladores", 4) is True
    assert can_access_admin_config_menu("faq", 0) is True
