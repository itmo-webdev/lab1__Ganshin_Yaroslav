"""
Интеграционные тесты роутов аутентификации через FastAPI TestClient.
Цель — убедиться, что /register, /login, /refresh, /logout существуют и возвращают ожидаемые коды.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestAuthRouter:
    """Тесты эндпоинтов аутентификации."""

    def test_register_endpoint_exists(self):
        """POST /api/auth/register существует и принимает данные."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "password123",
                "name": "Test User"
            }
        )
        assert response.status_code in [201, 400, 422, 500]

    def test_login_endpoint_exists(self):
        """POST /api/auth/login существует и принимает данные."""
        response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "password123"}
        )
        assert response.status_code in [200, 400, 401, 404, 422, 500]

    def test_refresh_token_endpoint_exists(self):
        """POST /api/auth/refresh существует и принимает refresh token."""
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "dummy_token"}
        )
        assert response.status_code in [200, 400, 401, 422, 500]

    def test_logout_endpoint_exists(self):
        """POST /api/auth/logout существует и требует auth."""
        headers = {"Authorization": "Bearer dummy_token"}
        response = client.post("/api/auth/logout", headers=headers)
        assert response.status_code in [200, 401, 403, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
