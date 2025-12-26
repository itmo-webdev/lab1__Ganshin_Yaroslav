"""
Юнит-тесты для функций безопасности (хеширование паролей, JWT-токены).

Охватывает:
- hash_password() и verify_password() (bcrypt)
- create_access_token() и decode_access_token() (JWT)
"""

import pytest
from app.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)


class TestSecurityFunctions:
    """Тесты функций безопасности."""

    # ==================== ХЕШИРОВАНИЕ ====================

    def test_hash_password(self):
        """Хеширование создаёт валидный хеш."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        assert hashed is not None
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password

    def test_verify_password_correct(self):
        """Верификация с правильным паролем — успех."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        assert verify_password(hashed, password) is True

    def test_verify_password_incorrect(self):
        """Верификация с неправильным паролем — fail."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        assert verify_password(hashed, "WrongPassword") is False

    def test_password_hash_different_each_time(self):
        """Хеш одного пароля каждый раз разный (salt)."""
        password = "TestPassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2
        assert verify_password(hash1, password)
        assert verify_password(hash2, password)

    # ==================== JWT ТОКЕНЫ ====================

    def test_create_access_token(self):
        """Создание JWT-токена."""
        user_id = 1
        role = "user"
        token = create_access_token(user_id, role)
        assert token is not None
        assert isinstance(token, str)
        assert token.count(".") == 2

    def test_decode_access_token(self):
        """Декодирование JWT-токена."""
        user_id = 1
        role = "user"
        token = create_access_token(user_id, role)
        decoded = decode_access_token(token)
        assert decoded is not None
        assert decoded["sub"] == str(user_id)
        assert decoded["role"] == role

    def test_create_access_token_admin_role(self):
        """Токен с admin-ролью."""
        token = create_access_token(user_id=1, role="admin")
        assert token is not None
        decoded = decode_access_token(token)
        assert decoded["role"] == "admin"

    def test_create_access_token_different_users(self):
        """Токены разных пользователей — разные."""
        token1 = create_access_token(user_id=1, role="user")
        token2 = create_access_token(user_id=2, role="user")
        assert token1 != token2
        assert decode_access_token(token1)["sub"] == "1"
        assert decode_access_token(token2)["sub"] == "2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
