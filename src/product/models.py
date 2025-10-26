from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

import sqlalchemy as sa
from sqlmodel import Field, Relationship

from src.common.models import CommonFieldMixin


from .associations import (
    ProductAttributeLink,
    ProductImageLink,
    ProductTagLink,
    ProductVariantAttributeVariantLink,
)
from .enums import (
    ExchangePolicy,
    ProductStatus,
    ProductType,
    ReturnPolicy,
    StockStatus,
)

if TYPE_CHECKING:
    from src.common.models import Media


class Brand(CommonFieldMixin, table=True):
    name: str
    slug: str = Field(sa_column=sa.Column(sa.String, unique=True, nullable=False))
    description: str | None

    # Foreign keys
    image_id: int = Field(foreign_key="media.id", nullable=False)
    seller_id: int | None = Field(default=None, foreign_key="seller.id")

    # Relationships
    image: Optional["Media"] = Relationship(back_populates="brands")
    products: list["Product"] = Relationship(back_populates="brand")


class Tag(CommonFieldMixin, table=True):
    name: str
    slug: str = Field(sa_column=sa.Column(sa.String, unique=True, nullable=False))

    # Relationships
    products: list["Product"] = Relationship(
        back_populates="tags", link_model=ProductTagLink
    )


class Product(CommonFieldMixin, table=True):
    name: str
    slug: str = Field(sa_column=sa.Column(sa.String, unique=True, nullable=False))
    product_no: str = Field(sa_column=sa.Column(sa.String, unique=True, nullable=False))
    description: str
    short_description: str | None
    meta_description: str | None
    video: str | None
    delivery_time: int | None = Field(
        sa_column=sa.Column(sa.Integer, nullable=True),
        description="Delivery time in days",
    )
    stock_management: bool = Field(default=False, nullable=False)

    # TODO: set this values by running cron
    rating: Decimal = Field(
        sa_column=sa.Column(
            sa.Numeric(precision=3, scale=2), nullable=False, default=0
        ),
    )  # Average Rating between 1 and 5
    total_sold: int = Field(nullable=False, default=0)

    # Enum fields
    type: ProductType
    status: ProductStatus
    return_policy: ReturnPolicy
    exchange_policy: ExchangePolicy
    stock_status: StockStatus = Field(default=StockStatus.IN_STOCK, nullable=False)

    # Foreign keys
    brand_id: int | None = Field(default=None, foreign_key="brand.id")
    category_id: int | None = Field(foreign_key="category.id", nullable=False)
    seller_id: int = Field(foreign_key="seller.id", nullable=False)
    size_guide_id: int | None = Field(default=None, foreign_key="sizeguide.id")

    # Relationships
    brand: Optional["Brand"] = Relationship(back_populates="products")
    category: Optional["Category"] = Relationship(back_populates="products")
    variants: list["ProductVariant"] = Relationship(back_populates="product")
    attributes: list["Attribute"] = Relationship(
        back_populates="products", link_model=ProductAttributeLink
    )
    tags: list["Tag"] = Relationship(
        back_populates="products", link_model=ProductTagLink
    )
    images: list["Media"] = Relationship(
        back_populates="products",
        link_model=ProductImageLink,
        sa_relationship_kwargs={"order_by": "ProductImageLink.priority"},
    )

    class Config:
        arbitrary_types_allowed = True

    @property
    def image(self) -> Optional["Media"]:  # TODO: should not be null
        return self.images[0] if self.images else None


class ProductVariant(CommonFieldMixin, table=True):
    sku: str | None
    description: str | None

    # Foreign keys
    image_id: int | None = Field(foreign_key="media.id")
    product_id: int | None = Field(default=None, foreign_key="product.id")

    # Price fields
    regular_price: Decimal = Field(
        sa_column=sa.Column(sa.Numeric(precision=10, scale=2), nullable=False),
    )
    discount_price: Decimal | None = Field(
        sa_column=sa.Column(sa.Numeric(precision=10, scale=2), nullable=True),
    )
    discount_start_date: datetime | None = Field(
        sa_column=sa.Column(sa.DateTime, nullable=True),
    )
    discount_end_date: datetime | None = Field(
        sa_column=sa.Column(sa.DateTime, nullable=True),
    )

    # Stock fields
    stock_status: StockStatus
    stock: int | None = Field(default=None)
    low_stock_threshold: int | None = Field(default=None)

    # Relationships
    image: Optional["Media"] = Relationship(back_populates="product_variants")
    product: Optional["Product"] = Relationship(back_populates="variants")
    attribute_variants: list["AttributeVariant"] = Relationship(
        back_populates="product_variants", link_model=ProductVariantAttributeVariantLink
    )

    @property
    def price(self) -> Decimal:
        return self.get_price(current_time=datetime.now())

    def get_price(self, current_time: datetime) -> Decimal:
        if current_time is None:
            current_time = datetime.now()

        if not self.discount_price:
            return self.regular_price

        has_valid_dates = (
            (not self.discount_start_date and not self.discount_end_date)
            or (
                self.discount_start_date
                and self.discount_end_date
                and self.discount_start_date <= current_time <= self.discount_end_date
            )
            or (
                self.discount_start_date
                and not self.discount_end_date
                and current_time >= self.discount_start_date
            )
            or (
                not self.discount_start_date
                and self.discount_end_date
                and current_time <= self.discount_end_date
            )
        )

        return self.discount_price if has_valid_dates else self.regular_price


class Category(CommonFieldMixin, table=True):
    name: str = Field(nullable=False)
    slug: str = Field(sa_column=sa.Column(sa.String, unique=True, nullable=False))

    # Foreign keys
    image_id: int = Field(foreign_key="media.id", nullable=False)
    banner_id: int = Field(foreign_key="media.id", nullable=False)
    parent_id: int | None = Field(default=None, foreign_key="category.id")

    # Relationships
    image: Optional["Media"] = Relationship(
        back_populates="category_images",
        sa_relationship_kwargs={"foreign_keys": "Category.image_id"},
    )
    banner: Optional["Media"] = Relationship(
        back_populates="category_banners",
        sa_relationship_kwargs={"foreign_keys": "Category.banner_id"},
    )
    products: list["Product"] = Relationship(back_populates="category")
    parent: Optional["Category"] = Relationship(
        back_populates="children", sa_relationship_kwargs={"remote_side": "Category.id"}
    )
    children: list["Category"] = Relationship(back_populates="parent")


class Attribute(CommonFieldMixin, table=True):
    name: str = Field(sa_column=sa.Column(sa.String, unique=True, nullable=False))
    slug: str = Field(sa_column=sa.Column(sa.String, unique=True, nullable=False))

    # Relationships
    products: list["Product"] = Relationship(
        back_populates="attributes", link_model=ProductAttributeLink
    )
    variants: list["AttributeVariant"] = Relationship(back_populates="attribute")


class AttributeVariant(CommonFieldMixin, table=True):
    name: str

    # Foreign keys
    attribute_id: int = Field(foreign_key="attribute.id", nullable=False)

    # Relationships
    attribute: Optional["Attribute"] = Relationship(back_populates="variants")
    product_variants: list["ProductVariant"] = Relationship(
        back_populates="attribute_variants",
        link_model=ProductVariantAttributeVariantLink,
    )
