import os
import base64
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Initialization of variables
datos_descifrados = None
ciphervalue = None
unciphervalue = None
secure_value_encrypted = None
secure_value_decrypted = None
fernet_key = None
fernet_value = None
fernet_value_decoded = None
fernet_value_decoded_decoded = None
insecure_values = None
unencripted_value = None
custom_encrypt_key = None

def basic_check_access(basic_string_for_checks):
    if basic_string_for_checks == "This@2025":
        return True
    else:
        return False


def custom_encrypt(global_shared_key_raw, insecure_value):
    clear_value = insecure_value
    internalinsecure_values = insecure_value
    internal_global_shared_key_raw = global_shared_key_raw

    """Create a Fernet cipher from a raw key string."""
    salt = b'static_salt_2025'  # In production, use a random salt
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000
    )
    # Initilize the Fernet key
    fernet_key_derivative_in_bytes = kdf.derive(internal_global_shared_key_raw.encode())
    fernet_key = base64.urlsafe_b64encode(fernet_key_derivative_in_bytes)


    fernet_to_use = Fernet(fernet_key)
    print(f"   Clave Fernet (Base64) generada: {fernet_key.decode()[:10]}...")
    print("--------------------------------") 

    # IA proposal
#    key = base64.urlsafe_b64encode(kdf.derive(internal_global_shared_key_raw.encode()))
#    key_decoded = base64.urlsafe_b64encode(kdf.derive(internal_global_shared_key_raw.decode()))   
#    key_derive_in_bytes = kdf.derive(internal_global_shared_key_raw.encode())
#    fernet_key_base64 = base64.urlsafe_b64encode(key)
    # initialize fernet object
#    fernet_base_64 = Fernet(fernet_key_base64)
#    print(f"key (Base64) generada: {key}")
#    print(f"key_decoded (Base64) generada: {key_decoded}")
#    print(f"fernet_key in bytes: {key_derive_in_bytes}")
#    print(f"fernet_key in Base64 decode: {fernet_key_base64.decode()[:10]}...")

    # Cipher the value
    print("\n1. Cifrando la cadena...")
    value_to_cipher = clear_value.encode()
    print(f"   Value of value_to_cipher: {value_to_cipher}")
    print(f"   secure_value_encrypted: {value_to_cipher}")
    secure_value_encrypted = value_to_cipher


    #Cipher and store in cipher_value_encrypted
    cipher_value_encrypted = fernet_to_use.encrypt(value_to_cipher)
    print(f"   Fernet_key_to_use: {fernet_to_use}")
    print(f"   Value to use is: {value_to_cipher}")
    print(f"   cipher_value_encrypted: {cipher_value_encrypted}")
    # IA proposal
    print("\n2. Descifrando la cadena...")
    print(f"   Valor Cifrado decodificado (cipher_value_encrypted): {cipher_value_encrypted.decode()[:40]}...")

    # decryption process   
    try:
        insecure_values = fernet_to_use.decrypt(cipher_value_encrypted)
        print(f"   insecure_values: {insecure_values}")
        encrypted_value = cipher_value_encrypted.decode()
        print(f"   unencripted_value: {encrypted_value}")
        secure_value_encrypted = encrypted_value
    except Exception as e:
        print(f"\n❌ Error to decrypt: {e}")  
        secure_value_encrypted = cipher_value_encrypted.decode()
        print(f"   secure_value_encrypted: {secure_value_encrypted}")
   
    return secure_value_encrypted


