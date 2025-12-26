"""
Unit-тесты модуля app.cache: работа с Redis обёртками (get/set/mget/sets/delete_by_prefix).
Redis полностью замокан (AsyncMock), поэтому тесты не требуют реального Redis.
"""


import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from app.cache import (
    get_redis,
    get_json,
    set_json,
    delete,
    mget_json,
    sadd,
    srem,
    smembers,
    delete_by_prefix,
)


class TestRedisConnection:
    """Test Redis связь и менеджмент."""

    @pytest.mark.asyncio
    async def test_get_redis_first_call(self):
        """Test  get_redis initializes connection по первому вызову."""
        with patch('app.cache.redis.from_url') as mock_from_url:
            mock_redis_instance = AsyncMock()
            mock_from_url.return_value = mock_redis_instance
            
            # Reset global state
            import app.cache
            app.cache._redis = None
            
            result = await get_redis()
            assert result is not None
            mock_from_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_redis_caches_connection(self):
        """Test that get_redis кеширует."""
        with patch('app.cache.redis.from_url') as mock_from_url:
            mock_redis_instance = AsyncMock()
            mock_from_url.return_value = mock_redis_instance
            
            import app.cache
            app.cache._redis = None
            
            result1 = await get_redis()
            result2 = await get_redis()
            
       
            assert mock_from_url.call_count == 1
            assert result1 is result2

    @pytest.mark.asyncio
    async def test_get_redis_uses_env_url(self):
        """Test that get_redis исплользует REDIS_URL из среды окружения"""
        with patch('app.cache.redis.from_url') as mock_from_url:
            with patch.dict('os.environ', {'REDIS_URL': 'redis://custom:6379/1'}):
                mock_redis_instance = AsyncMock()
                mock_from_url.return_value = mock_redis_instance
                
                import app.cache
                app.cache._redis = None
                
                await get_redis()
                mock_from_url.assert_called_once_with(
                    'redis://custom:6379/1',
                    decode_responses=True
                )


class TestGetJson:
    """Test JSON из кеша"""

    @pytest.mark.asyncio
    async def test_get_json_cache_hit(self):
        """Test успешное  JSON retrieval from cache."""
        test_data = {"user_id": 1, "name": "John"}
        with patch('app.cache.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.get.return_value = json.dumps(test_data)
            mock_get_redis.return_value = mock_redis
            
            result = await get_json("user:1")
            
            assert result == test_data
            mock_redis.get.assert_called_once_with("user:1")

    @pytest.mark.asyncio
    async def test_get_json_cache_miss(self):
        """Test cache miss returns None."""
        with patch('app.cache.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.get.return_value = None
            mock_get_redis.return_value = mock_redis
            
            result = await get_json("nonexistent:key")
            
            assert result is None
            mock_redis.get.assert_called_once_with("nonexistent:key")

    @pytest.mark.asyncio
    async def test_get_json_invalid_json(self):
        """Test невалидный JSON возвращает None."""
        with patch('app.cache.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.get.return_value = "invalid json {{{["
            mock_get_redis.return_value = mock_redis
            
            result = await get_json("bad:json")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_get_json_complex_object(self):
        """Test успешное извл сложн объекта"""
        test_data = {
            "user": {
                "id": 1,
                "profile": {
                    "name": "Alice",
                    "tags": ["admin", "verified"],
                    "metadata": None
                }
            }
        }
        with patch('app.cache.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.get.return_value = json.dumps(test_data)
            mock_get_redis.return_value = mock_redis
            
            result = await get_json("complex:object")
            
            assert result == test_data
            assert result["user"]["profile"]["tags"] == ["admin", "verified"]


class TestSetJson:
    """Test JSON хор в кеш."""

    @pytest.mark.asyncio
    async def test_set_json_with_ttl(self):
        """Test setting JSON value with TTL."""
        test_data = {"key": "value"}
        with patch('app.cache.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis
            
            await set_json("test:key", test_data, ttl_seconds=300)
            
            mock_redis.set.assert_called_once()
            call_args = mock_redis.set.call_args
            assert call_args[0][0] == "test:key"
            assert call_args[1]['ex'] == 300

    @pytest.mark.asyncio
    async def test_set_json_without_ttl(self):
        """Testустановку значения без TTL."""
        test_data = {"key": "value"}
        with patch('app.cache.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis
            
            await set_json("persistent:key", test_data)
            
            mock_redis.set.assert_called_once()
            call_args = mock_redis.set.call_args
            assert call_args[0][0] == "persistent:key"

    @pytest.mark.asyncio
    async def test_set_json_serialization(self):
        """Test что data корректно JSON serialized."""
        test_data = {"timestamp": "2025-12-25T15:00:00", "value": 42}
        with patch('app.cache.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis
            
            await set_json("test:data", test_data, ttl_seconds=600)
            
            call_args = mock_redis.set.call_args
            stored_json = call_args[0][1]
            parsed = json.loads(stored_json)
            assert parsed == test_data

    @pytest.mark.asyncio
    async def test_set_json_with_unicode(self):
        """А если установить  JSON с Unicode characters."""
        test_data = {"name": "Иван", "city": "Москва", "emoji": "🎉"}
        with patch('app.cache.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis
            
            await set_json("unicode:test", test_data)
            
            call_args = mock_redis.set.call_args
            stored_json = call_args[0][1]
            # ensure_ascii=False means Unicode is preserved
            assert "Иван" in stored_json or "\\u" in stored_json


class TestDelete:
    """Test Кеш deletion."""

    @pytest.mark.asyncio
    async def test_delete_key(self):
        """deleting a cache key."""
        with patch('app.cache.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis
            
            await delete("test:key")
            
            mock_redis.delete.assert_called_once_with("test:key")

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(self):
        """ deleting non-existent key не ошибка."""
        with patch('app.cache.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.delete.return_value = 0  # Key didn't exist
            mock_get_redis.return_value = mock_redis
            
            # Should not raise
            await delete("nonexistent:key")
            mock_redis.delete.assert_called_once()


class TestMgetJson:
    """Test batch JSON retrieval."""

    @pytest.mark.asyncio
    async def test_mget_json_all_hit(self):
        """Test retrieving мульти-ключи  with all hits."""
        data = [
            {"user_id": 1},
            {"user_id": 2},
            {"user_id": 3},
        ]
        with patch('app.cache.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.mget.return_value = [
                json.dumps(data[0]),
                json.dumps(data[1]),
                json.dumps(data[2]),
            ]
            mock_get_redis.return_value = mock_redis
            
            result = await mget_json(["user:1", "user:2", "user:3"])
            
            assert len(result) == 3
            assert result[0] == {"user_id": 1}
            assert result[1] == {"user_id": 2}
            assert result[2] == {"user_id": 3}

    @pytest.mark.asyncio
    async def test_mget_json_partial_miss(self):
        """Test retrieving multiple keys with some misses."""
        with patch('app.cache.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.mget.return_value = [
                json.dumps({"id": 1}),
                None,
                json.dumps({"id": 3}),
            ]
            mock_get_redis.return_value = mock_redis
            
            result = await mget_json(["key:1", "key:2", "key:3"])
            
            assert len(result) == 3
            assert result[0] == {"id": 1}
            assert result[1] is None
            assert result[2] == {"id": 3}

    @pytest.mark.asyncio
    async def test_mget_json_invalid_entries(self):
        """Test batch retrieval with неверным JSON entries."""
        with patch('app.cache.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.mget.return_value = [
                json.dumps({"valid": True}),
                "not valid json",
                None,
            ]
            mock_get_redis.return_value = mock_redis
            
            result = await mget_json(["key:1", "key:2", "key:3"])
            
            assert len(result) == 3
            assert result[0] == {"valid": True}
            assert result[1] is None  # Invalid JSON becomes None
            assert result[2] is None


class TestSetOperations:
    """Test Redis set operations."""

    @pytest.mark.asyncio
    async def test_sadd(self):
        """Test adding member to set."""
        with patch('app.cache.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis
            
            await sadd("tags:user:1", "admin")
            
            mock_redis.sadd.assert_called_once_with("tags:user:1", "admin")

    @pytest.mark.asyncio
    async def test_srem(self):
        """Test removing member from set."""
        with patch('app.cache.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis
            
            await srem("tags:user:1", "admin")
            
            mock_redis.srem.assert_called_once_with("tags:user:1", "admin")

    @pytest.mark.asyncio
    async def test_smembers_empty_set(self):
        """Test getting members from empty set."""
        with patch('app.cache.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.smembers.return_value = set()
            mock_get_redis.return_value = mock_redis
            
            result = await smembers("empty:set")
            
            assert result == []

    @pytest.mark.asyncio
    async def test_smembers_with_data(self):
        """Test getting members from set with data."""
        with patch('app.cache.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.smembers.return_value = {"admin", "moderator", "user"}
            mock_get_redis.return_value = mock_redis
            
            result = await smembers("roles:set")
            
            assert isinstance(result, list)
            assert len(result) == 3
            assert "admin" in result


class TestDeleteByPrefix:
    """Test prefix-based deletion."""

    @pytest.mark.asyncio
    async def test_delete_by_prefix_single_scan(self):
        """Test deletion with single scan iteration."""
        with patch('app.cache.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.scan.return_value = (0, ["user:1", "user:2", "user:3"])
            mock_get_redis.return_value = mock_redis
            
            await delete_by_prefix("user:")
            
            mock_redis.scan.assert_called_once()
            mock_redis.delete.assert_called_once_with("user:1", "user:2", "user:3")

    @pytest.mark.asyncio
    async def test_delete_by_prefix_multiple_scans(self):
        """Test deletion with multiple scan iterations."""
        with patch('app.cache.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            # Simulate multiple scan results
            mock_redis.scan.side_effect = [
                (1, ["key:1", "key:2"]),
                (0, ["key:3"]),
            ]
            mock_get_redis.return_value = mock_redis
            
            await delete_by_prefix("key:")
            
            assert mock_redis.scan.call_count == 2
            assert mock_redis.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_delete_by_prefix_no_keys(self):
        """Test deletion when no keys match prefix."""
        with patch('app.cache.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.scan.return_value = (0, [])
            mock_get_redis.return_value = mock_redis
            
            await delete_by_prefix("nonexistent:")
            
            mock_redis.delete.assert_not_called()
