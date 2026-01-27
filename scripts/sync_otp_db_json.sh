#!/bin/bash
# Script para sincronizar OTP entre MariaDB y users.json
# Este script lee el OTP de MariaDB y actualiza el JSON

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USERS_JSON="$ROOT_DIR/src/2_shared_application/moks/users.json"

echo "=== Sincronización OTP: MariaDB → JSON ==="
echo ""

# Verificar que el archivo JSON existe
if [ ! -f "$USERS_JSON" ]; then
    echo "ERROR: No se encontró $USERS_JSON"
    exit 1
fi

# Leer credenciales de MariaDB
MYSQL_PATH="/usr/local/opt/mariadb@10.6/bin/mariadb"
if [ ! -x "$MYSQL_PATH" ]; then
    echo "ERROR: No se encontró mariadb en $MYSQL_PATH"
    exit 1
fi

DB_NAME="myllm_core_db"
DB_USER="myllm_reader"
DB_PASS="Us3r@R3@derP@ss"

echo "Leyendo OTPs desde MariaDB (usando view_users_otp)..."
echo ""

# Obtener users y OTPs de la vista (más limpio y rápido)
DB_USERS=$($MYSQL_PATH -u"$DB_USER" -p"$DB_PASS" --database="$DB_NAME" -N -e "SELECT user_id, user_name, user_otp FROM view_users_otp;")

if [ -z "$DB_USERS" ]; then
    echo "ERROR: No se pudieron leer usuarios de MariaDB"
    exit 1
fi

echo "Usuarios en MariaDB:"
echo "$DB_USERS" | while IFS=$'\t' read -r uid uname uotp; do
    echo "  user_id=$uid, user_name=$uname, otp=$uotp"
done
echo ""

# Hacer backup del JSON actual
cp "$USERS_JSON" "$USERS_JSON.backup.$(date +%Y%m%d_%H%M%S)"
echo "Backup creado: $USERS_JSON.backup.*"

# Actualizar el JSON con los OTPs de la BD usando Python
python3 << PYEOF
import json
import subprocess

users_json_path = "$USERS_JSON"
mysql_path = "$MYSQL_PATH"
db_name = "$DB_NAME"
db_user = "$DB_USER"
db_pass = "$DB_PASS"

# Leer usuarios actuales del JSON
with open(users_json_path, 'r', encoding='utf-8') as f:
    users = json.load(f)

# Obtener OTPs de MariaDB usando la vista
result = subprocess.run(
    [mysql_path, f"-u{db_user}", f"-p{db_pass}", "--database", db_name, "-N", "-e",
     "SELECT user_id, user_otp FROM view_users_otp;"],
    capture_output=True, text=True
)

if result.returncode != 0:
    print(f"Error leyendo de MariaDB: {result.stderr}")
    exit(1)

# Parsear resultados
db_otps = {}
for line in result.stdout.strip().split('\n'):
    if line:
        parts = line.split('\t')
        if len(parts) >= 2:
            db_otps[int(parts[0])] = parts[1]

# Actualizar usuarios con OTPs de la BD
updated = 0
for user in users:
    user_id = user.get('user_id')
    if user_id in db_otps:
        old_otp = user.get('user_otp', '')
        new_otp = db_otps[user_id]
        if old_otp != new_otp:
            print(f"Actualizando user_id={user_id}: otp '{old_otp}' -> '{new_otp}'")
            user['user_otp'] = new_otp
            updated += 1

# Guardar JSON actualizado
with open(users_json_path, 'w', encoding='utf-8') as f:
    json.dump(users, f, ensure_ascii=False, indent=2)

print(f"\nActualizados {updated} usuarios en {users_json_path}")
PYEOF

echo ""
echo "=== Sincronización completada ==="
