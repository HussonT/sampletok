"""
Pytest configuration and fixtures for SampleTok tests
"""
import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
from app.core.config import settings
from app.core.database import Base, get_db


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db_engine():
    """Create a test database engine."""
    # Use a test database URL (you may want to configure this separately)
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        future=True
    )

    yield engine

    await engine.dispose()


@pytest.fixture
async def db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    async_session = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create a test client for API requests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_tiktok_url() -> str:
    """Return a sample TikTok URL for testing."""
    return "https://www.tiktok.com/@tiktok/video/7231338487075638570"


@pytest.fixture
def invalid_url() -> str:
    """Return an invalid URL for testing."""
    return "https://www.example.com/not-a-tiktok-video"
