import json
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlmodel import Session
import hashlib

from src.database import get_redis, get_db
from redis.asyncio import Redis
from . import services
from ..common.filters import PaginationParams, PaginationResponse
from ..common.response import StandardResponse, create_response
from ..common.utils import json_serializer

router = APIRouter()

"""Demo APIs to Validate Redis Integration and Data Operations"""


@router.get("/redis-test-product")
async def get_root(redis: Annotated[Redis, Depends(get_redis)]):
    await redis.set("user:1", "John")
    value = await redis.get("user:1")
    return {"value": value}


@router.post("/redis-test-product")
async def set_products(redis: Annotated[Redis, Depends(get_redis)], name: str):
    response = await services.set_product(redis, name)
    return response


"""The following APIs demonstrate how to implement production-level caching using Redis in FastAPI.
You’ll see how product information is fetched efficiently from cache and how updated product details are
 refreshed automatically to ensure data consistency."""


@router.get("")
async def get_products(
    db: Annotated[Session, Depends(get_db)],
    pagination: Annotated[PaginationParams, Depends(PaginationParams)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> StandardResponse:
    cache_key = f"products:page:{pagination.page}:size:{pagination.size}"
    cached_data = await redis.get(cache_key)
    if cached_data:
        print("Calling from Redis - Products List")
        cached_result = json.loads(cached_data)
        response = cached_result["data"]
        total_counts = cached_result["total"]

        pagination_response = PaginationResponse(
            page=pagination.page, size=pagination.size, total=total_counts
        )
        return create_response(
            data=response,
            message="Returned products data successfully (from cache)",
            pagination=pagination_response,
        )
    response, total_counts = services.get_products(db=db, pagination=pagination)

    cache_payload = {"data": response, "total": total_counts}

    await redis.setex(
        cache_key, 300, json.dumps(cache_payload, default=json_serializer)
    )

    pagination_response = PaginationResponse(
        page=pagination.page, size=pagination.size, total=total_counts
    )
    return create_response(
        data=response,
        message="Returned products data successfully",
        pagination=pagination_response,
    )


@router.get("/search")
async def get_products_by_search(
    db: Annotated[Session, Depends(get_db)],
    search: str,
    pagination: Annotated[PaginationParams, Depends(PaginationParams)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> StandardResponse:
    search_hash = hashlib.md5(search.encode()).hexdigest()[:8]
    cache_key = (
        f"products:search:{search_hash}:page:{pagination.page}:size:{pagination.size}"
    )
    cached_data = await redis.get(cache_key)

    if cached_data:
        print(f"Calling from Redis - Search: {search}")
        cached_result = json.loads(cached_data)
        response = cached_result["data"]
        total_counts = cached_result["total"]

        pagination_response = PaginationResponse(
            page=pagination.page, size=pagination.size, total=total_counts
        )
        return create_response(
            data=response,
            message="Returned products data successfully (from cache)",
            pagination=pagination_response,
        )

    print(f"Not Calling Redis - Search: {search}")
    response, total_counts = services.get_products_by_search_with_filter(
        db=db,
        search=search,
        pagination=pagination,
    )
    cache_payload = {"data": response, "total": total_counts}
    await redis.setex(
        cache_key, 600, json.dumps(cache_payload, default=json_serializer)
    )
    pagination_response = PaginationResponse(
        page=pagination.page, size=pagination.size, total=total_counts
    )
    return create_response(
        data=response,
        message="Returned products data successfully",
        pagination=pagination_response,
    )


@router.get("/{slug}")
async def get_product(
    db: Annotated[Session, Depends(get_db)],
    slug: str,
    redis: Annotated[Redis, Depends(get_redis)],
) -> StandardResponse[dict]:
    cache_key = f"product:{slug}"
    cached_data = await redis.get(cache_key)
    if cached_data:
        response = json.loads(cached_data)
        return create_response(response, message="Returned products data successfully")
    response = services.get_product_by_slug(db=db, slug=slug)
    print("Not Calling Redis")
    await redis.setex(cache_key, 3600, json.dumps(response, default=json_serializer))
    return create_response(response, message="Returned products data successfully")


@router.get("/category")
def get_category(
    db: Annotated[Session, Depends(get_db)],
    slug: str,
) -> StandardResponse[dict]:
    return create_response(
        data=services.get_category(db, slug),
        message="Returned category data successfully",
    )


@router.get("/category/top-products")
async def get_category_top_products(
    db: Annotated[Session, Depends(get_db)],
    slug: str,
    redis: Annotated[Redis, Depends(get_redis)],
) -> StandardResponse[dict]:
    cache_key = f"category:top_products:{slug}"

    cached_data = await redis.get(cache_key)

    if cached_data:
        print(f"Calling from Redis - Category Top Products: {slug}")
        response = json.loads(cached_data)
        return create_response(
            response,
            message="Returned category top product data successfully (from cache)",
        )
    response = services.get_category_top_products(
        db,
        slug,
    )
    await redis.setex(cache_key, 1800, json.dumps(response, default=json_serializer))
    return create_response(
        response, message="Returned category top product data successfully"
    )
