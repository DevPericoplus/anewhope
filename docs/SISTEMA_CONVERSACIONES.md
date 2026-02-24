# Sistema de Conversaciones

## Descripción General

Sistema completo de mensajería entre usuarios cliente (frontend) y usuarios internos (backoffice) con soporte para:

- Conversaciones multi-participante
- Referencias a tickets de soporte
- Tracking de mensajes leídos/no leídos
- Asignación de usuarios internos a organizaciones
- Reportes y estadísticas

## Arquitectura

### Tablas Principales

```
asignaciones_organizaciones_internas
├── Gestiona qué usuarios internos atienden qué organizaciones
└── Incluye roles y tracking de asignaciones

conversaciones
├── Registro de cada conversación
├── Tracking de estado y prioridad
└── Contadores de mensajes sin leer

participantes_conversacion
├── Quién participa en cada conversación
└── Múltiples internos pueden participar

mensajes_conversacion
├── Todos los mensajes de todas las conversaciones
└── Referencias a tickets opcionales

conversaciones_tickets_relacionados
└── Relaciones N:M entre conversaciones y tickets
```

### Vistas de Datos

- `v_conversaciones_activas`: Vista consolidada de conversaciones activas
- `v_estadisticas_usuarios_internos`: Métricas de usuarios internos

## Flujos de Trabajo

### Frontend (Cliente)

```
1. Usuario inicia conversación
   └─> Se crea registro en `conversaciones`
   └─> Se añade como participante
   └─> Envía primer mensaje

2. Usuario ve sus conversaciones
   └─> Filtradas por su user_id y org_id
   └─> Solo ve icono "Cliente"

3. Usuario recibe respuestas
   └─> Contador de mensajes sin leer
   └─> Notificación visual
```

### Backoffice (Interno)

```
1. Usuario ve organizaciones asignadas
   └─> Desde `asignaciones_organizaciones_internas`

2. Selecciona organización
   └─> Ve lista de conversaciones activas
   └─> Con indicadores de mensajes sin leer

3. Se une a conversación
   └─> Se registra en `participantes_conversacion`
   └─> Estado cambia a "en_curso"

4. Envía mensajes
   └─> Puede referenciar tickets
   └─> Múltiples internos pueden responder
```

## Instalación

### 1. Ejecutar DDL

```bash
# Instalación básica
python scripts/install_conversaciones_db.py

# Con datos de ejemplo
python scripts/install_conversaciones_db.py --with-examples

# Con conexión personalizada
python scripts/install_conversaciones_db.py --connection "mysql+pymysql://user:pass@host/db"
```

### 2. Verificar Instalación

```sql
-- Verificar tablas creadas
SHOW TABLES LIKE '%conversaciones%';
SHOW TABLES LIKE '%participantes%';
SHOW TABLES LIKE '%mensajes_conversacion%';
SHOW TABLES LIKE '%asignaciones_organizaciones%';

-- Verificar vistas
SHOW FULL TABLES WHERE Table_type = 'VIEW';

-- Verificar triggers
SHOW TRIGGERS LIKE 'mensajes_conversacion';
```

## Uso del Adapter

### Asignar Usuario Interno a Organización

```python
from adapters.conversaciones_adapter import crear_asignacion_interna

id_asignacion = crear_asignacion_interna(
    engine=engine,
    id_usuario_interno=123,  # Usuario interno
    id_organizacion=45,      # Organización cliente
    id_rol=2,                # Rol desde proyectos_roles_base
    asignado_por=1,          # Super admin
    notas="Asignado como soporte técnico principal"
)
```

### Crear Conversación (Cliente)

```python
from adapters.conversaciones_adapter import crear_conversacion, enviar_mensaje

# Crear conversación
id_conv = crear_conversacion(
    engine=engine,
    id_organizacion=session.org_id,
    id_usuario_cliente=session.user_id,
    asunto="Consulta sobre proyecto X",
    id_ticket_principal=789,  # Opcional
    prioridad="alta"
)

# Enviar primer mensaje
enviar_mensaje(
    engine=engine,
    id_conversacion=id_conv,
    id_usuario_emisor=session.user_id,
    tipo_emisor="cliente",
    texto_mensaje="Necesito ayuda urgente con..."
)
```

### Obtener Conversaciones (Backoffice)

```python
from adapters.conversaciones_adapter import (
    obtener_organizaciones_asignadas,
    obtener_conversaciones_organizacion
)

# Ver organizaciones asignadas
orgs = obtener_organizaciones_asignadas(
    engine=engine,
    id_usuario_interno=session.user_id
)

# Ver conversaciones de una organización
conversaciones = obtener_conversaciones_organizacion(
    engine=engine,
    id_organizacion=org_seleccionada,
    solo_activas=True
)
```

### Unirse y Responder (Backoffice)

```python
from adapters.conversaciones_adapter import (
    unirse_a_conversacion,
    obtener_mensajes_conversacion,
    enviar_mensaje,
    marcar_mensajes_como_leidos
)

# Unirse a la conversación
unirse_a_conversacion(
    engine=engine,
    id_conversacion=conv_id,
    id_usuario_interno=session.user_id
)

# Cargar mensajes
mensajes = obtener_mensajes_conversacion(
    engine=engine,
    id_conversacion=conv_id
)

# Marcar como leídos
marcar_mensajes_como_leidos(
    engine=engine,
    id_conversacion=conv_id,
    tipo_lector="interno"
)

# Enviar respuesta
enviar_mensaje(
    engine=engine,
    id_conversacion=conv_id,
    id_usuario_emisor=session.user_id,
    tipo_emisor="interno",
    texto_mensaje="Hola, voy a ayudarte con...",
    id_ticket_referenciado=789  # Opcional
)
```

## Integración con Tickets

### Referenciar Ticket en Mensaje

```python
from adapters.conversaciones_adapter import (
    obtener_tickets_disponibles_organizacion,
    enviar_mensaje
)

# Obtener tickets disponibles
tickets = obtener_tickets_disponibles_organizacion(
    engine=engine,
    id_organizacion=org_id
)

# Enviar mensaje con referencia
enviar_mensaje(
    engine=engine,
    id_conversacion=conv_id,
    id_usuario_emisor=session.user_id,
    tipo_emisor="interno",
    texto_mensaje="Relacionado con tu ticket, te informo que...",
    id_ticket_referenciado=ticket_id
)
```

### Ver Tickets Relacionados

```python
from adapters.conversaciones_adapter import obtener_tickets_conversacion

tickets_relacionados = obtener_tickets_conversacion(
    engine=engine,
    id_conversacion=conv_id
)

# Resultado incluye:
# - Ticket principal (si existe)
# - Tickets mencionados en mensajes
# - Tipo de relación
# - Quién lo vinculó
```

## Reportes y Estadísticas

### Estadísticas por Organización

```python
from adapters.conversaciones_adapter import (
    obtener_estadisticas_conversaciones_organizacion
)

stats = obtener_estadisticas_conversaciones_organizacion(
    engine=engine,
    id_organizacion=org_id
)

# Resultado:
# {
#   'total_conversaciones': 45,
#   'abiertas': 12,
#   'en_curso': 18,
#   'resueltas': 10,
#   'cerradas': 5,
#   'total_mensajes_sin_leer': 23,
#   'promedio_mensajes_por_conversacion': 8.5
# }
```

### Queries Personalizados

```sql
-- Conversaciones más activas
SELECT
    c.id_conversacion,
    c.asunto,
    COUNT(m.id_mensaje) as total_mensajes,
    COUNT(DISTINCT pc.id_usuario) as participantes
FROM conversaciones c
LEFT JOIN mensajes_conversacion m ON c.id_conversacion = m.id_conversacion
LEFT JOIN participantes_conversacion pc ON c.id_conversacion = pc.id_conversacion
WHERE c.id_organizacion = :org_id
GROUP BY c.id_conversacion
ORDER BY total_mensajes DESC
LIMIT 10;

-- Tiempo promedio de primera respuesta
SELECT
    AVG(TIMESTAMPDIFF(SECOND, primer_msg.fecha_envio, primera_resp.fecha_envio)) / 60 as minutos
FROM (
    SELECT id_conversacion, MIN(fecha_envio) as fecha_envio
    FROM mensajes_conversacion
    WHERE tipo_emisor = 'cliente'
    GROUP BY id_conversacion
) primer_msg
JOIN (
    SELECT id_conversacion, MIN(fecha_envio) as fecha_envio
    FROM mensajes_conversacion
    WHERE tipo_emisor = 'interno'
    GROUP BY id_conversacion
) primera_resp ON primer_msg.id_conversacion = primera_resp.id_conversacion;

-- Usuarios internos más activos
SELECT
    u.nombre,
    COUNT(DISTINCT m.id_conversacion) as conversaciones_atendidas,
    COUNT(m.id_mensaje) as mensajes_enviados,
    DATE(MAX(m.fecha_envio)) as ultima_actividad
FROM users u
JOIN mensajes_conversacion m ON u.id = m.id_usuario_emisor
WHERE m.tipo_emisor = 'interno'
GROUP BY u.id
ORDER BY mensajes_enviados DESC;
```

## Mantenimiento

### Cerrar Conversaciones

```python
from adapters.conversaciones_adapter import cerrar_conversacion

cerrar_conversacion(
    engine=engine,
    id_conversacion=conv_id,
    cerrada_por=session.user_id,
    estado_final="resuelta"  # o "cerrada"
)
```

### Desactivar Asignación

```python
from adapters.conversaciones_adapter import desactivar_asignacion_interna

desactivar_asignacion_interna(
    engine=engine,
    id_asignacion=asig_id,
    desactivado_por=session.user_id
)
```

### Archivado Automático

```sql
-- Crear evento para archivar conversaciones antiguas
CREATE EVENT IF NOT EXISTS archivar_conversaciones_antiguas
ON SCHEDULE EVERY 1 DAY
DO
    UPDATE conversaciones
    SET estado = 'cerrada'
    WHERE estado IN ('abierta', 'en_curso')
      AND fecha_ultima_actualizacion < DATE_SUB(NOW(), INTERVAL 30 DAY);
```

## Próximas Mejoras

- [ ] Notificaciones push en tiempo real
- [ ] Adjuntar archivos a mensajes
- [ ] Búsqueda full-text en mensajes
- [ ] Etiquetas/tags para conversaciones
- [ ] Plantillas de mensajes predefinidos
- [ ] Métricas de satisfacción del cliente
- [ ] Integración con sistema de notificaciones por email
- [ ] API REST para integraciones externas

## Troubleshooting

### Error: No se crean conversaciones

```sql
-- Verificar permisos FK
SHOW CREATE TABLE conversaciones;

-- Verificar usuarios y organizaciones existen
SELECT * FROM users WHERE id = :user_id;
SELECT * FROM organizaciones WHERE id = :org_id;
```

### Error: No se actualizan contadores

```sql
-- Verificar triggers están activos
SHOW TRIGGERS LIKE 'mensajes_conversacion';

-- Recalcular contadores manualmente
UPDATE conversaciones c
SET
    total_mensajes = (
        SELECT COUNT(*) FROM mensajes_conversacion
        WHERE id_conversacion = c.id_conversacion
    ),
    mensajes_sin_leer_interno = (
        SELECT COUNT(*) FROM mensajes_conversacion
        WHERE id_conversacion = c.id_conversacion
        AND tipo_emisor = 'cliente'
        AND leido_por_interno = FALSE
    );
```

### Performance con muchas conversaciones

```sql
-- Verificar índices
SHOW INDEX FROM conversaciones;
SHOW INDEX FROM mensajes_conversacion;

-- Analizar queries lentos
EXPLAIN SELECT ... FROM conversaciones ...;

-- Considerar particionado por fecha
ALTER TABLE mensajes_conversacion
PARTITION BY RANGE (YEAR(fecha_envio)) (
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p2025 VALUES LESS THAN (2026),
    ...
);
```

## Soporte

Para dudas o problemas:
1. Consultar este documento
2. Revisar logs de la aplicación
3. Verificar integridad de datos en BD
4. Contactar al equipo de desarrollo
