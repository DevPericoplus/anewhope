#!/bin/bash
# Sincroniza hojas de estilo CRT compartidas a assets de cada portal Reflex.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="${ROOT_DIR}/src/2_shared_application/reflex_shared/crt"
APPS=(
  "src/apps/5_web_frontend/assets/crt"
  "src/apps/6_web_backoffice/assets/crt"
  "src/apps/9_laimweb/assets/crt"
)

for target in "${APPS[@]}"; do
  mkdir -p "${ROOT_DIR}/${target}"
  cp "${SRC_DIR}/crt_base.css" "${ROOT_DIR}/${target}/crt_base.css"
  cp "${SRC_DIR}/crt_theme_green.css" "${ROOT_DIR}/${target}/crt_theme_green.css"
  cp "${SRC_DIR}/crt_theme_amber.css" "${ROOT_DIR}/${target}/crt_theme_amber.css"
  echo "✅ CRT CSS sincronizado → ${target}"
done
