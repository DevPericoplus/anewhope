# Testing E2E - Sistema de Entrenamientos y Descargas

**Fecha:** 2026-02-13
**Objetivo:** Verificar el flujo completo desde entrenamiento RAG hasta descarga de modelos GGUF

---

## Pre-requisitos

### 1. Servicios en Ejecución

```bash
# Verificar que todos los servicios estén corriendo
ps aux | grep -E "apicore|apitrainer|apife|apibe" | grep -v grep

# Puertos esperados:
# 8003 - Backend Core
# 8004 - Trainer
# 8005 - Frontend
# 8006 - Backoffice
# 8007 - Middleware
# 8008 - Broker
# 8100 - ChromaDB
```

### 2. Base de Datos

```bash
# Conectar a MariaDB
/usr/local/opt/mariadb@10.6/bin/mariadb -u myllm_admin -p'Us3r@dminP@ss' myllm_projects_db

# Verificar tablas necesarias
SHOW TABLES LIKE '%entrenamiento%';
# Debe mostrar:
# - entrenamientos
# - evoluciones_entrenamientos
# - entrenamientos_autonomos
# - evoluciones_autonomas
```

### 3. Configuración de Entorno

```bash
# Verificar .envglobal
cat .envglobal | grep training_mode
# Debe mostrar: training_mode: simulation (o test/production)

# Verificar env.yaml del entorno actual
cat infrastructure/environments/macbook/env.yaml | grep backend_ia
# Debe mostrar:
# - backend_ia_base_storage: ruta de entrada
# - backend_ia_internal_storage: ruta de salida
```

### 4. Usuario de Prueba

```sql
-- Verificar que existe un usuario para testing
SELECT id, name, email, mobile, identity_type_id
FROM users
WHERE email = 'admin@test.com';

-- Si no existe, crear uno:
-- identity_type_id = 1 (SuperAdmin) o 2 (OrgAdmin) para testing completo
```

---

## PARTE 1: Entrenamiento RAG (Fases 2-5)

### Paso 1.1: Preparar Documentos

```bash
# Verificar que existe el directorio de documentos fuente
# Ejemplo: ~/data/anewhope/files/trainer_server/external/ORG00001/PRJ00001/v002/

# Verificar que hay archivos en el directorio
ls -la ~/data/anewhope/files/trainer_server/external/ORG00001/PRJ00001/v002/

# Debe contener al menos 2-3 archivos (PDF, TXT, MD, etc.)
```

### Paso 1.2: Iniciar Entrenamiento RAG desde Backoffice

1. **Abrir Backoffice:** http://localhost:8006
2. **Login** con usuario de prueba
3. **Navegar a:** Menú Internal → Entrenamientos
4. **Seleccionar versión** en el visor de versiones
5. **Click en** "Enviar al Trainer"
6. **Configurar parámetros** en el modal (usar valores por defecto)
7. **Click en** "Enviar al Trainer"

**Verificación Inmediata:**
```sql
-- Debe aparecer un nuevo registro en entrenamientos
SELECT id, numero_secuencia, estado, fase_actual, created_at
FROM entrenamientos
ORDER BY id DESC LIMIT 1;

-- Debe aparecer 16 subfases en evoluciones_entrenamientos
SELECT COUNT(*) as total_subfases
FROM evoluciones_entrenamientos
WHERE id_entrenamiento = <ID_DEL_ENTRENAMIENTO>;
-- Resultado esperado: 16
```

### Paso 1.3: Monitorear Progreso RAG

**En la UI del Backoffice:**
- Panel de evolución debe aparecer automáticamente
- Verificar que las subfases se actualizan cada 1-2 segundos
- Ver el spinner girando en la subfase actual
- Observar el cambio de color: gris → azul → verde

**En la Base de Datos (en paralelo):**
```sql
-- Consulta de monitoreo (ejecutar cada 5-10 segundos)
SELECT
    subfase_key,
    subfase_name,
    status,
    duracion_segundos,
    updated_at
FROM evoluciones_entrenamientos
WHERE id_entrenamiento = <ID>
ORDER BY phase_key, subfase_key;

-- Ver progreso general
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completadas,
    SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as en_progreso,
    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pendientes
FROM evoluciones_entrenamientos
WHERE id_entrenamiento = <ID>;
```

**Logs del Trainer:**
```bash
# Seguir logs en tiempo real
tail -f src/apps/4_trainer/logs/trainer_api.log | grep -E "PHASE|SUBFASE|completed"
```

### Paso 1.4: Verificar Completitud RAG

**Tiempo Estimado:** 1-3 minutos (modo simulation en MacBook)

**Verificación Final:**
```sql
-- Todas las subfases deben estar completadas
SELECT
    subfase_key,
    status,
    duracion_segundos
FROM evoluciones_entrenamientos
WHERE id_entrenamiento = <ID>
  AND status != 'completed';
-- Resultado esperado: 0 filas (todas completadas)

-- Verificar estado del entrenamiento
SELECT id, estado, fase_actual, collection_name
FROM entrenamientos
WHERE id = <ID>;
-- estado esperado: 'completed'
-- fase_actual: '5.5'
-- collection_name: 'ENT<ID>'
```

**Verificación en ChromaDB:**
```bash
# Verificar que la colección existe
curl -s http://localhost:8100/api/v1/collections | jq '.[] | select(.name | contains("ENT"))'

# Verificar cantidad de documentos en la colección
curl -s http://localhost:8100/api/v1/collections/ENT<ID> | jq '.count'
```

**En la UI:**
- Panel de evolución debe mostrar todas las subfases en verde
- Debe aparecer un **callout verde** con el mensaje:
  - "Entrenamiento RAG completado exitosamente"
  - Botón: **"Entrenar Modelo Autónomo"** (naranja, icono de cohete)

---

## PARTE 2: Entrenamiento Autónomo (Fases 6-9)

### Paso 2.1: Iniciar Entrenamiento Autónomo

1. **En el panel de evolución**, hacer click en **"Entrenar Modelo Autónomo"**
2. **Verificar modal de confirmación:**
   - Título: "Iniciar Entrenamiento Autónomo"
   - Lista de fases: 6, 7-8, 9
   - Badge con training_mode actual: SIMULATION / TEST / PRODUCTION
   - Callout informativo según modo
3. **Click en** "Iniciar Entrenamiento"

**Verificación Inmediata:**
```sql
-- Debe aparecer registro en entrenamientos_autonomos
SELECT
    id_entrenamiento,
    training_mode,
    created_at
FROM entrenamientos_autonomos
WHERE id_entrenamiento = <ID>;

-- Debe aparecer subfases autónomas (cantidad depende del modo)
SELECT COUNT(*) as total_subfases_autonomas
FROM evoluciones_autonomas
WHERE id_entrenamiento = <ID>;
-- Resultado esperado:
-- - simulation: 5 subfases (solo fase 6)
-- - test/production: 20 subfases (fases 6-9)
```

### Paso 2.2: Monitorear Progreso Autónomo

**En la UI:**
- Panel se actualiza con las nuevas subfases (6.1-9.5)
- Polling cada 2 segundos
- Subfases se van completando secuencialmente

**En la Base de Datos:**
```sql
-- Consulta de monitoreo autónomo
SELECT
    subfase_key,
    subfase_name,
    status,
    duracion_segundos,
    updated_at
FROM evoluciones_autonomas
WHERE id_entrenamiento = <ID>
ORDER BY phase_key, subfase_key;

-- Progreso general
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completadas,
    ROUND(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as porcentaje
FROM evoluciones_autonomas
WHERE id_entrenamiento = <ID>;
```

**Logs del Trainer:**
```bash
tail -f src/apps/4_trainer/logs/trainer_api.log | grep -E "AUTONOMOUS|Phase 6|Phase 7|Phase 8|Phase 9"
```

### Paso 2.3: Verificar Tiempos por Modo

**Modo Simulation:**
- Fase 6: 2-5 min
- Fases 7-8-9: Omitidas
- Total: 2-5 min

**Modo Test:**
- Fase 6: 5-10 min
- Fases 7-8: 10-20 min
- Fase 9: 5-10 min
- Total: 20-40 min

**Modo Production:**
- Fase 6: 15-30 min
- Fases 7-8: 30-90 min
- Fase 9: 8-15 min
- Total: 53-135 min

### Paso 2.4: Verificar Completitud Autónomo

**Verificación en BD:**
```sql
-- Todas las subfases autónomas completadas
SELECT
    subfase_key,
    status,
    duracion_segundos
FROM evoluciones_autonomas
WHERE id_entrenamiento = <ID>
  AND status != 'completed';
-- Resultado esperado: 0 filas

-- Verificar información del paquete generado
SELECT
    training_mode,
    dataset_path,
    dataset_size,
    lora_adapters_path,
    gguf_path,
    package_path,
    package_size_mb,
    package_generated_at
FROM entrenamientos_autonomos
WHERE id_entrenamiento = <ID>;
-- package_path debe tener valor (solo en test/production)
-- package_size_mb debe ser > 0
```

**Verificación de Archivos Generados:**
```bash
# Obtener package_path de la consulta anterior
# Ejemplo: ~/data/anewhope/files/trainer_server/internal/models/ORG00001/PRJ00001/v002/exports/ENT123/ENT123_modelo_autonomo.zip

# Verificar que existe
ls -lh <PACKAGE_PATH>

# Verificar tamaño (debe ser 4-8 GB en test/production, 0 en simulation)
du -h <PACKAGE_PATH>

# Verificar contenido del ZIP
unzip -l <PACKAGE_PATH>
# Debe contener:
# - ENT<ID>_model_q4_k_m.gguf (o similar)
# - Modelfile
# - README.md
```

**En la UI:**
- Panel debe mostrar todas las subfases en verde
- Debe aparecer **callout verde** con:
  - "Modelo autónomo generado exitosamente"
  - Botón: **"Descargar Modelo GGUF"** (verde, icono de descarga)
  - Badge: "ZIP Package"

### Paso 2.5: Probar Descarga Directa desde Panel

1. **Click en** "Descargar Modelo GGUF"
2. **Verificar que se inicia la descarga** en el navegador
3. **Verificar archivo descargado:**
   - Nombre: `ENT<ID>_modelo_autonomo.zip`
   - Tamaño coincide con el de la BD
   - Se puede descomprimir sin errores

```bash
# Verificar archivo descargado
cd ~/Downloads
ls -lh ENT*_modelo_autonomo.zip

# Descomprimir y verificar contenido
unzip -l ENT*_modelo_autonomo.zip
```

---

## PARTE 3: Página de Descargas

### Paso 3.1: Acceder a Página de Descargas

1. **Navegar a:** Menú → Descargas
2. **Verificar que aparece la página**

**Si identity_type_id = 1 o 2:**
- Debe mostrar sección de "Validación de Identidad"
- Botón "Enviar Código OTP"
- Input para código OTP

**Si identity_type_id != 1 y != 2:**
- Debe mostrar directamente los filtros

### Paso 3.2: Validación OTP (solo SuperAdmin/OrgAdmin)

1. **Click en** "Enviar Código OTP"
2. **Verificar toast:** "Código OTP enviado por SMS"
3. **Simular código OTP:**
   ```bash
   # En desarrollo, verificar logs para obtener el código
   # O insertar uno manualmente en BD para testing
   ```
4. **Ingresar código** en el input (6 dígitos)
5. **Click en** "Validar Código"
6. **Verificar toast:** "Código OTP validado correctamente"

**Verificación:**
- Sección de OTP debe desaparecer
- Deben aparecer los filtros (Organización, Proyecto, Versión)

### Paso 3.3: Seleccionar Filtros

**Opción A: Backoffice (con selector de organizaciones)**
1. **Selector de Organización:**
   - Debe mostrar organizaciones según asignaciones del usuario
   - Seleccionar una organización

2. **Selector de Proyecto:**
   - Debe cargarse automáticamente
   - Debe mostrar proyectos de la org seleccionada
   - Seleccionar un proyecto

3. **Selector de Versión:**
   - Debe cargarse automáticamente
   - Debe mostrar versiones del proyecto
   - Seleccionar una versión

**Opción B: Frontend (organización automática)**
- Organización se selecciona automáticamente (la del usuario)
- Selectores de proyecto y versión funcionan igual

**Verificación en BD:**
```sql
-- Verificar que los selectores muestran datos correctos
-- Organizaciones (según asignaciones)
SELECT DISTINCT o.id, o.name
FROM organizations o
INNER JOIN user_organization_roles uor ON o.id = uor.id_organizacion
WHERE uor.id_user = <USER_ID>;

-- Proyectos de una organización
SELECT id, name
FROM projects
WHERE id_organizacion = <ORG_ID>;

-- Versiones de un proyecto
SELECT id, nombre, estado
FROM versiones
WHERE id_proyecto = <PROJECT_ID>;
```

### Paso 3.4: Ver Lista de Paquetes

Después de seleccionar versión, debe aparecer:

**Spinner de Carga:**
- "Cargando paquetes disponibles..."

**Lista de Paquetes (si hay):**
- Card por cada paquete con:
  - Icono de archivo
  - Nombre: `ENT<ID>_modelo_autonomo.zip`
  - Badges:
    - "Entrenamiento #<ID>" (azul)
    - Training mode: SIMULATION/TEST/PRODUCTION (coloreado)
    - Cuantización: q4_k_m (púrpura)
  - Grid con información:
    - Tamaño: X.X MB
    - Dataset: X ejemplos
    - Generado: YYYY-MM-DD
  - Botón: "Descargar Paquete" (verde)

**Si no hay paquetes:**
- Icono de inbox vacío
- "No se encontraron paquetes disponibles"
- "Seleccione otra versión o complete un entrenamiento autónomo primero."

**Verificación en BD:**
```sql
-- Listar paquetes disponibles (query del endpoint)
SELECT
    e.id AS id_entrenamiento,
    e.id_organizacion,
    e.id_proyecto,
    e.id_version,
    ea.training_mode,
    ea.package_path,
    ea.package_size_mb,
    ea.package_generated_at,
    ea.dataset_size,
    ea.gguf_quantization
FROM entrenamientos e
INNER JOIN entrenamientos_autonomos ea ON e.id = ea.id_entrenamiento
WHERE ea.package_path IS NOT NULL
  AND ea.package_generated_at IS NOT NULL
  AND e.id_organizacion = <ORG_ID>
  AND e.id_proyecto = <PROJECT_ID>
  AND e.id_version = <VERSION_ID>
ORDER BY ea.package_generated_at DESC;
```

### Paso 3.5: Descargar Paquete desde Página

1. **Click en** "Descargar Paquete" de cualquier card
2. **Verificar spinner** en el botón durante la descarga
3. **Verificar que inicia descarga** en el navegador
4. **Verificar archivo descargado:**
   ```bash
   cd ~/Downloads
   ls -lh ENT*_modelo_autonomo.zip

   # Verificar integridad
   unzip -t ENT*_modelo_autonomo.zip
   ```

---

## PARTE 4: Verificación de la Cadena de Endpoints

### Test 4.1: Endpoint de Listado de Paquetes

```bash
# Test directo al trainer
curl -X GET "http://localhost:8004/trainer/entrenamientos/autonomous/packages?id_organizacion=1&id_proyecto=1&id_version=2" \
  -H "X-Client-App: test"

# Debe devolver:
# {
#   "success": true,
#   "packages": [...],
#   "total": N
# }

# Test a través del broker
curl -X GET "http://localhost:8008/training/entrenamientos/autonomous/packages?id_organizacion=1" \
  -H "Authorization: Bearer <TOKEN>"

# Test a través del middleware
curl -X GET "http://localhost:8007/training/entrenamientos/autonomous/packages?id_organizacion=1" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "X-Session-Token: <SESSION_TOKEN>"
```

### Test 4.2: Endpoint de Descarga de Paquete

```bash
# Test directo al trainer
curl -X GET "http://localhost:8004/trainer/entrenamientos/<ID>/autonomous/package" \
  -H "X-Client-App: test" \
  --output test_download.zip

# Verificar archivo descargado
ls -lh test_download.zip
unzip -t test_download.zip

# Test a través de la cadena completa
curl -X GET "http://localhost:8007/training/entrenamientos/<ID>/autonomous/package" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "X-Session-Token: <SESSION_TOKEN>" \
  --output test_download2.zip
```

---

## PARTE 5: Tests de Regresión

### Test 5.1: Múltiples Entrenamientos Paralelos

1. Iniciar 2-3 entrenamientos RAG simultáneamente
2. Verificar que cada uno tiene su propio polling
3. Verificar que no hay interferencias entre paneles
4. Verificar que todos se completan correctamente

### Test 5.2: Cambio de Training Mode

```bash
# Cambiar training_mode en .envglobal
echo "training_mode: test" > .envglobal

# Reiniciar trainer
# Iniciar nuevo entrenamiento autónomo
# Verificar que:
# - Modal muestra "TEST"
# - Se ejecutan las fases 7-8-9
# - Se genera el ZIP completo
```

### Test 5.3: Filtrado de Paquetes

1. Crear paquetes en diferentes org/prj/ver
2. Verificar que el filtrado funciona correctamente:
   - Solo org: muestra todos los paquetes de esa org
   - Org + Proyecto: solo paquetes de ese proyecto
   - Org + Proyecto + Versión: solo paquetes de esa versión

### Test 5.4: Permisos de Descarga

1. Usuario sin permiso `training_read`:
   - Debe recibir error 403
   - Mensaje: "Sin permisos para listar/descargar paquetes"

2. Usuario sin asignación a organización:
   - No debe ver esa organización en el selector
   - No debe poder listar paquetes de esa org

---

## PARTE 6: Limpieza y Rollback

### Limpiar Datos de Prueba

```sql
-- Eliminar entrenamientos de prueba
DELETE FROM evoluciones_autonomas WHERE id_entrenamiento IN (<IDS>);
DELETE FROM entrenamientos_autonomos WHERE id_entrenamiento IN (<IDS>);
DELETE FROM evoluciones_entrenamientos WHERE id_entrenamiento IN (<IDS>);
DELETE FROM entrenamientos WHERE id IN (<IDS>);
```

### Limpiar Archivos

```bash
# Eliminar paquetes generados
rm -rf ~/data/anewhope/files/trainer_server/internal/models/ORG*/PRJ*/v*/exports/ENT*/

# Limpiar downloads
rm ~/Downloads/ENT*_modelo_autonomo.zip
```

### Limpiar ChromaDB

```bash
# Eliminar colecciones de prueba
curl -X DELETE "http://localhost:8100/api/v1/collections/ENT<ID>"
```

---

## Checklist de Validación Final

### ✅ Entrenamiento RAG
- [ ] Se crea registro en `entrenamientos`
- [ ] Se crean 16 subfases en `evoluciones_entrenamientos`
- [ ] Polling actualiza UI cada 1-2 segundos
- [ ] Todas las subfases se completan
- [ ] Se crea colección en ChromaDB
- [ ] Aparece botón "Entrenar Modelo Autónomo"

### ✅ Entrenamiento Autónomo
- [ ] Modal muestra training_mode correcto
- [ ] Se crea registro en `entrenamientos_autonomos`
- [ ] Se crean subfases en `evoluciones_autonomas` (5 o 20 según modo)
- [ ] Polling actualiza subfases cada 2 segundos
- [ ] Se genera el paquete ZIP (test/production)
- [ ] package_path se guarda en BD
- [ ] Aparece botón "Descargar Modelo GGUF"

### ✅ Página de Descargas
- [ ] Validación OTP funciona (identity_type_id 1 o 2)
- [ ] Selectores cargan datos correctos
- [ ] Filtrado por org/prj/ver funciona
- [ ] Lista muestra paquetes disponibles
- [ ] Información de paquetes es correcta
- [ ] Descarga funciona desde página

### ✅ Endpoints
- [ ] GET packages funciona en toda la cadena
- [ ] GET package/{id} funciona en toda la cadena
- [ ] Filtros opcionales funcionan
- [ ] Permisos se validan correctamente
- [ ] Errores se manejan apropiadamente

### ✅ Archivos y BD
- [ ] ZIP se genera en path correcto
- [ ] ZIP contiene todos los archivos
- [ ] Datos en BD son consistentes
- [ ] Tiempos de ejecución son razonables

---

## Problemas Conocidos y Soluciones

### Problema 1: Polling no actualiza
**Síntoma:** Panel de evolución no se actualiza automáticamente

**Solución:**
```bash
# Limpiar cache de Reflex
cd src/apps/6_web_backoffice
./run.sh --clean
```

### Problema 2: Package_path es NULL
**Síntoma:** El paquete no se descarga porque package_path es NULL

**Causa:** Training_mode es "simulation" (no genera ZIP)

**Solución:** Cambiar a "test" o "production" en `.envglobal`

### Problema 3: Error 403 en descarga
**Síntoma:** Usuario no puede listar/descargar paquetes

**Causa:** Falta permiso `training_read`

**Solución:**
```sql
-- Verificar permisos
SELECT * FROM user_permissions WHERE id_user = <USER_ID>;

-- Agregar permiso si falta
INSERT INTO user_permissions (id_user, can_training_read) VALUES (<USER_ID>, 1);
```

### Problema 4: Organizaciones no aparecen
**Síntoma:** Selector de organizaciones está vacío

**Causa:** Usuario no tiene asignaciones

**Solución:**
```sql
-- Verificar asignaciones
SELECT * FROM user_organization_roles WHERE id_user = <USER_ID>;

-- Agregar asignación
INSERT INTO user_organization_roles (id_user, id_organizacion, id_identity_type)
VALUES (<USER_ID>, <ORG_ID>, 1);
```

---

## Métricas de Éxito

### Performance
- RAG completo: < 5 min (simulation en MacBook Intel i7)
- Autónomo simulation: < 5 min
- Autónomo test: < 45 min
- Autónomo production: < 150 min

### Reliability
- 0 errores en logs durante ejecución normal
- 100% de subfases completadas sin fallos
- Archivo ZIP generado sin corrupción

### Usabilidad
- Usuario puede completar flujo sin documentación
- Feedback visual claro en cada paso
- Errores se muestran con mensajes comprensibles

---

**Fin del documento de Testing E2E**
