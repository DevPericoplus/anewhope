#!/bin/bash
# Entrypoint para ejecutar LAIM Web (9_laimweb) en contenedor.
# Arranca el servidor Reflex del portal (backend 8010 / frontend Vite 3110).
#
# NOTA de arquitectura: el daemon del foro LAIM (API 8766) NO se arranca aquí.
# Igual que en pre, el foro corre junto al backend (acceso a MariaDB laim_core_db
# y storage en /data/backend/laim/forum) y laimweb lo consume vía la URL
# configurada en laim_forum_api_base_url. Este contenedor solo sirve el portal.
#
# En el contenedor las dependencias ya están instaladas por pip (sin venv).
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -d "$ROOT_DIR/src/apps/9_laimweb" ]; then
    ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
fi
APP_DIR="$ROOT_DIR/src/apps/9_laimweb"
export PYTHONPATH="$ROOT_DIR"

mkdir -p "$APP_DIR/logs"

# Persistir reflex.db en el volumen montado (carpeta reflex_db/).
# rxconfig.py usa db_url="sqlite:///reflex.db" (relativo al working dir).
if [ -d "$APP_DIR/reflex_db" ]; then
    if [ -f "$APP_DIR/reflex.db" ] && [ ! -L "$APP_DIR/reflex.db" ]; then
        mv "$APP_DIR/reflex.db" "$APP_DIR/reflex_db/reflex.db" 2>/dev/null || true
    fi
    [ -e "$APP_DIR/reflex_db/reflex.db" ] || touch "$APP_DIR/reflex_db/reflex.db"
    ln -sfn "$APP_DIR/reflex_db/reflex.db" "$APP_DIR/reflex.db"
fi

cd "$APP_DIR"

# laimweb regenera .web/vite.config.js al arrancar (reflex run), perdiendo el
# patch del build. Un vigilante en segundo plano reaplica allowedHosts en
# bucle; Vite observa vite.config.js y recarga en caliente.
(
    while true; do
        if [ -f "$APP_DIR/.web/vite.config.js" ] && ! grep -q allowedHosts "$APP_DIR/.web/vite.config.js"; then
            python "$APP_DIR/patch_vite_config.py" 2>/dev/null || true
        fi
        sleep 5
    done
) &

echo "=========================================="
echo "LAIM Web — backend 8010 / frontend 3110"
echo "Foro consumido via: ${LAIM_FORUM_API_BASE_URL:-(backend)}"
echo "=========================================="
exec reflex run --env dev
