"""
Тесты обработки ошибок API (интеграционные).

Проверяют, что API корректно валидирует входные данные и возвращает “грейсфул”
ошибки на пограничные случаи (не отдаёт 500 там, где должен быть 4xx).
"""

import pytest
from httpx import AsyncClient
from app.main import app


class TestApiErrors:
    """Проверка обработки ошибок и валидации в API."""

    @pytest.mark.asyncio
    async def test_invalid_json_payload(self):
        """Невалидный JSON должен возвращать 400/422, а не 500."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/auth/register",
                content="{invalid json}",
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code in (400, 422), f"Got {response.status_code}, expected 400 or 422"

    @pytest.mark.asyncio
    async def test_missing_required_fields(self):
        """Отсутствие обязательных полей должно давать 422, а не 500."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/auth/register",
                json={"email": "test@example.com"}  # missing password and name
            )
            assert response.status_code == 422, f"Got {response.status_code}, expected 422"

    
    
    @pytest.mark.asyncio
    async def test_empty_request_body_json(self):
        """Пустой JSON-объект не должен приводить к 500."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/auth/register",
                json={}
            )
            assert response.status_code in (400, 422), f"Got {response.status_code}"

    @pytest.mark.asyncio
    async def test_null_values_in_json(self):
        """Null-значения в JSON должны обрабатываться корректно (без 500)."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/auth/register",
                json={
                    "email": None,
                    "password": None,
                    "name": None
                }
            )
            assert response.status_code in (400, 422), f"Got {response.status_code}"

    @pytest.mark.asyncio
    async def test_numeric_values_for_string_fields(self):
        """Неверные типы данных (числа вместо строк) должны давать 422."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/auth/register",
                json={
                    "email": 12345,
                    "password": 98765,
                    "name": 11111
                }
            )
            assert response.status_code == 422, f"Got {response.status_code}, expected 422"

    @pytest.mark.asyncio
    async def test_very_long_email_field(self):
        """Очень длинный email не должен приводить к 500."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            long_email = "a" * 1000 + "@example.com"
            response = await client.post(
                "/api/auth/register",
                json={
                    "email": long_email,
                    "password": "Pass123!",
                    "name": "Test"
                }
            )
            # Should either reject or pass, not 500
            assert response.status_code != 500, "Should handle long email gracefully"

    @pytest.mark.asyncio
    async def test_unauthorized_access_returns_401(self):
        """Неавторизованный доступ должен возвращать 401, а не 500."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/users/me",
                headers={"Authorization": "Bearer invalid_token"}
            )
            assert response.status_code == 401, f"Got {response.status_code}, expected 401"

    @pytest.mark.asyncio
    async def test_wrong_http_method_returns_405(self):
        """Неправильный HTTP-метод должен возвращать 405, а не 500."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.put(
                "/api/auth/register",
                json={"email": "test@example.com", "password": "pass"}
            )
            assert response.status_code == 405, f"Got {response.status_code}, expected 405"
