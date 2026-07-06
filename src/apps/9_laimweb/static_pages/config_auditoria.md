# Auditoría y logs

## Trazabilidad del portal

Consulta de eventos de seguridad y actividad registrados por LAIM Web y servicios asociados.

### Fuentes de registro

| Origen | Contenido |
|--------|-----------|
| **laim_auth_logs** | Intentos de login, registro y bloqueos |
| **activity.log** | Inferencias, flujos y decisiones de agentes (sin respuestas del modelo) |
| **console.log** | Arranque y errores de servicios |

### Retención y acceso

- Solo usuarios con rol **administrador** pueden acceder a esta sección
- Los registros no incluyen respuestas completas del asistente (almacenadas cifradas en `laim.memory` en el cliente)

> Use esta sección para investigar incidencias de acceso o cumplimiento normativo.
