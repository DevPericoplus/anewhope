import os
import json
import sys
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Initialization of variables
datos_descifrados = None
ciphervalue = None
unciphervalue = None
secure_value_encrypted = ""
secure_value_decrypted = ""
fernet_key = None
fernet_value = None
fernet_value_decoded = None
fernet_value_decoded_decoded = None
insecure_value = None
unencripted_value = None
custom_encrypt_key = None
secret_key_file = "security/basesecuritypass.json"
fernet_to_use = None
value_encrypted_verified = False
global_encrypted_value = None

# Funtions to manage the security
def basic_check_access(basic_string_for_checks):
    if basic_string_for_checks == "This@2025":
        return True
    else:
        return False

def initialize_fernet_environment():
    create_empty_file(secret_key_file)
    try:
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, parent_dir) 
        from protected_values import global_shared_key_raw
        master_secret_key = create_fernet_key(global_shared_key_raw)
        store_fernet_key_to_file(master_secret_key)
        print(f"✅ Global shared key loaded successfully: {global_shared_key_raw[:10]}...")
   
    except Exception as e:
        print(f"Error: {e}")
        print("Create a new master secret key failure")
    return master_secret_key


"""
    if create_fernet_key() == True:
        fernet_key = load_fernet_key_from_file(secret_key_file)
        fernet_to_use = fernet_key

        encrypted_value = encrypt_value(fernet_key, insecure_value_to_encrypt)
        global_encrypted_value = encrypted_value
    if verify_encrypted_value(fernet_to_use, encrypted_value) == True:
        print("✅ The value is encrypted and verified")
    else:
        print("❌ The value is not encrypted or verified")
    return fernet_key_to_use
"""

def load_global_shared_key_raw():
    """
    Load the global_shared_key_raw from protected_values.py file
    """
    try:      
        # Add the parent directory to the path to import protected_values
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, parent_dir)    
        from protected_values import global_shared_key_raw
        print(f"✅ Global shared key loaded successfully: {global_shared_key_raw[:10]}...")
        return global_shared_key_raw
        
    except ImportError as e:
        print(f"❌ Error importing global_shared_key_raw from protected_values.py: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error loading global_shared_key_raw: {e}")
        return None

def create_fernet_key(global_shared_key_raw):
    """Create a Fernet cipher from a raw key string."""
    key = Fernet.generate_key() 
    print("Clave Fernet generada (bytes):", key)
    print("-" * 30)
    clave_str = key.decode() 
    print("Clave Fernet decodificada (string):", clave_str)
    print("--------------------------------") 
    return clave_str

def encrypt_value(encript_key, value_to_encrypt):
    print("\n1. Cifrando la cadena...")
    
    # Check if encript_key is a string or Fernet object
    if isinstance(encript_key, str):
        # If it's a string, create a Fernet object from it
        fernet_key_bytes = encript_key.encode()
        encrypt_key_to_use = Fernet(fernet_key_bytes)
    else:
        # If it's already a Fernet object, use it directly
        encrypt_key_to_use = encript_key
    
    # Convert value to bytes if it's a string
    if isinstance(value_to_encrypt, str):
        value_bytes = value_to_encrypt.encode()
    else:
        value_bytes = value_to_encrypt
    
    secure_value_encrypted = encrypt_key_to_use.encrypt(value_bytes)
    print(f"   Value encrypted successfully")
    return secure_value_encrypted

def create_empty_file(file_name):
    with open(file_name, 'w') as f:
        f.write('')
    return True

def store_fernet_key_to_file(encrypted_value):
    """Store the Fernet key in JSON format"""
    try:
        # Create a dictionary to store the key
        data_to_save = {
            "fernet_key": encrypted_value
        }
        
        # Write the dictionary to the JSON file
        with open(secret_key_file, 'w') as f:
            json.dump(data_to_save, f, indent=4)
        
        print(f"✅ Fernet key stored in '{secret_key_file}' successfully.")
        print(f"   Key stored: {encrypted_value[:10]}... (It is part of the key)")
        return True
        
    except Exception as e:
        print(f"❌ Error writing the file: {e}")
        return False

def load_fernet_key_from_file(encrypted_value_file):
    secret_key_file = encrypted_value_file
    try:
        with open(secret_key_file, 'r') as f:
            secret_data_loaded = json.load(f)
        fernet_key = secret_data_loaded["fernet_key"]
        fernet_to_use = Fernet(fernet_key)
        print("🔑 Clave Fernet recuperada y Nuevo Objeto Fernet creado.")
        return fernet_to_use
 
    except FileNotFoundError:
        print(f"❌ Error: El archivo '{secret_key_file}' no fue encontrado.")
        # Create a new Fernet key if file doesn't exist
        global_shared_key_raw = load_global_shared_key_raw()
        if global_shared_key_raw:
            master_secret_key = create_fernet_key(global_shared_key_raw)
            store_fernet_key_to_file(master_secret_key)
            return Fernet(master_secret_key)
        else:
            # Generate a random key if we can't load the shared key
            random_key = Fernet.generate_key()
            store_fernet_key_to_file(random_key.decode())
            return Fernet(random_key)
            
    except json.JSONDecodeError:
        print(f"❌ Error: El archivo '{secret_key_file}' no es un JSON válido.")
        global_shared_key_raw = load_global_shared_key_raw()
        if global_shared_key_raw:
            master_secret_key = create_fernet_key(global_shared_key_raw)
            store_fernet_key_to_file(master_secret_key)
            return Fernet(master_secret_key)
        else:
            # Generate a random key if we can't load the shared key
            random_key = Fernet.generate_key()
            store_fernet_key_to_file(random_key.decode())
            return Fernet(random_key)
       
    except Exception as e:
        print(f"Error to load the fernet key from the file: {e}")
        # Generate a random key as fallback
        random_key = Fernet.generate_key()
        store_fernet_key_to_file(random_key.decode())
        return Fernet(random_key)   

def verify_encrypted_value(fernet_to_use, encrypted_value):
    evaluation_result = False
    fernet_original = fernet_to_use
    value_to_evaluate = encrypted_value
    value_to_evaluate_bytes = value_to_evaluate.encode()
    value_calculate = fernet_original.encrypt( value_to_evaluate_bytes)
    print(f"\n🚀 Value calculated: {value_calculate.decode()[:20]}...")
    if value_calculate.decode() == value_to_evaluate.decode():
        evaluation_result = True
        print("✅ The value is encrypted and verified")
    else:
        evaluation_result = False
        print("❌ The value is not encrypted or verified")
    return evaluation_result

# decryption process
def decrypt_value(fernet_to_use,cipher_value_encrypted):
    value_received = cipher_value_encrypted   
    try:
        insecure_values = fernet_to_use.decrypt(value_received)
        print(f"   insecure_values: {value_received}")
        encrypted_value = value_received.decode()
        print(f"   unencripted_value: {encrypted_value}")
#        secure_value_encrypted = encrypted_value
    except Exception as e:
        print(f"\n❌ Error to decrypt: {e}")  
        secure_value_encrypted = cipher_value_encrypted.decode()
        print(f"   secure_value_encrypted: {secure_value_encrypted}")
    return insecure_values, encrypted_value
