from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()
engine_options: dict[str, object] = {"pool_pre_ping": True}
if not settings.sqlalchemy_database_url.startswith("sqlite"):
    engine_options.update(pool_recycle=300, pool_size=5, max_overflow=0)
engine = create_async_engine(settings.sqlalchemy_database_url, **engine_options)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
