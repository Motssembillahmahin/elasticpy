from sqlalchemy import Subquery, or_
from sqlalchemy.orm import Query, joinedload, load_only, selectinload
from sqlmodel import Session, case, func, select
from src.common.filters import PaginationParams
from src.common.models import Media


from .associations import ProductTagLink
from .enums import ProductStatus, StockStatus
from .models import (
    Attribute,
    AttributeVariant,
    Brand,
    Category,
    Product,
    ProductVariant,
    Tag,
)
from .utlis import get_category_and_descendants


def get_products_with_relationships(  # noqa: C901
    db: Session,
    pagination: PaginationParams | None = None,
) -> tuple[list[Product], dict]:
    query = (
        db.query(Product)
        .options(
            joinedload(Product.category.and_(Category.is_active)).options(
                load_only(Category.public_id, Category.name, Category.slug)
            )
        )
        .options(
            joinedload(Product.brand.and_(Brand.is_active)).options(
                load_only(Brand.public_id, Brand.name, Brand.slug)
            )
        )
        .options(
            selectinload(Product.variants.and_(ProductVariant.is_active))
            .selectinload(
                ProductVariant.attribute_variants.and_(AttributeVariant.is_active)
            )
            .selectinload(AttributeVariant.attribute.and_(Attribute.is_active))
        )
        .options(joinedload(Product.attributes.and_(Attribute.is_active)))
        .options(joinedload(Product.tags.and_(Tag.is_active)))
        .options(selectinload(Product.images.and_(Media.is_active)))
        .filter(Product.is_active)
        .order_by(Product.updated_at.desc())
    )
    summary_query = query.order_by(None)
    summary_result = summary_query.with_entities(
        func.count(Product.id).label("total"),
        func.sum(case((Product.status == ProductStatus.PUBLISHED, 1), else_=0)).label(
            "published"
        ),
        func.sum(case((Product.status == ProductStatus.PENDING, 1), else_=0)).label(
            "pending"
        ),
        func.sum(
            case((Product.stock_status == StockStatus.IN_STOCK, 1), else_=0)
        ).label("in_stock"),
        func.sum(
            case((Product.stock_status == StockStatus.OUT_OF_STOCK, 1), else_=0)
        ).label("stock_out"),
        func.sum(case((Product.status == ProductStatus.DRAFT, 1), else_=0)).label(
            "draft"
        ),
    ).one()

    summary = {
        "total": summary_result.total or 0,
        "published": summary_result.published or 0,
        "pending": summary_result.pending or 0,
        "in_stock": summary_result.in_stock or 0,
        "stock_out": summary_result.stock_out or 0,
        "draft": summary_result.draft or 0,
    }

    if pagination:
        query = query.offset(pagination.offset).limit(pagination.size)
    return query.all(), summary


def get_product_with_product_variants_and_images(db: Session, slug: str) -> Product:
    return (
        db.query(Product)
        .options(
            selectinload(Product.variants).selectinload(
                ProductVariant.attribute_variants
            ),
            selectinload(Product.images),
            selectinload(Product.brand),
        )
        .filter(
            Product.is_active,
            Product.slug == slug,
            Product.status == ProductStatus.PUBLISHED,
        )
        .order_by(Product.name)
        .first()
    )


def get_variant_stats_subquery(db: Session) -> Subquery:
    return (
        db.query(
            ProductVariant.product_id,
            func.min(ProductVariant.regular_price).label("regular_price_min"),
            func.max(ProductVariant.regular_price).label("regular_price_max"),
            func.min(ProductVariant.discount_price).label("discount_price_min"),
            func.max(ProductVariant.discount_price).label("discount_price_max"),
            func.max(
                case(
                    (
                        ProductVariant.regular_price > 0,
                        (
                            (
                                ProductVariant.regular_price
                                - ProductVariant.discount_price
                            )
                            / ProductVariant.regular_price
                        )
                        * 100,
                    ),
                    else_=None,
                )
            ).label("max_discount_percentage"),
        )
        .group_by(ProductVariant.product_id)
        .subquery()
    )


def get_tag_subquery(search_pattern: str) -> Subquery:
    return (
        select(ProductTagLink.product_id)
        .join(Tag, ProductTagLink.tag_id == Tag.id)
        .filter(Tag.name.ilike(search_pattern))
    )


def products_query(db: Session) -> Query:
    variant_stats = get_variant_stats_subquery(db)
    return (
        (
            db.query(Product, variant_stats).outerjoin(
                variant_stats, Product.id == variant_stats.c.product_id
            )
        )
        .filter(Product.status == ProductStatus.PUBLISHED)
        .options(selectinload(Product.images))
        .order_by(Product.name)
    )


def get_products_by_search(
    db: Session,
    search: str,
) -> Query:
    query = products_query(db)
    search_pattern = f"%{search}%"

    tag_subquery = get_tag_subquery(search_pattern)

    query = (
        query.outerjoin(Product.brand)
        .outerjoin(Product.category)
        .filter(
            or_(
                Product.name.ilike(search_pattern),
                Product.slug.ilike(search_pattern),
                Product.product_no.ilike(search_pattern),
                Product.id.in_(tag_subquery),
                Brand.name.ilike(search_pattern),
                Category.name.ilike(search_pattern),
            )
        )
    )
    return query


def get_products_base_query(db: Session) -> tuple[Query, int]:
    query = products_query(db)
    total_counts = query.count()
    return query, total_counts


def get_category_base_query(db: Session, slug: str) -> tuple[Query, int]:
    query = products_query(db)
    category_id = db.query(Category.id).filter(Category.slug == slug).first()
    all_descendents = get_category_and_descendants(db, category_id)
    query = query.filter(Product.category_id.in_(all_descendents))
    total_counts = query.count()
    return query, total_counts


def get_category_top_rated_and_top_sold_products_query(
    db: Session, slug: str
) -> tuple[list, list]:
    base_query, total_counts = get_category_base_query(db, slug)
    top_rated = (
        base_query.order_by(Product.rating.desc()).limit(5).all()
    )  # adjust with your requirements
    top_sold = base_query.order_by(Product.total_sold.desc()).limit(5).all()
    return top_rated, top_sold
