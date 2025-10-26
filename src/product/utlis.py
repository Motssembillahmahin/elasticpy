from sqlmodel import Session

from src.product.models import Category


def get_response(results: list) -> list:
    processed = []

    for result in results:
        product = result[0]

        product_data = {
            "name": product.name,
            "slug": product.slug,
            "public_id": product.public_id,
            "rating": product.rating,
            "regular_price_min": int(result[2]) if len(result) > 2 else None,  # noqa: PLR2004
            "regular_price_max": int(result[3]) if len(result) > 3 else None,  # noqa: PLR2004
            "discount_price_min": result[4] if len(result) > 4 else None,  # noqa: PLR2004
            "discount_price_max": result[5] if len(result) > 5 else None,  # noqa: PLR2004
            "discount": round(result[6]) if len(result) > 6 and result[6] else None,  # noqa: PLR2004
            "total_sold": product.total_sold,
        }
        processed.append(product_data)

    return processed


def get_category_and_descendants(db: Session, category_ids: list[int]) -> list[int]:
    """
    Get the specified categories AND all their descendant category IDs.

    Example: If you pass "Men's top ware" category ID, it will return:
    - "Men's top ware" itself
    - "t-shirt" (child of Men's top ware)
    - "polo-shirt" (child of Men's top ware)
    But NOT "Men" (parent) or "Men's bottom ware" (sibling)
    """
    if not category_ids:
        return []

    all_categories = (
        db.query(Category.id, Category.parent_id).filter(Category.is_active).all()
    )

    children_map = {}
    for cat_id, parent_id in all_categories:
        if parent_id not in children_map:
            children_map[parent_id] = []
        children_map[parent_id].append(cat_id)

    def get_all_descendants(cat_id: int) -> list[int]:
        descendants = [cat_id]
        if cat_id in children_map:
            for child_id in children_map[cat_id]:
                descendants.extend(get_all_descendants(child_id))
        return descendants

    all_descendants = []
    for cat_id in category_ids:
        all_descendants.extend(get_all_descendants(cat_id))

    return list(set(all_descendants))
