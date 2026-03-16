from application.background_jobs.payloads import MediaDownloadJobPayload
from application.background_jobs.protocols import (
    BackgroundJobEnqueuerProtocol,
    EnqueuedBackgroundJob,
)
from infrastructure.background_jobs.tasks.media_download import (
    enqueue_media_download_task,
)


class CeleryBackgroundJobEnqueuer(BackgroundJobEnqueuerProtocol):
    def enqueue_media_download_job(
        self,
        payload: MediaDownloadJobPayload,
    ) -> EnqueuedBackgroundJob:
        enqueue_result = enqueue_media_download_task(payload)
        task_id = enqueue_result.id

        if task_id is None:
            raise RuntimeError("Celery returned an empty task id.")

        return EnqueuedBackgroundJob(task_id=task_id)
