from elasticsearch import AsyncElasticsearch
from typing import List, Dict, Any
from src.search.schemas import (
    SearchRequest,
    SearchResponse,
    SearchHit,
    ProductSearchRequest,
)
from src.search.indices import ProductIndex
import logging

logger = logging.getLogger(__name__)


class SearchService:
    """Core search operations"""

    def __init__(self, es_client: AsyncElasticsearch):
        self.es = es_client

    async def search(self, index_class: type, request: SearchRequest) -> SearchResponse:
        """
        Generic search method

        Query Types:
        - match: Full-text search (analyzed)
        - term: Exact match (not analyzed)
        - range: Numeric/date ranges
        - bool: Combine queries (must, should, must_not, filter)
        - multi_match: Search across multiple fields
        """
        index_name = index_class.get_index_name()

        # Build query
        query = self._build_query(request)

        # Calculate pagination
        from_offset = (request.page - 1) * request.size

        try:
            response = await self.es.search(
                index=index_name,
                query=query,
                from_=from_offset,
                size=request.size,
                sort=request.sort or [{"_score": "desc"}],
                highlight=self._build_highlight(),
                track_total_hits=True,
            )

            return self._parse_response(response, request)

        except Exception as e:
            logger.error(f"Search error in {index_name}: {e}")
            raise

    def _build_query(self, request: SearchRequest) -> Dict[str, Any]:
        """
        Build Elasticsearch query

        Bool Query Structure:
        - must: Clauses that must match (affects scoring)
        - filter: Clauses that must match (no scoring, cached)
        - should: Clauses that boost score if matched
        - must_not: Clauses that must not match
        """
        must_clauses = []
        filter_clauses = []

        # Main search query - multi_match across fields
        if request.query:
            must_clauses.append(
                {
                    "multi_match": {
                        "query": request.query,
                        "fields": [
                            "name^3",
                            "description^2",
                            "tags",
                        ],  # ^3 = boost by 3x
                        "type": "best_fields",  # or: most_fields, cross_fields, phrase
                        "fuzziness": "AUTO",  # Typo tolerance
                    }
                }
            )

        # Apply filters (exact matches, no scoring)
        if request.filters:
            for field, value in request.filters.items():
                if isinstance(value, list):
                    filter_clauses.append({"terms": {field: value}})
                else:
                    filter_clauses.append({"term": {field: value}})

        query = {
            "bool": {
                "must": must_clauses if must_clauses else [{"match_all": {}}],
                "filter": filter_clauses,
            }
        }

        return query

    def _build_highlight(self) -> Dict[str, Any]:
        """Configure result highlighting"""
        return {
            "fields": {"name": {}, "description": {}},
            "pre_tags": ["<mark>"],
            "post_tags": ["</mark>"],
        }

    def _parse_response(
        self, response: Dict[str, Any], request: SearchRequest
    ) -> SearchResponse:
        """Parse ES response into schema"""
        hits = [
            SearchHit(
                id=hit["_id"],
                score=hit["_score"],
                source=hit["_source"],
                highlight=hit.get("highlight"),
            )
            for hit in response["hits"]["hits"]
        ]

        return SearchResponse(
            total=response["hits"]["total"]["value"],
            page=request.page,
            size=request.size,
            hits=hits,
            took=response["took"],
        )

    async def autocomplete(
        self,
        index_class: type,
        query: str,
        field: str = "name.autocomplete",
        size: int = 10,
    ) -> List[str]:
        """Autocomplete suggestions"""
        index_name = index_class.get_index_name()

        response = await self.es.search(
            index=index_name,
            query={"match": {field: {"query": query, "operator": "and"}}},
            size=size,
            _source=[field.split(".")[0]],
        )

        return [hit["_source"][field.split(".")[0]] for hit in response["hits"]["hits"]]

    async def aggregate(
        self, index_class: type, aggregations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run aggregations (analytics)

        Common aggregation types:
        - terms: Group by field values (like SQL GROUP BY)
        - date_histogram: Time-based grouping
        - range: Numeric ranges
        - avg, sum, min, max: Numeric aggregations
        - cardinality: Unique count
        """
        index_name = index_class.get_index_name()

        response = await self.es.search(
            index=index_name,
            size=0,  # Don't return documents
            aggs=aggregations,
        )

        return response.get("aggregations", {})


class ProductSearchService(SearchService):
    """Product-specific search with custom logic"""

    async def search_products(self, request: "ProductSearchRequest") -> SearchResponse:
        """Search products with specific filters"""

        # Build custom query for products
        must_clauses = []
        filter_clauses = [
            {"term": {"is_active": True, "status": "PUBLISHED"}}
        ]  # Only active products

        if request.query:
            must_clauses.append(
                {
                    "multi_match": {
                        "query": request.query,
                        "fields": ["name^3", "description", "category^2"],
                        "fuzziness": "AUTO",
                    }
                }
            )

        # Price range filter
        if request.min_price is not None or request.max_price is not None:
            price_range = {}
            if request.min_price:
                price_range["gte"] = request.min_price
            if request.max_price:
                price_range["lte"] = request.max_price
            filter_clauses.append({"range": {"price": price_range}})

        # Category filter
        if request.categories:
            filter_clauses.append({"terms": {"category": request.categories}})

        # Tags filter
        if request.tags:
            filter_clauses.append({"terms": {"tags": request.tags}})

        index_name = ProductIndex.get_index_name()
        from_offset = (request.page - 1) * request.size

        response = await self.es.search(
            index=index_name,
            query={
                "bool": {
                    "must": must_clauses if must_clauses else [{"match_all": {}}],
                    "filter": filter_clauses,
                }
            },
            from_=from_offset,
            size=request.size,
            highlight={"fields": {"name": {}, "description": {}}},
        )

        return self._parse_response(response, request)

    async def get_facets(self) -> Dict[str, Any]:
        """Get aggregations for filters (categories, price ranges, etc.)"""
        aggregations = {
            "categories": {"terms": {"field": "category", "size": 50}},
            "price_ranges": {
                "range": {
                    "field": "price",
                    "ranges": [
                        {"to": 10},
                        {"from": 10, "to": 50},
                        {"from": 50, "to": 100},
                        {"from": 100},
                    ],
                }
            },
            "popular_tags": {"terms": {"field": "tags", "size": 20}},
        }

        return await self.aggregate(ProductIndex, aggregations)
