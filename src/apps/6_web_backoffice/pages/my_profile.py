"""Página para que el usuario consulte y modifique sus datos."""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from typing import Any

import reflex as rx

from portal_crt import COLORS, CRT_SHELL_CLASS

logger = logging.getLogger(__name__)

get_my_profile = None
update_my_profile = None
update_my_organization = None

try:
    adapter_path = Path(__file__).parent.parent / "adapters" / "api_client.py"
    spec = importlib.util.spec_from_file_location("api_client_profile", adapter_path)
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        get_my_profile = getattr(module, "get_my_profile", None)
        update_my_profile = getattr(module, "update_my_profile", None)
        update_my_organization = getattr(module, "update_my_organization", None)
except Exception as exc:
    logger.error("No se pudo cargar api_client de perfil: %s", exc)


def _empty_contact() -> dict[str, str]:
    return {
        "first_name": "",
        "sur_name": "",
        "country": "",
        "state": "",
        "zip_code": "",
        "address": "",
    }


class UserProfileState(rx.State):
    """Estado de la ficha Mis datos."""

    user_name: str = ""
    user_email: str = ""
    user_mobile: str = ""
    organization_id: int = 0
    identity_type_id: int = 0
    can_edit_organization: bool = False
    contact_first_name: str = ""
    contact_sur_name: str = ""
    contact_country: str = ""
    contact_state: str = ""
    contact_zip_code: str = ""
    contact_address: str = ""
    billing_first_name: str = ""
    billing_sur_name: str = ""
    billing_country: str = ""
    billing_state: str = ""
    billing_zip_code: str = ""
    billing_address: str = ""
    org_name: str = ""
    org_email: str = ""
    org_tlf: str = ""
    org_address: str = ""
    org_country: str = ""
    org_state: str = ""
    org_acronym: str = ""
    show_org_modal: bool = False
    show_contact_modal: bool = False
    message: str = ""
    message_type: str = ""
    access_token: str = ""
    session_token: str = ""

    async def on_page_load(self):
        """Carga la ficha si hay sesión activa."""
        from web_backoffice.web_backoffice import State as BackofficeState

        session = await self.get_state(BackofficeState)
        if not session.is_logged_in:
            return rx.redirect("/")
        self.access_token = session.access_token
        self.session_token = session.session_token
        self._apply_profile(
            get_my_profile(self.access_token, self.session_token)
            if get_my_profile
            else {}
        )

    def _apply_profile(self, profile: dict[str, Any]) -> None:
        if not profile:
            self.message = "No se pudo cargar la ficha"
            self.message_type = "error"
            return
        self.user_name = str(profile.get("user_name") or "")
        self.user_email = str(profile.get("user_email") or "")
        self.user_mobile = str(profile.get("user_mobile") or "")
        self.organization_id = int(profile.get("organization_id") or 0)
        self.identity_type_id = int(profile.get("identity_type_id") or 0)
        self.can_edit_organization = bool(profile.get("can_edit_organization"))
        contact = profile.get("contact_info") or _empty_contact()
        billing = profile.get("billing_info") or contact
        self.contact_first_name = str(contact.get("first_name") or "")
        self.contact_sur_name = str(contact.get("sur_name") or "")
        self.contact_country = str(contact.get("country") or "")
        self.contact_state = str(contact.get("state") or "")
        self.contact_zip_code = str(contact.get("zip_code") or "")
        self.contact_address = str(contact.get("address") or "")
        self.billing_first_name = str(billing.get("first_name") or "")
        self.billing_sur_name = str(billing.get("sur_name") or "")
        self.billing_country = str(billing.get("country") or "")
        self.billing_state = str(billing.get("state") or "")
        self.billing_zip_code = str(billing.get("zip_code") or "")
        self.billing_address = str(billing.get("address") or "")
        organization = profile.get("organization") or {}
        self.org_name = str(organization.get("organization_name") or "")
        self.org_email = str(organization.get("organization_email") or "")
        self.org_tlf = str(organization.get("organization_tlf") or "")
        self.org_address = str(organization.get("organization_address") or "")
        self.org_country = str(organization.get("organization_country") or "")
        self.org_state = str(organization.get("organization_state") or "")
        self.org_acronym = str(organization.get("organization_acronym") or "")
        self.message = ""
        self.message_type = ""

    def open_org_modal(self):
        self.show_org_modal = True

    def close_org_modal(self):
        self.show_org_modal = False

    def open_contact_modal(self):
        self.show_contact_modal = True

    def close_contact_modal(self):
        self.show_contact_modal = False

    def set_user_email(self, value: str):
        self.user_email = value

    def set_user_mobile(self, value: str):
        self.user_mobile = value

    def set_contact_first_name(self, value: str):
        self.contact_first_name = value

    def set_contact_sur_name(self, value: str):
        self.contact_sur_name = value

    def set_contact_country(self, value: str):
        self.contact_country = value

    def set_contact_state(self, value: str):
        self.contact_state = value

    def set_contact_zip_code(self, value: str):
        self.contact_zip_code = value

    def set_contact_address(self, value: str):
        self.contact_address = value

    def set_org_name(self, value: str):
        self.org_name = value

    def set_org_email(self, value: str):
        self.org_email = value

    def set_org_tlf(self, value: str):
        self.org_tlf = value

    def set_org_address(self, value: str):
        self.org_address = value

    def set_org_country(self, value: str):
        self.org_country = value

    def set_org_state(self, value: str):
        self.org_state = value

    def save_profile(self):
        """Guarda datos de cuenta y contacto."""
        if update_my_profile is None:
            self.message = "Cliente de perfil no disponible"
            self.message_type = "error"
            return
        try:
            profile = update_my_profile(
                self.access_token,
                self.session_token,
                {
                    "user_email": self.user_email.strip().lower(),
                    "user_mobile": self.user_mobile.strip(),
                    "contact_info": {
                        "first_name": self.contact_first_name.strip(),
                        "sur_name": self.contact_sur_name.strip(),
                        "country": self.contact_country.strip(),
                        "state": self.contact_state.strip(),
                        "zip_code": self.contact_zip_code.strip(),
                        "address": self.contact_address.strip(),
                    },
                    "billing_info": {
                        "first_name": self.billing_first_name.strip()
                        or self.contact_first_name.strip(),
                        "sur_name": self.billing_sur_name.strip()
                        or self.contact_sur_name.strip(),
                        "country": self.billing_country.strip()
                        or self.contact_country.strip(),
                        "state": self.billing_state.strip() or self.contact_state.strip(),
                        "zip_code": self.billing_zip_code.strip()
                        or self.contact_zip_code.strip(),
                        "address": self.billing_address.strip()
                        or self.contact_address.strip(),
                    },
                },
            )
            self._apply_profile(profile)
            self.message = "Datos actualizados"
            self.message_type = "success"
            self.show_contact_modal = False
        except Exception as exc:
            self.message = str(exc)
            self.message_type = "error"

    def save_organization(self):
        """Guarda datos de organización si el usuario es administrador."""
        if not self.can_edit_organization:
            self.message = "No puede modificar los datos de la organización"
            self.message_type = "error"
            return
        if update_my_organization is None:
            self.message = "Cliente de organización no disponible"
            self.message_type = "error"
            return
        try:
            profile = update_my_organization(
                self.access_token,
                self.session_token,
                {
                    "organization_name": self.org_name.strip(),
                    "organization_email": self.org_email.strip(),
                    "organization_tlf": self.org_tlf.strip(),
                    "organization_address": self.org_address.strip(),
                    "organization_country": self.org_country.strip(),
                    "organization_state": self.org_state.strip(),
                },
            )
            self._apply_profile(profile)
            self.message = "Organización actualizada"
            self.message_type = "success"
            self.show_org_modal = False
        except Exception as exc:
            self.message = str(exc)
            self.message_type = "error"


def _field(label: str, value, on_change, readonly: bool = False) -> rx.Component:
    return rx.vstack(
        rx.text(label, class_name="crt-label", font_size="0.9em"),
        rx.input(
            value=value,
            on_change=on_change,
            disabled=readonly,
            class_name="crt-input",
            width="100%",
        ),
        spacing="1",
        width="100%",
    )


def _org_modal() -> rx.Component:
    return rx.cond(
        UserProfileState.show_org_modal,
        rx.box(
            rx.vstack(
                rx.heading("Organización", size="6", color=COLORS["primary"]),
                rx.text(
                    rx.cond(
                        UserProfileState.can_edit_organization,
                        "Puede modificar los datos de la organización. El acrónimo de login no se cambia.",
                        "Solo el administrador de la organización puede modificar estos datos.",
                    ),
                    color=COLORS["muted_foreground"],
                    font_size="0.9em",
                ),
                _field(
                    "Nombre",
                    UserProfileState.org_name,
                    UserProfileState.set_org_name,
                    readonly=~UserProfileState.can_edit_organization,
                ),
                _field(
                    "Acrónimo (solo lectura)",
                    UserProfileState.org_acronym,
                    UserProfileState.set_org_name,
                    readonly=True,
                ),
                _field(
                    "Email",
                    UserProfileState.org_email,
                    UserProfileState.set_org_email,
                    readonly=~UserProfileState.can_edit_organization,
                ),
                _field(
                    "Teléfono",
                    UserProfileState.org_tlf,
                    UserProfileState.set_org_tlf,
                    readonly=~UserProfileState.can_edit_organization,
                ),
                _field(
                    "Dirección",
                    UserProfileState.org_address,
                    UserProfileState.set_org_address,
                    readonly=~UserProfileState.can_edit_organization,
                ),
                rx.hstack(
                    rx.cond(
                        UserProfileState.can_edit_organization,
                        rx.button(
                            "Guardar organización",
                            on_click=UserProfileState.save_organization,
                            class_name="crt-btn",
                        ),
                    ),
                    rx.button(
                        "Cerrar",
                        on_click=UserProfileState.close_org_modal,
                        class_name="crt-btn",
                    ),
                    spacing="3",
                ),
                spacing="3",
                width="100%",
            ),
            padding="1.5em",
            class_name="crt-panel",
            width="min(640px, 92vw)",
            position="fixed",
            top="8vh",
            left="50%",
            transform="translateX(-50%)",
            z_index="1200",
        ),
    )


def _contact_modal() -> rx.Component:
    return rx.cond(
        UserProfileState.show_contact_modal,
        rx.box(
            rx.vstack(
                rx.heading("Contacto", size="6", color=COLORS["primary"]),
                rx.hstack(
                    _field(
                        "Nombre",
                        UserProfileState.contact_first_name,
                        UserProfileState.set_contact_first_name,
                    ),
                    _field(
                        "Apellidos",
                        UserProfileState.contact_sur_name,
                        UserProfileState.set_contact_sur_name,
                    ),
                    spacing="3",
                    width="100%",
                ),
                rx.hstack(
                    _field(
                        "País",
                        UserProfileState.contact_country,
                        UserProfileState.set_contact_country,
                    ),
                    _field(
                        "Provincia",
                        UserProfileState.contact_state,
                        UserProfileState.set_contact_state,
                    ),
                    spacing="3",
                    width="100%",
                ),
                _field(
                    "Código postal",
                    UserProfileState.contact_zip_code,
                    UserProfileState.set_contact_zip_code,
                ),
                _field(
                    "Dirección",
                    UserProfileState.contact_address,
                    UserProfileState.set_contact_address,
                ),
                rx.hstack(
                    rx.button(
                        "Guardar contacto",
                        on_click=UserProfileState.save_profile,
                        class_name="crt-btn",
                    ),
                    rx.button(
                        "Cerrar",
                        on_click=UserProfileState.close_contact_modal,
                        class_name="crt-btn",
                    ),
                    spacing="3",
                ),
                spacing="3",
                width="100%",
            ),
            padding="1.5em",
            class_name="crt-panel",
            width="min(720px, 94vw)",
            position="fixed",
            top="8vh",
            left="50%",
            transform="translateX(-50%)",
            z_index="1200",
        ),
    )


def my_profile_page() -> rx.Component:
    """Ficha compacta de datos de usuario."""
    return rx.box(
        _org_modal(),
        _contact_modal(),
        rx.vstack(
            rx.heading("Mis datos", size="8", color=COLORS["primary"], margin_bottom="0.5em"),
            rx.text(
                "Actualice su cuenta. Organización y contacto se abren en ventanas aparte para aprovechar el espacio.",
                color=COLORS["muted_foreground"],
            ),
            rx.hstack(
                _field("Usuario", UserProfileState.user_name, UserProfileState.set_user_email, readonly=True),
                _field("Email", UserProfileState.user_email, UserProfileState.set_user_email),
                _field("Móvil", UserProfileState.user_mobile, UserProfileState.set_user_mobile),
                spacing="3",
                width="100%",
            ),
            rx.hstack(
                rx.cond(
                    UserProfileState.organization_id > 0,
                    rx.button(
                        "Organización",
                        on_click=UserProfileState.open_org_modal,
                        class_name="crt-btn",
                    ),
                ),
                rx.button(
                    "Contacto",
                    on_click=UserProfileState.open_contact_modal,
                    class_name="crt-btn",
                ),
                rx.button(
                    "Guardar",
                    on_click=UserProfileState.save_profile,
                    class_name="crt-btn",
                ),
                rx.link(
                    rx.button("Volver", class_name="crt-btn"),
                    href="/",
                ),
                spacing="3",
            ),
            rx.cond(
                UserProfileState.message != "",
                rx.text(
                    UserProfileState.message,
                    color=rx.cond(
                        UserProfileState.message_type == "success",
                        COLORS["primary"],
                        "#ff6b6b",
                    ),
                    font_weight="bold",
                ),
            ),
            spacing="4",
            width="100%",
            max_width="960px",
            padding="2em",
            class_name="crt-panel",
        ),
        width="100%",
        min_height="100vh",
        class_name=CRT_SHELL_CLASS,
        display="flex",
        justify_content="center",
        padding="2em",
    )
