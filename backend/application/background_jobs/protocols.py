from typing import Protocol, runtime_checkable

from celery import Task
from pydantic import BaseModel, ConfigDict

from application.background_jobs.payloads import MediaDownloadJobPayload


class EnqueuedBackgroundJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str


@runtime_checkable
class BackgroundJobEnqueuerProtocol(Protocol):
    def enqueue_media_download_job(
        self,
        payload: MediaDownloadJobPayload,
    ) -> EnqueuedBackgroundJob: ...

    def enqueue_job(self, job: Task, payload: object) -> EnqueuedBackgroundJob: ...
