# Shared domain entities
#
# This module contains the core entities shared across backend, trainer and
# frontend services. They model the ubiquitous language of the platform and
# avoid coupling to infrastructure concerns. When creating new entities,
# prefer dataclasses for immutability-friendly defaults and type hints for
# clarity.

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional


class ModelLifecycleState(str, Enum):
    """High-level status for a managed LLM artefact."""

    DRAFT = "draft"
    TRAINING = "training"
    EVALUATING = "evaluating"
    READY = "ready"
    DEPRECATED = "deprecated"


@dataclass(frozen=True)
class Tenant:
    """Represents a workspace or client that owns resources in the platform."""

    id: str
    name: str
    contact_email: str


@dataclass
class Dataset:
    """Canonical definition of a dataset used for training or evaluation."""

    id: str
    tenant_id: str
    name: str
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ModelVersion:
    """Shared representation of a fine-tuned LLM artefact."""

    id: str
    model_name: str
    tenant_id: str
    lifecycle_state: ModelLifecycleState
    source_dataset_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metrics: dict[str, float] = field(default_factory=dict)

    def mark_ready(self, metrics: dict[str, float]) -> None:
        """Transition the model to READY state with evaluation metrics."""
        self.lifecycle_state = ModelLifecycleState.READY
        self.metrics = metrics
        self.updated_at = datetime.now(timezone.utc)

class User:
    """Representa un usuario en el sistema."""

    def __init__(
        self,
        user_id: int,
        organization_id: int,
        identity_type_id: int,
        user_name: str,
        password: str,
        email: str,
        mobile: str,
        otp: str,
        active: bool = True,
        blocked: bool = False,
    ) -> None:
        self._id = user_id
        self._id_org = organization_id
        self._id_type = identity_type_id
        self._user_name = user_name
        self._user_password = password
        self._user_email = email
        self._user_mobile = mobile
        self._user_otp = otp
        self._active = active
        self._blocked = blocked

    @property
    def id(self) -> int:
        return self._id

    @id.setter
    def id(self, value: int) -> None:
        self._id = value

    @property
    def id_org(self) -> int:
        return self._id_org

    @id_org.setter
    def id_org(self, value: int) -> None:
        self._id_org = value

    @property
    def id_type(self) -> int:
        return self._id_type

    @id_type.setter
    def id_type(self, value: int) -> None:
        self._id_type = value

    @property
    def user_name(self) -> str:
        return self._user_name

    @user_name.setter
    def user_name(self, value: str) -> None:
        self._user_name = value

    @property
    def user_password(self) -> str:
        return self._user_password

    @user_password.setter
    def user_password(self, value: str) -> None:
        self._user_password = value

    @property
    def user_email(self) -> str:
        return self._user_email

    @user_email.setter
    def user_email(self, value: str) -> None:
        self._user_email = value

    @property
    def user_mobile(self) -> str:
        return self._user_mobile

    @user_mobile.setter
    def user_mobile(self, value: str) -> None:
        self._user_mobile = value
    
    @property
    def user_otp(self) -> str:
        return self._user_otp

    @user_otp.setter
    def user_otp(self, value: str) -> None:
        self._user_otp = value

    def generate_otp(self) -> str:
        new_otp = f"{random.randint(1000, 9999)}"
        self._user_otp = new_otp
        return new_otp

    @property
    def active(self) -> bool:
        return self._active

    @active.setter
    def active(self, value: bool) -> None:
        self._active = value

    @property
    def blocked(self) -> bool:
        return self._blocked

    @blocked.setter
    def blocked(self, value: bool) -> None:
        self._blocked = value

    def activate_user(self) -> None:
        self._active = True

    def deactivate_user(self) -> None:
        self._active = False

    def block_user(self) -> None:
        self._blocked = True

    def unblock_user(self) -> None:
        self._blocked = False


class ContactInfo:
    """Información de contacto para un usuario."""

    def __init__(
        self,
        first_name: str,
        sur_name: str,
        country: str,
        state: str,
        zip_code: str,
        address: str,
    ) -> None:
        self._first_name = first_name
        self._sur_name = sur_name
        self._country = country
        self._state = state
        self._zip_code = zip_code
        self._address = address

    @property
    def first_name(self) -> str:
        return self._first_name

    @first_name.setter
    def first_name(self, value: str) -> None:
        self._first_name = value

    @property
    def sur_name(self) -> str:
        return self._sur_name

    @sur_name.setter
    def sur_name(self, value: str) -> None:
        self._sur_name = value

    @property
    def country(self) -> str:
        return self._country

    @country.setter
    def country(self, value: str) -> None:
        self._country = value

    @property
    def state(self) -> str:
        return self._state

    @state.setter
    def state(self, value: str) -> None:
        self._state = value

    @property
    def zip_code(self) -> str:
        return self._zip_code

    @zip_code.setter
    def zip_code(self, value: str) -> None:
        self._zip_code = value

    @property
    def address(self) -> str:
        return self._address

    @address.setter
    def address(self, value: str) -> None:
        self._address = value


class UserExtended(User):
    """Usuario extendido con información de contacto adicional."""

    def __init__(
        self,
        user: User,
        contact_info: ContactInfo,
        billing_info: ContactInfo | None = None,
    ) -> None:
        super().__init__(
            user_id=user.id,
            organization_id=user.id_org,
            identity_type_id=user.id_type,
            user_name=user.user_name,
            password=user.user_password,
            email=user.user_email,
            mobile=user.user_mobile,
            otp=user.user_otp,
            active=user.active,
            blocked=user.blocked,
        )
        self._contact_info = contact_info
        self._billing_info = billing_info or contact_info

    @property
    def contact_info(self) -> ContactInfo:
        return self._contact_info

    @contact_info.setter
    def contact_info(self, value: ContactInfo) -> None:
        self._contact_info = value

    @property
    def billing_info(self) -> ContactInfo:
        return self._billing_info

    @billing_info.setter
    def billing_info(self, value: ContactInfo) -> None:
        self._billing_info = value
