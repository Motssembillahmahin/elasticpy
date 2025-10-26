from enum import StrEnum


class ProductType(StrEnum):
    SIMPLE = "SIMPLE"
    VARIABLE = "VARIABLE"


class ProductStatus(StrEnum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class ProductReviewType(StrEnum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"


class StockStatus(StrEnum):
    IN_STOCK = "IN_STOCK"
    OUT_OF_STOCK = "OUT_OF_STOCK"


class ReturnPolicy(StrEnum):
    INSTANT = "INSTANT"
    DAYS_3 = "3_DAYS"
    DAYS_7 = "7_DAYS"


class ExchangePolicy(StrEnum):
    NOT_EXCHANGEABLE = "NOT_EXCHANGEABLE"
    DAYS_3 = "3_DAYS"
    DAYS_7 = "7_DAYS"
