import json
from pathlib import Path

def get_identity_types_dict_id_name_sup_9() -> dict[int, str]:
    """
    Devuelve un diccionario {identity_type_id: identity_type_name} para aquellos
    identity_type_id superiores a 9, ordenado por identity_type_id.
    
    Returns:
        dict[int, str]: Diccionario ordenado por identity_type_id > 9.
    """
    # Get the path to the identity_types.json file (mock data)  
    data_file = Path(__file__).parent.parent.parent / "2_shared_application" / "moks" / "identity_types.json"
    if not data_file.exists():
        return {}
    try:
        with open(data_file, "r", encoding="utf-8") as f:
            identity_types = json.load(f)
    except Exception:
        return {}
    
    filtered = {
        identity_type["identity_type_id"]: identity_type["identity_type_name"]
        for identity_type in identity_types
        if isinstance(identity_type.get("identity_type_id"), int) and identity_type["identity_type_id"] > 9
    }
    # Ordenar el diccionario por identity_type_id
    result = dict(sorted(filtered.items()))
    # Verificación de tipo y muestra de valores
    assert isinstance(result, dict), f"El resultado no es un diccionario, es {type(result)}"
    print("Valores retornados por la función:", result)
    return result