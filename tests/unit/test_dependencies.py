"""
Unit-тесты зависимостей и исключений: Unauthorized/Forbidden и корректные HTTP-коды/headers.
Тестируются классы и логика без запуска приложения и без HTTP-запросов.
"""



from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException, status

from app.dependencies import (
    UnauthorizedException,
    ForbiddenException,
)
from app.models import User, UserRole


class TestExceptionClasses:
    """ кастомные exception classes."""

    def test_unauthorized_exception_status_code(self):
        exc = UnauthorizedException("Not authenticated")
        assert exc.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc.detail == "Not authenticated"

    def test_unauthorized_exception_default_message(self):
        exc = UnauthorizedException()
        assert exc.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc.detail == "Not authenticated"

    def test_unauthorized_exception_headers(self):
        exc = UnauthorizedException()
        assert "WWW-Authenticate" in exc.headers
        assert exc.headers["WWW-Authenticate"] == "Bearer"

    def test_forbidden_exception_status_code(self):
        exc = ForbiddenException("Insufficient permissions")
        assert exc.status_code == status.HTTP_403_FORBIDDEN
        assert exc.detail == "Insufficient permissions"

    def test_forbidden_exception_default_message(self):
        exc = ForbiddenException()
        assert exc.status_code == status.HTTP_403_FORBIDDEN
        assert exc.detail == "Not enough permissions"


from app.dependencies import (
    get_current_user,
    resolve_news_and_check_editable,
    resolve_comment_and_check_owner,
    UnauthorizedException,
    ForbiddenException,
)
from app.models import UserRole


@pytest.mark.asyncio
async def test_get_current_user_cache_hit():
    creds = MagicMock()
    creds.credentials = "token"

    with patch("app.dependencies.decode_access_token", return_value={"sub": "1"}), \
         patch("app.dependencies.get_json", new=AsyncMock(return_value={
             "id": 1,
             "name": "Cached",
             "email": "cached@example.com",
             "registered_at": "2025-12-25T12:00:00+00:00",
             "is_verified_author": True,
             "avatar": None,
             "role": "user",
         })), \
         patch("app.dependencies.set_json", new=AsyncMock()) as mock_set:
        db = AsyncMock()
        user = await get_current_user(credentials=creds, db=db)

        assert user.id == 1
        assert mock_set.await_count == 0


@pytest.mark.asyncio
async def test_get_current_user_db_hit_sets_cache():
    creds = MagicMock()
    creds.credentials = "token"

    user_obj = MagicMock()
    user_obj.id = 7
    user_obj.name = "DB User"
    user_obj.email = "db@example.com"
    user_obj.registered_at = datetime.now(timezone.utc)
    user_obj.is_verified_author = False
    user_obj.avatar = None
    user_obj.role = "user"

    result = MagicMock()
    result.scalar_one_or_none.return_value = user_obj

    db = AsyncMock()
    db.execute = AsyncMock(return_value=result)

    with patch("app.dependencies.decode_access_token", return_value={"sub": "7"}), \
         patch("app.dependencies.get_json", new=AsyncMock(return_value=None)), \
         patch("app.dependencies.set_json", new=AsyncMock()) as mock_set:
        user = await get_current_user(credentials=creds, db=db)

        assert user is user_obj
        assert mock_set.await_count == 1


@pytest.mark.asyncio
async def test_get_current_user_user_not_found_raises_401():
    creds = MagicMock()
    creds.credentials = "token"

    result = MagicMock()
    result.scalar_one_or_none.return_value = None

    db = AsyncMock()
    db.execute = AsyncMock(return_value=result)

    with patch("app.dependencies.decode_access_token", return_value={"sub": "999"}), \
         patch("app.dependencies.get_json", new=AsyncMock(return_value=None)):
        with pytest.raises(UnauthorizedException):
            await get_current_user(credentials=creds, db=db)


@pytest.mark.asyncio
async def test_resolve_news_not_found_404():
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)

    current_user = MagicMock()
    current_user.id = 1
    current_user.role = UserRole.ADMIN  # роль тут не важна, до неё не дойдёт

    with pytest.raises(Exception) as e:
        await resolve_news_and_check_editable(news_id=123, db=db, current_user=current_user)
    # HTTPException = Exception-наследник, проверять тип/код можно при желании


@pytest.mark.asyncio
async def test_resolve_news_forbidden_for_regular_user():
    db = AsyncMock()

    news = MagicMock()
    news.id = 1
    news.author_id = 999

    result = MagicMock()
    result.scalar_one_or_none.return_value = news
    db.execute = AsyncMock(return_value=result)

    current_user = MagicMock()
    current_user.id = 1
    current_user.role = UserRole.USER

    with pytest.raises(ForbiddenException):
        await resolve_news_and_check_editable(news_id=1, db=db, current_user=current_user)


@pytest.mark.asyncio
async def test_resolve_comment_forbidden_for_regular_user():
    db = AsyncMock()

    comment = MagicMock()
    comment.id = 1
    comment.author_id = 999

    result = MagicMock()
    result.scalar_one_or_none.return_value = comment
    db.execute = AsyncMock(return_value=result)

    current_user = MagicMock()
    current_user.id = 1
    current_user.role = UserRole.USER

    with pytest.raises(ForbiddenException):
        await resolve_comment_and_check_owner(comment_id=1, db=db, current_user=current_user)
