from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session
from elasticsearch import AsyncElasticsearch
from typing import Optional

from src.database import get_db
from src.es_client import get_es_client
from src.database import SessionLocal
from src.search.sync import ProductSyncService
from src.search.indices import IndexManager, ProductIndex

router = APIRouter(prefix="/admin/elasticsearch", tags=["admin", "elasticsearch"])


@router.post("/init")
async def initialize_indices(es: AsyncElasticsearch = Depends(get_es_client)):
    """
    Initialize Elasticsearch indices

    Creates all index mappings and settings
    """
    try:
        manager = IndexManager(es)
        await manager.create_index(ProductIndex)

        return {"status": "success", "message": "Indices initialized successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/products")
async def sync_products_endpoint(
    background_tasks: BackgroundTasks,
    limit: Optional[int] = None,
    batch_size: int = 500,
    es: AsyncElasticsearch = Depends(get_es_client),
):
    """
    Sync products to Elasticsearch in background

    - **limit**: Number of products to sync (default: all)
    - **batch_size**: Batch size for bulk operations (default: 500)
    """

    async def sync_task():
        from src.database import SessionLocal

        db_session = SessionLocal()

        try:
            sync_service = ProductSyncService(db=db_session, es_client=es)
            await sync_service.bulk_index_products(batch_size=batch_size)
        except Exception as e:
            print(f"Sync failed: {e}")
            raise
        finally:
            db_session.close()

    # Add to background tasks
    background_tasks.add_task(sync_task)

    return {
        "status": "started",
        "message": f"Syncing {'all' if not limit else limit} products in background",
        "batch_size": batch_size,
    }


@router.post("/sync/products/{product_id}")
async def sync_single_product(
    product_id: int,
    es: AsyncElasticsearch = Depends(get_es_client),
):
    """
    Sync single product to Elasticsearch immediately
    """
    # Verify ES connection first
    try:
        await es.ping()
    except Exception as e:
        raise HTTPException(
            status_code=503, detail=f"Elasticsearch is not available: {str(e)}"
        )

    db = SessionLocal()

    try:
        sync_service = ProductSyncService(db=db, es_client=es)
        await sync_service.index_product(product_id)

        return {
            "status": "success",
            "message": f"Product {product_id} synced successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/products/{product_id}")
async def get_product_from_index(
    product_id: int,
    es: AsyncElasticsearch = Depends(get_es_client),
):
    """
    Get product from Elasticsearch index
    """
    index_name = ProductIndex.get_index_name()

    try:
        result = await es.get(index=index_name, id=str(product_id))

        return {
            "id": result["_id"],
            "found": result["found"],
            "source": result["_source"],
        }
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=404,
                detail=f"Product {product_id} not found in Elasticsearch",
            )
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/products/{product_id}")
async def delete_product_from_index(
    product_id: int,
    db: Session = Depends(get_db),
    es: AsyncElasticsearch = Depends(get_es_client),
):
    """
    Delete product from Elasticsearch index
    """
    sync_service = ProductSyncService(db=db, es_client=es)

    try:
        await sync_service.delete_product(product_id)
        return {
            "status": "success",
            "message": f"Product {product_id} deleted from index",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def elasticsearch_health(es: AsyncElasticsearch = Depends(get_es_client)):
    """
    Check Elasticsearch cluster health
    """
    try:
        health = await es.cluster.health()

        # Try to get product index stats
        index_name = ProductIndex.get_index_name()
        try:
            stats = await es.indices.stats(index=index_name)
            product_stats = stats["indices"].get(index_name, {})
            doc_count = product_stats.get("total", {}).get("docs", {}).get("count", 0)
        except Exception as _:
            doc_count = 0

        return {
            "status": health["status"],
            "cluster_name": health["cluster_name"],
            "number_of_nodes": health["number_of_nodes"],
            "active_shards": health["active_shards"],
            "product_count": doc_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reindex-status")
async def get_reindex_status(es: AsyncElasticsearch = Depends(get_es_client)):
    """
    Get reindexing task status (if running)
    """
    try:
        tasks = await es.tasks.list(detailed=True, actions="*reindex")
        return {"running_tasks": len(tasks.get("nodes", {})), "tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
