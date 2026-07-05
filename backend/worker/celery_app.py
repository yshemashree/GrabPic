from celery import Celery

from app.config import get_settings
from app.logging_conf import configure_logging

configure_logging()
settings = get_settings()

celery_app = Celery(
    "grabpic",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["worker.tasks"],
)
celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)
