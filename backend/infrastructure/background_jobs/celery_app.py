from celery import Celery

from core.config import CelerySettings, config


def build_celery_app(
    celery_settings: CelerySettings | None = None,
    *,
    app_name: str = "news-agent",
) -> Celery:
    selected_settings = celery_settings or config.celery

    celery_config: dict[str, object] = {
        "broker_url": selected_settings.broker_url,
        "result_backend": selected_settings.result_backend,
        "task_always_eager": selected_settings.task_always_eager,
        "task_eager_propagates": selected_settings.task_eager_propagates,
        "task_store_eager_result": selected_settings.task_store_eager_result,
        "task_ignore_result": selected_settings.task_ignore_result,
        "task_acks_late": selected_settings.task_acks_late,
        "worker_prefetch_multiplier": selected_settings.worker_prefetch_multiplier,
        "result_expires": selected_settings.result_expires_seconds,
        "task_soft_time_limit": selected_settings.task_soft_time_limit_seconds,
        "task_time_limit": selected_settings.task_time_limit_seconds,
        "task_serializer": selected_settings.task_serializer,
        "result_serializer": selected_settings.result_serializer,
        "event_serializer": selected_settings.event_serializer,
        "accept_content": list(selected_settings.accept_content),
        "result_accept_content": list(selected_settings.result_accept_content),
        "broker_connection_retry_on_startup": (
            selected_settings.broker_connection_retry_on_startup
        ),
        "imports": selected_settings.imports,
    }

    app = Celery(app_name)
    app.conf.update(celery_config)
    app.set_default()
    return app


celery_app = build_celery_app()
