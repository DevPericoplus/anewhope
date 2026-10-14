# Auditoría y logs

## Guía documental (no es un visor de logs)

Esta página **solo documenta** qué se registra y quién puede verlo. No
hay un visor aquí. La consulta operativa vive **temporalmente en
laim_maintenance**. En el cliente local: `laim audit` (cambios de
`laim.dat`, solo administrador). El visor del portal llegará con el
**backoffice**.

### Fuentes de registro

| Origen | Contenido |
|--------|-----------|
| **laim_auth_logs** | Intentos de login, registro y bloqueos |
| **activity.log** | Inferencias, flujos y decisiones de agentes (sin respuestas del modelo) |
| **console.log** | Arranque y errores de servicios |
| **audit.dat** (cliente) | Quién cambió usuarios, tiers, Share/Connect… |

### Retención y acceso

- Solo rol **administrador** (y el menú Configuración)
- Los registros del portal no incluyen las respuestas completas del
  asistente (en el cliente van cifradas en `laim.memory`)

```bash
laim audit
```

> **Esta página es solo documental.** Para investigar un acceso o un
> cambio de configuración use laim_maintenance o `laim audit` en el
> equipo afectado.
