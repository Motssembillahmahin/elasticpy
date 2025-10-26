from fastapi import HTTPException, status


class HTTP400(HTTPException):
    def __init__(self, detail: str) -> None:
        """Raise HTTP 400 exception"""
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class HTTP404(HTTPException):
    def __init__(self, detail: str) -> None:
        """Raise HTTP 404 exception"""
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class HTTP500(HTTPException):
    def __init__(self, detail: str) -> None:
        """Raise HTTP 500 exception"""
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail
        )
