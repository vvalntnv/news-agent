from celery import Task
from pydantic import BaseModel

from application.background_jobs.payloads import MediaDownloadJobPayload
from application.background_jobs.protocols import (
    BackgroundJobEnqueuerProtocol,
    EnqueuedBackgroundJob,
)
from infrastructure.background_jobs.celery_app import celery_app


class CeleryBackgroundJobEnqueuer(BackgroundJobEnqueuerProtocol):
    def enqueue_job(self, job: Task, payload: object) -> EnqueuedBackgroundJob:
        serialized_payload = self._serialize_payload(payload)
        enqueue_result = job.apply_async(args=[serialized_payload], serializer="json")
        task_id = enqueue_result.id

        if task_id is None:
            raise RuntimeError("Celery returned an empty task id.")

        return EnqueuedBackgroundJob(task_id=task_id)

    def enqueue_media_download_job(
        self,
        payload: MediaDownloadJobPayload,
    ) -> EnqueuedBackgroundJob:
        media_download_job: Task = celery_app.tasks["background_jobs.media_download"]
        return self.enqueue_job(media_download_job, payload)

    def _serialize_payload(self, payload: object) -> object:
        if isinstance(payload, BaseModel):
            return payload.model_dump_json()

        return payload
