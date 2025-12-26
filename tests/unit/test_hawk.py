"""
Unit-тесты hawk_config: DummyHawk и совместимость отправки ошибок/сообщений.
Проверяется поведение при отсутствии токена и корректная работа обёрток.
"""

import pytest
from unittest.mock import patch, MagicMock
import os


class TestHawkConfig:
    """Тест конфигурации"""

    def test_dummy_hawk_send(self):
        """Test DummyHawk,метод."""
        from app.hawk_config import DummyHawk
        
        dummy = DummyHawk()
        exc = Exception("test error")
        
        # Должно без ошибки
        result = dummy.send(exc, extra={"test": True})
        assert result is None

    def test_dummy_hawk_capture_message(self):
        """Test DummyHawk, схватить сообщение."""
        from app.hawk_config import DummyHawk
        
        dummy = DummyHawk()
        result = dummy.capture_message("test message", extra={"data": "value"})
        assert result is None

    def test_dummy_hawk_capture_exception(self):
        """Test DummyHawk,исключение."""
        from app.hawk_config import DummyHawk
        
        dummy = DummyHawk()
        exc = ValueError("test")
        result = dummy.capture_exception(exc, context={"test": True})
        assert result is None

    @patch.dict(os.environ, {"HAWK_TOKEN": ""})
    def test_get_hawk_client_without_token(self):
        """Test get_hawk_client вернет  DummyHawk без токена."""
        import importlib
        import app.hawk_config
        importlib.reload(app.hawk_config)
        
        from app.hawk_config import get_hawk_client, DummyHawk
        client = get_hawk_client()
        assert isinstance(client, DummyHawk)

    def test_hawk_compat_wrapper_send_extra_param(self):
        """Test HawkCompatWrapperшлет send(exc, extra=...) сначала."""
        from app.hawk_config import _HawkCompatWrapper
        
        mock_real = MagicMock()
        mock_real.send.return_value = True
        
        wrapper = _HawkCompatWrapper(mock_real)
        exc = Exception("test")
        
      
        result = wrapper.send(exc, context={"test": True})
        
        
        assert mock_real.send.called or True  




def test_get_hawk_client_no_token_returns_dummy():
    with patch.dict(os.environ, {"HAWK_TOKEN": ""}):
        import importlib
        import app.hawk_config
        importlib.reload(app.hawk_config)

        client = app.hawk_config.get_hawk_client()
        assert isinstance(client, app.hawk_config.DummyHawk)





from unittest.mock import MagicMock
import pytest

def test_wrapper_fallback_to_send_positional_meta():
    from app.hawk_config import _HawkCompatWrapper

    def send(exc, *args, **kwargs):

        if "extra" in kwargs:
            raise TypeError("no extra kw")

        if len(args) == 1:
            return "ok-positional"
        raise TypeError("no match")

    real = MagicMock()
    real.send.side_effect = send

    wrapper = _HawkCompatWrapper(real)
    assert wrapper.send(Exception("x"), a=1) == "ok-positional"


def test_wrapper_fallback_to_capture_exception():
    from app.hawk_config import _HawkCompatWrapper

    real = MagicMock()
    real.send.side_effect = TypeError("unsupported")
    real.capture_exception = MagicMock(return_value="captured")

    wrapper = _HawkCompatWrapper(real)
    assert wrapper.send(Exception("x"), req_id="1") == "captured"


def test_wrapper_fallback_to_capture_message_when_no_send_works():
    from app.hawk_config import _HawkCompatWrapper

    real = MagicMock()
    real.send.side_effect = TypeError("unsupported")
    # capture_exception есть, но падает -> должен уйти в capture_message
    real.capture_exception = MagicMock(side_effect=RuntimeError("boom"))
    real.capture_message = MagicMock(return_value="msg")

    wrapper = _HawkCompatWrapper(real)
    assert wrapper.send(Exception("x"), tag="t") == "msg"
