from typing import Dict, Any
from src.config import settings
from src.search.analyzers import CUSTOM_ANALYZERS, CUSTOM_FILTERS
from elasticsearch import AsyncElasticsearch
import logging

logger = logging.getLogger(__name__)


class BaseIndex:
    """Base class for index definitions. Example to create/integrate any Index"""

    INDEX_NAME: str = None

    @classmethod
    def get_index_name(cls) -> str:
        """Get prefixed index name"""
        return f"{settings.ELASTICSEARCH_INDEX_PREFIX}_{cls.INDEX_NAME}"

    @classmethod
    def get_settings(cls) -> Dict[str, Any]:
        """Override for custom index settings"""
        return {
            "number_of_shards": 1,
            "number_of_replicas": 1,
            "analysis": {"analyzer": CUSTOM_ANALYZERS, "filter": CUSTOM_FILTERS},
        }

    @classmethod
    def get_mappings(cls) -> Dict[str, Any]:
        """Override with your field mappings"""
        raise NotImplementedError


class ProductIndex(BaseIndex):
    """Product search index"""

    INDEX_NAME = "products"

    @classmethod
    def get_mappings(cls) -> Dict[str, Any]:
        return {
            "properties": {
                "id": {"type": "keyword"},  # Exact match
                "name": {
                    "type": "text",
                    "analyzer": "standard",
                    "fields": {
                        "keyword": {"type": "keyword"},  # For sorting
                        "autocomplete": {
                            "type": "text",
                            "analyzer": "autocomplete_analyzer",
                            "search_analyzer": "autocomplete_search_analyzer",
                        },
                    },
                },
                "description": {"type": "text", "analyzer": "standard"},
                "price": {"type": "float"},
                "category": {"type": "keyword"},  # For filtering/aggregations
                "tags": {"type": "keyword"},  # Array support
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"},
                "is_active": {"type": "boolean"},
                "metadata": {  # Nested object
                    "type": "object",
                    "enabled": True,
                },
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

    async def create_index(self, index_class: BaseIndex) -> bool:
        """Create index with settings and mappings"""
        index_name = index_class.get_index_name()

        try:
            exists = await self.es.indices.exists(index=index_name)
            if exists:
                logger.info(f"Index {index_name} already exists")
                return False

            await self.es.indices.create(
                index=index_name,
                settings=index_class.get_settings(),
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

    async def recreate_index(self, index_class: BaseIndex):
        """Delete and recreate index"""
        await self.delete_index(index_class)
        await self.create_index(index_class)

    async def update_mapping(self, index_class: BaseIndex):
        """
        Update mapping (only adding new fields is safe)
        For major changes, use recreate_index
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

    async def initialize_all_indices(self):
        """Create all defined indices"""
        indices = [ProductIndex, UserIndex]  # Add your indices here

        for index_class in indices:
            await self.create_index(index_class)
