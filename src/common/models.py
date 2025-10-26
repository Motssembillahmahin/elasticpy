from datetime import datetime
from typing import TYPE_CHECKING, Optional

from pydantic import EmailStr
from sqlalchemy import CheckConstraint
from sqlmodel import Field, Relationship, SQLModel
import sqlalchemy as sa


from src.product.associations import ProductImageLink

from .utils import generate_public_id

if TYPE_CHECKING:
    from src.product.models import (
        Brand,
        Category,
        Product,
        ProductVariant,
    )


class TimestampMixin(SQLModel):
    created_at: datetime | None = Field(default_factory=datetime.now, nullable=False)
    updated_at: datetime | None = Field(
        default_factory=datetime.now,
        sa_column_kwargs={"onupdate": datetime.now},
        nullable=False,
    )


class IDMixin(SQLModel):
    id: int | None = Field(default=None, primary_key=True)
    public_id: str = Field(
        default_factory=lambda: generate_public_id(), unique=True, max_length=11
    )


class CommonFieldMixin(IDMixin, TimestampMixin):
    is_active: bool | None = Field(default=True, nullable=False)


class Media(CommonFieldMixin, table=True):
    name: str = Field(nullable=False)
    alt_text: str = Field(nullable=False)
    s3_key: str = Field(nullable=False)

    # Foreign keys
    created_by_id: int = Field(foreign_key="user.id", nullable=False)
    updated_by_id: int = Field(foreign_key="user.id", nullable=False)

    # Relationships
    # set it from user model
    created_by: Optional["User"] = Relationship(  # noqa: F821
        back_populates="created_media_files",
        sa_relationship_kwargs={"foreign_keys": "Media.created_by_id"},
    )
    updated_by: Optional["User"] = Relationship(  # noqa: F821
        back_populates="updated_media_files",
        sa_relationship_kwargs={"foreign_keys": "Media.updated_by_id"},
    )

    brands: list["Brand"] = Relationship(back_populates="image")
    category_images: list["Category"] = Relationship(
        back_populates="image",
        sa_relationship_kwargs={"foreign_keys": "Category.image_id"},
    )
    category_banners: list["Category"] = Relationship(
        back_populates="banner",
        sa_relationship_kwargs={"foreign_keys": "Category.banner_id"},
    )
    products: list["Product"] = Relationship(
        back_populates="images", link_model=ProductImageLink
    )
    product_variants: list["ProductVariant"] = Relationship(back_populates="image")


class User(CommonFieldMixin, table=True):
    __table_args__ = (
        CheckConstraint(
            "email IS NOT NULL OR mobile IS NOT NULL", name="email_or_mobile_required"
        ),
    )

    email: EmailStr | None = Field(
        sa_column=sa.Column(sa.String, unique=True, nullable=True)
    )
    mobile: str | None = Field(
        sa_column=sa.Column(sa.String, unique=True, nullable=True)
    )
    password: str | None

    is_verified: bool = Field(default=False, nullable=False)

    # Foreign Keys
    seller_id: int | None = Field(
        default=None, foreign_key="seller.id", nullable=True, unique=True
    )
    customer_id: int | None = Field(
        default=None, foreign_key="customer.id", nullable=True, unique=True
    )
    employee_id: int | None = Field(
        default=None, foreign_key="employee.id", nullable=True, unique=True
    )

    # Relationships
    created_media_files: list["Media"] = Relationship(
        back_populates="created_by",
        sa_relationship_kwargs={"foreign_keys": "Media.created_by_id"},
    )
    updated_media_files: list["Media"] = Relationship(
        back_populates="updated_by",
        sa_relationship_kwargs={"foreign_keys": "Media.updated_by_id"},
    )
