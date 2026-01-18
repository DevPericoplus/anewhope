# Shared domain entities
#
# This module contains the core entities shared across backend, trainer and
# frontend services. They model the ubiquitous language of the platform and
# avoid coupling to infrastructure concerns. When creating new entities,
# prefer dataclasses for immutability-friendly defaults and type hints for
# clarity.

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import List, Optional, Set


class DomainError(Exception):
    """Excepción base para errores de dominio."""
    pass


class ModelLifecycleState(str, Enum):
    """High-level status for a managed LLM artefact."""

    DRAFT = "draft"
    TRAINING = "training"
    EVALUATING = "evaluating"
    READY = "ready"
    DEPRECATED = "deprecated"


class Organization:
    """
    Representa una organización en el sistema.
    
    Esta clase se relaciona con las clases de tipo User a través del 
    organization_id, permitiendo que múltiples usuarios pertenezcan a 
    la misma organización.
    
    Relaciones:
        - Se relaciona con User a través de organization_id
        - Múltiples usuarios pueden pertenecer a la misma organización
    
    Atributos:
        organization_id (int): Identificador único de la organización.
                               Se relaciona con el organization_id de las clases User.
        organization_name (str): Nombre de la organización.
        organization_email (str): Email de contacto de la organización.
        organization_tlf (str): Teléfono de contacto de la organización.
        organization_address (str): Dirección física de la organización.
        organization_country (str): País donde se encuentra la organización.
        organization_state (str): Estado/Provincia donde se encuentra la organización.
    """

    def __init__(
        self,
        organization_id: int,
        organization_name: str,
        organization_email: str,
        organization_tlf: str,
        organization_address: str,
        organization_country: str,
        organization_state: str,
    ) -> None:
        # Validaciones
        if organization_id <= 0:
            raise DomainError(f"Organization ID must be positive, got: {organization_id}")
        if not organization_name or not organization_name.strip():
            raise DomainError("Organization name cannot be empty")
        if not self._is_valid_email(organization_email):
            raise DomainError(f"Invalid email format: {organization_email}")
        if not organization_tlf or not organization_tlf.strip():
            raise DomainError("Organization phone cannot be empty")
        if not organization_address or not organization_address.strip():
            raise DomainError("Organization address cannot be empty")
        if not organization_country or not organization_country.strip():
            raise DomainError("Organization country cannot be empty")
        if not organization_state or not organization_state.strip():
            raise DomainError("Organization state cannot be empty")
        
        self._organization_id = organization_id
        self._organization_name = organization_name.strip()
        self._organization_email = organization_email.lower().strip()
        self._organization_tlf = organization_tlf.strip()
        self._organization_address = organization_address.strip()
        self._organization_country = organization_country.strip()
        self._organization_state = organization_state.strip()

    def __eq__(self, other: object) -> bool:
        """Compara dos Organization por su ID."""
        if not isinstance(other, Organization):
            return False
        return self._organization_id == other._organization_id

    def __hash__(self) -> int:
        """Permite usar Organization en sets y diccionarios."""
        return hash(self._organization_id)

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """Valida el formato de email."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @property
    def organization_id(self) -> int:
        """Identificador único de la organización."""
        return self._organization_id

    @organization_id.setter
    def organization_id(self, value: int) -> None:
        if value <= 0:
            raise DomainError(f"Organization ID must be positive, got: {value}")
        self._organization_id = value

    @property
    def organization_name(self) -> str:
        """Nombre de la organización."""
        return self._organization_name

    @organization_name.setter
    def organization_name(self, value: str) -> None:
        if not value or not value.strip():
            raise DomainError("Organization name cannot be empty")
        self._organization_name = value.strip()

    @property
    def organization_email(self) -> str:
        """Email de contacto de la organización."""
        return self._organization_email

    @organization_email.setter
    def organization_email(self, value: str) -> None:
        if not self._is_valid_email(value):
            raise DomainError(f"Invalid email format: {value}")
        self._organization_email = value.lower().strip()

    @property
    def organization_tlf(self) -> str:
        """Teléfono de contacto de la organización."""
        return self._organization_tlf

    @organization_tlf.setter
    def organization_tlf(self, value: str) -> None:
        if not value or not value.strip():
            raise DomainError("Organization phone cannot be empty")
        self._organization_tlf = value.strip()

    @property
    def organization_address(self) -> str:
        """Dirección física de la organización."""
        return self._organization_address

    @organization_address.setter
    def organization_address(self, value: str) -> None:
        if not value or not value.strip():
            raise DomainError("Organization address cannot be empty")
        self._organization_address = value.strip()

    @property
    def organization_country(self) -> str:
        """País donde se encuentra la organización."""
        return self._organization_country

    @organization_country.setter
    def organization_country(self, value: str) -> None:
        if not value or not value.strip():
            raise DomainError("Organization country cannot be empty")
        self._organization_country = value.strip()

    @property
    def organization_state(self) -> str:
        """Estado/Provincia donde se encuentra la organización."""
        return self._organization_state

    @organization_state.setter
    def organization_state(self, value: str) -> None:
        if not value or not value.strip():
            raise DomainError("Organization state cannot be empty")
        self._organization_state = value.strip()

    def update_contact_info(self, email: str, phone: str) -> None:
        """Actualiza la información de contacto de la organización."""
        self.organization_email = email
        self.organization_tlf = phone

    def is_valid(self) -> bool:
        """Verifica si la organización tiene todos los datos requeridos."""
        return all([
            self._organization_id > 0,
            bool(self._organization_name),
            bool(self._organization_email),
            bool(self._organization_tlf),
            bool(self._organization_address),
            bool(self._organization_country),
            bool(self._organization_state),
        ])


class IdentityGlobal:
    """
    Representa un tipo de identidad global en el sistema.
    
    Esta clase se relaciona con las clases de tipo User a través del 
    identity_type_id, permitiendo definir diferentes tipos de identidades
    con sus respectivos roles y permisos.
    
    Relaciones:
        - Se relaciona con User a través de identity_type_id
        - Contiene una colección de Permissions que definen los permisos del tipo de identidad
    
    Atributos:
        identity_type_id (int): Identificador único del tipo de identidad.
                                Se relaciona con el identity_type_id de las clases User.
        identity_type_name (str): Nombre del tipo de identidad (ej: "Admin", "Usuario", "Invitado").
        identity_type_rol (str): Rol asociado al tipo de identidad.
        identity_type_group_permissions (List[Permissions]): Lista de permisos asociados al tipo de identidad.
    """

    def __init__(
        self,
        identity_type_id: int,
        identity_type_name: str,
        identity_type_rol: str,
        identity_type_group_permissions: List['Permissions'] | None = None,
    ) -> None:
        # Validaciones
        if identity_type_id <= 0:
            raise DomainError(f"Identity type ID must be positive, got: {identity_type_id}")
        if not identity_type_name or not identity_type_name.strip():
            raise DomainError("Identity type name cannot be empty")
        if not identity_type_rol or not identity_type_rol.strip():
            raise DomainError("Identity type role cannot be empty")
        if identity_type_group_permissions is None:
            identity_type_group_permissions = []
        if not isinstance(identity_type_group_permissions, list):
            raise DomainError("identity_type_group_permissions must be a list of Permissions")
        for perm in identity_type_group_permissions:
            if not isinstance(perm, Permissions):
                raise DomainError(f"All items in identity_type_group_permissions must be Permissions instances, got: {type(perm)}")
        
        self._identity_type_id = identity_type_id
        self._identity_type_name = identity_type_name.strip()
        self._identity_type_rol = identity_type_rol.strip()
        self._identity_type_group_permissions = identity_type_group_permissions

    def __eq__(self, other: object) -> bool:
        """Compara dos IdentityGlobal por su ID."""
        if not isinstance(other, IdentityGlobal):
            return False
        return self._identity_type_id == other._identity_type_id

    def __hash__(self) -> int:
        """Permite usar IdentityGlobal en sets y diccionarios."""
        return hash(self._identity_type_id)

    @property
    def identity_type_id(self) -> int:
        """Identificador único del tipo de identidad."""
        return self._identity_type_id

    @identity_type_id.setter
    def identity_type_id(self, value: int) -> None:
        if value <= 0:
            raise DomainError(f"Identity type ID must be positive, got: {value}")
        self._identity_type_id = value

    @property
    def identity_type_name(self) -> str:
        """Nombre del tipo de identidad."""
        return self._identity_type_name

    @identity_type_name.setter
    def identity_type_name(self, value: str) -> None:
        if not value or not value.strip():
            raise DomainError("Identity type name cannot be empty")
        self._identity_type_name = value.strip()

    @property
    def identity_type_rol(self) -> str:
        """Rol asociado al tipo de identidad."""
        return self._identity_type_rol

    @identity_type_rol.setter
    def identity_type_rol(self, value: str) -> None:
        if not value or not value.strip():
            raise DomainError("Identity type role cannot be empty")
        self._identity_type_rol = value.strip()

    @property
    def identity_type_group_permissions(self) -> List['Permissions']:
        """Lista de permisos asociados al tipo de identidad."""
        return self._identity_type_group_permissions.copy()

    @identity_type_group_permissions.setter
    def identity_type_group_permissions(self, value: List['Permissions']) -> None:
        if not isinstance(value, list):
            raise DomainError("identity_type_group_permissions must be a list of Permissions")
        for perm in value:
            if not isinstance(perm, Permissions):
                raise DomainError(f"All items must be Permissions instances, got: {type(perm)}")
        self._identity_type_group_permissions = value

    def add_permission(self, permission: 'Permissions') -> None:
        """Añade un permiso a la lista de permisos del tipo de identidad."""
        if not isinstance(permission, Permissions):
            raise DomainError(f"permission must be a Permissions instance, got: {type(permission)}")
        if permission not in self._identity_type_group_permissions:
            self._identity_type_group_permissions.append(permission)

    def remove_permission(self, permission: 'Permissions') -> None:
        """Elimina un permiso de la lista de permisos del tipo de identidad."""
        if permission in self._identity_type_group_permissions:
            self._identity_type_group_permissions.remove(permission)

    def has_permission(self, permission_id: int) -> bool:
        """Verifica si el tipo de identidad tiene un permiso específico por su ID."""
        return any(perm.id_permission == permission_id for perm in self._identity_type_group_permissions)


class Permissions:
    """
    Representa un permiso en el sistema.
    
    Esta clase define los permisos disponibles y sus características,
    incluyendo operaciones CRUD y otras acciones específicas.
    
    Atributos:
        id_permission (int): Identificador único del permiso.
        permission_name (str): Nombre del permiso.
        permission_description (str): Descripción detallada del permiso.
        enable (bool): Indica si el permiso está habilitado.
        create (bool): Permite crear recursos.
        delete (bool): Permite eliminar recursos.
        read (bool): Permite leer recursos.
        write (bool): Permite escribir/modificar recursos.
        execute (bool): Permite ejecutar acciones.
        log (bool): Indica si se debe registrar en log las acciones relacionadas.
        expired (datetime | None): Fecha y hora de expiración del permiso. None si no tiene expiración.
    """

    def __init__(
        self,
        id_permission: int,
        permission_name: str,
        permission_description: str,
        enable: bool = True,
        create: bool = False,
        delete: bool = False,
        read: bool = False,
        write: bool = False,
        execute: bool = False,
        log: bool = False,
        expired: datetime | None = None,
    ) -> None:
        # Validaciones
        if id_permission <= 0:
            raise DomainError(f"Permission ID must be positive, got: {id_permission}")
        if not permission_name or not permission_name.strip():
            raise DomainError("Permission name cannot be empty")
        if not permission_description or not permission_description.strip():
            raise DomainError("Permission description cannot be empty")
        if expired is not None and expired < datetime.now(timezone.utc):
            raise DomainError("Expiration date cannot be in the past")
        
        self._id_permission = id_permission
        self._permission_name = permission_name.strip()
        self._permission_description = permission_description.strip()
        self._enable = enable
        self._create = create
        self._delete = delete
        self._read = read
        self._write = write
        self._execute = execute
        self._log = log
        self._expired = expired

    def __eq__(self, other: object) -> bool:
        """Compara dos Permissions por su ID."""
        if not isinstance(other, Permissions):
            return False
        return self._id_permission == other._id_permission

    def __hash__(self) -> int:
        """Permite usar Permissions en sets y diccionarios."""
        return hash(self._id_permission)

    @property
    def id_permission(self) -> int:
        """Identificador único del permiso."""
        return self._id_permission

    @id_permission.setter
    def id_permission(self, value: int) -> None:
        if value <= 0:
            raise DomainError(f"Permission ID must be positive, got: {value}")
        self._id_permission = value

    @property
    def permission_name(self) -> str:
        """Nombre del permiso."""
        return self._permission_name

    @permission_name.setter
    def permission_name(self, value: str) -> None:
        if not value or not value.strip():
            raise DomainError("Permission name cannot be empty")
        self._permission_name = value.strip()

    @property
    def permission_description(self) -> str:
        """Descripción detallada del permiso."""
        return self._permission_description

    @permission_description.setter
    def permission_description(self, value: str) -> None:
        if not value or not value.strip():
            raise DomainError("Permission description cannot be empty")
        self._permission_description = value.strip()

    @property
    def enable(self) -> bool:
        """Indica si el permiso está habilitado."""
        return self._enable

    @enable.setter
    def enable(self, value: bool) -> None:
        self._enable = value

    @property
    def create(self) -> bool:
        """Permite crear recursos."""
        return self._create

    @create.setter
    def create(self, value: bool) -> None:
        self._create = value

    @property
    def delete(self) -> bool:
        """Permite eliminar recursos."""
        return self._delete

    @delete.setter
    def delete(self, value: bool) -> None:
        self._delete = value

    @property
    def read(self) -> bool:
        """Permite leer recursos."""
        return self._read

    @read.setter
    def read(self, value: bool) -> None:
        self._read = value

    @property
    def write(self) -> bool:
        """Permite escribir/modificar recursos."""
        return self._write

    @write.setter
    def write(self, value: bool) -> None:
        self._write = value

    @property
    def execute(self) -> bool:
        """Permite ejecutar acciones."""
        return self._execute

    @execute.setter
    def execute(self, value: bool) -> None:
        self._execute = value

    @property
    def log(self) -> bool:
        """Indica si se debe registrar en log las acciones relacionadas."""
        return self._log

    @log.setter
    def log(self, value: bool) -> None:
        self._log = value

    @property
    def expired(self) -> datetime | None:
        """Fecha y hora de expiración del permiso."""
        return self._expired

    @expired.setter
    def expired(self, value: datetime | None) -> None:
        if value is not None and value < datetime.now(timezone.utc):
            raise DomainError("Expiration date cannot be in the past")
        self._expired = value

    def is_expired(self) -> bool:
        """Verifica si el permiso ha expirado comparando la fecha de expiración con la fecha actual."""
        if self._expired is None:
            return False
        return datetime.now(timezone.utc) >= self._expired

    def is_active(self) -> bool:
        """Verifica si el permiso está activo (habilitado y no expirado)."""
        return self._enable and not self.is_expired()

    def has_crud_permissions(self) -> bool:
        """Verifica si el permiso tiene al menos una operación CRUD."""
        return self._create or self._read or self._write or self._delete

    def can_perform_action(self, action: str) -> bool:
        """Verifica si el permiso permite realizar una acción específica."""
        if not self.is_active():
            return False
        
        action_map = {
            'create': self._create,
            'read': self._read,
            'write': self._write,
            'delete': self._delete,
            'execute': self._execute,
        }
        return action_map.get(action.lower(), False)


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
    """
    Representa un usuario en el sistema.
    
    Relaciones:
        - Se relaciona con Organization a través de organization_id
        - Se relaciona con IdentityGlobal a través de identity_type_id
        - Un usuario pertenece a una organización y tiene un tipo de identidad
    
    Invariantes:
        - Un usuario no puede estar activo y bloqueado simultáneamente
        - El email debe tener un formato válido
        - La contraseña debe tener al menos 8 caracteres
        - El OTP debe tener exactamente 4 dígitos
    """

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
        # Validaciones
        if user_id <= 0:
            raise DomainError(f"User ID must be positive, got: {user_id}")
        if organization_id <= 0:
            raise DomainError(f"Organization ID must be positive, got: {organization_id}")
        if identity_type_id <= 0:
            raise DomainError(f"Identity type ID must be positive, got: {identity_type_id}")
        if not user_name or not user_name.strip():
            raise DomainError("Username cannot be empty")
        if not password or len(password) < 8:
            raise DomainError("Password must be at least 8 characters long")
        if not self._is_valid_email(email):
            raise DomainError(f"Invalid email format: {email}")
        if not mobile or not mobile.strip():
            raise DomainError("Mobile number cannot be empty")
        if not otp or len(otp) != 4 or not otp.isdigit():
            raise DomainError("OTP must be exactly 4 digits")
        
        # Invariante: usuario no puede estar activo y bloqueado simultáneamente
        if active and blocked:
            raise DomainError("User cannot be both active and blocked")
        
        self._id = user_id
        self._id_org = organization_id
        self._id_type = identity_type_id
        self._user_name = user_name.strip()
        self._user_password = password
        self._user_email = email.lower().strip()
        self._user_mobile = mobile.strip()
        self._user_otp = otp
        self._active = active
        self._blocked = blocked

    def __eq__(self, other: object) -> bool:
        """Compara dos User por su ID."""
        if not isinstance(other, User):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        """Permite usar User en sets y diccionarios."""
        return hash(self._id)

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """Valida el formato de email."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @property
    def id(self) -> int:
        return self._id

    @id.setter
    def id(self, value: int) -> None:
        if value <= 0:
            raise DomainError(f"User ID must be positive, got: {value}")
        self._id = value

    @property
    def id_org(self) -> int:
        return self._id_org

    @id_org.setter
    def id_org(self, value: int) -> None:
        if value <= 0:
            raise DomainError(f"Organization ID must be positive, got: {value}")
        self._id_org = value

    @property
    def id_type(self) -> int:
        return self._id_type

    @id_type.setter
    def id_type(self, value: int) -> None:
        if value <= 0:
            raise DomainError(f"Identity type ID must be positive, got: {value}")
        self._id_type = value

    @property
    def user_name(self) -> str:
        return self._user_name

    @user_name.setter
    def user_name(self, value: str) -> None:
        if not value or not value.strip():
            raise DomainError("Username cannot be empty")
        self._user_name = value.strip()

    @property
    def user_password(self) -> str:
        return self._user_password

    @user_password.setter
    def user_password(self, value: str) -> None:
        if not value or len(value) < 8:
            raise DomainError("Password must be at least 8 characters long")
        self._user_password = value

    @property
    def user_email(self) -> str:
        return self._user_email

    @user_email.setter
    def user_email(self, value: str) -> None:
        if not self._is_valid_email(value):
            raise DomainError(f"Invalid email format: {value}")
        self._user_email = value.lower().strip()

    @property
    def user_mobile(self) -> str:
        return self._user_mobile

    @user_mobile.setter
    def user_mobile(self, value: str) -> None:
        if not value or not value.strip():
            raise DomainError("Mobile number cannot be empty")
        self._user_mobile = value.strip()
    
    @property
    def user_otp(self) -> str:
        return self._user_otp

    @user_otp.setter
    def user_otp(self, value: str) -> None:
        if not value or len(value) != 4 or not value.isdigit():
            raise DomainError("OTP must be exactly 4 digits")
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
        if value and self._blocked:
            raise DomainError("Cannot activate a blocked user. Unblock first.")
        self._active = value

    @property
    def blocked(self) -> bool:
        return self._blocked

    @blocked.setter
    def blocked(self, value: bool) -> None:
        if value and self._active:
            # Si se bloquea, automáticamente desactivar
            self._active = False
        self._blocked = value

    def activate_user(self) -> None:
        """Activa el usuario. Si está bloqueado, primero lo desbloquea."""
        if self._blocked:
            raise DomainError("Cannot activate a blocked user. Unblock first.")
        self._active = True

    def deactivate_user(self) -> None:
        """Desactiva el usuario."""
        self._active = False

    def block_user(self) -> None:
        """Bloquea el usuario. Si está activo, primero lo desactiva."""
        if self._active:
            self._active = False
        self._blocked = True

    def unblock_user(self) -> None:
        """Desbloquea el usuario."""
        self._blocked = False

    def can_perform_action(self) -> bool:
        """Verifica si el usuario puede realizar acciones (activo y no bloqueado)."""
        return self._active and not self._blocked


@dataclass(frozen=True)
class ContactInfo:
    """
    Value Object que representa información de contacto para un usuario.
    Inmutable por diseño para garantizar consistencia.
    """

    first_name: str
    sur_name: str
    country: str
    state: str
    zip_code: str
    address: str

    def __post_init__(self) -> None:
        """Valida los datos después de la inicialización."""
        if not self.first_name or not self.first_name.strip():
            raise DomainError("First name cannot be empty")
        if not self.sur_name or not self.sur_name.strip():
            raise DomainError("Surname cannot be empty")
        if not self.country or not self.country.strip():
            raise DomainError("Country cannot be empty")
        if not self.state or not self.state.strip():
            raise DomainError("State cannot be empty")
        if not self.zip_code or not self.zip_code.strip():
            raise DomainError("Zip code cannot be empty")
        if not self.address or not self.address.strip():
            raise DomainError("Address cannot be empty")
        
        # Normalizar valores (usando object.__setattr__ porque es frozen)
        object.__setattr__(self, 'first_name', self.first_name.strip())
        object.__setattr__(self, 'sur_name', self.sur_name.strip())
        object.__setattr__(self, 'country', self.country.strip())
        object.__setattr__(self, 'state', self.state.strip())
        object.__setattr__(self, 'zip_code', self.zip_code.strip())
        object.__setattr__(self, 'address', self.address.strip())


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


@dataclass
class GoogleAuthInfo:
    """Información de autenticación de Google OAuth."""

    google_id: str
    google_access_token: str
    google_refresh_token: str | None = None
    google_token_expires_at: datetime | None = None
    google_picture_url: str | None = None
    google_verified_email: bool = False


class UserGoogle(User):
    """Usuario con autenticación de Google OAuth."""

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
        google_auth_info: GoogleAuthInfo,
        active: bool = True,
        blocked: bool = False,
    ) -> None:
        super().__init__(
            user_id=user_id,
            organization_id=organization_id,
            identity_type_id=identity_type_id,
            user_name=user_name,
            password=password,
            email=email,
            mobile=mobile,
            otp=otp,
            active=active,
            blocked=blocked,
        )
        self._google_auth_info = google_auth_info

    @property
    def google_auth_info(self) -> GoogleAuthInfo:
        """Información de autenticación de Google."""
        return self._google_auth_info

    @google_auth_info.setter
    def google_auth_info(self, value: GoogleAuthInfo) -> None:
        self._google_auth_info = value

    @property
    def google_id(self) -> str:
        """ID único de Google del usuario."""
        return self._google_auth_info.google_id

    @google_id.setter
    def google_id(self, value: str) -> None:
        self._google_auth_info.google_id = value

    @property
    def google_access_token(self) -> str:
        """Token de acceso de Google OAuth."""
        return self._google_auth_info.google_access_token

    @google_access_token.setter
    def google_access_token(self, value: str) -> None:
        self._google_auth_info.google_access_token = value

    @property
    def google_refresh_token(self) -> str | None:
        """Token de refresco de Google OAuth."""
        return self._google_auth_info.google_refresh_token

    @google_refresh_token.setter
    def google_refresh_token(self, value: str | None) -> None:
        self._google_auth_info.google_refresh_token = value

    @property
    def google_token_expires_at(self) -> datetime | None:
        """Fecha y hora de expiración del token de acceso."""
        return self._google_auth_info.google_token_expires_at

    @google_token_expires_at.setter
    def google_token_expires_at(self, value: datetime | None) -> None:
        self._google_auth_info.google_token_expires_at = value

    @property
    def google_picture_url(self) -> str | None:
        """URL de la foto de perfil de Google."""
        return self._google_auth_info.google_picture_url

    @google_picture_url.setter
    def google_picture_url(self, value: str | None) -> None:
        self._google_auth_info.google_picture_url = value

    @property
    def google_verified_email(self) -> bool:
        """Indica si el email está verificado por Google."""
        return self._google_auth_info.google_verified_email

    @google_verified_email.setter
    def google_verified_email(self, value: bool) -> None:
        self._google_auth_info.google_verified_email = value

    def is_token_expired(self) -> bool:
        """Verifica si el token de acceso ha expirado."""
        if self._google_auth_info.google_token_expires_at is None:
            return False
        return datetime.now(timezone.utc) >= self._google_auth_info.google_token_expires_at

    def update_tokens(
        self,
        access_token: str,
        refresh_token: str | None = None,
        expires_in: int | None = None,
    ) -> None:
        """Actualiza los tokens de Google OAuth."""
        self._google_auth_info.google_access_token = access_token
        if refresh_token is not None:
            self._google_auth_info.google_refresh_token = refresh_token
        if expires_in is not None:
            self._google_auth_info.google_token_expires_at = datetime.now(timezone.utc).replace(
                microsecond=0
            ) + timedelta(seconds=expires_in)
