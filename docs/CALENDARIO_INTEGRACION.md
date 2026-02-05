# Integración del Calendario con la Tabla Cambios

## Resumen

El componente de calendario en el backoffice ahora está integrado con la tabla `cambios` de la base de datos, permitiendo visualizar eventos basados en los cambios registrados en el sistema. Los eventos se muestran con colores según el tipo de cambio, con soporte para filtrado por organización y proyecto.

## Arquitectura (DDD)

### 1. Capa de Dominio (`/src/1_shared_domain/entities`)

**Archivo**: `calendario_event.py`

#### Entidades

- **`CambioEvento`**: Representa un evento individual del calendario
  - `id`: Identificador único
  - `fecha_cambio`: Fecha del evento
  - `tipo_cambio`: Tipo de cambio (ej: "VERSION_CREADA", "Asignación usuario")
  - `descripcion`: Descripción del cambio
  - `id_organizacion`: ID de la organización
  - `id_proyecto`: ID del proyecto (opcional)
  - `id_version`: ID de la versión (opcional)
  - `tipo_usuario`: Tipo de usuario ("cliente" o "interno", opcional)

- **`EventosDia`**: Agrupa eventos de un mismo día
  - `fecha`: Fecha del día
  - `eventos`: Lista de `CambioEvento`

#### Funciones de Dominio

- `get_color()`: Retorna el color asociado al tipo de cambio
- `get_tooltip_text()`: Genera el texto del tooltip
- `tiene_eventos_mixtos()`: Detecta si hay eventos de cliente e interno en el mismo día
- `agrupar_eventos_por_dia()`: Agrupa eventos por fecha

#### Mapeo de Colores

```python
COLOR_MAPPING = {
    "VERSION_CREADA": "#4CAF50",  # Verde
    "Asignación usuario": "#2196F3",  # Azul
    "Respuesta soporte proyecto": "#9C27B0",  # Púrpura
    "Quitar usuario": "#F44336",  # Rojo
    "Solicitud soporte proyecto": "#FF9800",  # Naranja
    "Actualización soporte proyecto": "#00BCD4",  # Cyan
}
COLOR_MIXTO = "#FFD700"  # Dorado (para días con eventos mixtos)
```

### 2. Capa de Aplicación (`/src/2_shared_application/adapters`)

**Archivo**: `cambios_adapter.py`

#### Funciones del Adaptador

- **`obtener_cambios_por_organizacion()`**
  - Obtiene cambios filtrados por organización, mes, año y proyecto
  - Retorna lista de `CambioEvento`

- **`obtener_tipos_cambio_unicos()`**
  - Obtiene todos los tipos de cambio registrados
  - Útil para generar mapeos dinámicos

- **`obtener_cambios_agrupados_por_dia()`**
  - Retorna eventos agrupados por día
  - Detecta días con eventos mixtos
  - Formato listo para el calendario

- **`obtener_proyectos_organizacion()`**
  - Obtiene proyectos de una organización
  - Usado en selector de proyectos

- **`obtener_organizaciones_internas_usuario()`**
  - Obtiene organizaciones disponibles
  - Usado en selector de organizaciones

### 3. Capa de Presentación

**Archivo**: `/src/apps/6_web_backoffice/components/seguimiento.py`

#### Estado del Calendario

```python
# Variables de selección
organizaciones_calendario: list[dict] = []
selected_org_calendario: int = 0
selected_org_nombre: str = ""
proyectos_calendario: list[dict] = []
selected_proyecto_calendario: int = 0
selected_proyecto_nombre: str = "Todos"

# Eventos cargados
events_data: list[dict] = []

# Fecha seleccionada
selected_year: str
selected_month: str
```

#### Métodos Principales

- **`load_organizaciones_calendario()`**
  - Carga organizaciones asignadas al usuario
  - Se ejecuta en `on_mount`

- **`load_proyectos_calendario()`**
  - Carga proyectos de la organización seleccionada

- **`load_events_data()`**
  - Carga eventos del calendario desde cambios
  - Se ejecuta al cambiar org/proyecto/mes/año

- **`month_days_with_events`** (computed)
  - Genera matriz de días con eventos integrados
  - Aplica colores y tooltips

#### Componente Visual

**`calendario_component()`** incluye:
- Selector de organización (backoffice)
- Selector de proyecto (opcional, "Todos" por defecto)
- Selectores de año y mes
- Grilla de calendario con eventos coloreados
- Tooltips con información del evento

## Características

### 1. Colores Automáticos por Tipo de Cambio

Cada tipo de cambio tiene un color asociado automáticamente. Si un día tiene múltiples eventos del mismo tipo, usa ese color. Si hay eventos de diferentes tipos, usa el color del primer evento.

### 2. Detección de Eventos Mixtos

Días con eventos tanto de clientes como de internos se marcan con color dorado especial (`#FFD700`) y un box-shadow brillante.

**Nota**: Actualmente deshabilitado porque la tabla `cambios` no tiene columna `id_usuario_ejecutor`. Se puede habilitar agregando esta columna.

### 3. Filtros Dinámicos

- **Organización**: Selector con organizaciones asignadas al usuario
- **Proyecto**: Selector con "Todos" + proyectos de la organización
- **Mes/Año**: Selectores para navegar por fechas

### 4. Tooltips Informativos

Cada día con eventos muestra un tooltip con:
- Tipo de cambio
- Descripción del cambio
- Si hay múltiples eventos, lista todos

## Flujo de Datos

```
┌─────────────────────┐
│  Tabla cambios      │
│  (myllm_projects_db)│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  cambios_adapter.py │
│  obtener_cambios... │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  CambioEvento       │
│  (domain entity)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  SeguimientoState   │
│  events_data        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  calendario_        │
│  component()        │
└─────────────────────┘
```

## Instalación y Configuración

### Requisitos

- Python 3.13+
- SQLAlchemy
- PyMySQL
- Reflex

### Base de Datos

La tabla `cambios` debe tener esta estructura mínima:

```sql
CREATE TABLE cambios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_version INT,
    fecha_cambio DATE NOT NULL,
    tipo_cambio VARCHAR(255),
    descripcion TEXT,
    id_organizacion INT,
    id_proyecto INT,
    creado_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizado_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### Configuración del Engine

El adaptador usa el engine configurado en `SeguimientoState._get_db_engine()`:

```python
DB_USER = "myllm_admin"
DB_PASS = "Us3r%40dminP%40ss"
DB_HOST = "localhost"
engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/myllm_projects_db")
```

## Uso

### En el Backoffice

1. Accede a la página de "Seguimiento"
2. El calendario se carga automáticamente con:
   - Primera organización asignada al usuario
   - Todos los proyectos
   - Mes y año actual

3. Usa los selectores para:
   - Cambiar de organización
   - Filtrar por proyecto específico
   - Navegar por meses/años

4. Haz hover sobre días con eventos para ver detalles

### Desde Código

```python
# Cargar eventos del mes actual
from cambios_adapter import obtener_cambios_agrupados_por_dia

eventos = obtener_cambios_agrupados_por_dia(
    engine=engine,
    id_organizacion=1,
    mes=2,
    anio=2026,
    id_proyecto=None  # Todos los proyectos
)

# Resultado:
# [
#   {
#     "date": "2026-02-03",
#     "color": "#4CAF50",
#     "tooltip": "• VERSION_CREADA: Versión v002...",
#     "count": 12,
#     "has_mixed": False
#   },
#   ...
# ]
```

## Testing

### Test de Integración

Ejecutar:

```bash
.venv_backoffice313/bin/python3 test_calendario_integration.py
```

El test verifica:
1. Tipos de cambio existentes
2. Organizaciones asignadas al usuario
3. Proyectos de la organización
4. Carga de cambios del mes actual
5. Agrupación de eventos por día

### Test Manual

1. Inicia el backoffice:
   ```bash
   cd src/apps/6_web_backoffice
   ../../../.venv_backoffice313/bin/reflex run --backend-port 8006 --frontend-port 3200
   ```

2. Accede a `http://localhost:3200`

3. Navega a "Seguimiento"

4. Verifica:
   - Selectores de organización y proyecto visibles
   - Calendario muestra eventos con colores
   - Tooltips funcionan correctamente
   - Cambios de filtro actualizan el calendario

## Limitaciones Actuales

1. **No hay detección de eventos mixtos**: La tabla `cambios` no tiene `id_usuario_ejecutor`. Para habilitar esta funcionalidad, agregar la columna y actualizar el adaptador.

2. **Nombres de organización genéricos**: Como no existe tabla `organizaciones`, se usan nombres "Organización {ID}". Se puede mejorar creando la tabla.

3. **Sin paginación**: Si hay muchos eventos en un mes, todos se cargan. Para grandes volúmenes, considerar paginación.

4. **Colores estáticos**: Los colores están hardcoded en el dominio. Se podría implementar configuración dinámica.

## Mejoras Futuras

### Corto Plazo

- [ ] Agregar indicador de cantidad de eventos en cada día
- [ ] Click en día para ver detalle de eventos
- [ ] Exportar eventos a CSV/PDF
- [ ] Filtro por tipo de cambio

### Mediano Plazo

- [ ] Agregar columna `id_usuario_ejecutor` en `cambios`
- [ ] Implementar detección de eventos mixtos
- [ ] Crear tabla `organizaciones` con nombres reales
- [ ] Agregar búsqueda de eventos

### Largo Plazo

- [ ] Vista de timeline para eventos
- [ ] Notificaciones de eventos importantes
- [ ] Integración con sistema de permisos
- [ ] API REST para eventos del calendario

## Soporte

Para problemas o preguntas, revisar:
- Logs del backoffice en `/tmp/backoffice_startup.log`
- Errores de SQL en el terminal donde corre Reflex
- Test de integración para diagnóstico

## Referencias

- [Reflex Documentation](https://reflex.dev/docs)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [DDD Pattern](https://martinfowler.com/bliki/DomainDrivenDesign.html)
