from celery.result import AsyncResult
from celery import Task

from application.background_jobs.payloads import (
    MediaDownloadJobPayload,
    MediaDownloadJobResult,
)
from application.services.media_download_service import MediaDownloadService
from infrastructure.background_jobs.async_runner import AsyncRunner
from infrastructure.background_jobs.celery_app import celery_app


@celery_app.task(
    name="background_jobs.media_download",
    ignore_result=True,
)
def download_media_task(payload_json: str) -> None:
    payload = MediaDownloadJobPayload.model_validate_json(payload_json)
    media_download_service = MediaDownloadService()
    async_runner = AsyncRunner[MediaDownloadJobResult]()
    async_runner.run_awaitable_safely(
        lambda: media_download_service.download_media(payload)
    )


def enqueue_media_download_task(payload: MediaDownloadJobPayload) -> AsyncResult:
    payload_json = payload.model_dump_json()
    return download_media_task.apply_async(args=[payload_json], serializer="json")  # type: ignore
