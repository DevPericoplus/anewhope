# Plan de Pruebas - Sistema de Flujo de Estados

**Fecha**: 2026-02-04
**Versión**: 2.0 (Actualizado con selector de estados)

## Cambios Implementados

### 1. Control de Acceso por Rol

**Frontend (Cliente/Org Admin)**:
- Solo usuarios con `identity_type_id` 1 o 2 (administradores) ven controles
- Panel de control simplificado:
  - Selector de estado: Solo Abierta ↔ Bloqueada
  - Checkbox de protección (sincronizado con estado)
  - Solo disponible mientras `final_c` y `final_i` sean `false`

**Backoffice (Interno/Soporte)**:
- Todos los usuarios internos ven el selector completo (soporte al cliente)
- Panel de control completo:
  - Selector de estado: Abierta, Bloqueada, Protegida, Final
  - Checkbox de protección
  - Checkbox de final_c (Capa Cliente)
  - Checkbox de final_i (Capa Interno)
  - Control directo sobre todos los flags para dar soporte

### 2. Bloqueo/Desbloqueo

**Condiciones**:
- Frontend: Solo admin de organización (identity_type_id 1 o 2)
- Backoffice: Todos los internos
- Solo mientras `final_c` y `final_i` sean `false`
- Cuando se bloquea:
  - Versión pasa a estado "Bloqueada"
  - Flag `protected` = `true`
  - **TODOS los elementos de esa versión se deshabilitan**
  - **NO aparecen menús contextuales** ni para carpetas ni para ficheros
  - Solo admin puede desbloquear

### 3. Visibilidad de Controles

| Rol | identity_type_id | Frontend | Backoffice |
|-----|------------------|----------|------------|
| Cliente | 3+ | Sin controles | N/A |
| Admin Org | 1 o 2 | Panel simple (Abierta ↔ Bloqueada) | N/A |
| Admin Org | 1 o 2 | N/A | Panel completo (todos los estados) |
| Interno | Cualquiera | N/A | Panel completo (soporte) |

---

## Para probar el sistema:

### **Requisitos Previos**
```bash
# Asegurarse de que todos los servicios están corriendo:
# - Backend (puerto 8001)
# - Middleware (puerto 8007)
# - Frontend (puerto 3000)
# - Backoffice (puerto 3001)
```

---

## **Test 1: Admin de Organización en Frontend**

### Setup
- **Usuario**: adminone (identity_type_id: 1 o 2)
- **Proyecto**: botweb (ID 2)
- **Versión**: v001 (ID 3)
- **Estado inicial**: Abierta

### Pasos

1. **Login como admin**
   ```
   http://localhost:3000
   Usuario: adminone
   Password: Password01
   OTP: [obtener de BD]
   ```

2. **Navegar a Explorador**
   - Seleccionar proyecto "botweb"
   - Seleccionar versión "v001"
   - **Verificar**: Estado muestra "Abierta" en verde

3. **Verificar Panel de Control (Solo Admin)**
   - **Debe aparecer**: Panel naranja "Control de Estados (Administrador)"
   - **Contenido**:
     - Selector de estado con opciones: Abierta, Bloqueada
     - Checkbox "Protegida" (desactivado)
     - Mensaje: No se puede cambiar si hay flags activos

4. **Bloquear versión (Opción A: Selector)**
   - Cambiar selector de "Abierta" a "Bloqueada"
   - **Verificar**:
     - Toast: "Estado cambiado a Bloqueada"
     - Estado muestra "Bloqueada" en naranja
     - Checkbox "Protegida" se activa automáticamente
     - **Menús contextuales desaparecen** (clic derecho no muestra opciones)
     - Elementos aparecen semi-transparentes (opacity 0.5)

5. **Bloquear versión (Opción B: Checkbox)**
   - (Si está en Abierta) Activar checkbox "Protegida"
   - **Verificar**: Mismo resultado que opción A

6. **Intentar crear carpeta/archivo**
   - Hacer clic derecho en cualquier carpeta o archivo
   - **Verificar**: NO aparece menú contextual (versión bloqueada)

7. **Desbloquear versión**
   - Cambiar selector de "Bloqueada" a "Abierta"
   - **O** desactivar checkbox "Protegida"
   - **Verificar**:
     - Toast: "Versión desbloqueada" o "Estado cambiado a Abierta"
     - Estado vuelve a "Abierta" en verde
     - **Menús contextuales vuelven a aparecer**
     - Elementos vuelven a opacity normal

8. **Verificar restricción con flags activos**
   - (Este paso requiere backoffice, ver Test 2)

---

## **Test 2: Usuario Interno en Backoffice (Soporte)**

### Setup
- **Usuario**: Cualquier usuario interno
- **Proyecto**: botweb (ID 2)
- **Versión**: v001 (ID 3)
- **Estado inicial**: Abierta

### Pasos

1. **Login como interno**
   ```
   http://localhost:3001
   Usuario: [usuario interno]
   Password: [password]
   OTP: [obtener de BD]
   ```

2. **Navegar a Explorador**
   - Seleccionar proyecto "botweb"
   - Seleccionar versión "v001"

3. **Verificar Panel de Control Completo**
   - **Debe aparecer**: Panel morado "Selector de Estados por Versión (Soporte)"
   - **Contenido**:
     - Selector de estado: Abierta, Bloqueada, Protegida, Final
     - Checkbox "Protegida"
     - Checkbox "final_c" (Capa Cliente)
     - Checkbox "final_i" (Capa Interno)
     - Mensaje: "Como usuario interno de soporte, puedes cambiar cualquier estado..."

4. **Test Flujo Cliente: Abierta → Protegida**
   - Cambiar selector a "Protegida"
   - **Verificar**:
     - Estado cambia a "Protegida"
     - Checkbox "Protegida" se activa
     - Checkbox "final_c" se activa automáticamente
     - Menús contextuales desaparecen

5. **Test Flujo Interno: Protegida → Final**
   - Cambiar selector a "Final"
   - **Verificar**:
     - Estado cambia a "Final"
     - Checkbox "final_i" se activa automáticamente
     - Versión completamente inmutable

6. **Test Control Directo de Flags**
   - Volver a "Abierta" (selector)
   - Activar manualmente checkbox "final_c"
   - **Verificar**: Toast confirma cambio
   - Desactivar checkbox "final_c"
   - **Verificar**: Toast confirma cambio

7. **Test Bloqueo desde Backoffice**
   - Cambiar a "Bloqueada"
   - **Verificar**: Menús contextuales desaparecen
   - Cambiar a "Abierta"
   - **Verificar**: Menús vuelven a aparecer

8. **Test Soporte: Revertir estado Final**
   - Poner versión en "Final" (final_c y final_i activos)
   - Cambiar selector a "Abierta"
   - **Verificar**:
     - Estado cambia a "Abierta"
     - Flags final_c y final_i se desactivan
     - Versión vuelve a ser modificable
     - (Esto simula un rollback de soporte al cliente)

---

## **Test 3: Usuario Cliente (NO Admin) en Frontend**

### Setup
- **Usuario**: Cliente sin permisos admin (identity_type_id > 2)
- **Proyecto**: botweb (ID 2)
- **Versión**: v001 (ID 3)

### Pasos

1. **Login como cliente normal**
   ```
   Usuario: [cliente sin admin]
   Password: [password]
   OTP: [obtener de BD]
   ```

2. **Navegar a Explorador**
   - Seleccionar proyecto "botweb"
   - Seleccionar versión "v001"

3. **Verificar Ausencia de Controles**
   - **NO debe aparecer**: Panel de control de estados
   - **NO debe aparecer**: Botones de bloquear/desbloquear
   - **Solo lectura**: Puede ver archivos pero no cambiar estados

4. **Verificar Comportamiento con Versión Bloqueada**
   - (Solicitar a admin que bloquee la versión v001)
   - Recargar explorador
   - **Verificar**: Menús contextuales no aparecen
   - Estado muestra "Bloqueada" en naranja

---

## **Test 4: Protección en Cascada**

### Setup
- **Usuario**: Admin en frontend O interno en backoffice
- **Proyecto**: botweb
- **Versión**: v001 con estructura:
  ```
  v001/
    ├── README.md
    ├── images/
    │   └── logo.png
    └── text/
        └── doc.txt
  ```

### Pasos

1. **Estado Inicial: Abierta**
   - Verificar menús contextuales en:
     - ✅ Carpeta v001 (depth=1): SIN menú (protección estructural)
     - ✅ Carpeta images/ (depth=2): CON menú
     - ✅ Archivo logo.png (depth=3): CON menú
     - ✅ Carpeta text/ (depth=2): CON menú
     - ✅ Archivo doc.txt (depth=3): CON menú
     - ✅ Archivo README.md (depth=2): CON menú

2. **Bloquear Versión**
   - Cambiar estado a "Bloqueada"

3. **Verificar Cascada de Bloqueo**
   - **TODOS los elementos** dentro de v001 deben:
     - Aparecer con opacity 0.5 (semi-transparentes)
     - NO mostrar menú contextual al hacer clic derecho
     - Esto incluye:
       - ❌ Carpeta images/
       - ❌ Archivo logo.png
       - ❌ Carpeta text/
       - ❌ Archivo doc.txt
       - ❌ Archivo README.md

4. **Desbloquear Versión**
   - Cambiar estado a "Abierta"

5. **Verificar Restauración**
   - Todos los elementos vuelven a ser interactivos
   - Menús contextuales vuelven a aparecer

---

## **Test 5: Validación de Base de Datos**

### Verificar coherencia entre UI y BD

```bash
.venv_backend313/bin/python -c "
import pymysql
import importlib.util
from pathlib import Path

protected_path = Path('infrastructure/environments/macbook/protected_values.py')
spec = importlib.util.spec_from_file_location('protected_values', protected_path)
protected = importlib.util.module_from_spec(spec)
spec.loader.exec_module(protected)

conn = pymysql.connect(
    host=protected.mariadb_host,
    port=protected.mariadb_port,
    user=protected.mariadb_admin_user,
    password=protected.mariadb_admin_password,
    database=protected.mariadb_ai_database,
    cursorclass=pymysql.cursors.DictCursor
)

try:
    with conn.cursor() as cursor:
        cursor.execute('''
            SELECT *
            FROM estado_version
            WHERE id_proyecto = 2 AND id_version = 3
        ''')
        version = cursor.fetchone()

        print('Estado en BD:')
        print(f'  Estado: {version[\"state\"]}')
        print(f'  Protected: {bool(version[\"protected\"])}')
        print(f'  final_c: {bool(version[\"final_c\"])}')
        print(f'  final_i: {bool(version[\"final_i\"])}')
finally:
    conn.close()
"
```

**Comparar con UI**: Los valores deben coincidir exactamente.

---

## Checklist de Validación

### Frontend (Admin Org)

- [ ] Panel de control solo visible para admin (identity_type_id 1 o 2)
- [ ] Selector muestra solo: Abierta, Bloqueada
- [ ] Checkbox "Protegida" sincroniza con estado
- [ ] Panel deshabilitado cuando final_c o final_i están activos
- [ ] Bloquear versión: menús contextuales desaparecen
- [ ] Desbloquear versión: menús vuelven a aparecer
- [ ] Usuario cliente (NO admin) no ve controles

### Backoffice (Soporte)

- [ ] Panel completo visible para todos los internos
- [ ] Selector muestra: Abierta, Bloqueada, Protegida, Final
- [ ] Checkboxes: Protegida, final_c, final_i
- [ ] Cambiar estado actualiza flags automáticamente
- [ ] Control directo sobre flags individuales
- [ ] Bloquear versión: menús desaparecen
- [ ] Puede revertir cualquier estado (soporte)

### Protección en Cascada

- [ ] Cuando protected=true, TODA la versión se bloquea
- [ ] Menús contextuales desaparecen en todos los niveles (depth >= 2)
- [ ] Elementos aparecen semi-transparentes (opacity 0.5)
- [ ] Al desbloquear, todo vuelve a la normalidad

### Base de Datos

- [ ] Cambios se reflejan en tabla estado_version
- [ ] Estados coherentes entre UI y BD
- [ ] Flags final_c y final_i correctos

---

## Casos Límite

### 1. Usuario sin permisos intenta acceder
- **Esperado**: No ve controles de estado

### 2. Intentar cambiar estado con final_c activo (Frontend)
- **Esperado**: Controles deshabilitados, mensaje de advertencia

### 3. Cambiar múltiples flags en secuencia rápida
- **Esperado**: Cada cambio se persiste correctamente

### 4. Versión en estado Final
- **Frontend**: No se puede cambiar
- **Backoffice**: Se puede revertir (soporte)

---

## Resultado Esperado

✅ **Sistema completamente funcional** con:
- Control de estados por rol
- Protección en cascada a nivel de versión completa
- Selector de estados en backoffice para soporte
- Validación correcta de permisos
- Sincronización perfecta entre UI y BD
