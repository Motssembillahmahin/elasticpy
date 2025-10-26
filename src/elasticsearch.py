from src.config import settings
import logging
from elasticsearch import AsyncElasticsearch

logger = logging.getLogger(__name__)


class ElasticsearchClient:
    """Singleton Elasticsearch client manager"""

    _client: AsyncElasticsearch = None

    @classmethod
    async def get_client(cls) -> AsyncElasticsearch:
        """Get or create async ES client"""
        if cls._client is None:
            cls._client = AsyncElasticsearch(
                hosts=[settings.ELASTICSEARCH_URL],
                basic_auth=("elastic", settings.ELASTICSEARCH_PASSWORD),
                verify_certs=False,  # Disable cert verification for development
                ssl_show_warn=False,  # Suppress SSL warnings
                request_timeout=settings.ELASTICSEARCH_TIMEOUT,
                max_retries=settings.ELASTICSEARCH_MAX_RETRIES,
                retry_on_timeout=True,
            )
            await cls._verify_connection()
        return cls._client

    @classmethod
    async def _verify_connection(cls):
        """Verify ES connection on startup"""
        try:
            info = await cls._client.info()
            logger.info(f"Connected to Elasticsearch: {info['version']['number']}")
        except Exception as e:
            logger.error(f"Failed to connect to Elasticsearch: {e}")
            raise

    @classmethod
    async def close(cls):
        """Close ES client on shutdown"""
        if cls._client:
            await cls._client.close()
            cls._client = None
            logger.info("Elasticsearch connection closed")


# Dependency for FastAPI
async def get_es_client() -> AsyncElasticsearch:
    return await ElasticsearchClient.get_client()
