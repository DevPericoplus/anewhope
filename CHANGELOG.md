# Changelog

Todos los cambios notables de este proyecto se documentarán en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
y este proyecto sigue [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Dockerfiles y `docker-compose.yml` para el frontend y el middleware con entrypoints dedicados.
- API REST para broker backend (`8_service_backend`) con tres capas y logging local.
- API REST para backend core (`3_backend`) con tres capas y persistencia mock inicial.
- Entornos virtuales separados para frontend y middleware para evitar conflictos de dependencias.
- Integración de logging de seguridad en procesos de creación de usuarios/organizaciones.
- Funcionalidad de envío de SMS y validaciones relacionadas.
- Test de seguridad para invalidación de tokens tras logout en el middleware.
- Tests unitarios e integración para broker/core y flujo middleware → broker → core.
- Documentación de la gestión de roles por organización con mapeo dominio/DTO/mock/BD.
- Documentación de permisos básicos con mapeo dominio/DTO/mock/BD y flujo API.
- Relación 1 a 1 entre roles y permisos en mocks y esquema de MariaDB.
- Capa de permisos de bajo nivel con mock exportado desde MariaDB y endpoints API.
- ADR actualizado: operaciones de filesystem delegadas a `fmanagement` (Go) por rendimiento y seguridad.
- Endpoint `GET /models/active` a través de toda la cadena API (middleware → broker → core).
- Esquema canónico de BD (`schema_core.sql`, `schema_projects.sql`) y documentación de inicialización.
- Páginas de descarga de modelos y soporte de paquetes GGUF en UI.
- Fases autónomas de entrenamiento 6-9 y subida via fmanagement.
- `tests/helpers.py`: módulo de utilidades compartidas para todos los tests (carga dinámica de módulos, credenciales, URLs de servicio, conexiones BD).
- `tests/conftest.py`: fixtures pytest con soporte multi-entorno (`project_root`, `protected_values`, `db_engine_core`, `db_engine_projects`).
- Ficheros `protected_values.py.example` para los 4 entornos (macbook, dev, pre, pro) con placeholders seguros.

### Changed
- Estandarización de puertos por regla `8000 + primer dígito del nombre de carpeta`.
- Ajustes a `run.sh` y `entrypoint.sh` para ejecución local y en contenedor.
- Mejoras de UX y validaciones en formularios de creación de usuario/organización.
- Actualización de configuraciones y documentación para el despliegue de servicios.
- Validación de sesión reforzada para rechazar tokens tras logout.
- Middleware con modo de almacenamiento conmutado (`mock`, `mock_and_db`, `db_only`).
- Reorganización de ficheros raíz en `tests/`, `scripts/` y `docs/`.
- `full_test.sh` reescrito con interfaz CLI (`--unit`, `--integration`, `--e2e`, `--all`) y activación automática de venvs por sección.
- Todos los tests de `tests/` actualizados para usar `importlib.util` en lugar de imports directos a directorios con prefijo numérico.
- Tests E2E y de integración migrados de credenciales hardcodeadas a carga dinámica desde `protected_values.py` via `tests/helpers.py`.
- `tests/requirements_test.txt` actualizado con dependencias completas (httpx, pytest, pymysql, SQLAlchemy, requests, PyYAML).

### Fixed
- Validación consistente de OTP (longitud y dígitos) en el dominio.
- Manejo correcto de errores de serialización al escribir JSON.
- Desempaquetado correcto del valor devuelto por `decrypt_value()`.
- Persistencia de sesiones al autenticar usuarios para no perder el registro creado.
- Carga segura de `DomainError` en `session.py` para evitar errores de importación.
- Imports rotos en `tests/unit/` y `tests/integration/` por directorios con prefijo numérico (`1_shared_domain`, `2_shared_application`, `3_backend`).
- URLs y credenciales hardcodeadas eliminadas de ~30 ficheros de test (Python y shell).
- Targets de `unittest.mock.patch` corregidos para imports lazy de SQLAlchemy.

## [0.1.0] - 2025-10-16

### Added
- Estructura inicial del proyecto y primera configuración de `.gitignore`.
- Primeras utilidades de cifrado y base del modelo de usuario.
