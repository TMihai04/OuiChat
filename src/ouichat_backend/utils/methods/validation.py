# Validation methods

from typing import Any

import uuid


def is_valid_uuid(val: Any) -> bool:
    """Checks wether the string representation of the input is a valid uuid."""
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False