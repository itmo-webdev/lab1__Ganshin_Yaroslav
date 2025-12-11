import os
from celery import Celery
from celery.schedules import crontab
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

broker_url = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL", "redis://localhost:6379/0")
backend_url = os.getenv("CELERY_RESULT_BACKEND", broker_url)

_timezone = os.getenv("TZ", "UTC")

app = Celery(
    "news_email_worker",
    broker=broker_url,
    backend=backend_url,
    include=["app.tasks.email"],
)

app.conf.update(
    task_reject_on_worker_lost=True,
    worker_cancel_long_running_tasks_on_connection_loss=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="default",
    task_routes={
        "app.tasks.email.*": {"queue": "email"},
    },
    timezone=_timezone,
    enable_utc=False if _timezone != "UTC" else True,
    beat_schedule={
        "weekly_digest": {
            "task": "app.tasks.email.weekly_digest",
            "schedule": crontab(minute=0, hour=9, day_of_week="sun"),
            "options": {"queue": "email"},
        }
    },
)