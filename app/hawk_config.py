
import os
import logging

logger = logging.getLogger(__name__)

HAWK_TOKEN = os.getenv("HAWK_TOKEN", "")

class _HawkCompatWrapper:
    """
    Обёртка для Hawk.
    Реализует метод send(exc, **meta) и пытается вызвать SDK несколькими способами,
    т.к. ранее у меня были проблемы со взаимоействием с Hawk SDK.
    Цель - чтобы существующие вызовы hawk_client.send(...) в main.py не падали.
    """
    def __init__(self, real_client):
        self._client = real_client

    def send(self, exc, **meta):
        # Попытка 1
        try:
            return self._client.send(exc, extra=meta)
        except TypeError:
            pass
        except Exception as e:
            logger.exception("hawk: send(exc, extra=...) failed", exc_info=e)

        # Попытка 2
        try:
            return self._client.send(exc, meta)
        except TypeError:
            pass
        except Exception as e:
            logger.exception("hawk: send(exc, meta) failed", exc_info=e)

        # Попытка 3
        try:
            return self._client.send(exc, **meta)
        except TypeError:
            pass
        except Exception as e:
            logger.exception("hawk: send(exc, **meta) failed", exc_info=e)

        # Попытка 4
        try:
            if hasattr(self._client, "capture_exception"):
                return self._client.capture_exception(exc, **meta)
        except Exception:
            logger.exception("hawk: capture_exception failed", exc_info=True)

        try:
            if hasattr(self._client, "capture_message"):
                return self._client.capture_message(str(exc), **meta)
        except Exception:
            logger.exception("hawk: capture_message failed", exc_info=True)

        # только исключение
        try:
            return self._client.send(exc)
        except Exception:
            logger.exception("hawk: final fallback send(exc) failed — giving up", exc_info=True)
            return None


class DummyHawk:
    """Заглушка для локальной разработки / при отсутствии токена."""
    def send(self, exc, **kwargs):
        logger.info("[Hawk Stub] Exception captured: %s — meta: %s", exc, kwargs)

    def capture_message(self, message, **kwargs):
        logger.info("[Hawk Stub] Message: %s — meta: %s", message, kwargs)

    def capture_exception(self, exc, **kwargs):
        logger.info("[Hawk Stub] capture_exception: %s — meta: %s", exc, kwargs)


def get_hawk_client():
    #Возвращает обертку или заглушку ( в случае разработки, в целом, заглушку я могу потом удалить, пока использовал для проверки корректности работы 'в целом')
    if not HAWK_TOKEN:
        logger.info("HAWK_TOKEN not set — using DummyHawk")
        return DummyHawk()

    try:
        from hawk_python_sdk import Hawk
        real = Hawk(HAWK_TOKEN)
        return _HawkCompatWrapper(real)
    except Exception as e:
        logger.exception("Failed to initialize real Hawk client — using DummyHawk", exc_info=e)
        return DummyHawk()


hawk_client = get_hawk_client()
