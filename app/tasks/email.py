import os
import json
import atexit
from datetime import datetime, timedelta
from typing import Iterable

from celery import shared_task
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import redis as redis_sync
import logging
from logging.handlers import RotatingFileHandler

from app.models import User, News

# метрики
from app.metrics import NEWS_NOTIFICATIONS_SENT

def _ensure_log_dir(path: str) -> None:
    d = os.path.dirname(path)
    if not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


_LOG_FILE = os.getenv("EMAIL_LOG_FILE", os.path.join(os.getcwd(), "logs", "email_worker.log"))
_ensure_log_dir(_LOG_FILE)
_logger = logging.getLogger("email_worker")
_logger.setLevel(logging.INFO)
if not _logger.handlers:
    _handler = RotatingFileHandler(_LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8")
    _fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    _handler.setFormatter(_fmt)
    _logger.addHandler(_handler)


def _close_handlers():
    for h in list(_logger.handlers):
        try:
            h.close()
        except Exception:
            pass


atexit.register(_close_handlers)


def _make_sync_db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    lower = url.lower()
    if "+asyncpg" in lower:
        return url.replace("+asyncpg", "+psycopg2")
    if lower.startswith("postgres://"):
        return "postgresql+psycopg2://" + url.split("://", 1)[1]
    if lower.startswith("postgresql://") and "+" not in lower:
        return "postgresql+psycopg2://" + url.split("://", 1)[1]
    return url


def _get_session():
    engine = create_engine(_make_sync_db_url(), poolclass=NullPool, future=True)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return Session()


def _get_redis():
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return redis_sync.from_url(url, decode_responses=True)


def _iter_users(session) -> Iterable[User]:
    return session.execute(select(User)).scalars().all()


def _news_by_id(session, news_id: int) -> News | None:
    return session.get(News, news_id)


def _week_key(dt: datetime) -> str:
    year, week, _ = dt.isocalendar()
    return f"{year}-W{week:02d}"


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=5, retry_backoff_max=300, retry_jitter=True, max_retries=5, name="app.tasks.email.notify_new_news")
def notify_new_news(self, news_id: int) -> None:
    r = _get_redis()
    session = _get_session()
    try:
        news = _news_by_id(session, news_id)
        if not news:
            _logger.warning(f"news_not_found id={news_id}")
            return
        users = _iter_users(session)
        for u in users:
            key = f"email:sent:news:{news.id}"
            added = r.sadd(key, str(u.id))
            if added == 0:
                continue
            payload = {
                "type": "new_news",
                "to_user_id": u.id,
                "to_email": u.email,
                "news_id": news.id,
                "title": news.title,
                "published_at": news.published_at.isoformat(),
            }
            _logger.info("send_mock %s", json.dumps(payload, ensure_ascii=False))
            # Метрика - НОВАЯ СТРОКА
            NEWS_NOTIFICATIONS_SENT.inc()
    finally:
        session.close()


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=10, retry_backoff_max=600, retry_jitter=True, max_retries=5, name="app.tasks.email.weekly_digest")
def weekly_digest(self) -> None:
    r = _get_redis()
    session = _get_session()
    try:
        now = datetime.utcnow()
        week = _week_key(now - timedelta(days=1))
        since = now - timedelta(days=7)
        news_list = session.execute(select(News).where(News.published_at >= since)).scalars().all()
        users = _iter_users(session)
        for u in users:
            key = f"email:sent:digest:{week}:{u.id}"
            if r.get(key):
                continue
            payload = {
                "type": "weekly_digest",
                "to_user_id": u.id,
                "to_email": u.email,
                "week": week,
                "news": [
                    {"id": n.id, "title": n.title, "published_at": n.published_at.isoformat()} for n in news_list
                ],
            }
            _logger.info("send_mock %s", json.dumps(payload, ensure_ascii=False))
            r.set(key, "1", ex=60 * 60 * 24 * 14)
    finally:
        session.close()
