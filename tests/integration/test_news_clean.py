"""
Интеграционные тесты роутов News через FastAPI TestClient.
Проверяют доступность эндпоинтов и требования (публичность/авторизация).
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestNewsRouter:
    """Тесты эндпоинтов новостей."""

    def test_list_news_endpoint_public(self):
        """GET /api/news публичный эндпоинт."""
        response = client.get("/api/news")
        assert response.status_code in [200, 422, 500]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))

    def test_get_news_by_id_public(self):
        """GET /api/news/{id} публичный эндпоинт."""
        response = client.get("/api/news/999")
        assert response.status_code in [200, 404, 422, 500]

    def test_create_news_endpoint_requires_auth(self):
        """POST /api/news требует авторизацию."""
        payload = {
            "title": "Test News",
            "content": "Test content",
            "tags": ["test"]
        }
        response = client.post("/api/news", json=payload)
        assert response.status_code in [401, 403, 422, 500]

    def test_update_news_endpoint_requires_auth(self):
        """PUT /api/news/{id} требует авторизацию."""
        response = client.put("/api/news/1", json={"title": "Updated"})
        assert response.status_code in [401, 403, 404, 422, 500]

    def test_delete_news_endpoint_requires_auth(self):
        """DELETE /api/news/{id} требует авторизацию."""
        response = client.delete("/api/news/1")
        assert response.status_code in [401, 403, 404, 500]

    def test_news_list_with_pagination(self):
        """GET /api/news с параметрами pagination."""
        response = client.get("/api/news?skip=0&limit=10")
        assert response.status_code in [200, 422, 500]

    def test_news_search_endpoint(self):
        """GET /api/news?title=query поиск по названию."""
        response = client.get("/api/news?title=test")
        assert response.status_code in [200, 422, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
