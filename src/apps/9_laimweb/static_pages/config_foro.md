# Foro LAIM

## Guía documental (no es un panel de gestión)

Esta página **solo documenta** cómo se administra el foro. No hay formularios
ni acciones aquí. El backoffice vive **temporalmente en laim_maintenance**.
Más adelante esas operaciones se montarán en el servicio **backoffice** de
anewhope. El foro que usan las personas autenticadas (`/foro`) sigue siendo
el hilo público: leer, abrir temas y responder.

### Qué cubre la administración del foro

| Área | Para qué sirve |
|------|----------------|
| **Categorías y subcategorías** | El árbol que ve el usuario al filtrar hilos |
| **Prefijos** | Etiquetas de tema (anuncio, duda, …) |
| **Moderación** | Cerrar, fijar o retirar un hilo; registros de actuación |
| **Baneos** | Impedir que una cuenta publique |

### Dónde se opera hoy

1. **laim_maintenance** — backoffice temporal del operador (mismo salto
   `support_ops` que Contacto y Tickets).
2. **Cliente local** — no sustituye al foro del portal; el chat y `laim config`
   no crean categorías del portal.

### Lo que no se hace en esta página

No se crean categorías, no se moderan hilos y no se banear usuarios desde
laimweb. Si necesita un cambio, hágalo en laim_maintenance o abra un ticket
en **Soporte**.

> **Esta página es solo documental.** Las pantallas funcionales de
> administración no se implementan en laimweb hasta el backoffice.
