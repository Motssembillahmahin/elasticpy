from sqlmodel import Field, SQLModel


class ProductImageLink(SQLModel, table=True):
    image_id: int = Field(foreign_key="media.id", nullable=False, primary_key=True)
    product_id: int = Field(foreign_key="product.id", nullable=False, primary_key=True)
    priority: int = Field(ge=1)


class ProductTagLink(SQLModel, table=True):
    product_id: int = Field(foreign_key="product.id", nullable=False, primary_key=True)
    tag_id: int = Field(foreign_key="tag.id", nullable=False, primary_key=True)


class ProductAttributeLink(SQLModel, table=True):
    product_id: int = Field(foreign_key="product.id", nullable=False, primary_key=True)
    attribute_id: int = Field(
        foreign_key="attribute.id", nullable=False, primary_key=True
    )


class ProductVariantAttributeVariantLink(SQLModel, table=True):
    product_variant_id: int = Field(
        foreign_key="productvariant.id", nullable=False, primary_key=True
    )
    attribute_variant_id: int = Field(
        foreign_key="attributevariant.id", nullable=False, primary_key=True
    )
