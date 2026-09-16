from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings


def create_engine_and_sessionmaker(settings: Settings) -> tuple:
    engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, session_factory


async def get_session(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session
