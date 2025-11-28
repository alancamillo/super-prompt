"""Fixtures compartilhadas para testes."""

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from ..core.database import Base, get_db
from ..core.cache import CacheService
from ..main import app


# Engine de teste (SQLite em memória)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """Cria event loop para sessão de testes."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Cria sessão de banco para testes."""
    # Cria tabelas
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestSessionLocal() as session:
        yield session
    
    # Limpa tabelas após teste
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Cliente HTTP para testes."""
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    
    app.dependency_overrides.clear()


class MockCacheService(CacheService):
    """Cache mock para testes."""
    
    def __init__(self):
        self._cache = {}
        self.ttl = 3600
        self.prefix = "test:"
    
    async def get(self, key: str) -> dict | None:
        return self._cache.get(self._make_key(key))
    
    async def set(self, key: str, value: dict, ttl: int | None = None) -> bool:
        self._cache[self._make_key(key)] = value
        return True
    
    async def delete(self, key: str) -> bool:
        key = self._make_key(key)
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def clear(self):
        self._cache.clear()


@pytest.fixture
def mock_cache() -> MockCacheService:
    """Cache mock para testes."""
    return MockCacheService()

