import asyncio
import json

from sqlalchemy import func
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from elasticsearch import AsyncElasticsearch
from typing import Dict, Any, List
from decimal import Decimal
from datetime import datetime, timedelta

from src.product.models import Product, ProductVariant, AttributeVariant


import logging

from src.search.indices import ProductIndex
from src.search.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


class ProductSyncService:
    def __init__(self, db: Session, es_client: AsyncElasticsearch):
        self.db = db
        self.es = es_client

    def _fetch_product_with_relations(self, product_id: int):
        """
        Fetch product with ALL related data using eager loading
        This prevents N+1 query problem
        """
        statement = (
            select(Product)
            .where(Product.id == product_id)
            .options(
                selectinload(Product.category),
                selectinload(Product.tags),
                selectinload(Product.brand),
                selectinload(Product.variants)
                .selectinload(ProductVariant.attribute_variants)
                .selectinload(AttributeVariant.attribute),
                selectinload(Product.variants).selectinload(ProductVariant.image),
                selectinload(Product.images),
            )
        )

        result = self.db.execute(statement)
        return result.scalars().first()

    @staticmethod
    def _build_variant_attributes(variant: ProductVariant) -> Dict[str, str]:
        """
        Build attributes dictionary from variant's attribute variants

        Returns:
        {
            "Color": "Red",
            "Size": "M",
            "Material": "Cotton"
        }
        """
        attributes = {}

        if variant.attribute_variants:
            for attr_variant in variant.attribute_variants:
                # attr_variant.attribute.name is the attribute name (e.g., "Color", "Size")
                # attr_variant.name is the value (e.g., "Red", "M")
                attribute_name = attr_variant.attribute.name
                attribute_value = attr_variant.name
                attributes[attribute_name] = attribute_value

        return attributes

    @staticmethod
    def _extract_brand_name(product) -> str | None:
        """
        Extract brand name from product
        Handles both brand objects and string brands
        """
        if not hasattr(product, "brand") or product.brand is None:
            return None

        brand = product.brand

        if hasattr(brand, "name"):
            return brand.name

        if isinstance(brand, str):
            return brand

        try:
            return str(brand)
        except:  # noqa: E722
            return None

    @staticmethod
    def _is_discount_active(
        discount_price: Decimal | None,
        discount_start_date: datetime | None,
        discount_end_date: datetime | None,
        current_time: datetime = None,
    ) -> bool:
        """
        Check if discount is currently active
        """
        if not discount_price:
            return False

        if current_time is None:
            current_time = datetime.now()

        # No dates means discount is always active
        if not discount_start_date and not discount_end_date:
            return True

        # Both dates present
        if discount_start_date and discount_end_date:
            return discount_start_date <= current_time <= discount_end_date

        # Only start date
        if discount_start_date and not discount_end_date:
            return current_time >= discount_start_date

        # Only end date
        if not discount_start_date and discount_end_date:
            return current_time <= discount_end_date

        return False

    def _build_variants_data(self, product: Product) -> Dict[str, Any]:
        """
        Build comprehensive variants data with all attributes

        Returns:
        {
            "variants": [...],
            "prices": [...],
            "total_stock": int,
            "all_attributes": dict
        }
        """
        variants = []
        prices = []
        total_stock = 0
        current_time = datetime.now()

        # Track all unique attribute values grouped by attribute name
        attribute_values = {}  # {attribute_name: set(values)}

        if product.variants:
            for variant in product.variants:
                # Get attributes for this variant
                variant_attributes = self._build_variant_attributes(variant)

                # Check if discount is active
                is_discount_active = self._is_discount_active(
                    variant.discount_price,
                    variant.discount_start_date,
                    variant.discount_end_date,
                    current_time,
                )

                # Calculate final price
                final_price = float(
                    variant.discount_price
                    if is_discount_active
                    else variant.regular_price
                )

                # Build variant data
                variant_data = {
                    "id": str(variant.id),
                    "sku": variant.sku,
                    "description": variant.description,
                    # Attributes (e.g., {"Color": "Red", "Size": "M"})
                    "attributes": variant_attributes,
                    # Pricing
                    "regular_price": float(variant.regular_price),
                    "discount_price": float(variant.discount_price)
                    if variant.discount_price
                    else None,
                    "final_price": final_price,
                    "has_active_discount": is_discount_active,
                    "discount_start_date": variant.discount_start_date.isoformat()
                    if variant.discount_start_date
                    else None,
                    "discount_end_date": variant.discount_end_date.isoformat()
                    if variant.discount_end_date
                    else None,
                    # Stock
                    "stock": variant.stock,
                    "stock_status": variant.stock_status.value
                    if variant.stock_status
                    else None,
                    "low_stock_threshold": variant.low_stock_threshold,
                    "is_available": variant.stock > 0 if variant.stock else False,
                    "is_low_stock": (
                        variant.stock <= variant.low_stock_threshold
                        if variant.stock and variant.low_stock_threshold
                        else False
                    ),
                    # Image
                    "image_url": variant.image.url if variant.image else None,
                    "image_alt": variant.image.alt
                    if variant.image and hasattr(variant.image, "alt")
                    else None,
                }
                variants.append(variant_data)

                # Collect pricing data
                prices.append(final_price)

                # Collect stock
                if variant.stock:
                    total_stock += variant.stock

                # Collect all attribute values for faceting
                for attr_name, attr_value in variant_attributes.items():
                    if attr_name not in attribute_values:
                        attribute_values[attr_name] = set()
                    attribute_values[attr_name].add(attr_value)

        # Convert sets to sorted lists for ES
        formatted_attributes = {
            attr_name: sorted(list(values))
            for attr_name, values in attribute_values.items()
        }

        return {
            "variants": variants,
            "prices": prices,
            "total_stock": total_stock,
            "all_attributes": formatted_attributes,  # {"Color": ["Black", "Red"], "Size": ["M", "L", "XL"]}
        }

    def _product_to_document(self, product) -> Dict[str, Any]:
        """
        Transform normalized PostgreSQL data to denormalized ES document
        """
        # Build category data
        category_data = None
        category_name = None
        category_path = []

        if product.category:
            category_data = {
                "id": str(product.category.id),
                "name": product.category.name,
                "slug": product.category.slug,
            }
            category_name = product.category.name
            category_path = self._build_category_path(product.category)

        # Build tags array
        tags = []
        tag_names = []

        if product.tags:
            for tag in product.tags:
                tags.append({"id": str(tag.id), "name": tag.name})
                tag_names.append(tag.name)

        # Build variants with attributes - THIS IS THE KEY PART
        variants_data = self._build_variants_data(product)

        # Build images array
        images = []
        primary_image_url = None

        if product.images:
            sorted_images = sorted(
                product.images,
                key=lambda x: x.priority if hasattr(x, "priority") else 0,
            )
            for img in sorted_images:
                image_data = {
                    "url": getattr(img, "url", ""),
                    "alt": getattr(img, "alt_text", "")
                    or getattr(img, "alt", "")
                    or "",
                    "is_primary": getattr(img, "is_primary", False),
                    "priority": getattr(img, "priority", 0),
                }
                images.append(image_data)

                if getattr(img, "is_primary", False) and not primary_image_url:
                    primary_image_url = img.url

            if not primary_image_url and images:
                primary_image_url = images[0]["url"]

        brand_name = self._extract_brand_name(product)

        # Build search keywords
        search_keywords_parts = [
            product.name,
            product.description,
            category_name,
            " ".join(tag_names),
            brand_name,
            getattr(product, "sku", None),
        ]

        # Add variant descriptions and SKUs to search keywords
        if variants_data["variants"]:
            for variant in variants_data["variants"]:
                if variant.get("description"):
                    search_keywords_parts.append(variant["description"])
                if variant.get("sku"):
                    search_keywords_parts.append(variant["sku"])

        search_keywords = " ".join(filter(None, search_keywords_parts))

        # Check if any variant has active discount
        has_active_discount = any(
            v.get("has_active_discount", False) for v in variants_data["variants"]
        )

        # Create final document
        document = {
            "id": str(product.id),
            "name": product.name,
            "description": product.description,
            "sku": getattr(product, "sku", None),
            "brand": brand_name,
            # Base price (minimum price from variants)
            "price": min(variants_data["prices"]) if variants_data["prices"] else None,
            # Category
            "category": category_data,
            "category_name": category_name,
            "category_path": category_path,
            # Tags
            "tags": tags,
            "tag_names": tag_names,
            # Variants with attributes
            "variants": variants_data["variants"],
            "variant_count": len(variants_data["variants"]),
            # Images
            "images": images,
            "primary_image_url": primary_image_url,
            "image_count": len(images),
            # Pre-computed pricing
            "min_price": min(variants_data["prices"])
            if variants_data["prices"]
            else None,
            "max_price": max(variants_data["prices"])
            if variants_data["prices"]
            else None,
            "has_discount": has_active_discount,
            # Pre-computed stock
            "total_stock": variants_data["total_stock"],
            "in_stock": variants_data["total_stock"] > 0,
            # All available attributes for filtering/faceting
            "available_attributes": variants_data["all_attributes"],
            # Flattened specific attributes for easier filtering
            "available_colors": variants_data["all_attributes"].get("Color", []),
            "available_sizes": variants_data["all_attributes"].get("Size", []),
            "available_materials": variants_data["all_attributes"].get("Material", []),
            # Get all attribute names that this product has
            "attribute_names": list(variants_data["all_attributes"].keys()),
            # Search optimization
            "search_keywords": search_keywords,
            # Metadata
            "is_active": getattr(product, "is_active", True),
            "is_featured": getattr(product, "is_featured", False),
            "is_new": self._is_product_new(product),
            "is_on_sale": has_active_discount,
            "created_at": product.created_at.isoformat()
            if hasattr(product, "created_at") and product.created_at
            else None,
            "updated_at": product.updated_at.isoformat()
            if hasattr(product, "updated_at") and product.updated_at
            else None,
            # Analytics
            "view_count": getattr(product, "view_count", 0),
            "sales_count": getattr(product, "sales_count", 0),
            "rating_average": getattr(product, "rating_average", 0.0),
            "rating_count": getattr(product, "rating_count", 0),
        }

        # Semantic embedding — concatenate the most meaningful text fields
        embed_text = " ".join(
            filter(
                None,
                [
                    product.name,
                    product.description,
                    category_name,
                    " ".join(tag_names),
                    brand_name,
                ],
            )
        )
        document["text_embedding"] = EmbeddingService.embed(embed_text)

        return document

    @staticmethod
    def _build_category_path(category) -> List[str]:
        """
        Build hierarchical category path
        Example: ["Electronics", "Computers", "Laptops"]
        """
        path = [category.name]
        current = category

        while hasattr(current, "parent") and current.parent:
            current = current.parent
            path.insert(0, current.name)

        return path

    @staticmethod
    def _is_product_new(product) -> bool:
        """Check if product is new (created in last 30 days)"""
        if not hasattr(product, "created_at") or not product.created_at:
            return False

        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        return product.created_at > thirty_days_ago

    async def index_product(self, product_id: int):
        """Index single product with all relations"""
        product = self._fetch_product_with_relations(product_id)
        if not product:
            logger.warning(f"Product {product_id} not found")
            return

        document = self._product_to_document(product)
        index_name = ProductIndex.get_index_name()

        try:
            await self.es.index(index=index_name, id=str(product_id), document=document)
            logger.info(f"Indexed product: {product_id}")
        except Exception as e:
            logger.error(f"Failed to index product {product_id}: {e}")
            raise

    async def bulk_index_products(
        self,
        batch_size: int = 100,
        limit: int | None = None,
        delay_between_batches: float = 0.5,
    ):
        """
        Optimized bulk index with better memory management
        """
        index_name = ProductIndex.get_index_name()

        count_query = select(func.count(Product.id))
        if limit:
            total = min(limit, self.db.execute(count_query).scalar())
            logger.info(f"Starting bulk index of {total} products (limited)")
        else:
            total = self.db.execute(count_query).scalar()
            logger.info(f"Starting bulk index of {total} products")

        offset = 0
        processed = 0
        errors = []

        while offset < total:
            current_batch_size = min(batch_size, total - offset)

            try:
                statement = (
                    select(Product)
                    .options(
                        selectinload(Product.category),
                        selectinload(Product.brand),
                        selectinload(Product.tags),
                        selectinload(Product.variants)
                        .selectinload(ProductVariant.attribute_variants)
                        .selectinload(AttributeVariant.attribute),
                        selectinload(Product.variants).selectinload(
                            ProductVariant.image
                        ),
                        selectinload(Product.images),
                    )
                    .offset(offset)
                    .limit(current_batch_size)
                )

                result = self.db.execute(statement)
                products = result.scalars().all()

                if not products:
                    logger.warning(f"No products found at offset {offset}")
                    break

                operations = []
                for product in products:
                    try:
                        doc = self._product_to_document(product)
                        json.dumps(doc)
                        operations.append(
                            {"index": {"_index": index_name, "_id": str(product.id)}}
                        )
                        operations.append(doc)
                    except (TypeError, ValueError) as e:
                        logger.error(
                            f"Product {product.id} has non-serializable data: {e}"
                        )
                        # Print the problematic document to see which field is the issue
                        logger.error(f"Document: {doc}")
                        errors.append({"product_id": product.id, "error": str(e)})
                        continue

                if operations:
                    try:
                        response = await self.es.bulk(
                            body=operations, request_timeout=60
                        )

                        if response.get("errors"):
                            logger.error(
                                f"Bulk index had errors in batch {offset}-{offset + current_batch_size}"
                            )

                            for item in response["items"]:
                                if "error" in item.get("index", {}):
                                    error = item["index"]["error"]
                                    logger.error(f"Error: {error}")
                                    errors.append(
                                        {
                                            "product_id": item["index"]["_id"],
                                            "error": error,
                                        }
                                    )
                        else:
                            processed += len(products)
                            logger.info(
                                f"✓ Indexed batch {offset}-{offset + current_batch_size}/{total} ({processed} total)"
                            )

                    except Exception as e:
                        logger.error(
                            f"Bulk index failed for batch {offset}-{offset + current_batch_size}: {e}"
                        )
                        errors.append(
                            {
                                "batch": f"{offset}-{offset + current_batch_size}",
                                "error": str(e),
                            }
                        )

                if delay_between_batches > 0:
                    await asyncio.sleep(delay_between_batches)

            except Exception as e:
                logger.error(
                    f"Failed to fetch batch {offset}-{offset + current_batch_size}: {e}"
                )
                errors.append(
                    {
                        "batch": f"{offset}-{offset + current_batch_size}",
                        "error": str(e),
                    }
                )

            offset += current_batch_size

            if limit and processed >= limit:
                break

            if offset % (batch_size * 5) == 0:
                self.db.commit()

        logger.info(f"Bulk indexing completed. Processed {processed}/{total} products")

        if errors:
            logger.warning(f"Encountered {len(errors)} errors during sync")
            return {
                "status": "completed_with_errors",
                "processed": processed,
                "total": total,
                "errors": errors[:10],
            }

        return {"status": "success", "processed": processed, "total": total}

    async def delete_product(self, product_id: int):
        """Delete product from index"""
        index_name = ProductIndex.get_index_name()

        try:
            await self.es.delete(index=index_name, id=str(product_id), ignore=404)
            logger.info(f"Deleted product from index: {product_id}")
        except Exception as e:
            logger.error(f"Failed to delete product {product_id}: {e}")
