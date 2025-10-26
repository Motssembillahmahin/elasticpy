import secrets
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Any


def generate_public_id() -> str:
    """Generate a unique 11-character public id"""
    return secrets.token_urlsafe(nbytes=8)


def json_serializer(obj: Any) -> Any:  # noqa: ANN401
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, bytes):
        return obj.decode("utf-8")
    if hasattr(obj, "__dict__"):
        # Handle objects with __dict__ (like SQLAlchemy models)
        return obj.__dict__

    # Print the problematic object type for debugging
    print(f"Cannot serialize object of type: {type(obj).__name__}, value: {obj}")
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
