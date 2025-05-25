from typing import AsyncGenerator, cast

from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

engine = create_async_engine(
    str(settings.database_url),
    echo=True,
    future=True,
)

AsyncSessionLocal = sessionmaker(
    bind=cast(Engine, engine),
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides an async database session.

    :return: AsyncSession instance
    """
    async with AsyncSessionLocal() as session:
        yield session
