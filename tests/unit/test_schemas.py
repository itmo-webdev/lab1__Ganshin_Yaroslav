"""Тесты для схем Pydantic."""

from datetime import datetime
from app.schemas import (
    UserCreate, UserOut, NewsCreate, NewsUpdate, NewsOut,
    CommentCreate, CommentUpdate, CommentOut, TokenOut,
    RegisterIn, LoginIn, RefreshIn
)
import pytest


def test_user_create_schema():
    """Тест схемы создания пользователя."""
    user_data = {
        "name": "Test User",
        "email": "test@example.com",
        "password": "password123"
    }
    user = UserCreate(**user_data)
    assert user.name == "Test User"
    assert user.email == "test@example.com"
    assert user.password == "password123"


def test_user_out_schema():
    """Тест схемы вывода пользователя."""
    user_data = {
        "id": 1,
        "name": "Test User",
        "email": "test@example.com",
        "registered_at": datetime.now(),
        "is_verified_author": True,
        "avatar": "http://example.com/avatar.jpg",
        "role": "user"
    }
    user = UserOut(**user_data)
    assert user.id == 1
    assert user.name == "Test User"
    assert user.email == "test@example.com"


def test_news_create_schema():
    """Тест схемы создания новости."""
    news_data = {
        "title": "Test News",
        "content": {"text": "Test content", "images": []},
        "cover": "http://example.com/cover.jpg"
    }
    news = NewsCreate(**news_data)
    assert news.title == "Test News"
    assert news.content == {"text": "Test content", "images": []}
    assert news.cover == "http://example.com/cover.jpg"


def test_comment_create_schema():
    """Тест схемы создания комментария."""
    comment_data = {
        "text": "Test comment"
    }
    comment = CommentCreate(**comment_data)
    assert comment.text == "Test comment"


def test_token_out_schema():
    """Тест схемы вывода токена."""
    token_data = {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "token_type": "bearer"
    }
    token = TokenOut(**token_data)
    assert token.access_token == "test_access_token"
    assert token.refresh_token == "test_refresh_token"
    assert token.token_type == "bearer"


def test_register_in_schema():
    """Тест схемы регистрации."""
    # Корректные данные
    register_data = {
        "name": "Test User",
        "email": "test@example.com",
        "password": "TestPassword123!"
    }
    register = RegisterIn(**register_data)
    assert register.name == "Test User"
    assert register.email == "test@example.com"
    assert register.password == "TestPassword123!"
    
    # Тест валидации пароля
    with pytest.raises(ValueError):
        RegisterIn(name="Test", email="test@example.com", password="weak")


def test_login_in_schema():
    """Тест схемы входа."""
    login_data = {
        "email": "test@example.com",
        "password": "TestPassword123!"
    }
    login = LoginIn(**login_data)
    assert login.email == "test@example.com"
    assert login.password == "TestPassword123!"


def test_refresh_in_schema():
    """Тест схемы обновления токена."""
    refresh_data = {
        "refresh_token": "test_refresh_token"
    }
    refresh = RefreshIn(**refresh_data)
    assert refresh.refresh_token == "test_refresh_token"
    
def test_register_password_validation():
    """Тест валидации пароля при регистрации."""
    # Тестируем все случаи валидации
    test_cases = [
        ("Weak1!", "без строчной буквы", False),
        ("weak1!", "без заглавной буквы", False),
        ("WeakPass!", "без цифры", False),
        ("WeakPass1", "без спецсимвола", False),
        ("TestPass123!", "корректный пароль", True),
    ]
    
    for password, description, should_pass in test_cases:
        if should_pass:
            # Должен пройти
            RegisterIn(
                name="Test", 
                email="test@example.com", 
                password=password
            )
        else:
            # Должен вызвать ошибку
            with pytest.raises(ValueError):
                RegisterIn(
                    name="Test", 
                    email="test@example.com", 
                    password=password
                )

def test_user_create_without_password():
    """Тест создания пользователя без пароля."""
    user_data = {
        "name": "Test User",
        "email": "test@example.com",
        # password специально не передаем
    }
    user = UserCreate(**user_data)
    assert user.password is None
    assert user.name == "Test User"
    assert user.is_verified_author is False  # По умолчанию False