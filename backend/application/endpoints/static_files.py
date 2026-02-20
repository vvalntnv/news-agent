from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from core.config import config


def mount_static_files(
    app: FastAPI,
    static_root: Path | str = config.static_root,
    mount_path: str = config.static_mount_path,
) -> None:
    static_path = Path(static_root)
    static_path.mkdir(parents=True, exist_ok=True)
    (static_path / "media").mkdir(parents=True, exist_ok=True)

    has_static_route = any(
        getattr(route, "path", "") == mount_path for route in app.routes
    )
    if has_static_route:
        return

    app.mount(mount_path, StaticFiles(directory=str(static_path)), name="static")
