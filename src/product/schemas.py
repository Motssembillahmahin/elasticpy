from decimal import Decimal

from pydantic import BaseModel, computed_field
from src.common.schemas import BaseModelSchema
from src.product.enums import StockStatus


class AttributeVariantShortOut(BaseModelSchema):
    attribute: BaseModelSchema


class ProductVariantShortOut(BaseModel):
    public_id: str
    regular_price: Decimal
    discount_price: Decimal | None
    stock: int | None
    stock_status: StockStatus
    attribute_variants: list[AttributeVariantShortOut]

    @computed_field
    @property
    def discount_percentage(self) -> int | None:
        if self.discount_price:
            return round(
                ((self.regular_price - self.discount_price) / self.regular_price) * 100
            )
        return None


class CategoryBase(BaseModel):
    name: str
    slug: str


class AttributeCreate(BaseModel):
    name: str
    slug: str


class AttributeOut(AttributeCreate):
    public_id: str


class AttributeWithVariantsOut(AttributeOut):
    variants: list[BaseModelSchema]
