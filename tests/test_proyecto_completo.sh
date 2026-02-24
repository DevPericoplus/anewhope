#!/bin/bash

echo "=========================================="
echo "Test Completo: Proyecto con Propuesta Cliente"
echo "=========================================="
echo ""
echo "PREREQUISITOS:"
echo "- Backend Core debe estar corriendo en puerto 8003"
echo "- Middleware debe estar corriendo en puerto 8007"
echo "- Base de datos MariaDB operativa"
echo ""
read -p "¿Continuar con el test? (s/n): " respuesta

if [ "$respuesta" != "s" ]; then
    echo "Test cancelado"
    exit 0
fi

MARIADB_PATH="/usr/local/opt/mariadb@10.6/bin/mariadb"

echo ""
echo "=========================================="
echo "PASO 1: Login y obtención de tokens"
echo "=========================================="

LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8007/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "user_name": "adminone",
    "password": "Admin123!",
    "organization_id": 1
  }')

ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)

if [ -z "$ACCESS_TOKEN" ]; then
    echo "❌ Error: No se pudo obtener el token de acceso"
    echo "Response: $LOGIN_RESPONSE"
    exit 1
fi

SESSION_TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('session_token', ''))" 2>/dev/null)

echo "✅ Tokens obtenidos correctamente"

echo ""
echo "=========================================="
echo "PASO 2: Crear proyecto de prueba via API"
echo "=========================================="

PROJECT_NAME="Test Flujo Completo $(date +%s)"
CREATE_RESPONSE=$(curl -s -X POST http://localhost:8007/projects \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "X-Session-Token: $SESSION_TOKEN" \
  -d "{
    \"nombre\": \"$PROJECT_NAME\",
    \"descripcion\": \"Test completo de flujo Propuesta Cliente\",
    \"id_organizacion\": 1,
    \"id_flujo\": 1,
    \"active\": true
  }")

echo "Response: $CREATE_RESPONSE"

PROJECT_ID=$(echo $CREATE_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('project_id', 0))" 2>/dev/null)

if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" -eq "0" ]; then
    echo "❌ Error: No se pudo crear el proyecto"
    exit 1
fi

echo "✅ Proyecto creado con ID: $PROJECT_ID"

sleep 2  # Dar tiempo a que se cree la versión

echo ""
echo "=========================================="
echo "PASO 3: Verificar proyecto en BD"
echo "=========================================="

echo "Consultando tabla proyectos..."
$MARIADB_PATH -u myllm_admin -p'Us3r@dminP@ss' --database=myllm_projects_db -e \
  "SELECT id, nombre, id_flujo, active FROM proyectos WHERE id = $PROJECT_ID;"

ID_FLUJO=$($MARIADB_PATH -u myllm_admin -p'Us3r@dminP@ss' --database=myllm_projects_db -N -B -e \
  "SELECT id_flujo FROM proyectos WHERE id = $PROJECT_ID;")

if [ "$ID_FLUJO" != "1" ]; then
    echo "❌ ERROR: id_flujo NO es 1"
    exit 1
fi

echo "✅ id_flujo = 1"

echo ""
echo "=========================================="
echo "PASO 4: Verificar versión creada"
echo "=========================================="

VERSION_COUNT=$($MARIADB_PATH -u myllm_admin -p'Us3r@dminP@ss' --database=myllm_projects_db -N -B -e \
  "SELECT COUNT(*) FROM versiones WHERE id_proyecto = $PROJECT_ID;")

echo "Número de versiones: $VERSION_COUNT"

if [ "$VERSION_COUNT" -eq "0" ]; then
    echo "❌ ERROR: No se creó la versión automáticamente"
    exit 1
fi

VERSION_ID=$($MARIADB_PATH -u myllm_admin -p'Us3r@dminP@ss' --database=myllm_projects_db -N -B -e \
  "SELECT id FROM versiones WHERE id_proyecto = $PROJECT_ID ORDER BY id LIMIT 1;")

echo "✅ Versión creada con ID: $VERSION_ID"

echo ""
echo "=========================================="
echo "PASO 5: Verificar estado con propuesta_cliente"
echo "=========================================="

echo "Consultando tabla estado..."
$MARIADB_PATH -u myllm_admin -p'Us3r@dminP@ss' --database=myllm_projects_db -e \
  "SELECT id_proyecto, id_version, propuesta_cliente, revision_interna, entrenamiento_inicial 
   FROM estado WHERE id_proyecto = $PROJECT_ID AND id_version = $VERSION_ID;"

PROPUESTA_CLIENTE=$($MARIADB_PATH -u myllm_admin -p'Us3r@dminP@ss' --database=myllm_projects_db -N -B -e \
  "SELECT propuesta_cliente FROM estado WHERE id_proyecto = $PROJECT_ID AND id_version = $VERSION_ID;")

echo ""
if [ "$PROPUESTA_CLIENTE" != "1" ]; then
    echo "❌ ERROR: propuesta_cliente NO es 1, es: $PROPUESTA_CLIENTE"
    echo ""
    echo "El backend NO está estableciendo propuesta_cliente=1 correctamente."
    echo "Verifica que el backend se haya reiniciado con los cambios aplicados."
    exit 1
fi

echo "✅ propuesta_cliente = 1 (CORRECTO!)"

echo ""
echo "=========================================="
echo "RESUMEN FINAL"
echo "=========================================="
echo "✅ Proyecto creado: $PROJECT_NAME (ID: $PROJECT_ID)"
echo "✅ Campo id_flujo = 1 en tabla proyectos"
echo "✅ Versión v001 creada automáticamente (ID: $VERSION_ID)"
echo "✅ Campo propuesta_cliente = 1 en tabla estado"
echo ""
echo "🎉 TEST EXITOSO: El flujo completo funciona correctamente"
echo "   Los proyectos se crean con el estado 'Propuesta Cliente' activo"
echo "=========================================="

