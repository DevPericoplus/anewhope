# Guía de Testing Manual - Entrenamientos Autónomos y Descargas

**Fecha:** 2026-02-13
**Estado de Servicios:** ✅ Todos operativos y con endpoints funcionando

---

## Pre-requisitos Completados ✅

- ✅ Servicios reiniciados y funcionando
- ✅ Endpoints de descargas implementados y verificados
- ✅ Correcciones de código aplicadas (URL encoding, imports)
- ✅ Entrenamiento RAG #37 completado y verificado (16/16 subfases)
- ✅ Base de datos verificada

---

## PARTE 2: Entrenamiento Autónomo (Manual - UI)

### Objetivo

Ejecutar el entrenamiento autónomo (Fases 6-9) para el entrenamiento RAG #37 ya completado, y verificar la generación del paquete GGUF.

### Paso 2.1: Acceder al Backoffice

1. **Abrir navegador** y acceder a: http://localhost:8006
2. **Login:**
   - Email: `admintest@myllm.ai`
   - Password: (tu contraseña configurada)
3. **Verificar que entras correctamente** al dashboard

### Paso 2.2: Navegar a Entrenamientos

1. En el **menú lateral izquierdo**, buscar la sección **"Internal"**
2. Click en **"Entrenamientos"**
3. Deberías ver un visor de entrenamientos con el entrenamiento #37

### Paso 2.3: Verificar Entrenamiento RAG Completado

Busca el entrenamiento #37 y verifica:
- ✅ Estado: `completado`
- ✅ Fase actual: `5.5` o `entrenamiento`
- ✅ Collection name: `ORG00001_PRJ00001_v002_ENT37_SEQ33`
- ✅ Debe aparecer un panel de evolución con las 16 subfases en verde

### Paso 2.4: Verificar Botón "Entrenar Modelo Autónomo"

En el panel de evolución del entrenamiento #37, deberías ver:
- **Callout verde** con el mensaje: "Entrenamiento RAG completado exitosamente"
- **Botón naranja** con texto: **"Entrenar Modelo Autónomo"** 🚀

Si NO ves el botón:
```sql
-- Verificar en BD que el entrenamiento está completado
SELECT id, estado, fase_actual FROM entrenamientos WHERE id = 37;
-- Resultado esperado: estado='completado', fase_actual='entrenamiento' o '5.5'
```

### Paso 2.5: Iniciar Entrenamiento Autónomo

1. **Click en** "Entrenar Modelo Autónomo"
2. **Se abrirá un modal** con el título: "Iniciar Entrenamiento Autónomo"

**Verificar información del modal:**
- Lista de fases a ejecutar:
  - Fase 6: Preparación del Dataset
  - Fases 7-8: Entrenamiento LoRA y Fusión
  - Fase 9: Exportación GGUF
- **Badge de Training Mode:** Debe mostrar el modo actual (SIMULATION / TEST / PRODUCTION)
  - Color verde: SIMULATION (solo fase 6, no genera ZIP)
  - Color amarillo: TEST (fases 6-9, genera ZIP ~4-8GB)
  - Color rojo: PRODUCTION (fases 6-9, genera ZIP completo)
- **Callout informativo** según el modo:
  - SIMULATION: "Solo se ejecutará la fase 6. No se generará paquete ZIP."
  - TEST: "Se ejecutarán todas las fases con configuración ligera."
  - PRODUCTION: "Se ejecutarán todas las fases con configuración completa."

3. **Click en** "Iniciar Entrenamiento"

### Paso 2.6: Monitorear Progreso en la UI

Una vez iniciado, el panel de evolución debe actualizarse automáticamente:

**Comportamiento esperado:**
- Polling cada 2 segundos (automático)
- Las subfases autónomas aparecen debajo de las 16 subfases RAG
- Subfases cambian de color:
  - Gris: pendiente
  - Azul: en progreso (con spinner)
  - Verde: completada
- Puedes ver el tiempo de duración de cada subfase

**Subfases según modo:**

**SIMULATION (5 subfases - Fase 6):**
- 6.1 Cargar datos RAG
- 6.2 Estructurar ejemplos
- 6.3 Generar dataset
- 6.4 Validar dataset
- 6.5 Guardar dataset

**TEST/PRODUCTION (20 subfases - Fases 6-9):**
- Fase 6: 6.1-6.5 (dataset)
- Fase 7: 7.1-7.5 (entrenamiento LoRA)
- Fase 8: 8.1-8.5 (fusión modelo)
- Fase 9: 9.1-9.5 (exportación GGUF)

### Paso 2.7: Monitorear en Base de Datos (Paralelo)

Mientras se ejecuta el entrenamiento, puedes monitorear en la BD:

```bash
# Conectar a MariaDB
/usr/local/opt/mariadb@10.6/bin/mariadb -u myllm_admin -p'Us3r@dminP@ss' myllm_projects_db
```

**Consulta 1: Verificar registro autónomo**
```sql
SELECT
    id_entrenamiento,
    training_mode,
    created_at
FROM entrenamientos_autonomos
WHERE id_entrenamiento = 37;
-- Debe aparecer 1 fila con el modo actual
```

**Consulta 2: Contar subfases**
```sql
SELECT COUNT(*) as total_subfases
FROM evoluciones_autonomas
WHERE id_entrenamiento = 37;
-- Resultado esperado: 5 (simulation) o 20 (test/production)
```

**Consulta 3: Monitorear progreso en tiempo real**
```sql
SELECT
    subfase_key,
    subfase_name,
    status,
    duracion_segundos,
    updated_at
FROM evoluciones_autonomas
WHERE id_entrenamiento = 37
ORDER BY phase_key, subfase_key;
-- Ejecutar cada 10-15 segundos para ver el progreso
```

**Consulta 4: Ver resumen de progreso**
```sql
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completadas,
    SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as en_progreso,
    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pendientes,
    ROUND(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as porcentaje
FROM evoluciones_autonomas
WHERE id_entrenamiento = 37;
```

### Paso 2.8: Tiempos Esperados

**SIMULATION:**
- Fase 6: 2-5 minutos
- Total: 2-5 minutos
- No genera paquete ZIP

**TEST:**
- Fase 6: 5-10 minutos
- Fases 7-8: 10-20 minutos
- Fase 9: 5-10 minutos
- Total: 20-40 minutos
- Genera ZIP de ~4-8 GB

**PRODUCTION:**
- Fase 6: 15-30 minutos
- Fases 7-8: 30-90 minutos
- Fase 9: 8-15 minutos
- Total: 53-135 minutos
- Genera ZIP completo

### Paso 2.9: Verificar Completitud

Una vez completado el entrenamiento autónomo:

**En la UI:**
- ✅ Todas las subfases en verde
- ✅ Debe aparecer **callout verde** con:
  - Mensaje: "Modelo autónomo generado exitosamente"
  - Botón: **"Descargar Modelo GGUF"** 📥 (verde)
  - Badge: "ZIP Package"

**En la Base de Datos:**
```sql
-- Verificar que todas las subfases están completadas
SELECT
    subfase_key,
    status,
    duracion_segundos
FROM evoluciones_autonomas
WHERE id_entrenamiento = 37
  AND status != 'completed';
-- Resultado esperado: 0 filas (todas completadas)

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
WHERE id_entrenamiento = 37;
-- package_path debe tener valor (solo en test/production)
-- package_size_mb debe ser > 0
```

**Verificar archivos generados (TEST/PRODUCTION):**
```bash
# Obtener el package_path de la consulta anterior
# Ejemplo: ~/data/anewhope/files/trainer_server/internal/models/ORG00001/PRJ00001/v002/exports/ENT37/ENT37_modelo_autonomo.zip

# Verificar que el archivo existe
ls -lh <PACKAGE_PATH>

# Verificar tamaño
du -h <PACKAGE_PATH>

# Verificar contenido del ZIP
unzip -l <PACKAGE_PATH>
# Debe contener:
# - ENT37_model_q4_k_m.gguf (o similar)
# - Modelfile
# - README.md
```

### Paso 2.10: Probar Descarga Directa desde Panel

1. En el panel de evolución, **click en** "Descargar Modelo GGUF"
2. Debe iniciarse la descarga en el navegador
3. Verificar archivo descargado:

```bash
# Ir a directorio de descargas
cd ~/Downloads

# Verificar archivo
ls -lh ENT37_modelo_autonomo.zip

# Verificar que no está corrupto
unzip -t ENT37_modelo_autonomo.zip
```

---

## PARTE 3: Página de Descargas (Manual - UI)

### Pre-requisito

✅ Completar PARTE 2 (debe haber al menos un paquete generado)

### Paso 3.1: Acceder a Página de Descargas

1. En el **menú del Backoffice**, buscar el ítem **"Descargas"**
2. **Click en** "Descargas"
3. La página debe cargar

### Paso 3.2: Validación OTP (Solo SuperAdmin/OrgAdmin)

Como el usuario **admintest** tiene `identity_type_id = 1` (SuperAdmin), debe aparecer:

**Sección de Validación de Identidad:**
- Card con título: "Validación de Identidad"
- Texto explicativo sobre OTP
- Botón: **"Enviar Código OTP"** 📱

**Proceso OTP:**
1. **Click en** "Enviar Código OTP"
2. **Verificar toast** con mensaje: "Código OTP enviado por SMS"
3. **Ingresar código OTP:**
   - En desarrollo, el código puede estar en logs o BD
   - Código de 6 dígitos
4. **Click en** "Validar Código"
5. **Verificar toast:** "Código OTP validado correctamente"
6. La sección de OTP debe **desaparecer**
7. Deben **aparecer los filtros** (Organización, Proyecto, Versión)

**Nota:** Si `identity_type_id` no es 1 o 2, la sección de OTP no aparece y los filtros se muestran directamente.

### Paso 3.3: Seleccionar Filtros

**Selector 1: Organización**
- Debe mostrar organizaciones según asignaciones del usuario
- En este caso: ORG00001 (Organización 1)
- **Seleccionar:** ORG00001

**Selector 2: Proyecto (se carga automáticamente)**
- Debe mostrar proyectos de la organización seleccionada
- En este caso: PRJ00001 (Proyecto 1)
- **Seleccionar:** PRJ00001

**Selector 3: Versión (se carga automáticamente)**
- Debe mostrar versiones del proyecto seleccionado
- En este caso: v002 (Versión 2)
- **Seleccionar:** v002

### Paso 3.4: Ver Lista de Paquetes

Después de seleccionar la versión, debe aparecer:

**Spinner de Carga:**
- Mensaje: "Cargando paquetes disponibles..."
- Debe durar 1-2 segundos

**Card del Paquete (si hay paquetes):**

Cada paquete debe mostrar:
- 📦 **Icono de archivo**
- **Filename:** `ENT37_modelo_autonomo.zip`
- **Badges:**
  - "Entrenamiento #37" (azul)
  - Training mode: "SIMULATION" / "TEST" / "PRODUCTION" (coloreado)
  - Cuantización: "q4_k_m" (púrpura)
- **Grid de información:**
  - Tamaño: X.X MB o X.X GB
  - Dataset: X ejemplos
  - Generado: YYYY-MM-DD HH:MM
- **Botón:** "Descargar Paquete" 📥 (verde)

**Si NO hay paquetes:**
- Icono de bandeja vacía
- Mensaje: "No se encontraron paquetes disponibles"
- Submensaje: "Seleccione otra versión o complete un entrenamiento autónomo primero."

### Paso 3.5: Descargar Paquete

1. **Click en** "Descargar Paquete" en el card del paquete
2. **Verificar spinner** en el botón durante la descarga
3. Debe iniciarse la descarga en el navegador
4. **Verificar archivo descargado:**

```bash
cd ~/Downloads
ls -lh ENT37_modelo_autonomo.zip

# Verificar integridad
unzip -t ENT37_modelo_autonomo.zip

# Ver contenido
unzip -l ENT37_modelo_autonomo.zip
```

### Paso 3.6: Probar Filtros Diferentes

**Test de filtrado:**
1. Cambiar a otra organización (si hay)
2. Verificar que se cargan proyectos diferentes
3. Cambiar a otro proyecto
4. Verificar que se cargan versiones diferentes
5. Cambiar a otra versión
6. Verificar que se filtran correctamente los paquetes

---

## Verificaciones SQL para Descargas

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
  AND e.id_organizacion = 1
  AND e.id_proyecto = 1
  AND e.id_version = 2
ORDER BY ea.package_generated_at DESC;

-- Ver organizaciones asignadas al usuario
SELECT DISTINCT o.id, o.name
FROM organizations o
INNER JOIN user_organization_roles uor ON o.id = uor.id_organizacion
WHERE uor.id_user = 58;

-- Ver proyectos de una organización
SELECT id, name
FROM projects
WHERE id_organizacion = 1;

-- Ver versiones de un proyecto
SELECT id, id_version, fecha_lanzamiento
FROM versiones
WHERE id_proyecto = 1
ORDER BY id DESC;
```

---

## Checklist de Validación

### ✅ PARTE 2: Entrenamiento Autónomo

- [ ] Modal de confirmación apareció
- [ ] Training mode correcto mostrado
- [ ] Subfases autónomas aparecen en UI
- [ ] Polling actualiza cada 2 segundos
- [ ] Todas las subfases se completan
- [ ] Registro en `entrenamientos_autonomos` creado
- [ ] Subfases en `evoluciones_autonomas` creadas
- [ ] Paquete ZIP generado (test/production)
- [ ] Botón "Descargar Modelo GGUF" aparece
- [ ] Descarga desde panel funciona

### ✅ PARTE 3: Página de Descargas

- [ ] Página de Descargas carga correctamente
- [ ] Validación OTP funciona (si aplica)
- [ ] Selector de organización muestra opciones
- [ ] Selector de proyecto carga automáticamente
- [ ] Selector de versión carga automáticamente
- [ ] Lista de paquetes aparece después de seleccionar versión
- [ ] Card muestra información correcta del paquete
- [ ] Descarga desde página funciona
- [ ] Archivo descargado es válido
- [ ] Filtros funcionan correctamente

---

## Problemas Conocidos y Soluciones

### Problema: Botón "Entrenar Modelo Autónomo" no aparece

**Causa:** El entrenamiento RAG no está marcado como completado

**Solución:**
```sql
-- Verificar estado
SELECT id, estado, fase_actual FROM entrenamientos WHERE id = 37;

-- Si necesario, marcar como completado manualmente
UPDATE entrenamientos
SET estado = 'completado', fase_actual = '5.5'
WHERE id = 37;
```

### Problema: Modal no muestra training_mode

**Causa:** No se encuentra el archivo de configuración

**Solución:**
- Verificar que el trainer puede leer la configuración
- Por defecto usa "simulation"

### Problema: OTP no llega

**Causa:** En desarrollo, el SMS no se envía realmente

**Solución:**
- Verificar logs del backoffice
- En desarrollo, considerar simular validación OTP

### Problema: Organizaciones vacías en selector

**Causa:** Usuario no tiene asignaciones

**Solución:**
```sql
-- Agregar asignación
INSERT INTO user_organization_roles (id_user, id_organizacion, id_identity_type)
VALUES (58, 1, 1);
```

### Problema: Paquetes no aparecen

**Causa:**
1. No se completó el entrenamiento autónomo
2. Training mode es SIMULATION (no genera ZIP)
3. Filtros incorrectos

**Solución:**
- Verificar en BD que package_path no es NULL
- Cambiar training_mode a TEST o PRODUCTION
- Verificar filtros de org/prj/ver

---

## Siguiente Paso

Una vez completadas las PARTES 2 y 3, puedes ejecutar la **PARTE 5: Tests de Regresión** que incluye:
- Múltiples entrenamientos paralelos
- Cambio de training_mode
- Filtrado de paquetes
- Permisos de descarga

Ver archivo `docs/TESTING_E2E_ENTRENAMIENTOS.md` sección PARTE 5 para instrucciones.

---

**Fin de la guía manual**
