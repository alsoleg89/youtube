import logging

from celery import Celery
from celery.signals import worker_ready

from app.core.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "workers",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    worker_concurrency=2,
)

celery_app.autodiscover_tasks(["app.workers"])


@worker_ready.connect
def _ollama_preflight_on_worker_start(**kwargs):
    if settings.llm_provider != "local_ollama":
        return
    from app.providers.ollama_preflight import check_ollama_ready

    check_ollama_ready()
