# Anewhope in a special project
import os
import sys
from protected_values import *
#from security.custom_cipher_lib import basic_check_access, custom_encrypt
import security.custom_cipher_lib as security

# Global variables
ready_to_use = False
basic_string_for_checks = "This@2025"
basic_string_for_results = ""
security_local_folder = "security"
security_local_file_name = "basesecuritypass"
security_path = os.path.join(security_local_folder, security_local_file_name)
secure_value_encrypted = ""
# Security file name
security_file_name = "basesecuritypass.json"
security_file_path = os.path.join(security_local_folder, security_file_name)
fernet_string = ""
global_fernet_key = ""


# Temporary to check
ready_to_use = True

print("After close the door always exists a new hope")
print("Check the currect status")

if ready_to_use:
    print("The system is ready to use")
    print(f"Operating system: {os.name}")
else:
    print("The system need start to be able ready to use")

# Security usage
if security.basic_check_access(basic_string_for_checks):
    print("The cipher system is available")
else:
    print("The cipher system is not available")

if os.path.exists(security_path):
    print("The security file is available")
else:
    print("The security file is not available")

# value only to check
insecure_value_to_encrypt = "This@2026"
print(f"Original value to encrypt only for check: {insecure_value_to_encrypt}")
print("--------------------------------")

# Start the security process
secret_key_file = security_file_path
if os.path.exists(secret_key_file):
    fernet_key = security.load_fernet_key_from_file(secret_key_file)
    print(f"Fernet key: {fernet_key}")
    print("--------------------------------")
    encrypted_value = security.encrypt_value(fernet_key, insecure_value_to_encrypt)
#    insecure_values, encrypted_value = security.encrypt_value(fernet_key, insecure_value_to_encrypt)
#    print(f"Insecure values: {insecure_values}")
    print(f"Encrypted value: {encrypted_value}")
    print("--------------------------------")

    recovered_value = security.decrypt_value(fernet_key, encrypted_value)
    print(f"Original value recovered from encrypt value: {recovered_value}")
else:
    print(f"Error: the file {secret_key_file} not exist")
    security.initialize_fernet_environment()
    print("Fernet file created")
    fernet_key = security.load_fernet_key_from_file(secret_key_file)
    print(f"Fernet key: {fernet_key}")
    encrypted_value = security.encrypt_value(fernet_key, insecure_value_to_encrypt)
    print(f"Encrypted value: {encrypted_value}")
    print("--------------------------------")
    recovered_value = security.decrypt_value(fernet_key, encrypted_value)
    print(f"Original value recovered from encrypt value: {recovered_value}")
