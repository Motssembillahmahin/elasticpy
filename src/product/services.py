from __future__ import annotations

from redis.asyncio import Redis
from sqlalchemy.orm import joinedload
from sqlmodel import Session

from src.common.exceptions import HTTP400
from src.common.filters import PaginationParams
from src.common.schemas import MediaOut
from src.product import schemas
from src.product.models import Category, Attribute
from src.product.queries import (
    get_category_top_rated_and_top_sold_products_query,
    get_products_base_query,
    get_product_with_product_variants_and_images,
    get_products_by_search,
)
from src.product.schemas import ProductVariantShortOut
from src.product.utlis import get_response


async def set_product(redis: Redis, name: str):
    await redis.set("products:1", f"{name}")
    value = await redis.get("products:1")
    return {"product": value}


def get_products(
    db: Session,
    pagination: PaginationParams | None = None,
) -> tuple[list, int]:
    base_query, total_counts = get_products_base_query(db)
    if pagination:
        base_query = base_query.offset(pagination.offset).limit(pagination.size)
    return get_response(base_query.all()), total_counts


def get_product_by_slug(db: Session, slug: str) -> dict:
    product = get_product_with_product_variants_and_images(db, slug)
    if product is None:
        raise HTTP400(detail="Product not found")
    if product.variants:
        variants = product.variants

        regular_prices = [v.regular_price for v in variants if v.regular_price]
        discount_prices = [v.discount_price for v in variants if v.discount_price]

        regular_price_min = int(min(regular_prices)) if regular_prices else None
        regular_price_max = int(max(regular_prices)) if regular_prices else None
        discount_price_min = int(min(discount_prices)) if discount_prices else None
        discount_price_max = int(max(discount_prices)) if discount_prices else None

        if not discount_price_min:
            discount_price_min = None
        if not discount_price_max:
            discount_price_max = None

        if discount_price_min is None and discount_price_max is None:
            max_discount_percentage = None
        else:
            discount_percentages = [
                ((v.regular_price - v.discount_price) / v.regular_price) * 100
                for v in variants
                if v.discount_price is not None and v.regular_price > 0
            ]
            max_discount_percentage = (
                max(discount_percentages) if discount_percentages else None
            )

    else:
        regular_price_min = regular_price_max = None
        discount_price_min = discount_price_max = None
        max_discount_percentage = None

    variants = [
        ProductVariantShortOut.model_validate(variant, from_attributes=True)
        for variant in product.variants
    ]

    attribute_ids = list(
        {
            attr_variant.attribute_id
            for p_variant in product.variants
            for attr_variant in p_variant.attribute_variants
        }
    )
    attributes = (
        db.query(Attribute)
        .options(joinedload(Attribute.variants))
        .filter(Attribute.id.in_(attribute_ids))
        .order_by(Attribute.name)
        .all()
    )

    brand = (
        {"name": product.brand.name, "slug": product.brand.slug}
        if product.brand_id
        else None
    )
    return {
        "name": product.name,
        "public_id": product.public_id,
        "description": product.description,
        "stock_status": product.stock_status,
        "slug": product.slug,
        "rating": product.rating,
        "variants": variants,
        "brand": brand,
        "category": schemas.CategoryBase.model_validate(
            product.category, from_attributes=True
        ),
        "attributes": [
            schemas.AttributeWithVariantsOut.model_validate(
                attribute, from_attributes=True
            )
            for attribute in attributes
        ],
        "regular_price_min": regular_price_min,
        "regular_price_max": regular_price_max,
        "discount_price_min": discount_price_min,
        "discount_price_max": discount_price_max,
        "discount": round(max_discount_percentage) if max_discount_percentage else None,
        "return_policy": product.return_policy,
        "exchange_policy": product.exchange_policy,
        "delivery_time": product.delivery_time or None,
        "total_sold": product.total_sold,
    }


def get_products_by_search_with_filter(
    db: Session,
    search: str,
    pagination: PaginationParams | None = None,
) -> tuple[dict, int]:
    base_query = get_products_by_search(db, search)
    total_counts = base_query.count()
    if pagination:
        base_query = base_query.offset(pagination.offset).limit(pagination.size)
    result = {
        "products": get_response(base_query.all()),
    }
    return result, total_counts


def get_category(db: Session, slug: str) -> dict:
    category = (
        db.query(Category)
        .options(joinedload(Category.image))
        .filter(Category.slug == slug, Category.is_active)
        .first()
    )

    if not category:
        raise HTTP400(detail="Category not found")
    return {
        "name": category.name,
        "image": MediaOut.model_validate(category.image, from_attributes=True),
        "banner": MediaOut.model_validate(category.banner, from_attributes=True),
    }


def get_category_top_products(db: Session, slug: str) -> dict:
    top_rated, top_sold = get_category_top_rated_and_top_sold_products_query(db, slug)
    return {
        "top_rated": get_response(top_rated),
        "top_sold": get_response(top_sold),
    }
