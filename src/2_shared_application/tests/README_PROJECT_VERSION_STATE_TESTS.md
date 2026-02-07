# Tests para Estado de Proyectos (Project Version State)

Este documento describe la suite de tests para el sistema Estado de Proyectos, implementado con arquitectura DDD (Domain-Driven Design).

## Estructura de Tests

```
tests/
├── test_project_version_state_domain.py       # Tests de Domain Layer
├── test_project_version_state_service.py      # Tests de Application Service
├── test_project_version_state_repository.py   # Tests de Repository
└── ../3_backend/tests/
    └── test_project_version_state_api.py      # Tests de integración de API
```

---

## 1. Tests de Domain Layer

**Archivo:** `test_project_version_state_domain.py`

**Objetivo:** Verificar que las entidades de dominio y Value Objects funcionan correctamente.

### Cobertura:
- ✅ Inmutabilidad de Value Objects (`frozen=True`)
- ✅ Métodos de transición de estado retornan nuevos objetos
- ✅ Lógica de negocio en Value Objects
- ✅ Aggregate Root (ProjectVersionState)

### Clases de test:
- `TestProposalPhase` - 6 tests
- `TestTrainingPhase` - 3 tests
- `TestEvaluationPhase` - 4 tests
- `TestGenerationPhase` - 3 tests
- `TestNotificationPhase` - 2 tests
- `TestProjectVersionState` - 3 tests

### Ejemplo de test:

```python
def test_approve_by_client_returns_new_object(self):
    """Verifica que approve_by_client retorna nuevo objeto sin mutar original."""
    phase = ProposalPhase(aceptacion_cliente=False, aceptacion_interna=False)

    approved = phase.approve_by_client(user_id=1)

    # Nuevo objeto modificado
    assert approved.aceptacion_cliente is True
    # Original inmutable
    assert phase.aceptacion_cliente is False
```

### Ejecutar tests:

```bash
# Activar entorno virtual correcto
source .venv_middleware313/bin/activate

# Ejecutar tests de dominio
pytest src/2_shared_application/tests/test_project_version_state_domain.py -v
```

---

## 2. Tests de Application Service

**Archivo:** `test_project_version_state_service.py`

**Objetivo:** Verificar que el Service orquesta correctamente entre dominio y repositorio, y valida permisos.

### Cobertura:
- ✅ Validación de permisos de lectura (`_has_read_permission`)
- ✅ Validación de permisos de escritura (`_has_write_permission`)
- ✅ SuperAdmin bypass de permisos
- ✅ Auditor/Lector bloqueados en escritura
- ✅ Verificación de asignaciones activas en DB
- ✅ Operaciones de todas las fases (Proposal, Training, Evaluation, etc.)
- ✅ Manejo de errores (PermissionDeniedError, NotFoundError)

### Clases de test:
- `TestReadPermissions` - 3 tests
- `TestWritePermissions` - 5 tests
- `TestProposalPhaseOperations` - 3 tests
- `TestTrainingPhaseOperations` - 1 test
- `TestEvaluationPhaseOperations` - 1 test
- `TestErrorHandling` - 2 tests

### Ejemplo de test:

```python
def test_user_without_assignment_cannot_read(
    self, mock_repository, mock_db_engine, sample_project_version_state
):
    """Usuario sin asignación NO puede leer estado."""
    mock_repository.get_by_id.return_value = sample_project_version_state

    # Mock de consulta SQL que retorna 0 asignaciones
    mock_conn = MagicMock()
    mock_result_org = Mock()
    mock_result_org.count = 0  # Sin asignación

    with pytest.raises(PermissionDeniedError):
        service.get_state_by_id(state_id=1, requesting_user_id=10, ...)
```

### Ejecutar tests:

```bash
# Activar entorno virtual correcto
source .venv_middleware313/bin/activate

# Ejecutar tests de Service
pytest src/2_shared_application/tests/test_project_version_state_service.py -v

# Ver output detallado
pytest src/2_shared_application/tests/test_project_version_state_service.py -v -s
```

---

## 3. Tests de Repository

**Archivo:** `test_project_version_state_repository.py`

**Objetivo:** Verificar conversión correcta entre rows SQL y entidades de dominio.

### Cobertura:
- ✅ Conversión `_row_to_entity` (SQL → Entidad)
- ✅ Conversión implícita en `save` (Entidad → SQL)
- ✅ Operación `get_by_id`
- ✅ Operación `get_by_version`
- ✅ Operación `save` (UPDATE)
- ✅ Round-trip (Entidad → SQL → Entidad preserva datos)

### Clases de test:
- `TestRowToEntity` - 7 tests
- `TestGetById` - 2 tests
- `TestSave` - 5 tests
- `TestGetByVersion` - 2 tests
- `TestRoundTrip` - 1 test

### Ejemplo de test:

```python
def test_row_to_entity_converts_all_fields(self, mock_engine, mock_sql_row):
    """Verifica que _row_to_entity convierte todos los campos correctamente."""
    repository = MariaDBProjectVersionStateRepository(mock_engine)

    entity = repository._row_to_entity(mock_sql_row)

    assert entity.id == 1
    assert isinstance(entity.proposal, ProposalPhase)
    assert isinstance(entity.training, TrainingPhase)
    # ... verificar todos los Value Objects
```

### Ejecutar tests:

```bash
# Activar entorno virtual correcto
source .venv_middleware313/bin/activate

# Ejecutar tests de Repository
pytest src/2_shared_application/tests/test_project_version_state_repository.py -v
```

---

## 4. Tests de Integración API

**Archivo:** `src/apps/3_backend/tests/test_project_version_state_api.py`

**Objetivo:** Verificar que los endpoints de la API funcionan correctamente con autenticación y permisos.

### Cobertura:
- ✅ Endpoint GET `/project-version-states/{state_id}`
- ✅ Endpoint PATCH `/project-version-states/{state_id}/proposal`
- ✅ Endpoint PATCH `/project-version-states/{state_id}/evaluation`
- ✅ Respuestas HTTP correctas (200, 403, 400, 422)
- ✅ Validación de payloads con Pydantic
- ✅ Flujo completo de autenticación
- ✅ Permisos por rol (SuperAdmin, Editor, Auditor, Lector)

### Clases de test:
- `TestGetProjectVersionState` - 2 tests
- `TestUpdateProposalPhase` - 4 tests
- `TestUpdateEvaluationPhase` - 2 tests
- `TestPayloadValidation` - 2 tests
- `TestFullFlow` - 1 test
- `TestErrorHandling` - 1 test

### Ejemplo de test:

```python
def test_auditor_cannot_update_proposal(
    self, mock_update, test_client, auditor_headers
):
    """Auditor NO puede actualizar (solo lectura)."""
    mock_update.side_effect = BackendCorePermissionError(...)

    response = test_client.patch(
        "/project-version-states/1/proposal",
        json={"aceptacion_cliente": True, ...},
        params={"user_id": 20, "identity_type_id": 4},
    )

    assert response.status_code == 403
```

### Ejecutar tests:

```bash
# Activar entorno virtual correcto
source .venv_middleware313/bin/activate

# Ejecutar tests de API
pytest src/apps/3_backend/tests/test_project_version_state_api.py -v
```

---

## Ejecutar Todos los Tests

### Opción 1: Script completo (full_test.sh)

El proyecto incluye un script que ejecuta todos los tests con los entornos virtuales correctos:

```bash
./full_test.sh
```

### Opción 2: Solo tests de Estado de Proyectos

```bash
# Activar entorno correcto
source .venv_middleware313/bin/activate

# Ejecutar todos los tests de Estado de Proyectos
pytest \
  src/2_shared_application/tests/test_project_version_state_domain.py \
  src/2_shared_application/tests/test_project_version_state_service.py \
  src/2_shared_application/tests/test_project_version_state_repository.py \
  src/apps/3_backend/tests/test_project_version_state_api.py \
  -v
```

### Opción 3: Con cobertura

```bash
# Ejecutar con reporte de cobertura
pytest \
  src/2_shared_application/tests/test_project_version_state_*.py \
  src/apps/3_backend/tests/test_project_version_state_api.py \
  --cov=src/1_shared_domain/entities/project_version_state \
  --cov=src/2_shared_application/services/project_version_state_service \
  --cov=src/2_shared_application/adapters/mariadb_project_version_state_repository \
  --cov-report=html
```

---

## Matriz de Permisos Testeados

| Rol | identity_type_id | Lectura | Escritura | Tests |
|-----|------------------|---------|-----------|-------|
| **SuperAdmin** | 1 | ✅ Sin verificar asignación | ✅ Sin verificar asignación | 4 tests |
| **Admin** | 2 | ✅ Con asignación activa | ✅ Con asignación activa | 2 tests |
| **Editor** | 3 | ✅ Con asignación activa | ✅ Con asignación activa | 3 tests |
| **Auditor** | 4 | ✅ Con asignación activa | ❌ Bloqueado | 3 tests |
| **Lector** | 5 | ✅ Con asignación activa | ❌ Bloqueado | 2 tests |

---

## Resultados Esperados

### Total de Tests: ~65 tests

- **Domain Layer:** 21 tests
- **Application Service:** 15 tests
- **Repository:** 17 tests
- **API Integration:** 12 tests

### Tiempo de Ejecución Estimado

- Domain: ~1-2 segundos
- Service: ~2-3 segundos
- Repository: ~2-3 segundos
- API: ~3-5 segundos

**Total:** ~10-15 segundos

---

## Troubleshooting

### Error: ModuleNotFoundError

**Problema:** `ModuleNotFoundError: No module named 'src.apps.backend'`

**Solución:** Asegurarse de estar en el entorno virtual correcto:
```bash
source .venv_middleware313/bin/activate
```

### Error: STORAGE_MODE no configurado

**Problema:** Tests intentan conectar a MariaDB real

**Solución:** Los tests ya configuran `os.environ["STORAGE_MODE"] = "mock"` automáticamente.

### Error: Import de entidades de dominio

**Problema:** No encuentra `project_version_state.py`

**Solución:** Los tests usan carga dinámica de path. Verificar que el archivo existe:
```bash
ls src/1_shared_domain/entities/project_version_state.py
```

---

## Contribuir Nuevos Tests

### Estructura recomendada:

1. **Crear clase de test** por funcionalidad
2. **Usar fixtures** para setup común
3. **Nombrar tests descriptivamente:** `test_<what>_<expected_behavior>`
4. **Incluir docstrings** en cada test
5. **Usar mocks** para aislar dependencias

### Ejemplo:

```python
class TestNewFeature:
    """Tests para nueva funcionalidad X."""

    def test_feature_works_correctly(self, mock_dependency):
        """Verifica que la funcionalidad X funciona correctamente."""
        # Arrange
        setup = ...

        # Act
        result = ...

        # Assert
        assert result == expected
```

---

## Referencias

- **AGENTS.md** - Sección 24: "Estado de Proyectos - Domain-Driven Design Architecture"
- **README.md** - Sección: "Estado de Proyectos (Project Status Management)"
- **Código fuente:**
  - Domain: `src/1_shared_domain/entities/project_version_state.py`
  - Service: `src/2_shared_application/services/project_version_state_service.py`
  - Repository: `src/2_shared_application/adapters/mariadb_project_version_state_repository.py`
  - API: `src/apps/3_backend/apicore.py` (endpoints), `src/apps/3_backend/routercore.py` (router)

---

**Última actualización:** 2026-02-06
**Versión:** 1.0
**Autor:** Claude Sonnet 4.5
