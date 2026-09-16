from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient
from redis.asyncio import Redis

from app import __version__
from app.api.deps import set_runtime
from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging
from app.db import Base
from app.db.session import create_engine_and_sessionmaker
from app.services.vectorstore import VectorStore


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.debug)

    engine, session_factory = create_engine_and_sessionmaker(settings)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    qdrant = AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
    openai_client = AsyncOpenAI(
        api_key=settings.openai_api_key or "missing",
        base_url=settings.openai_base_url,
    )

    if not settings.booking_encryption_key:
        raise RuntimeError(
            "BOOKING_ENCRYPTION_KEY is required. Generate one with: "
            'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )

    await VectorStore(qdrant, settings).ensure_collection()
    set_runtime(session_factory, redis, qdrant, openai_client)

    app.state.engine = engine
    app.state.redis = redis
    app.state.qdrant = qdrant
    yield

    await redis.aclose()
    await qdrant.close()
    await openai_client.close()
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="RAG Interview Backend",
        version=__version__,
        description=(
            "Document ingestion with selectable chunking, Qdrant embeddings, "
            "custom conversational RAG, Redis memory, and encrypted interview booking."
        ),
        lifespan=lifespan,
        debug=settings.debug,
    )

    @application.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @application.get("/")
    async def root() -> dict[str, str]:
        return {"service": application.title, "docs": "/docs", "health": "/api/v1/health"}

    application.include_router(api_router, prefix=settings.api_v1_prefix)
    return application


app = create_app()
