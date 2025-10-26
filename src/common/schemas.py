import re
from datetime import datetime

from pydantic import BaseModel, field_validator


class BasePublicID(BaseModel):
    public_id: str


class BaseModelSchema(BasePublicID):
    name: str


class BaseModelSlugSchema(BaseModel):
    slug: str
    name: str


class CommentOut(BaseModel):
    public_id: str
    created_at: datetime
    comment: str


class MediaOut(BaseModel):
    public_id: str
    url: str
    alt_text: str


class MobileField(BaseModel):
    mobile: str | None = None

    @field_validator("mobile")
    @classmethod
    def validate_mobile(cls, v: str | None) -> str | None:
        if v is None:
            return v

        if not isinstance(v, str):
            raise TypeError("Mobile number must be a string")
        if not re.match(r"^01\d{9}$", v):
            raise ValueError("Mobile number must be exactly 11 digits starting with 01")

        return v
