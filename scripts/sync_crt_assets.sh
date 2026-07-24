#!/bin/bash
# Sincroniza hojas de estilo CRT compartidas a assets y a .web/public de cada portal Reflex.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="${ROOT_DIR}/src/2_shared_application/reflex_shared/crt"
APPS=(
  "src/apps/5_web_frontend"
  "src/apps/6_web_backoffice"
  "src/apps/9_laimweb"
)

CRT_FILES=(
  "crt_base.css"
  "crt_theme_green.css"
  "crt_theme_amber.css"
)

for app_rel in "${APPS[@]}"; do
  assets_dir="${ROOT_DIR}/${app_rel}/assets/crt"
  public_dir="${ROOT_DIR}/${app_rel}/.web/public/crt"

  mkdir -p "${assets_dir}"
  for css_file in "${CRT_FILES[@]}"; do
    cp "${SRC_DIR}/${css_file}" "${assets_dir}/${css_file}"
  done
  echo "✅ CRT CSS sincronizado → ${app_rel}/assets/crt"

  if [ -d "${ROOT_DIR}/${app_rel}/.web/public" ]; then
    mkdir -p "${public_dir}"
    for css_file in "${CRT_FILES[@]}"; do
      cp "${assets_dir}/${css_file}" "${public_dir}/${css_file}"
    done
    echo "✅ CRT CSS publicado → ${app_rel}/.web/public/crt"
  fi
done
