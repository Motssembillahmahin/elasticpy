import logging
import secrets
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Any

from aiohttp import ClientError

from src.common.const import S3_CLIENT
from src.common.exceptions import HTTP500

logger = logging.getLogger(__name__)


def generate_public_id() -> str:
    """Generate a unique 11-character public id"""
    return secrets.token_urlsafe(nbytes=8)


def generate_presigned_url(bucket: str, key: str, expiration: int = 3600) -> str:
    """Generate a presigned URL for private file access"""
    try:
        return S3_CLIENT.generate_presigned_url(
            "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expiration
        )
    except ClientError as e:
        message = "Failed to fetch image"
        logger.exception(msg=message)
        raise HTTP500(detail=message) from e


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
