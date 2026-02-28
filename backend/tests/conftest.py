import asyncio
import os
import uuid
from collections.abc import AsyncGenerator, Generator
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.dependencies import get_async_session
from app.core.rate_limit import limiter
from app.db.base import Base
from app.db.models import GeneratedContent, Source, Transcript, Validation  # noqa: F401
from app.main import app

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    settings.database_url,
)

limiter.enabled = False


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_async_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def mock_llm() -> MagicMock:
    llm = MagicMock()
    llm.complete.return_value = "Generated text"
    llm.complete_json.return_value = {
        "checks": [
            {"name": "policy_risk", "passed": True, "details": "ok"},
            {"name": "hallucination", "passed": True, "details": "ok"},
            {"name": "tone_mismatch", "passed": True, "details": "ok"},
        ]
    }
    return llm


@pytest.fixture
def sample_source_id() -> uuid.UUID:
    return uuid.uuid4()
