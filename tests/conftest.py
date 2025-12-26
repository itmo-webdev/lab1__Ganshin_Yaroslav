# tests/conftest.py (complete version with fixes)
import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncGenerator

os.environ["TESTING"] = "1"
os.environ["JWT_SECRET"] = "test_secret_key_123"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://localhost/test_none"
os.environ["REDIS_URL"] = "redis://localhost:9999/99"

with patch('sqlalchemy.ext.asyncio.create_async_engine') as mock_engine:
    mock_engine.return_value = MagicMock(
        begin=MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=AsyncMock()),
            __aexit__=AsyncMock(return_value=None)
        )),
        dispose=AsyncMock()
    )

    from app.main import app
    from fastapi.testclient import TestClient
    from httpx import AsyncClient, ASGITransport

from app.db import get_db
from app.models import User, News, Comment
from app.security import hash_password, create_access_token
from datetime import datetime, timezone

@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.get = AsyncMock()
    session.add = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.close = AsyncMock()
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock()
    mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock()))
    
    session.execute.return_value = mock_result
    
    return session

@pytest.fixture
def test_user():
    return User(
        id=1,
        name="Test User",
        email="test@example.com",
        password_hash=hash_password("TestPass123!"),
        is_verified_author=True,
        avatar=None,
        role="user",
        registered_at=datetime.now(timezone.utc)
    )

@pytest.fixture
def admin_user():
    return User(
        id=2,
        name="Admin User",
        email="admin@example.com",
        password_hash=hash_password("AdminPass123!"),
        is_verified_author=True,
        avatar=None,
        role="admin",
        registered_at=datetime.now(timezone.utc)
    )

@pytest.fixture
def auth_headers(test_user):
    token = create_access_token(test_user.id, test_user.role)
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def admin_headers(admin_user):
    token = create_access_token(admin_user.id, admin_user.role)
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def mock_cache(monkeypatch):
    monkeypatch.setattr("app.cache.get_json", AsyncMock(return_value=None))
    monkeypatch.setattr("app.cache.set_json", AsyncMock())
    monkeypatch.setattr("app.cache.delete", AsyncMock())
    monkeypatch.setattr("app.cache.delete_by_prefix", AsyncMock())

@pytest.fixture
async def async_client(mock_db_session):
    async def override_get_db():
        yield mock_db_session
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()
    
    
    
    
    
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

@pytest.fixture
def client():
    """FastAPI протестируем клиента."""
    from app.main import app
    return TestClient(app)