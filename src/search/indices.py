from typing import Dict, Any, Optional
from src.config import settings
from src.search.analyzers import CUSTOM_ANALYZERS, CUSTOM_FILTERS
from elasticsearch import AsyncElasticsearch
import logging

from src.search.const import DEFAULT_SHARDS, DEFAULT_REPLICAS

logger = logging.getLogger(__name__)


class BaseIndex:
    """Base class for index definitions. Example to create/integrate any Index"""

    INDEX_NAME: str = None

    @classmethod
    def get_index_name(cls) -> str:
        """Get prefixed index name"""
        return f"{settings.ELASTICSEARCH_INDEX_PREFIX}_{cls.INDEX_NAME}"

    @classmethod
    def get_settings(
        cls, num_of_shards: Optional[int] = None, num_of_replicas: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get index settings with optional shard/replica override.

        Args:
            num_of_shards: Number of primary shards (defaults to DEFAULT_SHARDS)
            num_of_replicas: Number of replicas (defaults to DEFAULT_REPLICAS)
        """
        return {
            "number_of_shards": num_of_shards or DEFAULT_SHARDS,
            "number_of_replicas": num_of_replicas or DEFAULT_REPLICAS,
            "analysis": {"analyzer": CUSTOM_ANALYZERS, "filter": CUSTOM_FILTERS},
        }

    @classmethod
    def get_mappings(cls) -> Dict[str, Any]:
        """Override with your field mappings"""
        raise NotImplementedError


class ProductIndex(BaseIndex):
    INDEX_NAME = "products"

    @classmethod
    def get_mappings(cls) -> Dict[str, Any]:
        return {
            "properties": {
                "id": {"type": "keyword"},
                "name": {
                    "type": "text",
                    "analyzer": "standard",
                    "fields": {
                        "keyword": {"type": "keyword"},
                        "autocomplete": {
                            "type": "text",
                            "analyzer": "autocomplete_analyzer",
                            "search_analyzer": "autocomplete_search_analyzer",
                        },
                    },
                },
                "slug": {"type": "text", "analyzer": "standard"},
                "description": {"type": "text", "analyzer": "standard"},
                "price": {"type": "float"},
                "category": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "keyword"},
                        "name": {
                            "type": "text",
                            "fields": {"keyword": {"type": "keyword"}},
                        },
                        "slug": {"type": "keyword"},
                        "parent_id": {"type": "keyword"},
                    },
                },
                "category_name": {"type": "keyword"},
                "category_path": {"type": "keyword"},
                "tags": {
                    "type": "nested",
                    "properties": {
                        "id": {"type": "keyword"},
                        "name": {
                            "type": "text",
                            "fields": {"keyword": {"type": "keyword"}},
                        },
                    },
                },
                "tag_names": {"type": "keyword"},
                "variants": {
                    "type": "nested",
                    "properties": {
                        "id": {"type": "keyword"},
                        "sku": {"type": "keyword"},
                        "color": {"type": "keyword"},
                        "size": {"type": "keyword"},
                        "price": {"type": "float"},
                        "stock": {"type": "integer"},
                        "is_available": {"type": "boolean"},
                        "attributes": {
                            "type": "object",
                            "enabled": True,
                        },
                    },
                },
                "images": {
                    "type": "nested",
                    "properties": {
                        "id": {"type": "keyword"},
                        "url": {"type": "keyword"},
                        "alt": {"type": "text"},
                        "is_primary": {"type": "boolean"},
                        "order": {"type": "integer"},
                    },
                },
                "min_price": {"type": "float"},
                "max_price": {"type": "float"},
                "total_stock": {"type": "integer"},
                "available_colors": {"type": "keyword"},
                "available_sizes": {"type": "keyword"},
                "primary_image_url": {"type": "keyword"},
                "image_count": {"type": "integer"},
                "variant_count": {"type": "integer"},
                "search_keywords": {
                    "type": "text",
                    "analyzer": "standard",
                },
                "text_embedding": {
                    "type": "dense_vector",
                    "dims": 384,
                    "index": True,
                    "similarity": "cosine",
                },
                "is_active": {"type": "boolean"},
                "is_new": {"type": "boolean"},
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"},
                "view_count": {"type": "integer"},
                "sales_count": {"type": "integer"},
                "rating_average": {"type": "float"},
                "rating_count": {"type": "integer"},
            }
        }


class UserIndex(BaseIndex):
    """User search index"""

    INDEX_NAME = "users"

    @classmethod
    def get_mappings(cls) -> Dict[str, Any]:
        return {
            "properties": {
                "id": {"type": "keyword"},
                "email": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "full_name": {"type": "text", "analyzer": "standard"},
                "role": {"type": "keyword"},
                "created_at": {"type": "date"},
            }
        }


class IndexManager:
    """Manage index lifecycle"""

    def __init__(self, es_client: AsyncElasticsearch):
        self.es = es_client

    async def create_index(
        self,
        index_class: BaseIndex,
        num_of_shards: Optional[int] = None,
        num_of_replicas: Optional[int] = None,
    ) -> bool:
        """
        Create index with settings and mappings.

        Args:
            index_class: Index class to create
            num_of_shards: Number of primary shards (optional)
            num_of_replicas: Number of replicas (optional)
        """
        index_name = index_class.get_index_name()

        try:
            exists = await self.es.indices.exists(index=index_name)
            if exists:
                logger.info(f"Index {index_name} already exists")
                return False

            settings = index_class.get_settings(
                num_of_shards=num_of_shards, num_of_replicas=num_of_replicas
            )

            logger.info(
                f"Creating index {index_name} with "
                f"{settings['number_of_shards']} shards and "
                f"{settings['number_of_replicas']} replicas"
            )

            await self.es.indices.create(
                index=index_name,
                settings=settings,
                mappings=index_class.get_mappings(),
            )
            logger.info(f"Created index: {index_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create index {index_name}: {e}")
            raise

    async def delete_index(self, index_class: BaseIndex) -> bool:
        """Delete index"""
        index_name = index_class.get_index_name()
        try:
            await self.es.indices.delete(index=index_name, ignore_unavailable=True)
            logger.info(f"Deleted index: {index_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete index {index_name}: {e}")
            return False

    async def recreate_index(
        self,
        index_class: BaseIndex,
        num_of_shards: Optional[int] = None,
        num_of_replicas: Optional[int] = None,
    ):
        """Delete and recreate index with new settings"""
        await self.delete_index(index_class)
        await self.create_index(index_class, num_of_shards, num_of_replicas)

    async def update_mapping(self, index_class: BaseIndex):
        """
        Update mapping (only adding new fields is safe).
        For major changes, use recreate_index.
        """
        index_name = index_class.get_index_name()
        try:
            await self.es.indices.put_mapping(
                index=index_name, body=index_class.get_mappings()
            )
            logger.info(f"Updated mapping for: {index_name}")
        except Exception as e:
            logger.error(f"Failed to update mapping for {index_name}: {e}")
            raise

    async def initialize_all_indices(
        self, num_of_shards: Optional[int] = None, num_of_replicas: Optional[int] = None
    ):
        """
        Create all defined indices.

        Args:
            num_of_shards: Number of shards for all indices (optional)
            num_of_replicas: Number of replicas for all indices (optional)
        """
        indices = [ProductIndex, UserIndex]

        for index_class in indices:
            await self.create_index(
                index_class,
                num_of_shards=num_of_shards,
                num_of_replicas=num_of_replicas,
            )
