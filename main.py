# Anewhope in a special project
import os
from protected_values import *
from security.custom_cipher_lib import basic_check_access, custom_encrypt

# Global variables
ready_to_use = False
basic_string_for_checks = "This@2025"
basic_string_for_results = ""
security_local_folder = "security"
security_local_file_name = "basesecuritypass"
security_path = os.path.join(security_local_folder, security_local_file_name)
secure_value_encrypted = ""


print("After close the door always exists a new hope")
print("Check the currect status")

if ready_to_use:
    print("The system is ready to use")
    print(f"Operating system: {os.name}")
else:
    print("The system need start to be able ready to use")

# Security usage
if basic_check_access(basic_string_for_checks):
    print("The cipher system is available")
else:
    print("The cipher system is not available")

if os.path.exists(security_path):
    print("The security file is available")
else:
    print("The security file is not available")

# hidden values
#print(f"Global shared key raw: {global_shared_key_raw}")
# rememeber pass as argument the variable global_shared_key_raw to secrity custom cipher
insecure_value_to_encrypt = "This@2026"
custom_encrypt_key = ""
custom_encrypt_result = custom_encrypt(global_shared_key_raw, insecure_value_to_encrypt)
print("--------------------------------")  
print(f"Original value to encrypt: {insecure_value_to_encrypt}")
print(f"Custom cipher result: {custom_encrypt_result}")
