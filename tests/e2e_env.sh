#!/bin/bash
# Carga URLs y rutas del entorno activo (silicon/macbook/...) via tests.helpers.
# Usar: source "$(dirname "$0")/e2e_env.sh"

_E2E_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -x "$_E2E_ROOT/.venv_middleware313/bin/python" ]; then
    _E2E_PY="$_E2E_ROOT/.venv_middleware313/bin/python"
else
    _E2E_PY="python3"
fi

eval "$(
    PYTHONPATH="$_E2E_ROOT${PYTHONPATH:+:$PYTHONPATH}" "$_E2E_PY" -c \
        "from tests.helpers import emit_shell_exports; print(emit_shell_exports())"
)"

# En silicon, "default" no resuelve: hay que pasar la ruta de env.yaml.
FMO_BASEPATH="${TEST_STORAGE_EXTERNAL:-default}"

fmo_list() {
    local org_path="$1"
    local prj_path="$2"
    local version_path="$3"
    curl -sS --max-time 15 \
        "${TEST_FMANAGEMENT_URL}/fmo/list?iduser=1&basepath=${FMO_BASEPATH}&orgpath=${org_path}&prjpath=${prj_path}&versionpath=${version_path}&identity_type_id=1"
}

fmo_contains() {
    local listing="$1"
    local name="$2"
    printf '%s' "$listing" | grep -q "$name"
}
