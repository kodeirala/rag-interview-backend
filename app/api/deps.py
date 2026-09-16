from collections.abc import AsyncIterator

from fastapi import Depends
from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.core.security import PIICipher
from app.services.booking import BookingService
from app.services.embeddings import EmbeddingClient
from app.services.ingest import IngestService
from app.services.llm import LLMClient
from app.services.memory import ChatMemory
from app.services.rag import RAGService
from app.services.vectorstore import VectorStore

_session_factory: async_sessionmaker[AsyncSession] | None = None
_redis: Redis | None = None
_qdrant: AsyncQdrantClient | None = None
_openai: AsyncOpenAI | None = None


def set_runtime(
    session_factory: async_sessionmaker[AsyncSession],
    redis: Redis,
    qdrant: AsyncQdrantClient,
    openai_client: AsyncOpenAI,
) -> None:
    global _session_factory, _redis, _qdrant, _openai
    _session_factory = session_factory
    _redis = redis
    _qdrant = qdrant
    _openai = openai_client


async def get_db() -> AsyncIterator[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Database session factory is not initialized")
    async with _session_factory() as session:
        yield session


def get_redis() -> Redis:
    if _redis is None:
        raise RuntimeError("Redis is not initialized")
    return _redis


def get_qdrant() -> AsyncQdrantClient:
    if _qdrant is None:
        raise RuntimeError("Qdrant is not initialized")
    return _qdrant


def get_openai() -> AsyncOpenAI:
    if _openai is None:
        raise RuntimeError("OpenAI client is not initialized")
    return _openai


def get_ingest_service(
    session: AsyncSession = Depends(get_db),
    openai_client: AsyncOpenAI = Depends(get_openai),
    qdrant: AsyncQdrantClient = Depends(get_qdrant),
    settings: Settings = Depends(get_settings),
) -> IngestService:
    return IngestService(
        session=session,
        embeddings=EmbeddingClient(openai_client, settings),
        vectors=VectorStore(qdrant, settings),
        settings=settings,
    )


def get_rag_service(
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    openai_client: AsyncOpenAI = Depends(get_openai),
    qdrant: AsyncQdrantClient = Depends(get_qdrant),
    settings: Settings = Depends(get_settings),
) -> RAGService:
    memory = ChatMemory(redis, settings)
    return RAGService(
        memory=memory,
        embeddings=EmbeddingClient(openai_client, settings),
        vectors=VectorStore(qdrant, settings),
        llm=LLMClient(openai_client, settings),
        booking=BookingService(session, memory, PIICipher(settings)),
        settings=settings,
    )
