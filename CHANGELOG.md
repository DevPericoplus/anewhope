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
- Script `full_test.sh` para ejecutar tests de frontend y middleware de forma secuencial.
- Integración de logging de seguridad en procesos de creación de usuarios/organizaciones.
- Funcionalidad de envío de SMS y validaciones relacionadas.
- Test de seguridad para invalidación de tokens tras logout en el middleware.
- Tests unitarios e integración para broker/core y flujo middleware → broker → core.
- Documentación de la gestión de roles por organización con mapeo dominio/DTO/mock/BD.
- Documentación de permisos básicos con mapeo dominio/DTO/mock/BD y flujo API.
- Relación 1 a 1 entre roles y permisos en mocks y esquema de MariaDB.
- Capa de permisos de bajo nivel con mock exportado desde MariaDB y endpoints API.

### Changed
- Estandarización de puertos por regla `8000 + primer dígito del nombre de carpeta`.
- Ajustes a `run.sh` y `entrypoint.sh` para ejecución local y en contenedor.
- Mejoras de UX y validaciones en formularios de creación de usuario/organización.
- Actualización de configuraciones y documentación para el despliegue de servicios.
- Validación de sesión reforzada para rechazar tokens tras logout.
- Middleware con modo de almacenamiento conmutado (`mock`, `mock_and_db`, `db_only`).

### Fixed
- Validación consistente de OTP (longitud y dígitos) en el dominio.
- Manejo correcto de errores de serialización al escribir JSON.
- Desempaquetado correcto del valor devuelto por `decrypt_value()`.
- Ajustes de imports en tests para ejecución estable desde la raíz.
- Persistencia de sesiones al autenticar usuarios para no perder el registro creado.
- Carga segura de `DomainError` en `session.py` para evitar errores de importación.

## [0.1.0] - 2025-10-16

### Added
- Estructura inicial del proyecto y primera configuración de `.gitignore`.
- Primeras utilidades de cifrado y base del modelo de usuario.
