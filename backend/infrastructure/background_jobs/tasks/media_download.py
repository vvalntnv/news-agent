import logging

from celery.result import AsyncResult
from celery import Task

from application.background_jobs.payloads import (
    MediaDownloadJobPayload,
    MediaDownloadJobResult,
)
from application.services.media_download_service import MediaDownloadService
from infrastructure.background_jobs.async_runner import AsyncRunner
from infrastructure.background_jobs.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="background_jobs.media_download",
    ignore_result=True,
    bind=True,
)
def download_media_task(self: Task, payload_json: str) -> None:
    try:
        payload = MediaDownloadJobPayload.model_validate_json(payload_json)
        media_download_service = MediaDownloadService()
        async_runner = AsyncRunner[MediaDownloadJobResult]()
        async_runner.run_awaitable_safely(
            lambda: media_download_service.download_media(payload)
        )
    except Exception as exc:
        logger.exception("Media download task failed for payload: %s", payload_json)
        raise self.retry(exc=exc, countdown=60) from exc


def enqueue_media_download_task(payload: MediaDownloadJobPayload) -> AsyncResult:
    payload_json = payload.model_dump_json()
    return download_media_task.apply_async(args=[payload_json], serializer="json")  # type: ignore
