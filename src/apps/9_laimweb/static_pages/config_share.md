# LAIM Share / Connect

## Guía documental (no es un panel de gestión)

Esta página **solo documenta** las topologías Share y Connect. No se
arranca el listener ni se guardan credenciales desde el portal. Eso se
hace en el **cliente** (`laim share` / `laim connect`) y, a nivel de
organización, **temporalmente en laim_maintenance**. El backoffice de
laimweb llegará más adelante.

### Share (maestro)

Un equipo **ofrece** inferencia a otros de la red.

- Listener `share_api` (puerto por defecto **4322**)
- Credenciales que entregan los clientes Connect
- Qué modelos remotos se publican

```bash
laim share
```

### Connect (cliente)

Un equipo **usa** la IA de un Share. Las acciones sobre el sistema vivo
siguen ejecutándose donde usted está sentado; lo que viaja es la
inferencia, cifrada.

- URL del nodo maestro
- Prueba de conectividad
- Chat remoto sin Ollama local

```bash
laim connect
```

### Ejemplo de lectura

En el Mac que tiene GPU: `laim share`. En el portátil de la sala:
`laim connect` y elige ese maestro. El portal no sustituye esos dos
comandos.

> **Esta página es solo documental.** No hay botones de arranque ni
> formularios de credenciales en laimweb.
