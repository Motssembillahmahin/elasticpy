from typing import Generic, TypeVar

from pydantic import BaseModel

from src.common.filters import PaginationResponse

T = TypeVar("T")
MESSAGE_201 = "Created successfully"
MESSAGE_200 = "Returned successfully"


class StandardResponse(BaseModel, Generic[T]):
    pagination: PaginationResponse | None
    detail: str
    data: T


def create_response(
    data: list[dict] | dict | list[BaseModel] | BaseModel | None = None,
    message: str = MESSAGE_200,
    pagination: PaginationResponse | None = None,
) -> StandardResponse:
    """Create a standardized response"""
    return StandardResponse(detail=message, data=data, pagination=pagination)
