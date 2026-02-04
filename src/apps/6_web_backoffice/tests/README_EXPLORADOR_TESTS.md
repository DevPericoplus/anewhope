# Tests de Explorador: Estados de Versión y Persistencia

## Descripción

Los tests de `test_explorador_version_state.py` verifican que el sistema de estados de versiones funciona correctamente y que los cambios persisten en la base de datos.

## Qué se Verifica

### 1. Persistencia en Base de Datos
- ✅ Los cambios de estado se guardan en la tabla `estado_version`
- ✅ La API devuelve el mismo estado que está en la base de datos
- ✅ Los estados persisten cuando el usuario cambia entre versiones

### 2. Transiciones de Estado (Backoffice)

**Flujo Completo:**
```
Abierta → Bloqueada → Protegida → Final
   ↑          ↓
   └──────────┘ (reversible solo si final_c y final_i = false)
```

#### Tests de Transición:
- `test_transition_abierta_to_bloqueada`: Abierta → Bloqueada
  - Estado: "Bloqueada"
  - protected: `True`
  - final_c/final_i: `False`

- `test_transition_bloqueada_to_abierta`: Bloqueada → Abierta (desbloquear)
  - Estado: "Abierta"
  - protected: `False`

- `test_transition_abierta_to_protegida`: Abierta → Protegida (solicitar entrenamiento)
  - Estado: "Protegida"
  - protected: `True`
  - final_c: `True` (cliente solicitó)
  - final_i: `False` (interno aún no confirmó)

- `test_transition_protegida_to_final`: Protegida → Final (confirmar entrenamiento)
  - Estado: "Final"
  - protected: `True`
  - final_c: `True`
  - final_i: `True` (interno confirmó)

### 3. Flags Individuales

Los tests verifican que cada flag persiste correctamente:

- `test_protected_flag_persistence`: `protected` (True/False)
- `test_final_c_flag_persistence`: `final_c` (activar)
- `test_final_i_flag_persistence`: `final_i` (activar)

### 4. Permisos por Rol

- `test_editor_cannot_change_state`: Editor (identity_type_id=3) NO puede cambiar estados
  - **PENDIENTE**: Implementar validación en middleware

### 5. Cleanup

- `test_cleanup_reset_to_abierta`: Resetea la versión a "Abierta" después de ejecutar todos los tests

## Prerrequisitos

### 1. Instalar Dependencias

```bash
# Activar entorno virtual del backoffice
source /Users/administrator/develop/anewhope/.venv_backoffice313/bin/activate

# Instalar dependencias de testing
pip install pytest pytest-asyncio mariadb requests
```

### 2. Servicios en Ejecución

Los siguientes servicios deben estar corriendo:

```bash
# Terminal 1 - Backend Core (puerto 8003)
cd /Users/administrator/develop/anewhope/src/apps/3_backend
bash run.sh

# Terminal 2 - Broker Backend (puerto 8008)
cd /Users/administrator/develop/anewhope/src/apps/8_service_backend
bash run.sh

# Terminal 3 - Middleware (puerto 8007)
cd /Users/administrator/develop/anewhope/src/apps/7_service_frontend
bash run.sh

# Terminal 4 - MariaDB (puerto 3306)
# Ya debe estar corriendo
mysql.server status
```

### 3. Base de Datos Poblada

Asegúrate de que la base de datos tiene:
- ✅ Tabla `estado_version` creada
- ✅ Usuarios de prueba: `adminone`, `admintwo`, `editorone`
- ✅ Proyecto `botweb` (id=2) con versiones 1 y 2
- ✅ Registros de estado inicial para las versiones

```bash
# Verificar tabla
mysql -u writer_user -pPassWriter2025 mydb -e "DESCRIBE estado_version;"

# Verificar datos
mysql -u writer_user -pPassWriter2025 mydb -e "SELECT * FROM estado_version WHERE id_proyecto=2;"
```

## Ejecutar Tests

### Todos los Tests

```bash
cd /Users/administrator/develop/anewhope/src/apps/6_web_backoffice
pytest tests/test_explorador_version_state.py -v -s
```

### Tests Específicos

```bash
# Solo transiciones
pytest tests/test_explorador_version_state.py -v -s -k "transition"

# Solo persistencia de flags
pytest tests/test_explorador_version_state.py -v -s -k "flag_persistence"

# Solo permisos
pytest tests/test_explorador_version_state.py -v -s -k "cannot_change"
```

### Modo Verbose con Output

```bash
# Ver todos los prints y logs
pytest tests/test_explorador_version_state.py -v -s --tb=short

# Con coverage
pytest tests/test_explorador_version_state.py --cov=components.explorador --cov-report=html
```

## Resultado Esperado

```
tests/test_explorador_version_state.py::test_version_state_exists_in_db PASSED
✓ Estado inicial en DB: Abierta

tests/test_explorador_version_state.py::test_version_state_api_matches_db PASSED
✓ API y DB coinciden: Abierta

tests/test_explorador_version_state.py::test_transition_abierta_to_bloqueada PASSED
✓ Transición Abierta → Bloqueada OK y persistió en DB

tests/test_explorador_version_state.py::test_transition_bloqueada_to_abierta PASSED
✓ Transición Bloqueada → Abierta OK y persistió en DB

tests/test_explorador_version_state.py::test_transition_abierta_to_protegida PASSED
✓ Transición Abierta → Protegida OK y persistió en DB

tests/test_explorador_version_state.py::test_transition_protegida_to_final PASSED
✓ Transición Protegida → Final OK y persistió en DB

tests/test_explorador_version_state.py::test_protected_flag_persistence PASSED
✓ Flag 'protected' persiste correctamente

tests/test_explorador_version_state.py::test_final_c_flag_persistence PASSED
✓ Flag 'final_c' persiste correctamente

tests/test_explorador_version_state.py::test_final_i_flag_persistence PASSED
✓ Flag 'final_i' persiste correctamente

tests/test_explorador_version_state.py::test_editor_cannot_change_state PASSED
⚠ Test de permisos pendiente de implementar en middleware

tests/test_explorador_version_state.py::test_cleanup_reset_to_abierta PASSED
✓ Versión reseteada a estado Abierta

======================== 11 passed in 5.43s =========================
```

## Troubleshooting

### Error: "Connection refused" al conectar a servicios

**Solución**: Verificar que todos los servicios estén corriendo:

```bash
lsof -i :8003  # Backend Core
lsof -i :8007  # Middleware
lsof -i :8008  # Broker Backend
```

### Error: "Access denied" al conectar a MariaDB

**Solución**: Verificar credenciales en `DB_CONFIG` del test:

```python
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "writer_user",
    "password": "PassWriter2025",
    "database": "mydb",
}
```

### Error: "Login failed" para usuarios de prueba

**Solución**: Verificar que los usuarios existen en la base de datos:

```bash
mysql -u writer_user -pPassWriter2025 mydb -e \
  "SELECT user_id, username, identity_type_id, active FROM users WHERE username IN ('adminone', 'admintwo', 'editorone');"
```

### Error: "Estado no persistió en DB"

**Posibles causas**:
1. El middleware no está enviando la petición correctamente
2. El backend tiene un error al guardar
3. El test no está esperando suficiente tiempo (`time.sleep(0.5)`)

**Debugging**:
```bash
# Ver logs del middleware
tail -f /Users/administrator/develop/anewhope/src/apps/7_service_frontend/logs/middleware_activiy.log

# Ver logs del backend
tail -f /Users/administrator/develop/anewhope/src/apps/3_backend/logs/backend_core_activity.log

# Verificar manualmente en DB
mysql -u writer_user -pPassWriter2025 mydb -e \
  "SELECT id_proyecto, id_version, state, protected, final_c, final_i FROM estado_version WHERE id_proyecto=2 AND id_version=2;"
```

## Tests Pendientes de Implementar

### 1. Validación de Permisos en Middleware

Actualmente el test `test_editor_cannot_change_state` pasa pero no valida realmente los permisos porque el middleware no está verificando `identity_type_id`.

**TODO**: Agregar validación en `/Users/administrator/develop/anewhope/src/apps/7_service_frontend/apife.py`:

```python
@app.patch("/proyectos/{project_id}/versiones/{version_id}/estado")
def update_version_state_endpoint(
    session: SessionContext = Depends(get_session_context),
):
    # Validar permisos
    allowed_identity_types = (1, 2, 10)  # SuperAdmin, Admin Org, Agente Admin
    if session.identity_type_id not in allowed_identity_types:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Sin permisos (identity_type_id={session.identity_type_id})",
        )
    # ... resto del código
```

### 2. Tests de UI con Selenium/Playwright

Para verificar que los botones y selectores del explorador funcionan correctamente en el navegador real.

## Integración Continua

Para ejecutar estos tests en CI/CD:

```yaml
# .github/workflows/test_explorador.yml
name: Test Explorador

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      mariadb:
        image: mariadb:10.6
        env:
          MYSQL_ROOT_PASSWORD: root
          MYSQL_DATABASE: mydb
          MYSQL_USER: writer_user
          MYSQL_PASSWORD: PassWriter2025
        ports:
          - 3306:3306

    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: |
          pip install pytest pytest-asyncio mariadb requests

      - name: Start services
        run: |
          # Iniciar backend, middleware, broker en background
          cd src/apps/3_backend && bash run.sh &
          cd src/apps/7_service_frontend && bash run.sh &
          cd src/apps/8_service_backend && bash run.sh &
          sleep 10  # Esperar a que inicien

      - name: Run tests
        run: |
          cd src/apps/6_web_backoffice
          pytest tests/test_explorador_version_state.py -v
```

## Documentación Relacionada

- `/Users/administrator/develop/anewhope/docs/ESTADO_ACTUAL_Y_SIGUIENTES_PASOS.md`
- `/Users/administrator/develop/anewhope/@AGENTS.md` (sección estado_version)
- `/Users/administrator/develop/anewhope/infrastructure/database/ddl_estado_version.sql`
- `/Users/administrator/develop/anewhope/src/apps/6_web_backoffice/components/explorador.py`
