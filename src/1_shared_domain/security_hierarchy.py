"""Modelos de jerarquía de seguridad a nivel de dominio."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Sequence, TypeVar

Record: TypeVar = TypeVar("Record")


@dataclass(frozen=True, slots=True)
class Role:
    """Representa un rol dentro de la jerarquía de seguridad."""

    identity_type_id: int
    identity_type_name: str
    identity_type_rol: str
    identity_type_group_permissions: tuple[int, ...]

    def __post_init__(self) -> None:
        _require_int(self.identity_type_id, "identity_type_id")
        _require_str(self.identity_type_name, "identity_type_name")
        _require_str(self.identity_type_rol, "identity_type_rol")
        _require_int_sequence(
            self.identity_type_group_permissions, "identity_type_group_permissions"
        )
        if len(self.identity_type_group_permissions) != 1:
            raise ValueError(
                "identity_type_group_permissions debe contener exactamente un permiso"
            )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Role":
        """Crea un rol desde un diccionario de datos."""

        identity_type_id = _require_mapping_int(data, "identity_type_id")
        identity_type_name = _require_mapping_str(data, "identity_type_name")
        identity_type_rol = _require_mapping_str(data, "identity_type_rol")
        permissions = _require_mapping_int_sequence(
            data, "identity_type_group_permissions"
        )
        return cls(
            identity_type_id=identity_type_id,
            identity_type_name=identity_type_name,
            identity_type_rol=identity_type_rol,
            identity_type_group_permissions=tuple(permissions),
        )


@dataclass(frozen=True, slots=True)
class BasicPermission:
    """Representa un permiso básico del sistema."""

    permission_id: int
    permission_name: str
    permission_description: str

    def __post_init__(self) -> None:
        _require_int(self.permission_id, "permission_id")
        _require_str(self.permission_name, "permission_name")
        _require_str(self.permission_description, "permission_description")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "BasicPermission":
        """Crea un permiso básico desde un diccionario de datos."""

        permission_id = _require_mapping_int(data, "id")
        permission_name = _require_mapping_str(data, "PermissionName")
        permission_description = _require_mapping_str(data, "PermissionDescription")
        return cls(
            permission_id=permission_id,
            permission_name=permission_name,
            permission_description=permission_description,
        )


@dataclass(frozen=True, slots=True)
class LowLevelPermission:
    """Representa permisos de bajo nivel asociados a un permiso base."""

    id_permissions: int
    folder_create: bool
    folder_delete: bool
    folder_rename: bool
    folder_read: bool
    file_create: bool
    file_read: bool
    file_update: bool
    file_delete: bool
    project_create: bool
    project_read: bool
    project_update: bool
    project_delete: bool
    version_create: bool
    version_read: bool
    version_update: bool
    version_delete: bool
    training_create: bool
    training_read: bool
    training_update: bool
    training_delete: bool
    training_start: bool
    training_stop: bool
    parameters_create: bool
    parameters_read: bool
    parameters_update: bool
    parameters_delete: bool
    notifications_create: bool
    notifications_read: bool
    notifications_update: bool
    notifications_delete: bool
    user_create: bool
    user_read: bool
    user_update: bool
    user_delete: bool
    user_enable: bool
    user_disable: bool
    folder_list: bool
    file_list: bool
    project_list: bool
    version_list: bool

    def __post_init__(self) -> None:
        _require_int(self.id_permissions, "id_permissions")
        _require_bool(self.folder_create, "folder_create")
        _require_bool(self.folder_delete, "folder_delete")
        _require_bool(self.folder_rename, "folder_rename")
        _require_bool(self.folder_read, "folder_read")
        _require_bool(self.file_create, "file_create")
        _require_bool(self.file_read, "file_read")
        _require_bool(self.file_update, "file_update")
        _require_bool(self.file_delete, "file_delete")
        _require_bool(self.project_create, "project_create")
        _require_bool(self.project_read, "project_read")
        _require_bool(self.project_update, "project_update")
        _require_bool(self.project_delete, "project_delete")
        _require_bool(self.version_create, "version_create")
        _require_bool(self.version_read, "version_read")
        _require_bool(self.version_update, "version_update")
        _require_bool(self.version_delete, "version_delete")
        _require_bool(self.training_create, "training_create")
        _require_bool(self.training_read, "training_read")
        _require_bool(self.training_update, "training_update")
        _require_bool(self.training_delete, "training_delete")
        _require_bool(self.training_start, "training_start")
        _require_bool(self.training_stop, "training_stop")
        _require_bool(self.parameters_create, "parameters_create")
        _require_bool(self.parameters_read, "parameters_read")
        _require_bool(self.parameters_update, "parameters_update")
        _require_bool(self.parameters_delete, "parameters_delete")
        _require_bool(self.notifications_create, "notifications_create")
        _require_bool(self.notifications_read, "notifications_read")
        _require_bool(self.notifications_update, "notifications_update")
        _require_bool(self.notifications_delete, "notifications_delete")
        _require_bool(self.user_create, "user_create")
        _require_bool(self.user_read, "user_read")
        _require_bool(self.user_update, "user_update")
        _require_bool(self.user_delete, "user_delete")
        _require_bool(self.user_enable, "user_enable")
        _require_bool(self.user_disable, "user_disable")
        _require_bool(self.folder_list, "folder_list")
        _require_bool(self.file_list, "file_list")
        _require_bool(self.project_list, "project_list")
        _require_bool(self.version_list, "version_list")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LowLevelPermission":
        """Crea permisos de bajo nivel desde un diccionario."""

        return cls(
            id_permissions=_require_mapping_int(data, "id_permissions"),
            folder_create=_require_mapping_bool(data, "folder_create"),
            folder_delete=_require_mapping_bool(data, "folder_delete"),
            folder_rename=_require_mapping_bool(data, "folder_rename"),
            folder_read=_require_mapping_bool(data, "folder_read"),
            file_create=_require_mapping_bool(data, "file_create"),
            file_read=_require_mapping_bool(data, "file_read"),
            file_update=_require_mapping_bool(data, "file_update"),
            file_delete=_require_mapping_bool(data, "file_delete"),
            project_create=_require_mapping_bool(data, "project_create"),
            project_read=_require_mapping_bool(data, "project_read"),
            project_update=_require_mapping_bool(data, "project_update"),
            project_delete=_require_mapping_bool(data, "project_delete"),
            version_create=_require_mapping_bool(data, "version_create"),
            version_read=_require_mapping_bool(data, "version_read"),
            version_update=_require_mapping_bool(data, "version_update"),
            version_delete=_require_mapping_bool(data, "version_delete"),
            training_create=_require_mapping_bool(data, "training_create"),
            training_read=_require_mapping_bool(data, "training_read"),
            training_update=_require_mapping_bool(data, "training_update"),
            training_delete=_require_mapping_bool(data, "training_delete"),
            training_start=_require_mapping_bool(data, "training_start"),
            training_stop=_require_mapping_bool(data, "training_stop"),
            parameters_create=_require_mapping_bool(data, "parameters_create"),
            parameters_read=_require_mapping_bool(data, "parameters_read"),
            parameters_update=_require_mapping_bool(data, "parameters_update"),
            parameters_delete=_require_mapping_bool(data, "parameters_delete"),
            notifications_create=_require_mapping_bool(data, "notifications_create"),
            notifications_read=_require_mapping_bool(data, "notifications_read"),
            notifications_update=_require_mapping_bool(data, "notifications_update"),
            notifications_delete=_require_mapping_bool(data, "notifications_delete"),
            user_create=_require_mapping_bool(data, "user_create"),
            user_read=_require_mapping_bool(data, "user_read"),
            user_update=_require_mapping_bool(data, "user_update"),
            user_delete=_require_mapping_bool(data, "user_delete"),
            user_enable=_require_mapping_bool(data, "user_enable"),
            user_disable=_require_mapping_bool(data, "user_disable"),
            folder_list=_require_mapping_bool(data, "folder_list"),
            file_list=_require_mapping_bool(data, "file_list"),
            project_list=_require_mapping_bool(data, "project_list"),
            version_list=_require_mapping_bool(data, "version_list"),
        )

@dataclass(frozen=True, slots=True)
class ManagedRoleByOrg:
    """Representa una asignación de rol por organización."""

    user_id: int
    organization_id: int
    identity_type_id: int
    create_date: str
    modification_date: str
    modifier_user_id: int
    active: bool

    def __post_init__(self) -> None:
        _require_int(self.user_id, "user_id")
        _require_int(self.organization_id, "organization_id")
        _require_int(self.identity_type_id, "identity_type_id")
        _require_str(self.create_date, "create_date")
        _require_str(self.modification_date, "modification_date")
        _require_int(self.modifier_user_id, "modifier_user_id")
        _require_bool(self.active, "active")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ManagedRoleByOrg":
        """Crea una asignación desde un diccionario de datos."""

        user_id = _require_mapping_int(data, "id_user")
        organization_id = _require_mapping_int(data, "id_organization")
        identity_type_id = _require_mapping_int(data, "identity_type_id")
        create_date = _require_mapping_str(data, "create_date")
        modification_date = _require_mapping_str(data, "modification_date")
        modifier_user_id = _require_mapping_int(data, "id_modifier_user")
        active = _require_mapping_bool(data, "active")
        return cls(
            user_id=user_id,
            organization_id=organization_id,
            identity_type_id=identity_type_id,
            create_date=create_date,
            modification_date=modification_date,
            modifier_user_id=modifier_user_id,
            active=active,
        )


class Roles:
    """Contenedor de roles, independiente del origen de datos."""

    def __init__(self, items: Sequence[Role]) -> None:
        self._items = tuple(items)

    @property
    def items(self) -> tuple[Role, ...]:
        """Retorna los roles en memoria."""

        return self._items

    def get_by_identity_type_id(self, identity_type_id: int) -> Role | None:
        """Obtiene un rol por `identity_type_id`."""

        for role in self._items:
            if role.identity_type_id == identity_type_id:
                return role
        return None

    def get_name_map(self) -> dict[int, str]:
        """Retorna un mapa `{identity_type_id: identity_type_name}`."""

        result = {role.identity_type_id: role.identity_type_name for role in self._items}
        return dict(sorted(result.items()))

    @classmethod
    def from_records(cls, records: Iterable[Mapping[str, Any]]) -> "Roles":
        """Construye el contenedor desde registros externos."""

        return cls([Role.from_dict(record) for record in records])

    @staticmethod
    def validate_structure(
        records: Iterable[Mapping[str, Any]],
    ) -> tuple[bool, list[str]]:
        """Valida la estructura de roles proveniente de cualquier fuente."""

        return _validate_records(records, Role.from_dict)


class BasicPermissions:
    """Contenedor de permisos básicos, independiente del origen de datos."""

    def __init__(self, items: Sequence[BasicPermission]) -> None:
        self._items = tuple(items)

    @property
    def items(self) -> tuple[BasicPermission, ...]:
        """Retorna los permisos en memoria."""

        return self._items

    def get_by_id(self, permission_id: int) -> BasicPermission | None:
        """Obtiene un permiso por `permission_id`."""

        for permission in self._items:
            if permission.permission_id == permission_id:
                return permission
        return None

    def get_name_map(self) -> dict[int, str]:
        """Retorna un mapa `{permission_id: permission_name}`."""

        result = {
            permission.permission_id: permission.permission_name
            for permission in self._items
        }
        return dict(sorted(result.items()))

    @classmethod
    def from_records(
        cls, records: Iterable[Mapping[str, Any]]
    ) -> "BasicPermissions":
        """Construye el contenedor desde registros externos."""

        return cls([BasicPermission.from_dict(record) for record in records])

    @staticmethod
    def validate_structure(
        records: Iterable[Mapping[str, Any]],
    ) -> tuple[bool, list[str]]:
        """Valida la estructura de permisos proveniente de cualquier fuente."""

        return _validate_records(records, BasicPermission.from_dict)


class LowLevelPermissions:
    """Contenedor de permisos de bajo nivel."""

    def __init__(self, items: Sequence[LowLevelPermission]) -> None:
        self._items = tuple(items)

    @property
    def items(self) -> tuple[LowLevelPermission, ...]:
        """Retorna los permisos de bajo nivel en memoria."""

        return self._items

    def get_by_id(self, permission_id: int) -> LowLevelPermission | None:
        """Obtiene permisos de bajo nivel por `id_permissions`."""

        for permission in self._items:
            if permission.id_permissions == permission_id:
                return permission
        return None

    @classmethod
    def from_records(
        cls, records: Iterable[Mapping[str, Any]]
    ) -> "LowLevelPermissions":
        """Construye el contenedor desde registros externos."""

        return cls([LowLevelPermission.from_dict(record) for record in records])

    @staticmethod
    def validate_structure(
        records: Iterable[Mapping[str, Any]],
    ) -> tuple[bool, list[str]]:
        """Valida la estructura de permisos de bajo nivel."""

        return _validate_records(records, LowLevelPermission.from_dict)


class ManageRolesByOrg:
    """Contenedor de asignaciones de roles por organización."""

    def __init__(self, items: Sequence[ManagedRoleByOrg]) -> None:
        self._items = tuple(items)

    @property
    def items(self) -> tuple[ManagedRoleByOrg, ...]:
        """Retorna las asignaciones en memoria."""

        return self._items

    def filter_by_user_id(self, user_id: int) -> tuple[ManagedRoleByOrg, ...]:
        """Retorna asignaciones para un `user_id` específico."""

        return tuple(item for item in self._items if item.user_id == user_id)

    def filter_by_organization_id(
        self, organization_id: int
    ) -> tuple[ManagedRoleByOrg, ...]:
        """Retorna asignaciones para un `organization_id` específico."""

        return tuple(
            item for item in self._items if item.organization_id == organization_id
        )

    @classmethod
    def from_records(
        cls, records: Iterable[Mapping[str, Any]]
    ) -> "ManageRolesByOrg":
        """Construye el contenedor desde registros externos."""

        return cls([ManagedRoleByOrg.from_dict(record) for record in records])

    @staticmethod
    def validate_structure(
        records: Iterable[Mapping[str, Any]],
    ) -> tuple[bool, list[str]]:
        """Valida la estructura de asignaciones proveniente de cualquier fuente."""

        return _validate_records(records, ManagedRoleByOrg.from_dict)


def _validate_records(
    records: Iterable[Mapping[str, Any]],
    builder: Callable[[Mapping[str, Any]], Record],
) -> tuple[bool, list[str]]:
    """Valida registros construyendo modelos y capturando errores."""

    errors: list[str] = []

    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            errors.append(f"Registro {index}: se esperaba un mapeo de datos")
            continue
        try:
            builder(record)
        except ValueError as exc:
            errors.append(f"Registro {index}: {exc}")

    return len(errors) == 0, errors


def _require_mapping_int(data: Mapping[str, Any], key: str) -> int:
    """Obtiene un entero obligatorio desde un mapeo."""

    value = _require_mapping_value(data, key)
    _require_int(value, key)
    return value


def _require_mapping_str(data: Mapping[str, Any], key: str) -> str:
    """Obtiene un string obligatorio desde un mapeo."""

    value = _require_mapping_value(data, key)
    _require_str(value, key)
    return value


def _require_mapping_bool(data: Mapping[str, Any], key: str) -> bool:
    """Obtiene un booleano obligatorio desde un mapeo."""

    value = _require_mapping_value(data, key)
    _require_bool(value, key)
    return value


def _require_mapping_int_sequence(
    data: Mapping[str, Any], key: str
) -> tuple[int, ...]:
    """Obtiene una secuencia de enteros desde un mapeo."""

    value = _require_mapping_value(data, key)
    _require_int_sequence(value, key)
    return tuple(value)


def _require_mapping_value(data: Mapping[str, Any], key: str) -> Any:
    """Obtiene un valor obligatorio desde un mapeo."""

    if key not in data:
        raise ValueError(f"falta la clave '{key}'")
    return data[key]


def _require_int(value: Any, field_name: str) -> None:
    """Valida que el valor sea un entero."""

    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"'{field_name}' debe ser un entero")


def _require_str(value: Any, field_name: str) -> None:
    """Valida que el valor sea un string."""

    if not isinstance(value, str):
        raise ValueError(f"'{field_name}' debe ser un string")


def _require_bool(value: Any, field_name: str) -> None:
    """Valida que el valor sea un booleano."""

    if not isinstance(value, bool):
        raise ValueError(f"'{field_name}' debe ser un booleano")


def _require_int_sequence(value: Any, field_name: str) -> None:
    """Valida que el valor sea una secuencia de enteros."""

    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"'{field_name}' debe ser una secuencia de enteros")
    for item in value:
        if not isinstance(item, int) or isinstance(item, bool):
            raise ValueError(f"'{field_name}' debe contener solo enteros")
