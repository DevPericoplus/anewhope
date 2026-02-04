# Tests del Sistema de Permisos del Explorador

Este directorio contiene los tests de integración para el sistema de permisos del explorador.

## Estructura de Tests

### 1. `test_explorador_permissions.py`

Tests del sistema de permisos basado en roles por proyecto.

**Verifica:**
- ✅ Carga de permisos desde `proyectos_roles` + `low_level_permissions`
- ✅ Permisos específicos por proyecto (no globales)
- ✅ Fallback a permisos por defecto si no hay datos en BD
- ✅ Validación de permisos por rol (Editor, Lector, Auditor)
- ✅ Estructura correcta de las tablas de BD

**Ejecutar:**
```bash
cd src/apps/5_web_frontend
pytest tests/test_explorador_permissions.py -v -s
```

### 2. `test_explorador_version_state.py`

Tests del flujo de estados de versiones (Abierta, Bloqueada, Protegida, Final).

**Verifica:**
- ✅ Solo admins pueden cambiar estados de versión
- ✅ Transiciones válidas: Abierta ↔ Bloqueada
- ✅ Persistencia en base de datos
- ✅ Restricciones de Cliente vs Interno

**Ejecutar:**
```bash
cd src/apps/5_web_frontend
pytest tests/test_explorador_version_state.py -v -s
```

### 3. `test_explorador_file_actions.py`

Tests de operaciones CRUD sobre archivos y carpetas.

**Verifica:**
- ✅ Crear carpeta
- ✅ Renombrar carpeta
- ✅ Eliminar carpeta
- ✅ Subir archivo con token JWT
- ✅ Descargar archivo con token JWT
- ✅ Validación de seguridad (tokens expirados, operaciones incorrectas)

**Ejecutar:**
```bash
cd src/apps/5_web_frontend
pytest tests/test_explorador_file_actions.py -v -s
```

## Ejecutar Todos los Tests

```bash
cd src/apps/5_web_frontend
pytest tests/test_explorador*.py -v -s
```

## Tests Específicos

### Por Rol

```bash
# Editor (puede crear, editar, eliminar)
pytest tests/test_explorador_permissions.py::test_editor_permissions -v

# Lector (solo lectura)
pytest tests/test_explorador_permissions.py::test_lector_permissions -v

# Auditor (lectura limitada para auditoría)
pytest tests/test_explorador_permissions.py::test_auditor_permissions -v
```

### Por Funcionalidad

```bash
# Verificar que usuario tiene rol en proyecto
pytest tests/test_explorador_permissions.py::test_user_has_role_in_project -v

# Verificar permisos diferentes en proyectos diferentes
pytest tests/test_explorador_permissions.py::test_user_different_roles_different_projects -v

# Verificar estructura de tablas
pytest tests/test_explorador_permissions.py::test_permissions_table_structure -v
pytest tests/test_explorador_permissions.py::test_proyectos_roles_table_structure -v
```

## Requisitos Previos

### Servicios en Ejecución

Los tests requieren que los siguientes servicios estén corriendo:

1. **MariaDB** (puerto 3306)
   ```bash
   # macOS
   brew services start mariadb

   # Linux
   sudo systemctl start mariadb
   ```

2. **Middleware** (puerto 8007)
   ```bash
   cd src/apps/7_service_frontend
   bash run.sh
   ```

3. **Broker Backend** (puerto 8008)
   ```bash
   cd src/apps/8_service_backend
   bash run.sh
   ```

4. **Backend Core** (puerto 8003)
   ```bash
   cd src/apps/3_backend
   bash run.sh
   ```

5. **fmanagement** (puerto 1666)
   ```bash
   cd /Users/administrator/develop/fmanagement
   go run main.go
   ```

### Verificar Servicios

```bash
# Verificar que todos los servicios responden
curl -I http://localhost:8007/health  # Middleware
curl -I http://localhost:8008/health  # Broker
curl -I http://localhost:8003/health  # Backend Core
curl -I http://localhost:1666/health  # fmanagement
```

### Datos de Prueba

Los tests requieren datos básicos en la base de datos:

**Usuario de prueba:** `adminone`
- `user_name`: "adminone"
- `password`: "Password01"
- `identity_type_id`: 1 (SuperAdmin)
- `organization_id`: 1

**Proyectos de prueba:**
- `id`: 1, `nombre`: "Asistente Comercial"
- `id`: 2, `nombre`: "botweb"

**Roles definidos en `low_level_permissions`:**
- `id_permissions`: 3 (Editor) - Permisos de edición completos
- `id_permissions`: 4 (Lector) - Solo lectura
- `id_permissions`: 5 (Auditor) - Lectura limitada

## Configuración de Base de Datos

### Crear Usuario de Tests

```sql
-- Usuario de solo lectura para tests
CREATE USER IF NOT EXISTS 'myllm_reader'@'localhost'
IDENTIFIED BY 'Us3r@r3@d3rP@ss';

GRANT SELECT ON myllm_core_db.* TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.* TO 'myllm_reader'@'localhost';

-- Usuario de escritura para tests de modificación
CREATE USER IF NOT EXISTS 'myllm_writer'@'localhost'
IDENTIFIED BY 'Us3r@wr1t3rP@ss';

GRANT ALL PRIVILEGES ON myllm_projects_db.* TO 'myllm_writer'@'localhost';
```

### Verificar Tablas

```sql
-- Verificar que existen las tablas necesarias
SHOW TABLES IN myllm_core_db LIKE 'low_level_permissions';
SHOW TABLES IN myllm_projects_db LIKE 'proyectos_roles';

-- Verificar estructura
DESC myllm_core_db.low_level_permissions;
DESC myllm_projects_db.proyectos_roles;

-- Verificar que hay permisos definidos
SELECT id_permissions, folder_create, file_create, version_create
FROM myllm_core_db.low_level_permissions;
```

## Interpretación de Resultados

### Test Exitoso

```
test_editor_permissions PASSED
✓ Editor tiene permisos correctos: {'folder_create': True, 'file_create': True, ...}
```

### Test Fallido - Falta Rol

```
test_user_has_role_in_project FAILED
AssertionError: Usuario no tiene rol asignado en proyectos_roles
```

**Solución:**
```sql
INSERT INTO myllm_projects_db.proyectos_roles
(id_usuario, id_proyecto, id_organizacion, id_rol, active)
VALUES (1, 1, 1, 3, 1);
```

### Test Fallido - Permisos Incorrectos

```
test_lector_permissions FAILED
AssertionError: Lector NO debe poder crear carpetas
```

**Solución:**
```sql
UPDATE myllm_core_db.low_level_permissions
SET folder_create = 0, folder_delete = 0, file_create = 0
WHERE id_permissions = 4;
```

## Debugging

### Ver Logs Detallados

Los tests incluyen mensajes de logging que pueden ayudar a diagnosticar problemas:

```bash
pytest tests/test_explorador_permissions.py -v -s --log-cli-level=DEBUG
```

### Modo Interactivo

Para debugging paso a paso:

```bash
pytest tests/test_explorador_permissions.py --pdb
```

### Ver Solo Tests que Fallaron

```bash
pytest tests/test_explorador_permissions.py --lf -v
```

## Cobertura de Tests

Para generar reporte de cobertura:

```bash
cd src/apps/5_web_frontend
pytest tests/test_explorador*.py --cov=components.explorador --cov-report=html
```

Ver reporte:
```bash
open htmlcov/index.html
```

## CI/CD

Los tests se ejecutan automáticamente en cada push mediante GitHub Actions.

**Configuración:** `.github/workflows/tests.yml`

**Badge de estado:** (pendiente de implementar)

## Mejoras Futuras

- [ ] Tests de UI con Selenium/Playwright para verificar menús contextuales
- [ ] Tests de rendimiento para carga de permisos
- [ ] Tests de concurrencia (múltiples usuarios)
- [ ] Mock de base de datos para tests unitarios más rápidos
- [ ] Fixtures con datos de prueba más completos
- [ ] Tests de integración con Redis (caché de permisos)

## Contacto

Para reportar problemas con los tests o sugerir mejoras, crear un issue en el repositorio del proyecto.
