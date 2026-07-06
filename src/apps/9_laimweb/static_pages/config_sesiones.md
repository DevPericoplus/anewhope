# Gestión de sesiones

## Sesiones activas del portal

Visualización y revocación de sesiones JWT almacenadas en **laim_core_db** (`laim_sessions`).

### Información por sesión

- Usuario y organización
- Fecha de creación y última actividad
- Dirección IP y agente de usuario
- Estado: activa, expirada o revocada

### Acciones administrativas

- Cerrar sesión remota (logout forzado)
- Auditar accesos concurrentes (CLI + web)
- Limpiar sesiones expiradas

> Alineado con **Gestión de sesiones** en `laim config` del cliente de escritorio.
