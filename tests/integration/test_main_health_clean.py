"""
Интеграционные тесты основных эндпоинтов приложения: / и /health.
Проверяют структуру ответа и статус 200.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestBasicEndpoints:
    """Тесты основных публичных эндпоинтов."""

    def test_root_endpoint_returns_message(self):
        """GET / возвращает 200 с message."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_root_endpoint_structure(self):
        """GET / возвращает структуру с required полями."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data
        assert "health" in data
        assert data["message"] == "News API"
        assert data["version"] == "1.0.0"

    def test_health_endpoint_returns_status(self):
        """GET /health возвращает 200 с status и components."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "components" in data
        assert "timestamp" in data
        assert isinstance(data["components"], dict)

    def test_health_endpoint_has_timestamp(self):
        """GET /health включает timestamp."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert len(data["timestamp"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
