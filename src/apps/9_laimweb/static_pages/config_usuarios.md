# Gestión de usuarios

## Guía documental (no es un panel de gestión)

Esta página **solo documenta** las cuentas del portal. No se dan de alta,
baja ni se cambian roles desde aquí. Esas operaciones viven
**temporalmente en laim_maintenance**. Más adelante se montarán en el
servicio **backoffice**. En cada instalación local, el equivalente sigue
siendo `laim config` (usuarios de `laim.dat`), que es **otro** censo: el
del cliente, no el de `laim_core_db`.

### Cuentas del portal

Los usuarios registrados en **laim_core_db**: altas, bajas lógicas, roles
y restablecimiento de acceso.

### Operaciones previstas (en el backoffice, no aquí)

- Listar usuarios activos e inactivos de la organización
- Asignar rol (Lector, Editor, Administrador, etc.)
- Habilitar o deshabilitar cuentas
- Revisar intentos de acceso fallidos

### Roles habituales

| Rol | Uso |
|-----|-----|
| **SuperAdmin** | Configuración completa del portal y catálogos |
| **Administrador** | Gestión de usuarios y recursos de la organización |
| **Editor** | Uso avanzado de modelos y complementos |
| **Lector** | Acceso estándar tras el registro público |

Solo SuperAdmin y Administrador de organización ven el menú
**Configuración**. Un lector o editor no debe ver estas páginas.

> **Esta página es solo documental.** Use laim_maintenance para operar;
> el backoffice de laimweb llegará después.
