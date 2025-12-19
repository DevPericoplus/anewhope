"""Tests para verificar el cifrado y descifrado de contraseñas."""
import pytest
import sys
import importlib.util
import json
from pathlib import Path

# Añadir el directorio raíz del proyecto al path para imports relativos
# El archivo está en: src/apps/5_web_frontend/tests/test_encrypt_password.py
# Necesitamos llegar a: src/2_shared_application/security/custom_cipher_lib.py
test_file_path = Path(__file__)
project_root = test_file_path.parent.parent.parent.parent  # Desde tests/ hasta src/
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Cargar dinámicamente custom_cipher_lib.py
common_security_path = project_root / "2_shared_application" / "security" / "custom_cipher_lib.py"
spec = importlib.util.spec_from_file_location("custom_cipher_lib", common_security_path)
if spec and spec.loader:
    cipher_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cipher_module)
else:
    raise ImportError(f"No se pudo cargar el módulo custom_cipher_lib desde {common_security_path}")

# Ruta al archivo users.json
_users_json_path = project_root / "2_shared_application" / "moks" / "users.json"


@pytest.fixture(scope="session", autouse=True)
def show_password_summary():
    """
    Fixture que se ejecuta al final de todos los tests para mostrar un resumen
    de las contraseñas cifradas y sin cifrar en users.json.
    """
    yield  # Ejecutar todos los tests primero
    
    # Código que se ejecuta después de todos los tests
    if not _users_json_path.exists():
        print("\n" + "=" * 60)
        print("RESUMEN DE CONTRASEÑAS EN users.json")
        print("=" * 60)
        print(f"⚠️  El archivo users.json no existe en: {_users_json_path}")
        return

    try:
        # Cargar la clave Fernet para descifrar
        fernet_key_path = common_security_path.parent / "basesecuritypass.json"
        fernet_instance = cipher_module.load_fernet_key_from_file(fernet_key_path)

        # Leer el archivo users.json
        with open(_users_json_path, "r", encoding="utf-8") as f:
            users = json.load(f)

        print("\n" + "=" * 60)
        print("RESUMEN DE CONTRASEÑAS EN users.json")
        print("=" * 60)

        encrypted_passwords = []
        unencrypted_passwords = []
        decryption_errors = []

        for user in users:
            user_id = user.get("user_id", "N/A")
            user_name = user.get("user_name", "N/A")
            password = user.get("user_password", "")

            if not password:
                continue

            if password.startswith("gAAAAAB"):
                # Contraseña cifrada - intentar descifrar
                try:
                    encrypted_bytes = password.encode("utf-8")
                    decrypted_bytes, _ = cipher_module.decrypt_value(fernet_instance, encrypted_bytes)
                    if decrypted_bytes:
                        decrypted_password = decrypted_bytes.decode("utf-8")
                        encrypted_passwords.append({
                            "user_id": user_id,
                            "user_name": user_name,
                            "encrypted": password,
                            "decrypted": decrypted_password,
                        })
                    else:
                        decryption_errors.append({
                            "user_id": user_id,
                            "user_name": user_name,
                            "encrypted": password,
                            "error": "No se pudo descifrar",
                        })
                except Exception as e:
                    decryption_errors.append({
                        "user_id": user_id,
                        "user_name": user_name,
                        "encrypted": password,
                        "error": str(e),
                    })
            else:
                # Contraseña sin cifrar
                unencrypted_passwords.append({
                    "user_id": user_id,
                    "user_name": user_name,
                    "password": password,
                })

        # Mostrar resumen
        print(f"\nTotal de usuarios: {len(users)}")
        print(f"Contraseñas cifradas: {len(encrypted_passwords)}")
        print(f"Contraseñas sin cifrar: {len(unencrypted_passwords)}")
        if decryption_errors:
            print(f"Errores al descifrar: {len(decryption_errors)}")

        # Mostrar contraseñas cifradas
        if encrypted_passwords:
            print("\n" + "-" * 60)
            print("CONTRASEÑAS CIFRADAS:")
            print("-" * 60)
            for item in encrypted_passwords:
                print(f"\n  Usuario ID {item['user_id']} ({item['user_name']}):")
                print(f"    Cifrada: {item['encrypted'][:50]}... (longitud: {len(item['encrypted'])})")
                print(f"    Descifrada: {item['decrypted']}")

        # Mostrar contraseñas sin cifrar
        if unencrypted_passwords:
            print("\n" + "-" * 60)
            print("⚠️  CONTRASEÑAS SIN CIFRAR:")
            print("-" * 60)
            for item in unencrypted_passwords:
                print(f"\n  Usuario ID {item['user_id']} ({item['user_name']}):")
                print(f"    Contraseña: {item['password']}")

        # Mostrar errores de descifrado
        if decryption_errors:
            print("\n" + "-" * 60)
            print("❌ ERRORES AL DESCIFRAR:")
            print("-" * 60)
            for item in decryption_errors:
                print(f"\n  Usuario ID {item['user_id']} ({item['user_name']}):")
                print(f"    Error: {item['error']}")
                print(f"    Valor cifrado: {item['encrypted'][:50]}...")

        print("\n" + "=" * 60)

    except Exception as e:
        print("\n" + "=" * 60)
        print("RESUMEN DE CONTRASEÑAS EN users.json")
        print("=" * 60)
        print(f"❌ Error al generar el resumen: {e}")
        import traceback
        traceback.print_exc()


@pytest.fixture
def fernet_instance():
    """
    Fixture que carga la instancia Fernet desde el archivo de configuración.
    """
    fernet_key_path = common_security_path.parent / "basesecuritypass.json"
    return cipher_module.load_fernet_key_from_file(fernet_key_path)


def test_encrypt_password(fernet_instance):
    """
    Test que verifica que una contraseña sin cifrar se cifra correctamente.
    
    Usa el valor de prueba "This@2026" y verifica que se cifra correctamente.
    """
    plain_password = "This@2026"
    
    # Cifrar la contraseña
    encrypted_bytes = cipher_module.encrypt_value(fernet_instance, plain_password)
    encrypted_string = encrypted_bytes.decode('utf-8')
    
    # Verificar que el valor cifrado no está vacío
    assert encrypted_string, "El valor cifrado no debe estar vacío"
    
    # Verificar que el valor cifrado es diferente del original
    assert encrypted_string != plain_password, "El valor cifrado debe ser diferente del original"
    
    # Verificar que el valor cifrado tiene el formato correcto (base64)
    assert encrypted_string.startswith('gAAAAAB'), "El valor cifrado debe empezar con el prefijo de Fernet"
    
    print("\n✅ Contraseña cifrada exitosamente")
    print(f"   Original: {plain_password}")
    print(f"   Cifrado: {encrypted_string[:50]}... (longitud: {len(encrypted_string)})")


def test_decrypt_password(fernet_instance):
    """
    Test que verifica que una contraseña cifrada se descifra correctamente.
    
    Usa el valor cifrado conocido y verifica que se descifra a "This@2026".
    """
    encrypted_password = "gAAAAABpRW_6FWIIa-dJz2NzZKTgoUsAjwjda42E5VwnMIvWCbDIfIptmCwEAfeFqm58gU4JMMDZuHpdSpwv4HnmVSq2f6yldQ=="
    expected_password = "This@2026"
    
    # Convertir el string cifrado a bytes
    encrypted_bytes = encrypted_password.encode('utf-8')
    
    # Descifrar la contraseña
    decrypted_bytes, _ = cipher_module.decrypt_value(fernet_instance, encrypted_bytes)
    
    # Verificar que se descifró correctamente
    assert decrypted_bytes, "El valor descifrado no debe estar vacío"
    
    # Convertir bytes a string
    decrypted_password = decrypted_bytes.decode('utf-8')
    
    # Verificar que el valor descifrado coincide con el esperado
    assert decrypted_password == expected_password, f"El valor descifrado '{decrypted_password}' no coincide con el esperado '{expected_password}'"
    
    print("\n✅ Contraseña descifrada exitosamente")
    print(f"   Cifrado: {encrypted_password[:50]}...")
    print(f"   Descifrado: {decrypted_password}")


def test_encrypt_decrypt_reversible(fernet_instance):
    """
    Test que verifica que el proceso de cifrado y descifrado es reversible.
    
    Cifra una contraseña y luego la descifra, verificando que se obtiene el valor original.
    """
    original_password = "This@2026"
    
    # Paso 1: Cifrar la contraseña
    encrypted_bytes = cipher_module.encrypt_value(fernet_instance, original_password)
    encrypted_string = encrypted_bytes.decode('utf-8')
    
    # Verificar que se cifró
    assert encrypted_string, "El valor cifrado no debe estar vacío"
    assert encrypted_string != original_password, "El valor cifrado debe ser diferente del original"
    
    # Paso 2: Descifrar la contraseña
    encrypted_bytes_back = encrypted_string.encode('utf-8')
    decrypted_bytes, _ = cipher_module.decrypt_value(fernet_instance, encrypted_bytes_back)
    
    # Verificar que se descifró
    assert decrypted_bytes, "El valor descifrado no debe estar vacío"
    
    # Paso 3: Verificar que el valor descifrado coincide con el original
    decrypted_password = decrypted_bytes.decode('utf-8')
    assert decrypted_password == original_password, f"El proceso no es reversible. Original: '{original_password}', Descifrado: '{decrypted_password}'"
    
    print("\n✅ Proceso reversible verificado")
    print(f"   Original: {original_password}")
    print(f"   Cifrado: {encrypted_string[:50]}...")
    print(f"   Descifrado: {decrypted_password}")


def test_encrypt_decrypt_known_values(fernet_instance):
    """
    Test que verifica el cifrado y descifrado con valores conocidos.
    
    Verifica que "This@2026" se cifra y descifra correctamente usando el valor
    cifrado conocido del archivo users.json.
    """
    plain_password = "This@2026"
    known_encrypted = "gAAAAABpRW_6FWIIa-dJz2NzZKTgoUsAjwjda42E5VwnMIvWCbDIfIptmCwEAfeFqm58gU4JMMDZuHpdSpwv4HnmVSq2f6yldQ=="
    
    # Test 1: Cifrar "This@2026" y verificar que el resultado es válido
    encrypted_bytes = cipher_module.encrypt_value(fernet_instance, plain_password)
    encrypted_string = encrypted_bytes.decode('utf-8')
    
    assert encrypted_string, "El valor cifrado no debe estar vacío"
    assert len(encrypted_string) > 0, "El valor cifrado debe tener contenido"
    
    # Test 2: Descifrar el valor conocido y verificar que es "This@2026"
    known_encrypted_bytes = known_encrypted.encode('utf-8')
    decrypted_bytes, _ = cipher_module.decrypt_value(fernet_instance, known_encrypted_bytes)
    
    assert decrypted_bytes, "El valor descifrado no debe estar vacío"
    decrypted_password = decrypted_bytes.decode('utf-8')
    assert decrypted_password == plain_password, f"El valor conocido no se descifra correctamente. Esperado: '{plain_password}', Obtenido: '{decrypted_password}'"
    
    # Test 3: Verificar que el valor cifrado generado también se puede descifrar
    encrypted_bytes_generated = encrypted_string.encode('utf-8')
    decrypted_bytes_generated, _ = cipher_module.decrypt_value(fernet_instance, encrypted_bytes_generated)
    decrypted_password_generated = decrypted_bytes_generated.decode('utf-8')
    
    assert decrypted_password_generated == plain_password, f"El valor cifrado generado no se descifra correctamente. Esperado: '{plain_password}', Obtenido: '{decrypted_password_generated}'"
    
    print("\n✅ Valores conocidos verificados")
    print(f"   Contraseña original: {plain_password}")
    print(f"   Valor cifrado conocido (longitud): {len(known_encrypted)} caracteres")
    print(f"   Valor cifrado generado (longitud): {len(encrypted_string)} caracteres")
    print(f"   Ambos valores se descifran correctamente a: {plain_password}")


def test_password_encryption_integration(fernet_instance):
    """
    Test de integración que simula el proceso completo de cifrado de contraseña
    como se hace en user_creation.py.
    """
    # Simular el proceso de cifrado como en user_creation.py
    user_password = "This@2026"
    
    # Paso 1: Cifrar la contraseña (como en user_creation.py línea 935-937)
    encrypted_password_bytes = cipher_module.encrypt_value(fernet_instance, user_password)
    encrypted_password = encrypted_password_bytes.decode('utf-8')
    
    # Verificar que el valor cifrado es un string válido
    assert isinstance(encrypted_password, str), "El valor cifrado debe ser un string"
    assert len(encrypted_password) > 0, "El valor cifrado no debe estar vacío"
    assert encrypted_password.startswith('gAAAAAB'), "El valor cifrado debe tener el formato correcto de Fernet"
    
    # Paso 2: Simular que se guarda en el objeto User (la contraseña ya está cifrada)
    # En el código real, esto se hace en user_creation.py línea 951: password=encrypted_password
    
    # Paso 3: Simular la conversión a diccionario (como en api_client.py línea 76)
    # user_password ya está cifrada en el objeto User, así que se copia directamente
    user_dict_password = encrypted_password
    
    # Verificar que el valor en el diccionario es el mismo que el cifrado
    assert user_dict_password == encrypted_password, "El valor en el diccionario debe ser el mismo que el cifrado"
    
    # Paso 4: Verificar que el valor se puede descifrar correctamente
    encrypted_bytes_back = user_dict_password.encode('utf-8')
    decrypted_bytes, _ = cipher_module.decrypt_value(fernet_instance, encrypted_bytes_back)
    decrypted_password = decrypted_bytes.decode('utf-8')
    
    # Verificar que el valor descifrado coincide con el original
    assert decrypted_password == user_password, f"El proceso de integración falló. Original: '{user_password}', Descifrado: '{decrypted_password}'"
    
    print("\n✅ Test de integración exitoso")
    print(f"   Contraseña original: {user_password}")
    print(f"   Contraseña cifrada (longitud): {len(encrypted_password)} caracteres")
    print(f"   Contraseña en diccionario: {user_dict_password[:50]}...")
    print(f"   Contraseña descifrada: {decrypted_password}")
    print("   ✅ El proceso completo funciona correctamente")



