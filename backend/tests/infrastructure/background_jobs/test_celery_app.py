from core.config import CelerySettings
from infrastructure.background_jobs.celery_app import build_celery_app


def test_build_celery_app_uses_json_serialization_and_eager_flags() -> None:
    celery_settings = CelerySettings(
        broker_url="redis://localhost:6379/9",
        task_always_eager=True,
        task_eager_propagates=True,
        imports=("infrastructure.background_jobs.tasks.media_download",),
    )

    app = build_celery_app(celery_settings=celery_settings, app_name="test-news-agent")

    assert app.conf.broker_url == "redis://localhost:6379/9"
    assert app.conf.task_always_eager is True
    assert app.conf.task_eager_propagates is True
    assert app.conf.task_serializer == "json"
    assert app.conf.result_serializer == "json"
    assert app.conf.accept_content == ["json"]
