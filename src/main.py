from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from src.config import app_configs, settings


from starlette.middleware.cors import CORSMiddleware

from src.database import init_redis_pool, close_redis_pool

from src.product.routes import router as product_router

if TYPE_CHECKING:
    pass


from contextlib import asynccontextmanager
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(_application: FastAPI) -> AsyncGenerator:
    # Startup
    await init_redis_pool()
    yield
    # Shutdown
    await close_redis_pool()


app = FastAPI(
    **app_configs,
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True},
)

app.include_router(
    product_router,
    prefix="/product",
    tags=["Product"],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGINS_REGEX,
    allow_credentials=True,
    allow_methods=("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"),
    allow_headers=settings.CORS_HEADERS,
)


@app.get("/healthcheck", include_in_schema=False)
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
