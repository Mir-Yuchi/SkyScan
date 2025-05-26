import asyncio

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

import app.db.session as session_mod
import app.middleware as middleware_mod
from app.db.base import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def engine(event_loop):
    """
    Create one AsyncEngine for all tests
    """
    eng = create_async_engine(
        TEST_DATABASE_URL,
        future=True,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async def _prep_db():
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    event_loop.run_until_complete(_prep_db())
    yield eng
    event_loop.run_until_complete(eng.dispose())


@pytest.fixture(scope="session")
def SessionLocal(engine):
    """
    Our async_sessionmaker bound to that engine.
    """
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest.fixture(autouse=True)
def override_sessionmaker(monkeypatch, SessionLocal):
    """
    Override the sessionmaker in app.db.session and app.middleware
    """
    monkeypatch.setattr(session_mod, "AsyncSessionLocal", SessionLocal)
    monkeypatch.setattr(middleware_mod, "AsyncSessionLocal", SessionLocal)

    async def _get_test_session():
        async with SessionLocal() as s:
            yield s

    monkeypatch.setattr(session_mod, "get_async_session", _get_test_session)


@pytest.fixture
def db_session(event_loop, SessionLocal):

    session = event_loop.run_until_complete(SessionLocal().__aenter__())
    yield session

    event_loop.run_until_complete(session.__aexit__(None, None, None))
