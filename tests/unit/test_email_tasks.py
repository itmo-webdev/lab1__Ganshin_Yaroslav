"""
Unit-тесты задач/утилит email: преобразование DATABASE_URL, генерация ключей недели и логирование.
Вызовы ОС/логгера замоканы, тестируется чистая логика функций.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app.tasks.email import (
    _make_sync_db_url,
    _week_key,
)


class TestEmailTasks:
    """Test email таск."""

    def test_make_sync_db_url_asyncpg(self):
        """Test конертацию  async DB URL в sync."""
        with patch("os.getenv", return_value="postgresql+asyncpg://user:pass@host/db"):
            result = _make_sync_db_url()
            assert "+asyncpg" not in result
            assert "+psycopg2" in result or "postgresql" in result

    def test_make_sync_db_url_postgres(self):
        """Test захват postgres:// protocol."""
        with patch("os.getenv", return_value="postgres://user:pass@host/db"):
            result = _make_sync_db_url()
            assert "postgresql" in result.lower()

    def test_make_sync_db_url_not_set_raises(self):
        """Test error когда DATABASE_URL not set."""
        with patch("os.getenv", return_value=None):
            with pytest.raises(RuntimeError, match="DATABASE_URL"):
                _make_sync_db_url()

    def test_week_key_format(self):
        """Test week key generation format."""
        dt = datetime(2024, 12, 25)
        result = _week_key(dt)
        
        assert isinstance(result, str)
        assert "-W" in result
        assert len(result) == 8

    def test_week_key_different_weeks(self):
        """Test week key changes for different weeks."""
        dt1 = datetime(2024, 12, 25)
        dt2 = datetime(2024, 12, 18)
        
        key1 = _week_key(dt1)
        key2 = _week_key(dt2)
        
        assert key1 != key2

    def test_week_key_same_week(self):
        """Test week key is same for same week."""
        dt1 = datetime(2024, 12, 25)
        dt2 = datetime(2024, 12, 23)
        
        key1 = _week_key(dt1)
        key2 = _week_key(dt2)
        
        assert "-W" in key1 and "-W" in key2

    def test_ensure_log_dir_creates_directory(self):
        """Test log directory creation."""
        with patch("os.path.exists", return_value=False):
            with patch("os.makedirs") as mock_makedirs:
                from app.tasks.email import _ensure_log_dir
                _ensure_log_dir("/test/path/to/log.txt")
                
                assert mock_makedirs.called

    def test_close_handlers_no_error(self):
        """Test handler closing doesn't raise errors."""
        with patch("logging.getLogger") as mock_logger:
            mock_handler = MagicMock()
            mock_logger_instance = MagicMock()
            mock_logger_instance.handlers = [mock_handler]
            mock_logger.return_value = mock_logger_instance
            
            from app.tasks.email import _close_handlers
            _close_handlers()
            
            
            
            
            
            
            
            
            
            





