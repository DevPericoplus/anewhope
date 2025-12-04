import json
from pathlib import Path

import unicodedata

def get_organization_by_name_exist(organization_name: str) -> bool:
    """
    Checks if an organization with the given name exists in the organizations.json file.

    The comparison ignores case and also ignores diacritics (accented vowels, etc).

    Args:
        organization_name (str): The name of the organization to check.

    Returns:
        bool: True if the organization exists, False otherwise.
    """

    def normalize(text: str) -> str:
        # Remove leading/trailing whitespace, lowercase, and remove accents/diacritics
        text = text.strip().lower()
        # Decompose Unicode so accents become their own codepoints, then strip combining (accent) chars
        text = ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
        return text

    # Get the path to the organizations.json file (mock data)  
    data_file = Path(__file__).parent.parent.parent / "2_shared_application" / "moks" / "organizations.json"
    if not data_file.exists():
        return False
    try:
        with open(data_file, "r", encoding="utf-8") as f:
            orgs = json.load(f)
    except Exception:
        return False

    normalized_input = normalize(organization_name)
    for org in orgs:
        org_name = org.get("organization_name", "")
        if normalize(org_name) == normalized_input:
            return True
    return False
    """
    Checks if an organization with the given name exists in the organizations.json file.

    Args:
        organization_name (str): The name of the organization to check.

    Returns:
        bool: True if the organization exists, False otherwise.
    """
    # Get the path to the organizations.json file (mock data)  
    data_file = Path(__file__).parent.parent.parent / "2_shared_application" / "moks" / "organizations.json"
    if not data_file.exists():
        return False
    try:
        with open(data_file, "r", encoding="utf-8") as f:
            orgs = json.load(f)
    except Exception:
        return False

    # Normalize name for case-insensitive comparison and whitespace
    normalized_input = organization_name.strip().lower()
    for org in orgs:
        if org.get("organization_name", "").strip().lower() == normalized_input:
            return True
    return False


def create_organization(organization) -> bool:
        """
        Creates a new organization entry in the organizations.json file.
        Assigns a unique, sequential organization_id.

        Args:
            organization (Organization): The organization object to add. Must have organization_id=None.

        Returns:
            bool: True if creation succeeded, False otherwise.
        """
        # Get the path to the organizations.json file (mock data)  
        data_file = Path(__file__).parent.parent.parent / "2_shared_application" / "moks" / "organizations.json"
        # Load existing organizations
        orgs = []
        if data_file.exists():
            try:
                with open(data_file, "r", encoding="utf-8") as f:
                    orgs = json.load(f)
            except Exception:
                return False

        # Determine next organization_id
        if orgs:
            existing_ids = [org.get("organization_id", 0) for org in orgs if isinstance(org.get("organization_id"), int)]
            next_id = max(existing_ids, default=0) + 1
        else:
            next_id = 1

        # Build new organization dict
        org_dict = {
            "organization_id": next_id,
            "organization_name": getattr(organization, "_organization_name", None) or getattr(organization, "organization_name", None),
            "organization_email": getattr(organization, "_organization_email", None) or getattr(organization, "organization_email", None),
            "organization_tlf": getattr(organization, "_organization_tlf", None) or getattr(organization, "organization_tlf", None),
            "organization_address": getattr(organization, "_organization_address", None) or getattr(organization, "organization_address", None),
            "organization_country": getattr(organization, "_organization_country", None) or getattr(organization, "organization_country", None),
            "organization_state": getattr(organization, "_organization_state", None) or getattr(organization, "organization_state", None),
        }

        # Replace or set the id in the passed-in organization object if possible
        if hasattr(organization, "_organization_id"):
            setattr(organization, "_organization_id", next_id)
        elif hasattr(organization, "organization_id"):
            setattr(organization, "organization_id", next_id)

        orgs.append(org_dict)
        try:
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump(orgs, f, indent=2, ensure_ascii=False)
        except Exception:
            return False

        return True


