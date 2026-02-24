# Estado del Testing E2E - Sistema de Entrenamientos y Descargas

**Fecha:** 2026-02-13 23:30
**Estado:** Testing parcialmente completado - Requiere reinicio de servicios y testing manual de UI

---

## ✅ COMPLETADO

### Pre-requisitos
- ✅ Todos los servicios corriendo (puertos 8003, 8004, 8006, 8007, 8008, 8100)
- ✅ Tablas de BD verificadas (entrenamientos, evoluciones_entrenamientos, entrenamientos_autonomos, evoluciones_autonomas)
- ✅ Usuario de prueba identificado: user_id=58, admintest@myllm.ai, SuperAdmin (identity_type_id=1)
- ✅ Documentos de prueba disponibles: ORG00001/PRJ00002/v012 (5 archivos txt/md)
- ✅ Versión en BD: id=28, id_proyecto=2, id_version=12 (v012), id_organizacion=1

### PARTE 1: Entrenamiento RAG (Fases 2-5) ✅

**Entrenamiento #37 verificado (completado hoy 13:12-13:14):**
- ✅ Registro creado en `entrenamientos` (id=37, estado=completado)
- ✅ 16 subfases creadas en `evoluciones_entrenamientos`
- ✅ Todas las 16 subfases completadas (100%)
- ✅ Collection_name asignado: `ORG00001_PRJ00001_v002_ENT37_SEQ33`
- ✅ Tiempo de ejecución: ~112 segundos (~2 min)

**Detalles de subfases:**
```
Fase 2 (Validación): 4 subfases (2.1-2.4) - 0-1s cada una
Fase 3 (Preparación): 3 subfases (3.1-3.3) - 0-6s (3.3 embeddings: 6s)
Fase 4 (Configuración): 4 subfases (4.1-4.4) - 0-1s cada una
Fase 5 (Entrenamiento): 5 subfases (5.1-5.5) - 0-101s (5.5 test: 101s)
```

**SQL de verificación:**
```sql
-- Ver entrenamiento completado
SELECT id, numero_secuencia, estado, fase_actual, collection_name
FROM entrenamientos WHERE id = 37;

-- Ver subfases completadas
SELECT subfase_key, subfase_name, status, duracion_segundos
FROM evoluciones_entrenamientos WHERE id_entrenamiento = 37
ORDER BY phase_key, subfase_key;
```

---

## ⚠️ PENDIENTE - Requiere Acción

### Reinicio de Servicios REQUERIDO

Los archivos de código fueron modificados hoy 22:20-22:25, pero los servicios están corriendo con versiones anteriores.

**Servicios que necesitan reinicio:**

1. **Trainer (puerto 8004)**
   ```bash
   # Detener proceso actual
   ps aux | grep apitrainer | grep -v grep | awk '{print $2}' | xargs kill

   # Reiniciar
   cd src/apps/4_trainer
   ./run.sh
   # O si no existe run.sh:
   python apitrainer.py
   ```

2. **Broker (puerto 8008)**
   ```bash
   ps aux | grep apibe | grep -v grep | awk '{print $2}' | xargs kill
   cd src/apps/8_service_backend
   ./run.sh
   ```

3. **Middleware (puerto 8007)**
   ```bash
   ps aux | grep apife | grep -v grep | awk '{print $2}' | xargs kill
   cd src/apps/7_service_frontend
   ./run.sh
   ```

**Verificar que los servicios reiniciaron correctamente:**
```bash
lsof -i :8004,8007,8008 -P -n | grep LISTEN
curl -s http://localhost:8004/docs | head -5  # Debe devolver HTML
curl -s http://localhost:8008/docs | head -5
curl -s http://localhost:8007/docs | head -5
```

---

### PARTE 2: Entrenamiento Autónomo (Fases 6-9) ⏸️ PENDIENTE

**Estado:** No hay entrenamientos autónomos en la BD (tabla `entrenamientos_autonomos` está vacía)

**Pasos para ejecutar:**

1. **Acceder al Backoffice:** http://localhost:8006
2. **Login** con admintest@myllm.ai (password según tu configuración)
3. **Navegar a:** Menú Internal → Entrenamientos
4. **Seleccionar** el entrenamiento #37 (ya completado) o iniciar uno nuevo
5. **Click en** botón "Entrenar Modelo Autónomo" (debe aparecer en panel de evolución)
6. **Verificar modal de confirmación:**
   - Debe mostrar el `training_mode` actual (SIMULATION / TEST / PRODUCTION)
   - Lista de fases a ejecutar (6, 7-8, 9)
   - Callout informativo según modo
7. **Click en** "Iniciar Entrenamiento"

**Monitorear progreso:**

```sql
-- Verificar que se creó registro autónomo
SELECT id_entrenamiento, training_mode, created_at
FROM entrenamientos_autonomos
WHERE id_entrenamiento = 37;

-- Ver subfases autónomas (cantidad depende del modo)
SELECT COUNT(*) as total_subfases
FROM evoluciones_autonomas
WHERE id_entrenamiento = 37;
-- Esperado: 5 (simulation) o 20 (test/production)

-- Monitorear progreso en tiempo real
SELECT subfase_key, subfase_name, status, duracion_segundos
FROM evoluciones_autonomas
WHERE id_entrenamiento = 37
ORDER BY phase_key, subfase_key;
```

**Verificar archivos generados:**

```bash
# Obtener package_path de la BD
/usr/local/opt/mariadb@10.6/bin/mariadb -u myllm_admin -p'Us3r@dminP@ss' myllm_projects_db -e \
  "SELECT package_path, package_size_mb FROM entrenamientos_autonomos WHERE id_entrenamiento = 37;"

# Verificar que el archivo existe
ls -lh <PACKAGE_PATH>

# Verificar contenido del ZIP
unzip -l <PACKAGE_PATH>
```

**Tiempos esperados según modo:**
- SIMULATION: 2-5 min (solo fase 6, no genera ZIP)
- TEST: 20-40 min (fases 6-9, genera ZIP ~4-8 GB)
- PRODUCTION: 53-135 min (fases 6-9, genera ZIP completo)

---

### PARTE 3: Página de Descargas ⏸️ PENDIENTE

**Pre-requisito:** Completar PARTE 2 (debe haber al menos un paquete generado)

**Pasos para ejecutar:**

1. **Navegar a:** Menú → Descargas en el Backoffice
2. **Validación OTP** (para SuperAdmin/OrgAdmin):
   - Click en "Enviar Código OTP"
   - Verificar toast de confirmación
   - Ingresar código OTP (6 dígitos)
   - Click en "Validar Código"
3. **Seleccionar filtros:**
   - Organización: Seleccionar ORG00001
   - Proyecto: Seleccionar PRJ00001
   - Versión: Seleccionar v002
4. **Verificar lista de paquetes:**
   - Debe aparecer card con paquete generado
   - Información: ID entrenamiento, training mode, tamaño, fecha
5. **Descargar paquete:**
   - Click en "Descargar Paquete"
   - Verificar que inicia descarga en navegador
   - Verificar archivo descargado en ~/Downloads

**Verificación SQL:**

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
    ea.dataset_size
FROM entrenamientos e
INNER JOIN entrenamientos_autonomos ea ON e.id = ea.id_entrenamiento
WHERE ea.package_path IS NOT NULL
  AND ea.package_generated_at IS NOT NULL
  AND e.id_organizacion = 1
  AND e.id_proyecto = 1
  AND e.id_version = 2
ORDER BY ea.package_generated_at DESC;
```

---

### PARTE 4: Verificación de Endpoints ⏸️ REQUIERE REINICIO

**Estado:** Endpoints no disponibles porque servicios necesitan reiniciarse

**Después de reiniciar servicios, ejecutar:**

#### Test 4.1: Endpoint de Listado de Paquetes

```bash
# Test directo al Trainer
curl -s -X GET "http://localhost:8004/trainer/entrenamientos/autonomous/packages?id_organizacion=1" \
  -H "X-Client-App: test"

# Debe devolver:
# {
#   "success": true,
#   "packages": [...],
#   "total": N
# }

# Test a través del Broker
curl -s -X GET "http://localhost:8008/training/entrenamientos/autonomous/packages?id_organizacion=1" \
  -H "Authorization: Bearer <TOKEN>"

# Test a través del Middleware
curl -s -X GET "http://localhost:8007/training/entrenamientos/autonomous/packages?id_organizacion=1" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "X-Session-Token: <SESSION_TOKEN>"
```

**Nota:** Para obtener tokens válidos, usar el proceso de login del usuario admintest.

#### Test 4.2: Endpoint de Descarga de Paquete

```bash
# Test directo al Trainer (requiere id_entrenamiento de un entrenamiento autónomo completado)
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

### PARTE 5: Tests de Regresión ⏸️ PENDIENTE

**Estado:** No iniciado (requiere completar PARTE 2 y 3 primero)

**Tests a ejecutar:**

1. **Múltiples Entrenamientos Paralelos:**
   - Iniciar 2-3 entrenamientos RAG simultáneamente
   - Verificar que cada uno tiene su propio polling
   - Verificar que no hay interferencias

2. **Cambio de Training Mode:**
   - Si existe .envglobal: cambiar `training_mode` a "test"
   - Reiniciar trainer
   - Iniciar entrenamiento autónomo
   - Verificar que se ejecutan fases 7-8-9

3. **Filtrado de Paquetes:**
   - Crear paquetes en diferentes org/prj/ver
   - Verificar filtrado por organización
   - Verificar filtrado por proyecto
   - Verificar filtrado por versión

4. **Permisos de Descarga:**
   - Probar con usuario sin permiso `training_read`
   - Debe recibir error 403
   - Probar con usuario sin asignación a organización
   - No debe ver organizaciones no asignadas

---

## 📊 Resumen del Estado

| Parte | Estado | Progreso | Notas |
|-------|--------|----------|-------|
| Pre-requisitos | ✅ Completado | 100% | Todos los servicios y datos verificados |
| PARTE 1: RAG | ✅ Completado | 100% | Entrenamiento #37 verificado completamente |
| PARTE 2: Autónomo | ⏸️ Pendiente | 0% | Requiere ejecución manual desde UI |
| PARTE 3: Descargas | ⏸️ Pendiente | 0% | Requiere PARTE 2 completada |
| PARTE 4: Endpoints | ⚠️ Bloqueado | 0% | Requiere reinicio de servicios |
| PARTE 5: Regresión | ⏸️ Pendiente | 0% | Requiere PARTE 2, 3 y 4 completadas |

**Progreso Total:** 2/6 partes completadas (33%)

---

## 🎯 Próximos Pasos

### Inmediato (Paso 1)
**Reiniciar servicios** (Trainer, Broker, Middleware) para cargar los nuevos endpoints

### Paso 2
**Ejecutar PARTE 2:** Entrenar modelo autónomo desde el Backoffice
- Usar entrenamiento #37 existente o iniciar uno nuevo
- Monitorear progreso en UI y BD
- Verificar generación de archivos

### Paso 3
**Ejecutar PARTE 3:** Probar página de Descargas
- Validación OTP
- Filtros de org/prj/ver
- Listado y descarga de paquetes

### Paso 4
**Ejecutar PARTE 4:** Verificar endpoints con curl
- Listado de paquetes (3 niveles: Trainer, Broker, Middleware)
- Descarga de paquetes (3 niveles)

### Paso 5
**Ejecutar PARTE 5:** Tests de regresión
- Entrenamientos paralelos
- Cambios de modo
- Filtrado
- Permisos

---

## 📝 Notas Importantes

1. **Training Mode:** No se encontró archivo `.envglobal` para configurar el modo. Verificar dónde se configura el `training_mode` (simulation/test/production).

2. **ChromaDB:** API v1 deprecada, usar v2. No se pudo verificar colecciones directamente, pero el entrenamiento tiene `collection_name` asignado.

3. **Logs:** El trainer usa `console.log` en lugar de `trainer_api.log`. Última actividad: 2026-02-13 13:14.

4. **Archivos Modificados:** Los endpoints de descargas autónomas fueron agregados/modificados hoy 22:20-22:25, pero los servicios están corriendo con código anterior.

5. **Base de Datos:**
   - Core DB: `myllm_core_db` (usuarios, permisos, organizaciones)
   - Projects DB: `myllm_projects_db` (entrenamientos, evoluciones, versiones)
   - User: `myllm_admin` / Pass: `Us3r@dminP@ss`

---

**Fin del reporte de estado**
