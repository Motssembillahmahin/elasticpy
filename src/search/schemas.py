from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class SearchRequest(BaseModel):
    """Base search request"""

    query: str = Field(..., min_length=1, description="Search query")
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(10, ge=1, le=100, description="Results per page")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filters")
    sort: Optional[List[Dict[str, str]]] = Field(None, description="Sort options")


class ProductSearchRequest(SearchRequest):
    """Product-specific search"""

    categories: Optional[List[str]] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    tags: Optional[List[str]] = None


class SearchHit(BaseModel):
    """Single search result"""

    id: str
    score: float
    source: Dict[str, Any]
    highlight: Optional[Dict[str, List[str]]] = None


class SearchResponse(BaseModel):
    """Search response with pagination"""

    total: int
    page: int
    size: int
    hits: List[SearchHit]
    took: int  # Query time in ms
    aggregations: Optional[Dict[str, Any]] = None
