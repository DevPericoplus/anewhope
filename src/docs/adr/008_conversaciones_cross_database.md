# ADR 008: Sistema de Conversaciones con Referencias Cross-Database

**Fecha:** 2026-02-05
**Estado:** Aceptado
**Decisores:** Equipo de Desarrollo
**Tags:** conversaciones, base-de-datos, integridad-referencial, arquitectura

## Contexto y Problema

Necesitamos implementar un sistema de conversaciones entre usuarios cliente (frontend) y usuarios internos (backoffice) que:

1. Permita comunicación en tiempo real sobre proyectos y tickets de soporte
2. Mantenga historial completo de mensajes
3. Soporte múltiples usuarios internos atendiendo la misma conversación
4. Relacione conversaciones con tickets de soporte
5. Gestione asignaciones de usuarios internos a organizaciones

### Desafío Arquitectónico

El sistema tiene dos bases de datos separadas:
- **`myllm_core_db`**: Contiene `users` y `organizations`
- **`myllm_projects_db`**: Contiene `proyectos`, `tickets`, `versiones`, etc.

Las conversaciones necesitan referenciar:
- Usuarios (en `myllm_core_db.users`)
- Organizaciones (en `myllm_core_db.organizations`)
- Tickets (en `myllm_projects_db.tickets`)

**Problema:** MariaDB/MySQL no permite crear Foreign Keys entre bases de datos diferentes.

## Decisión

**Crear todas las tablas de conversaciones en `myllm_projects_db` SIN foreign keys a `users` y `organizations`.**

### Tablas Creadas

1. `asignaciones_organizaciones_internas` - Asignación de usuarios internos a organizaciones
2. `conversaciones` - Registro de cada conversación
3. `participantes_conversacion` - Participantes de cada conversación
4. `mensajes_conversacion` - Todos los mensajes
5. `conversaciones_tickets_relacionados` - Relación N:M con tickets

### Foreign Keys Implementadas

✅ **Mantenidas (tablas locales):**
- `conversaciones.id_ticket_principal` → `tickets.id`
- `asignaciones_organizaciones_internas.id_rol` → `proyectos_roles_base.id`
- `participantes_conversacion.id_conversacion` → `conversaciones.id_conversacion`
- `mensajes_conversacion.id_conversacion` → `conversaciones.id_conversacion`
- `mensajes_conversacion.id_ticket_referenciado` → `tickets.id`
- `conversaciones_tickets_relacionados.id_conversacion` → `conversaciones.id_conversacion`
- `conversaciones_tickets_relacionados.id_ticket` → `tickets.id`

❌ **Omitidas (referencias cross-database):**
- `conversaciones.id_organizacion` (ref: `myllm_core_db.organizations.id`)
- `conversaciones.id_usuario_cliente` (ref: `myllm_core_db.users.id`)
- `conversaciones.cerrada_por` (ref: `myllm_core_db.users.id`)
- `asignaciones_organizaciones_internas.id_usuario_interno` (ref: `myllm_core_db.users.id`)
- `asignaciones_organizaciones_internas.id_organizacion` (ref: `myllm_core_db.organizations.id`)
- `asignaciones_organizaciones_internas.asignado_por` (ref: `myllm_core_db.users.id`)
- `asignaciones_organizaciones_internas.desactivado_por` (ref: `myllm_core_db.users.id`)
- `participantes_conversacion.id_usuario` (ref: `myllm_core_db.users.id`)
- `mensajes_conversacion.id_usuario_emisor` (ref: `myllm_core_db.users.id`)
- `mensajes_conversacion.editado_por` (ref: `myllm_core_db.users.id`)
- `conversaciones_tickets_relacionados.mencionado_por` (ref: `myllm_core_db.users.id`)

### Estrategia de Integridad Referencial

**En lugar de FKs de base de datos, implementamos validación en la capa de aplicación:**

```python
# Antes de crear conversación, validar que usuario y organización existen
def crear_conversacion(engine_projects, engine_core, id_usuario, id_org, ...):
    # 1. Validar en myllm_core_db que el usuario existe
    with engine_core.connect() as conn:
        result = conn.execute(
            text("SELECT id FROM users WHERE id = :user_id"),
            {"user_id": id_usuario}
        )
        if not result.fetchone():
            raise ValueError(f"Usuario {id_usuario} no existe")

    # 2. Validar en myllm_core_db que la organización existe
    with engine_core.connect() as conn:
        result = conn.execute(
            text("SELECT id FROM organizations WHERE id = :org_id"),
            {"org_id": id_org}
        )
        if not result.fetchone():
            raise ValueError(f"Organización {id_org} no existe")

    # 3. Ahora sí, crear conversación en myllm_projects_db
    with engine_projects.connect() as conn:
        result = conn.execute(
            text("""INSERT INTO conversaciones
                    (id_organizacion, id_usuario_cliente, ...)
                    VALUES (:org_id, :user_id, ...)"""),
            {"org_id": id_org, "user_id": id_usuario, ...}
        )
```

## Alternativas Consideradas

### Alternativa 1: Crear todo en `myllm_core_db`

**Ventajas:**
- ✅ Todas las FKs funcionan (users, organizations, identity_types)
- ✅ Integridad referencial completa garantizada por la BD

**Desventajas:**
- ❌ Conversaciones separadas conceptualmente de proyectos y tickets
- ❌ `myllm_core_db` se vuelve monolítica con lógica de negocio de proyectos
- ❌ Pérdida de cohesión: los proyectos están en otra BD

**Razón del rechazo:** Las conversaciones están fuertemente acopladas a proyectos y tickets de soporte, que ya están en `myllm_projects_db`. Separar esto rompería la cohesión del dominio de negocio.

### Alternativa 2: Migrar users y organizations a `myllm_projects_db`

**Ventajas:**
- ✅ Todo en una sola base de datos
- ✅ Todas las FKs funcionan

**Desventajas:**
- ❌ Requiere migración masiva de datos
- ❌ Rompe otras integraciones existentes
- ❌ Alto riesgo y esfuerzo

**Razón del rechazo:** Demasiado riesgo y esfuerzo para una solución que puede resolverse con validación en aplicación.

### Alternativa 3: Usar vistas en `myllm_projects_db` que repliquen datos de `myllm_core_db`

**Ventajas:**
- ✅ Datos accesibles sin joins cross-database

**Desventajas:**
- ❌ Vistas no soportan FKs
- ❌ Datos desincronizados si no hay triggers
- ❌ Complejidad adicional

**Razón del rechazo:** No resuelve el problema de las FKs y añade complejidad innecesaria.

## Consecuencias

### Positivas

✅ **Cohesión del dominio:** Todas las tablas relacionadas con proyectos (proyectos, versiones, tickets, conversaciones) están juntas en `myllm_projects_db`

✅ **Mantenibilidad:** Los desarrolladores saben que todo lo relacionado con proyectos está en una sola base de datos

✅ **Escalabilidad:** Las conversaciones pueden crecer independientemente sin afectar a `myllm_core_db`

✅ **FKs internas garantizadas:** Las relaciones entre conversaciones, mensajes, tickets y participantes están protegidas por FKs

### Negativas

❌ **Integridad referencial parcial:** No hay garantía a nivel de BD de que `id_usuario_cliente` o `id_organizacion` sean válidos

❌ **Validación obligatoria en aplicación:** Los adapters DEBEN validar la existencia de users/organizations antes de crear registros

❌ **Posibilidad de huérfanos:** Si se borra un usuario en `myllm_core_db`, no hay CASCADE automático en `myllm_projects_db`

### Mitigaciones

Para minimizar los riesgos, implementamos:

1. **Validación estricta en adapters:**
   ```python
   # En conversaciones_adapter.py
   def crear_conversacion(...):
       # SIEMPRE validar que user_id y org_id existen en myllm_core_db
       validar_usuario_existe(engine_core, id_usuario_cliente)
       validar_organizacion_existe(engine_core, id_organizacion)
       # Luego crear en myllm_projects_db
   ```

2. **Índices para performance:**
   ```sql
   CREATE INDEX idx_usuario_cliente ON conversaciones(id_usuario_cliente);
   CREATE INDEX idx_organizacion ON conversaciones(id_organizacion);
   CREATE INDEX idx_usuario_emisor ON mensajes_conversacion(id_usuario_emisor);
   ```

3. **Triggers para mantener contadores:**
   - `after_mensaje_insert`: Actualiza contadores en conversaciones
   - `after_mensaje_leido_cliente`: Actualiza mensajes sin leer
   - `after_mensaje_leido_interno`: Actualiza mensajes sin leer

4. **Vista consolidada:**
   ```sql
   CREATE VIEW v_conversaciones_activas AS ...
   ```

5. **Jobs de limpieza periódicos:**
   ```python
   # Ejecutar diariamente
   def limpiar_registros_huerfanos():
       """Marca conversaciones de usuarios/orgs inexistentes."""
       # Identificar conversaciones con id_usuario_cliente que no existe
       # Marcar como "cerrada" automáticamente
   ```

6. **Documentación clara:**
   - README.md explica la decisión
   - AGENTS.md incluye reglas de validación obligatoria
   - ADR documenta el razonamiento completo

## Implementación

### Archivos creados:
- `infrastructure/database/migrations/007_conversaciones_sistema_final.sql`
- `src/2_shared_application/adapters/conversaciones_adapter.py`
- `src/1_shared_domain/conversacion.py`
- `docs/SISTEMA_CONVERSACIONES.md`

### Tests implementados:
- `tests/integration/test_conversaciones_adapter.py`
- `tests/unit/test_conversacion_entities.py`

### Reglas AGENTS.md:
- Regla: "Siempre validar users/organizations antes de crear conversaciones"
- Regla: "Usar dos engines: engine_core y engine_projects"

## Referencias

- [MySQL Cross-database Foreign Keys](https://dev.mysql.com/doc/refman/8.0/en/create-table-foreign-keys.html)
- [MariaDB Foreign Key Constraints](https://mariadb.com/kb/en/foreign-keys/)
- Discusión técnica: Thread 2026-02-05 sobre cross-database references
- Arquitectura del proyecto: `README.md` sección "Estructura de Base de Datos"

## Validación

Este ADR será revisado en 3 meses (mayo 2026) para evaluar:
- ¿Ha habido problemas de integridad referencial?
- ¿Los jobs de limpieza son suficientes?
- ¿Deberíamos considerar consolidar las bases de datos?

---

**Última actualización:** 2026-02-05
**Responsable:** Equipo de Arquitectura
**Próxima revisión:** 2026-05-05
