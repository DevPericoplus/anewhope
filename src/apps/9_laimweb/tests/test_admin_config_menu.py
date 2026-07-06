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
        "config_usuarios",
        "config_modelos_ia",
        "config_fases_tiers",
        "config_sesiones",
        "config_share",
        "config_agentes",
        "config_auditoria",
    }
    assert expected == ADMIN_CONFIG_PAGE_MENUS
    for menu in expected:
        content = load_static_page_markdown(menu)
        assert content.startswith("#")


def test_is_admin_config_menu() -> None:
    """Solo las claves config_* pertenecen a configuración."""
    assert is_admin_config_menu("config_usuarios") is True
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
